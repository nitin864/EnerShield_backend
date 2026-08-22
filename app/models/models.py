"""
ORM models — one Python class per DB table.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Corridor(Base):
    __tablename__ = "corridors"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    region = Column(String(120), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    current_risk_score = Column(Integer, nullable=True)
    last_scored_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    headlines = relationship("Headline", back_populates="corridor")
    risk_history = relationship("RiskHistory", back_populates="corridor")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    corridor_id = Column(Integer, ForeignKey("corridors.id"), nullable=False)
    corridor = relationship("Corridor")
    distance_km = Column(Float, nullable=True)
    cost_proxy = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Headline(Base):
    __tablename__ = "headlines"

    id = Column(Integer, primary_key=True)
    corridor_id = Column(Integer, ForeignKey("corridors.id"), nullable=False)
    corridor = relationship("Corridor", back_populates="headlines")
    title = Column(String(500), nullable=False)
    source = Column(String(100), nullable=True)
    url = Column(String(1000), nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RiskHistory(Base):
    __tablename__ = "risk_history"

    id = Column(Integer, primary_key=True)
    corridor_id = Column(Integer, ForeignKey("corridors.id"), nullable=False)
    corridor = relationship("Corridor", back_populates="risk_history")
    score = Column(Integer, nullable=False)
    confidence = Column(Float, nullable=True)
    justification = Column(Text, nullable=True)
    scored_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EnergyMetric(Base):
    __tablename__ = "energy_metrics"

    id = Column(Integer, primary_key=True)
    series_id = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)
    period = Column(String(20), nullable=False)
    value = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SanctionsSignal(Base):
    """
    Snapshot of how many OFAC-sanctioned entities are currently linked to a
    corridor's associated sanctions program (e.g. Iran-related listings for
    Hormuz). One row per corridor, overwritten (not appended) each ingestion
    run — this is a live count, not a history log.
    """
    __tablename__ = "sanctions_signals"

    id = Column(Integer, primary_key=True)
    corridor_id = Column(Integer, ForeignKey("corridors.id"), nullable=False, unique=True)
    corridor = relationship("Corridor")
    matched_keywords = Column(String(255), nullable=True)   # e.g. "IRAN"
    entity_count = Column(Integer, nullable=False, default=0)
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))