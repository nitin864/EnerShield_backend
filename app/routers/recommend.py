"""Procurement recommendation endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.procurement_orchestrator import recommend_suppliers

router = APIRouter(prefix="/recommend", tags=["recommend"])


@router.get("")
def get_recommendations(db: Session = Depends(get_db)):
    """Ranked alternate suppliers/routes with LLM reasoning for the top 3."""
    return recommend_suppliers(db)
