from fastapi import APIRouter
from backend.services.safety_service import dashboard_risk, refresh

router = APIRouter(prefix="/api/safety", tags=["safety"])


@router.get("/intelligence")
def intelligence():
    return dashboard_risk()


@router.post("/refresh")
def refresh_intelligence():
    return refresh()
