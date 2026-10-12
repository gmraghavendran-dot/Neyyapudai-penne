from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from backend.services.incident_service import list_incidents, add_incident, change_status
from backend.services.location_service import resolve_area

router = APIRouter(prefix="/api/incidents", tags=["incidents"])

class IncidentIn(BaseModel):
    incident_type: str = Field(min_length=2, max_length=120)
    severity: str = "medium"
    area_name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    source: str = "dashboard"

class StatusIn(BaseModel):
    status: str
    resolution_type: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=2000)

@router.get("")
def incidents(limit: int = Query(100, ge=1, le=500)):
    return list_incidents(limit)

@router.post("", status_code=201)
def create(payload: IncidentIn):
    try:
        area = resolve_area(payload.area_name)
        data = payload.model_dump()
        data.update({"latitude": area["latitude"], "longitude": area["longitude"], "location_label": area["area_name"]})
        data.pop("area_name", None)
        return add_incident(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc))

@router.patch("/{incident_id}/status")
def status(incident_id: int, payload: StatusIn):
    try:
        result = change_status(incident_id, payload.status, payload.resolution_type, payload.notes)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    if not result:
        raise HTTPException(404, "Incident not found")
    return result
