from fastapi import APIRouter, HTTPException
from backend.services.location_service import list_areas, resolve_area

router = APIRouter(prefix="/api/locations", tags=["locations"])

@router.get("/areas")
def areas():
    return list_areas()

@router.get("/areas/{area_name}")
def area(area_name: str):
    result = resolve_area(area_name)
    if not result:
        raise HTTPException(404, "Area not found")
    return result
