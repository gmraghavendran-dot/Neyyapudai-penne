from typing import Any
from sqlalchemy import text
from backend.database.connection import engine


def rows(sql: str, params: dict[str, Any] | None = None) -> list[dict]:
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(r._mapping) for r in result]


def one(sql: str, params: dict[str, Any] | None = None) -> dict | None:
    result = rows(sql, params)
    return result[0] if result else None


def execute(sql: str, params: dict[str, Any] | None = None):
    with engine.begin() as conn:
        return conn.execute(text(sql), params or {})


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def operational_incidents(limit: int = 100) -> list[dict]:
    return rows("""
        SELECT i.*, r.name AS responder_name, r.responder_type
        FROM core.incidents i
        LEFT JOIN core.responders r ON r.responder_id = i.assigned_responder_id
        ORDER BY i.reported_at DESC
        LIMIT :limit
    """, {"limit": limit})


def get_incident(incident_id: int) -> dict | None:
    return one("""
        SELECT i.*, r.name AS responder_name, r.responder_type
        FROM core.incidents i
        LEFT JOIN core.responders r ON r.responder_id=i.assigned_responder_id
        WHERE i.incident_id=:id
    """, {"id": incident_id})


def create_incident(payload: dict) -> dict:
    with engine.begin() as conn:
        result = conn.execute(text("""
            INSERT INTO core.incidents
            (incident_type,severity,latitude,longitude,location_label,description,source,risk_score)
            VALUES (:incident_type,:severity,:latitude,:longitude,:location_label,:description,:source,:risk_score)
            RETURNING *
        """), payload)
        incident = dict(result.first()._mapping)
        import json
        conn.execute(text("""
            INSERT INTO core.audit_events(event_type,entity_type,entity_id,payload)
            VALUES ('incident_created','incident',:id,CAST(:payload AS JSONB))
        """), {"id": incident["incident_id"], "payload": json.dumps(payload)})
        return incident


