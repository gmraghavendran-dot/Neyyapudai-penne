import math
from backend.database.repository import execute, rows
from backend.services.risk_service import point_context


def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(max(0, min(1, a))))


def compare_routes(origin_lat, origin_lng, destination_lat, destination_lng):
    from backend.services.osrm_routing_service import calculate_road_routes
    start = point_context(origin_lat, origin_lng)
    end = point_context(destination_lat, destination_lng)
    base = (start["context_risk"] + end["context_risk"]) / 2
    incident_pressure = min(100, (start["nearby_incidents"] + end["nearby_incidents"]) * 8)
    context_risk = min(100, 0.75 * base + 0.25 * incident_pressure)

    candidates = calculate_road_routes(origin_lat, origin_lng, destination_lat, destination_lng)
    routes = []
    for r in candidates:
        risk = min(100, max(0, context_risk + r.get("risk_delta", 0)))
        routes.append({
            **r,
            "risk_score": round(risk, 1),
            "context_source": "OSRM Road Network + NCRB Historical & Live Risk"
        })
    best = min(routes, key=lambda x: (x["risk_score"] * 0.65 + x["distance_km"] * 5))
    for r in routes:
        r["recommended"] = (r["route_name"] == best["route_name"])
    
    execute("""
        INSERT INTO core.mobility_checks
        (origin_lat,origin_lng,destination_lat,destination_lng,route_name,distance_km,risk_score,lighting_score,transport_score,context_source)
        VALUES (:ol,:og,:dl,:dg,:name,:distance,:risk,:light,:transport,:source)
    """, [{"ol":origin_lat,"og":origin_lng,"dl":destination_lat,"dg":destination_lng,"name":r["route_name"],"distance":r["distance_km"],"risk":r["risk_score"],"light":r["lighting_score"],"transport":r["transport_score"],"source":r["context_source"]} for r in routes])
    return routes


def compare_routes_by_area(origin_area: str, destination_area: str):
    from backend.services.location_service import resolve_area
    origin = resolve_area(origin_area)
    destination = resolve_area(destination_area)
    routes = compare_routes(origin["latitude"], origin["longitude"], destination["latitude"], destination["longitude"])
    for route in routes:
        route["origin_area"] = origin["area_name"]
        route["destination_area"] = destination["area_name"]
    return routes
