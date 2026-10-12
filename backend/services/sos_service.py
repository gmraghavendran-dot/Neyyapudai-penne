from backend.database.repository import create_incident, execute, get_incident, dispatch
from backend.services.location_service import resolve_area


def trigger(payload):
    area = resolve_area(payload["area_name"])
    incident_payload = {
        "incident_type": "SOS",
        "severity": "critical",
        "latitude": area["latitude"],
        "longitude": area["longitude"],
        "location_label": area["area_name"],
        "description": payload.get("description") or "Emergency SOS triggered",
        "source": "sos",
        "risk_score": 100,
    }
    incident = create_incident(incident_payload)
    execute("""
        INSERT INTO core.sos_events(incident_id,latitude,longitude,device_ref)
        VALUES (:iid,:lat,:lng,:device)
    """, {"iid":incident["incident_id"],"lat":area["latitude"],"lng":area["longitude"],"device":payload.get("device_ref")})
    try:
        from data_engineering.kafka.producers.sos_producer import send_sos
        send_sos(incident)
    except Exception:
        pass
    response = None
    try:
        response = dispatch(int(incident["incident_id"]))
    except ValueError:
        response = {"warning":"SOS recorded, but no responder is currently available."}
    
    # Broadcast to ERSS 112 Police CAD Gateway
    try:
        from backend.integrations.erss_gateway import transmit_to_police_cad
        responder_info = response.get("responder") if isinstance(response, dict) else None
        cad_packet = transmit_to_police_cad(incident, responder_info)
    except Exception:
        cad_packet = None

    return {"incident": get_incident(int(incident["incident_id"])), "response": response, "erss_cad": cad_packet}

