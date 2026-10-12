from backend.database.repository import create_incident, operational_incidents, update_incident_status, get_incident, execute, one, audit
from backend.services.risk_service import calculate_incident_risk

VALID_STATUSES = {"open", "dispatched", "responding", "resolved", "cancelled"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def list_incidents(limit=100):
    return operational_incidents(limit)


def add_incident(payload):
    payload = dict(payload)
    payload["severity"] = str(payload.get("severity", "medium")).lower()
    if payload["severity"] not in VALID_SEVERITIES:
        raise ValueError("Invalid severity")
    payload["risk_score"] = calculate_incident_risk(payload)
    incident = create_incident(payload)
    try:
        from data_engineering.kafka.producers.incident_producer import send_incident
        send_incident(incident)
    except Exception:
        pass
    return get_incident(int(incident["incident_id"]))


def change_status(incident_id, status, resolution_type=None, notes=None):
    status = str(status).lower()
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status. Use one of: {', '.join(sorted(VALID_STATUSES))}")
    incident = get_incident(incident_id)
    if not incident:
        return None
    updated = update_incident_status(incident_id, status)
    if status == "resolved":
        response = one("""SELECT * FROM core.response_events WHERE incident_id=:id ORDER BY response_id DESC LIMIT 1""", {"id": incident_id})
        response_time = float(response["response_time_minutes"]) if response and response["response_time_minutes"] is not None else None
        score = 60.0
        if response_time is not None:
            score += max(-20.0, 25.0 - response_time*1.5)
        if incident["severity"] == "critical": score += 10
        score = round(max(0, min(100, score)), 1)
        execute("""
            INSERT INTO core.outcome_events(incident_id,resolution_type,resolved_at,effectiveness_score,notes)
            VALUES (:id,:rtype,CURRENT_TIMESTAMP,:score,:notes)
        """, {"id": incident_id, "rtype": resolution_type or "resolved", "score": score, "notes": notes})
        execute("""UPDATE core.sos_events SET status='resolved' WHERE incident_id=:id AND status='active'""", {"id": incident_id})
        if response and response["responder_id"]:
            execute("""UPDATE core.responders SET status='available',updated_at=CURRENT_TIMESTAMP WHERE responder_id=:rid""", {"rid": response["responder_id"]})
        audit("incident_resolved", "incident", incident_id, {"resolution_type": resolution_type, "effectiveness_score": score})
    else:
        audit("incident_status_changed", "incident", incident_id, {"status": status})
    return get_incident(incident_id)
