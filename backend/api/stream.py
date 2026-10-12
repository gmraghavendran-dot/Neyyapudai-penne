import asyncio, json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.database.repository import operational_incidents

router = APIRouter(tags=["stream"])

@router.websocket("/ws/incidents")
async def incident_stream(websocket: WebSocket):
    await websocket.accept()
    last_signature = None
    try:
        while True:
            incidents = operational_incidents(50)
            signature = tuple((x["incident_id"], x["status"], x.get("risk_score")) for x in incidents)
            if signature != last_signature:
                await websocket.send_text(json.dumps({"type":"incidents","data":incidents}, default=str))
                last_signature = signature
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


@router.websocket("/ws/telemetry")
async def telemetry_stream(websocket: WebSocket):
    await websocket.accept()
    from backend.services.telemetry_service import get_all_active_telemetry
    try:
        while True:
            telemetry_data = get_all_active_telemetry()
            await websocket.send_text(json.dumps({"type": "telemetry", "data": telemetry_data}, default=str))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return

