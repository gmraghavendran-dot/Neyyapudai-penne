from fastapi import APIRouter, HTTPException, Query
from backend.services.mobility_service import compare_routes, compare_routes_by_area

router = APIRouter(prefix="/api/mobility", tags=["mobility"])

@router.get("/routes")
def routes(
    origin_area: str | None = Query(default=None), destination_area: str | None = Query(default=None),
    origin_lat: float | None = Query(default=None, ge=-90, le=90), origin_lng: float | None = Query(default=None, ge=-180, le=180),
    destination_lat: float | None = Query(default=None, ge=-90, le=90), destination_lng: float | None = Query(default=None, ge=-180, le=180),
):
    try:
        if origin_area and destination_area:
            return compare_routes_by_area(origin_area, destination_area)
        if None not in (origin_lat, origin_lng, destination_lat, destination_lng):
            return compare_routes(origin_lat, origin_lng, destination_lat, destination_lng)
        raise ValueError("Select both origin and destination areas")
    except ValueError as exc:
        raise HTTPException(422, str(exc))
