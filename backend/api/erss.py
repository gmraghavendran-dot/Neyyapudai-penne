from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.integrations.erss_gateway import get_cad_stream_logs, trigger_escalation, get_escalation_status, transmit_to_police_cad
from backend.database.repository import get_incident

router = APIRouter(prefix="/api/erss", tags=["erss_112_cad"])


class EscalateRequest(BaseModel):
    reason: str = Field(default="SLA response threshold exceeded", min_length=2, max_length=200)


@router.get("/status")
def erss_gateway_status():
    return {
        "gateway_status": "ONLINE",
        "psap_node": "PSAP-TN-CHENNAI-COMMISSIONERATE",
        "protocol": "ERSS_CAD_v2.4_IND / DIAL 112",
        "encryption": "TLS_AES_256_GCM",
        "latency_ms": 14.2,
        "cad_queue_depth": 0,
        "auto_escalation_enabled": True
    }


@router.get("/cad-stream")
def get_cad_stream():
    return get_cad_stream_logs()


@router.post("/transmit/{incident_id}")
def transmit_cad_endpoint(incident_id: int):
    inc = get_incident(incident_id)
    if not inc:
        raise HTTPException(404, "Incident not found")
    packet = transmit_to_police_cad(inc)
    return packet


@router.post("/escalate/{incident_id}")
def escalate_incident_endpoint(incident_id: int, payload: EscalateRequest):
    try:
        return trigger_escalation(incident_id, payload.reason)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@router.get("/escalate/{incident_id}")
def get_escalation(incident_id: int):
    status = get_escalation_status(incident_id)
    if not status:
        return {"incident_id": incident_id, "escalated": False}
    return status
