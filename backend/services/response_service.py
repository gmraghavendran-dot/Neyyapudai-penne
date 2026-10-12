import math
from backend.database.repository import available_responders, all_responders, dispatch, rows, execute, one, get_incident


def responders():
    return all_responders()


def dispatch_incident(incident_id: int):
    return dispatch(incident_id)


def mark_arrived(incident_id: int):
    response = one("""SELECT * FROM core.response_events WHERE incident_id=:id AND arrived_at IS NULL ORDER BY response_id DESC LIMIT 1""", {"id": incident_id})
    if not response:
        raise ValueError("No active dispatch found for this incident")
    result = one("""UPDATE core.response_events SET arrived_at=CURRENT_TIMESTAMP, response_time_minutes=EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP-dispatched_at))/60.0 WHERE response_id=:id RETURNING *""", {"id": response["response_id"]})
    execute("""UPDATE core.incidents SET status='responding' WHERE incident_id=:id""", {"id": incident_id})
    return {"incident": get_incident(incident_id), "response": result}


def close_response(incident_id: int, outcome: str = "handled"):
    response = one("""SELECT * FROM core.response_events WHERE incident_id=:id ORDER BY response_id DESC LIMIT 1""", {"id": incident_id})
    if not response:
        raise ValueError("No response record found")
    result = one("""UPDATE core.response_events SET closed_at=CURRENT_TIMESTAMP,outcome=:outcome WHERE response_id=:id RETURNING *""", {"id": response["response_id"], "outcome": outcome})
    if response["responder_id"]:
        execute("""UPDATE core.responders SET status='available',updated_at=CURRENT_TIMESTAMP WHERE responder_id=:rid""", {"rid": response["responder_id"]})
    return {"incident": get_incident(incident_id), "response": result}


def response_metrics():
    return rows("""
        SELECT COUNT(*) AS total_dispatches,
               COALESCE(ROUND(AVG(eta_minutes)::numeric,1),0) AS avg_eta_minutes,
               COALESCE(ROUND(AVG(response_time_minutes)::numeric,1),0) AS avg_response_minutes,
               COUNT(*) FILTER (WHERE response_time_minutes <= 10) AS within_10_minutes,
               COUNT(*) FILTER (WHERE arrived_at IS NOT NULL) AS arrivals,
               COUNT(*) FILTER (WHERE closed_at IS NOT NULL) AS closed_responses
        FROM core.response_events
    """)[0]
