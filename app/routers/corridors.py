"""Corridor endpoints — the map/dashboard's primary data source."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Corridor, Headline
from app.schemas.corridor import CorridorOut, HeadlineOut

router = APIRouter(prefix="/corridors", tags=["corridors"])


@router.get("", response_model=list[CorridorOut])
def list_corridors(db: Session = Depends(get_db)):
    """All corridors with their current cached risk score — for the map."""
    return db.query(Corridor).all()


@router.get("/{corridor_id}", response_model=CorridorOut)
def get_corridor(corridor_id: int, db: Session = Depends(get_db)):
    corridor = db.query(Corridor).filter_by(id=corridor_id).first()
    if not corridor:
        raise HTTPException(status_code=404, detail="Corridor not found")
    return corridor


@router.get("/{corridor_id}/headlines", response_model=list[HeadlineOut])
def get_corridor_headlines(corridor_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """Headlines driving this corridor's score — powers the 'click to see why' panel."""
    corridor = db.query(Corridor).filter_by(id=corridor_id).first()
    if not corridor:
        raise HTTPException(status_code=404, detail="Corridor not found")

    return (
        db.query(Headline)
        .filter_by(corridor_id=corridor_id)
        .order_by(Headline.published_at.desc())
        .limit(limit)
        .all()
    )
