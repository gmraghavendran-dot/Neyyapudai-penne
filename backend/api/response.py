from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.services.response_service import responders, dispatch_incident, response_metrics, mark_arrived, close_response

router = APIRouter(prefix="/api/response", tags=["response"])

class CloseResponseIn(BaseModel):
    outcome: str = Field(default="handled", min_length=2, max_length=100)

@router.get("/responders")
def get_responders():
    return responders()

@router.get("/metrics")
def metrics():
    return response_metrics()

@router.post("/dispatch/{incident_id}")
def dispatch_endpoint(incident_id: int):
    try:
        return dispatch_incident(incident_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc))

@router.post("/arrive/{incident_id}")
def arrive(incident_id: int):
    try:
        return mark_arrived(incident_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc))

@router.get("/telemetry")
def get_all_telemetry():
    from backend.services.telemetry_service import get_all_active_telemetry
    return get_all_active_telemetry()


@router.get("/telemetry/{incident_id}")
def get_incident_telemetry(incident_id: int):
    from backend.services.telemetry_service import get_live_telemetry
    telemetry = get_live_telemetry(incident_id)
    if not telemetry:
        raise HTTPException(404, "No active telemetry found for this incident")
    return telemetry


@router.post("/close/{incident_id}")
def close(incident_id: int, payload: CloseResponseIn):
    try:
        return close_response(incident_id, payload.outcome)
    except ValueError as exc:
        raise HTTPException(409, str(exc))

