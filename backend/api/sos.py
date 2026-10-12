from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.services.sos_service import trigger

router = APIRouter(prefix="/api/sos", tags=["sos"])

class SOSIn(BaseModel):
    area_name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    device_ref: str | None = Field(default=None, max_length=200)

@router.post("", status_code=201)
def sos(payload: SOSIn):
    try:
        return trigger(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(422, str(exc))
