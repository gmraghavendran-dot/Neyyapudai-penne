import math
from backend.database.repository import rows

SEVERITY_BASE = {"low": 20.0, "medium": 40.0, "high": 65.0, "critical": 90.0}
WOMEN_INCIDENT_WORDS = ("rape", "sexual", "molest", "stalk", "harass", "kidnap", "abduct", "dowry", "domestic", "assault", "sos")


def _haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(max(0, min(1, a))))


def point_context(latitude: float, longitude: float, radius_km: float = 3.0) -> dict:
    incidents = rows("""
        SELECT incident_id,severity,incident_type,risk_score,latitude,longitude,reported_at
        FROM core.incidents
        WHERE reported_at >= CURRENT_TIMESTAMP - INTERVAL '180 days'
        ORDER BY reported_at DESC LIMIT 5000
    """)
    nearby = [r for r in incidents if _haversine(latitude, longitude, float(r["latitude"]), float(r["longitude"])) <= radius_km]
    density = min(100.0, len(nearby) * 12.0)
    severity = {"low": 20, "medium": 45, "high": 70, "critical": 95}
    sev = sum(severity.get(str(r["severity"]).lower(), 45) for r in nearby) / max(1, len(nearby)) if nearby else 0
    women_share = sum(any(k in str(r["incident_type"]).lower() for k in WOMEN_INCIDENT_WORDS) for r in nearby) / max(1, len(nearby)) if nearby else 0
    historical = rows("""SELECT COALESCE(AVG(risk_score),40) AS risk FROM analytics.area_risk""")[0]["risk"] or 40
    hour = rows("""SELECT risk_score FROM analytics.time_risk WHERE hour=EXTRACT(HOUR FROM CURRENT_TIMESTAMP)::INTEGER""")
    time_risk = float(hour[0]["risk_score"]) if hour else 40.0
    contextual = 0.30*float(historical) + 0.30*time_risk + 0.25*density + 0.15*sev
    return {"historical_context": round(float(historical),1), "time_risk": round(time_risk,1), "nearby_incidents": len(nearby), "incident_density": round(density,1), "women_incident_share": round(women_share,2), "context_risk": round(min(100,max(0,contextual)),1)}


def calculate_incident_risk(payload: dict) -> float:
    base = SEVERITY_BASE.get(str(payload.get("severity", "medium")).lower(), 40.0)
    incident_type = str(payload.get("incident_type", "")).lower()
    women_bonus = 12 if any(k in incident_type for k in WOMEN_INCIDENT_WORDS) else 0
    if str(payload.get("source", "")).lower() == "sos":
        base = max(base, 90)
    context = point_context(float(payload["latitude"]), float(payload["longitude"]))
    score = 0.55*min(100, base + women_bonus) + 0.45*context["context_risk"]
    return round(min(100, max(0, score)), 1)
