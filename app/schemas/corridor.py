"""API response schemas — define the JSON shape returned to the frontend."""
from datetime import datetime
from pydantic import BaseModel


class CorridorOut(BaseModel):
    id: int
    name: str
    region: str | None
    latitude: float | None
    longitude: float | None
    current_risk_score: int | None
    last_scored_at: datetime | None

    class Config:
        from_attributes = True  # lets Pydantic read directly from SQLAlchemy objects


class HeadlineOut(BaseModel):
    id: int
    title: str
    source: str | None
    url: str | None
    published_at: datetime | None

    class Config:
        from_attributes = True


class RiskHistoryOut(BaseModel):
    id: int
    score: int
    confidence: float | None
    justification: str | None
    scored_at: datetime

    class Config:
        from_attributes = True


class ScoringRunResult(BaseModel):
    corridor: str
    score: int
    confidence: float
