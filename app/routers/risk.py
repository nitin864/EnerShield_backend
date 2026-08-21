"""Risk scoring endpoints — trigger scoring runs, read trend history."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Corridor, RiskHistory
from app.schemas.corridor import RiskHistoryOut, ScoringRunResult
from app.services.risk_scoring import score_corridor, score_all_corridors

router = APIRouter(prefix="/risk-score", tags=["risk-score"])


@router.post("/run", response_model=list[ScoringRunResult])
def trigger_scoring_run(db: Session = Depends(get_db)):
    """
    Manually trigger a scoring run across all corridors (in addition to the
    scheduled job). Useful for demo purposes — score on-demand right before
    presenting, so scores are guaranteed fresh.
    """
    corridors = db.query(Corridor).all()
    results = []
    for corridor in corridors:
        result = score_corridor(db, corridor)
        results.append(ScoringRunResult(corridor=corridor.name, score=result["score"], confidence=result["confidence"]))
    db.commit()
    return results


@router.post("/run/{corridor_id}", response_model=ScoringRunResult)
def trigger_scoring_for_corridor(corridor_id: int, db: Session = Depends(get_db)):
    """Score a single corridor on demand."""
    corridor = db.query(Corridor).filter_by(id=corridor_id).first()
    if not corridor:
        raise HTTPException(status_code=404, detail="Corridor not found")

    result = score_corridor(db, corridor)
    db.commit()
    return ScoringRunResult(corridor=corridor.name, score=result["score"], confidence=result["confidence"])


@router.get("/{corridor_id}/history", response_model=list[RiskHistoryOut])
def get_risk_history(corridor_id: int, limit: int = 30, db: Session = Depends(get_db)):
    """Score history for the trend chart, most recent last (chronological order)."""
    corridor = db.query(Corridor).filter_by(id=corridor_id).first()
    if not corridor:
        raise HTTPException(status_code=404, detail="Corridor not found")

    history = (
        db.query(RiskHistory)
        .filter_by(corridor_id=corridor_id)
        .order_by(RiskHistory.scored_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(history))  # oldest -> newest, ready for a line chart