def update_incident_status(incident_id: int, status: str) -> dict | None:
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE core.incidents
            SET status=:status,
                resolved_at=CASE WHEN :status='resolved' THEN COALESCE(resolved_at,CURRENT_TIMESTAMP) ELSE resolved_at END
            WHERE incident_id=:incident_id
            RETURNING *
        """), {"incident_id": incident_id, "status": status})
        row = result.first()
        return dict(row._mapping) if row else None


def available_responders() -> list[dict]:
    return rows("""SELECT * FROM core.responders WHERE status='available' ORDER BY responder_id""")


def all_responders() -> list[dict]:
    return rows("SELECT * FROM core.responders ORDER BY responder_id")


def overview() -> dict:
    incident = one("""
        SELECT COUNT(*) AS total_incidents,
               COUNT(*) FILTER (WHERE status IN ('open','dispatched','responding')) AS active_incidents,
               COUNT(*) FILTER (WHERE severity='critical' AND status <> 'resolved') AS critical_incidents,
               COUNT(*) FILTER (WHERE severity='high' AND status <> 'resolved') AS high_incidents,
               COUNT(*) FILTER (WHERE status='resolved') AS resolved_incidents
        FROM core.incidents
    """) or {}
    response = one("""
        SELECT COALESCE(ROUND(AVG(response_time_minutes)::numeric,1),0) AS avg_response_minutes
        FROM core.response_events WHERE response_time_minutes IS NOT NULL
    """) or {}
    registry = one("""
        SELECT COUNT(*) AS total_datasets,
               COUNT(*) FILTER (WHERE status='SUCCESS') AS successful_datasets,
               COUNT(*) FILTER (WHERE status='FAILED') AS failed_datasets,
               COALESCE(SUM(column_count) FILTER (WHERE status='SUCCESS'),0) AS total_columns
        FROM core.dataset_registry
    """) or {}
    raw_count = one("""SELECT COUNT(*) AS raw_tables FROM information_schema.tables WHERE table_schema='raw' AND table_type='BASE TABLE'""") or {}
    responders = one("""SELECT COUNT(*) FILTER (WHERE status='available') AS available_responders FROM core.responders""") or {}
    sos = one("""SELECT COUNT(*) FILTER (WHERE status='active') AS active_sos FROM core.sos_events""") or {}
    intelligence = one("""SELECT COUNT(*) AS safety_datasets, COUNT(*) FILTER (WHERE focus='women_safety') AS women_safety_datasets FROM analytics.dataset_profile WHERE safety_relevance >= 0.25""") or {}
    areas = one("""SELECT COUNT(*) AS risk_areas FROM analytics.area_risk""") or {}
    return {**incident, **response, **registry, **raw_count, **responders, **sos, **intelligence, **areas}


def audit(event_type: str, entity_type: str | None, entity_id: int | None, payload: dict | None = None):
    import json
    execute("""
        INSERT INTO core.audit_events(event_type,entity_type,entity_id,payload)
        VALUES (:event_type,:entity_type,:entity_id,CAST(:payload AS JSONB))
    """, {"event_type": event_type, "entity_type": entity_type, "entity_id": entity_id, "payload": json.dumps(payload or {})})


def dispatch(incident_id: int) -> dict:
    import math
    incident = get_incident(incident_id)
    if not incident:
        raise ValueError("Incident not found")
    if incident["status"] == "resolved":
        raise ValueError("Resolved incident cannot be dispatched")

    preferred = "women_safety" if any(k in str(incident["incident_type"]).lower() for k in ("sos", "rape", "sexual", "molest", "stalk", "harass", "kidnap", "assault")) else "police"

    def haversine(a_lat, a_lng, b_lat, b_lng):
        r = 6371.0
        p1, p2 = math.radians(a_lat), math.radians(b_lat)
        dp, dl = math.radians(b_lat-a_lat), math.radians(b_lng-a_lng)
        a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        return 2*r*math.asin(math.sqrt(max(0,min(1,a))))

    with engine.begin() as conn:
        responders = [dict(r._mapping) for r in conn.execute(text("""
            SELECT * FROM core.responders
            WHERE status='available'
            ORDER BY CASE WHEN responder_type=:preferred THEN 0 WHEN responder_type='police' THEN 1 ELSE 2 END, responder_id
            FOR UPDATE SKIP LOCKED
        """), {"preferred": preferred})]
        if not responders:
            raise ValueError("No responder is currently available")
        chosen = min(responders, key=lambda r: haversine(incident["latitude"], incident["longitude"], r["latitude"], r["longitude"]))
        distance = haversine(incident["latitude"], incident["longitude"], chosen["latitude"], chosen["longitude"])
        eta = round(max(3.0, distance/0.45 + 3), 1)
        conn.execute(text("""UPDATE core.responders SET status='dispatched',updated_at=CURRENT_TIMESTAMP WHERE responder_id=:rid"""), {"rid": chosen["responder_id"]})
        updated = conn.execute(text("""UPDATE core.incidents SET assigned_responder_id=:rid,status='dispatched' WHERE incident_id=:iid RETURNING *"""), {"rid": chosen["responder_id"], "iid": incident_id}).first()
        response = conn.execute(text("""INSERT INTO core.response_events(incident_id,responder_id,eta_minutes) VALUES (:iid,:rid,:eta) RETURNING *"""), {"iid": incident_id, "rid": chosen["responder_id"], "eta": eta}).first()
        conn.execute(text("""INSERT INTO core.audit_events(event_type,entity_type,entity_id,payload) VALUES ('responder_dispatched','incident',:id,CAST(:payload AS JSONB))"""), {"id": incident_id, "payload": '{"responder_id":'+str(chosen["responder_id"])+',"distance_km":'+str(round(distance,2))+'}'})
    
    # Initialize real-time GPS telemetry along road waypoints
    try:
        from backend.services.telemetry_service import init_dispatch_telemetry
        init_dispatch_telemetry(incident_id, chosen["responder_id"], chosen["latitude"], chosen["longitude"], incident["latitude"], incident["longitude"])
    except Exception:
        pass

    return {"incident": dict(updated._mapping), "response": dict(response._mapping), "responder": chosen, "distance_km": round(distance, 2)}
