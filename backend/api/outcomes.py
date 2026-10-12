from fastapi import APIRouter
from backend.services.outcome_service import outcomes

router = APIRouter(prefix="/api/outcomes", tags=["outcomes"])

@router.get("")
def outcome_intelligence():
    return outcomes()
