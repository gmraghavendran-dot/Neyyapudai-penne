import time
import math
from typing import Any
from backend.database.repository import rows, one, execute
from backend.services.osrm_routing_service import calculate_road_routes, generate_fallback_waypoints, haversine

# Active telemetry trackers in-memory
_active_telemetry: dict[int, dict[str, Any]] = {}


def init_dispatch_telemetry(incident_id: int, responder_id: int, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float):
    """Initializes live vehicle telemetry tracking along road waypoints for a dispatched responder."""
    routes = calculate_road_routes(origin_lat, origin_lng, dest_lat, dest_lng)
    chosen_route = routes[0] # Direct/Emergency path
    waypoints = chosen_route.get("polyline") or generate_fallback_waypoints(origin_lat, origin_lng, dest_lat, dest_lng)
    
    total_dist_km = chosen_route["distance_km"]
    initial_eta = chosen_route["driving_time_mins"]
    
    _active_telemetry[incident_id] = {
        "incident_id": incident_id,
        "responder_id": responder_id,
        "start_time": time.time(),
        "total_distance_km": total_dist_km,
        "initial_eta_mins": initial_eta,
        "waypoints": waypoints,
        "origin": [origin_lat, origin_lng],
        "destination": [dest_lat, dest_lng],
        "speed_kmh": 44.5,
        "heading_deg": 124,
        "battery_pct": 94,
        "status": "in_transit",
        "acknowledged": True,
        "escalated": False
    }


def get_live_telemetry(incident_id: int) -> dict[str, Any] | None:
    """Returns dynamic current location, progress, heading, and updated road ETA for a dispatched responder."""
    tracker = _active_telemetry.get(incident_id)
    if not tracker:
        # Check database if there is an active dispatch
        disp = one("""
            SELECT re.*, r.latitude AS r_lat, r.longitude AS r_lng, r.name AS r_name, r.responder_type,
                   i.latitude AS i_lat, i.longitude AS i_lng, i.status AS inc_status
            FROM core.response_events re
            JOIN core.responders r ON r.responder_id = re.responder_id
            JOIN core.incidents i ON i.incident_id = re.incident_id
            WHERE re.incident_id = :id AND re.arrived_at IS NULL
            ORDER BY re.response_id DESC LIMIT 1
        """, {"id": incident_id})
        
        if disp and disp.get("r_lat") and disp.get("i_lat"):
            init_dispatch_telemetry(incident_id, disp["responder_id"], disp["r_lat"], disp["r_lng"], disp["i_lat"], disp["i_lng"])
            tracker = _active_telemetry.get(incident_id)
        else:
            return None

    waypoints = tracker["waypoints"]
    if not waypoints:
        return None

    elapsed_seconds = time.time() - tracker["start_time"]
    # Simulated transit speed: full journey completes in ~60-90 seconds for crisp demo feedback
    simulated_duration = max(30.0, tracker["initial_eta_mins"] * 10.0)
    progress_ratio = min(1.0, elapsed_seconds / simulated_duration)
    
    # Calculate current waypoint index
    total_points = len(waypoints)
    current_index = int(progress_ratio * (total_points - 1))
    next_index = min(total_points - 1, current_index + 1)
    
    current_lat, current_lng = waypoints[current_index]
    next_lat, next_lng = waypoints[next_index]
    
    # Calculate heading
    dy = next_lat - current_lat
    dx = (next_lng - current_lng) * math.cos(math.radians(current_lat))
    heading = (math.degrees(math.atan2(dx, dy)) + 360) % 360 if (dx != 0 or dy != 0) else tracker["heading_deg"]
    
    remaining_ratio = 1.0 - progress_ratio
    remaining_dist_km = round(tracker["total_distance_km"] * remaining_ratio, 2)
    remaining_eta_mins = round(max(0.1, tracker["initial_eta_mins"] * remaining_ratio), 1)
    
    # Speed fluctuates realistically
    current_speed = round(42.0 + math.sin(elapsed_seconds) * 6.0, 1) if remaining_ratio > 0.02 else 0.0
    
    # Update responder GPS in DB if moved
    execute("""
        UPDATE core.responders
        SET latitude = :lat, longitude = :lng, updated_at = CURRENT_TIMESTAMP
        WHERE responder_id = :rid
    """, {"lat": current_lat, "lng": current_lng, "rid": tracker["responder_id"]})

    status_desc = "arrived" if progress_ratio >= 0.99 else "in_transit"
    if status_desc == "arrived":
        tracker["status"] = "arrived"

    return {
        "incident_id": incident_id,
        "responder_id": tracker["responder_id"],
        "current_position": [current_lat, current_lng],
        "destination": tracker["destination"],
        "waypoints": waypoints,
        "progress_percentage": round(progress_ratio * 100, 1),
        "distance_remaining_km": remaining_dist_km,
        "eta_minutes": remaining_eta_mins,
        "speed_kmh": current_speed,
        "heading_degrees": round(heading, 1),
        "battery_level_pct": max(80, tracker["battery_pct"] - int(elapsed_seconds / 20)),
        "telemetry_status": status_desc,
        "is_escalated": tracker.get("escalated", False)
    }


def get_all_active_telemetry() -> list[dict[str, Any]]:
    """Returns telemetry for all currently active dispatches."""
    active_incidents = rows("""
        SELECT DISTINCT incident_id FROM core.response_events WHERE arrived_at IS NULL
    """)
    results = []
    for row in active_incidents:
        t = get_live_telemetry(row["incident_id"])
        if t:
            results.append(t)
    return results
