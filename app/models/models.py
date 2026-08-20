"""
ORM models — one Python class per DB table.

Pattern to follow (see Corridor below):
1. Class inherits from Base
2. __tablename__ = the actual SQL table name (snake_case, plural)
3. id column: Integer, primary_key=True — every table needs this
4. Other columns: Column(TYPE, nullable=..., default=...)
5. ForeignKey columns point at another table's id: ForeignKey("corridors.id")
6. relationship() gives you the Python-side convenience accessor

Reference: https://docs.sqlalchemy.org/en/20/orm/quickstart.html
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


 
class Corridor(Base):
    """
    A geopolitical energy corridor (e.g. 'Strait of Hormuz', 'Red Sea / Bab-el-Mandeb').
    This is the hub table — headlines and risk scores both point back to a corridor.
    """
    __tablename__ = "corridors"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)     # "Strait of Hormuz"
    region = Column(String(120), nullable=True)                  # "Middle East"

    # For the map UI (frontend plots these as pins/lines)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Denormalized "latest score" for fast dashboard reads —
    # avoids a JOIN + ORDER BY every time the map loads.
    # The full history still lives in RiskHistory below.
    current_risk_score = Column(Integer, nullable=True)          # 0–100
    last_scored_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # relationship() is Python-side only — no new column here.
    # Lets you do: my_corridor.headlines -> list of Headline objects
    headlines = relationship("Headline", back_populates="corridor")
    risk_history = relationship("RiskHistory", back_populates="corridor")


 

class Supplier(Base):
    """
    An alternate supplier/route the Procurement Orchestrator can recommend
    instead of a disrupted corridor.
    """
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)

    name = Column(String(120), nullable=False)

    corridor_id = Column(Integer, ForeignKey("corridors.id"), nullable=False)
    corridor = relationship("Corridor")

    distance_km = Column(Float, nullable=True)

    cost_proxy = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Headline(Base):
    """
    A single news headline that fed into a corridor's risk score.
    Lets the frontend show "here's WHY this corridor is red" when clicked.
    """
    __tablename__ = "headlines"

    id = Column(Integer, primary_key=True)

    corridor_id = Column(Integer, ForeignKey("corridors.id"), nullable=False)
    corridor = relationship("Corridor", back_populates="headlines")

    title = Column(String(500), nullable=True)

    source = Column(String(100), nullable=True)

    url = Column(String(1000), nullable=True)

    published_at = Column(DateTime, nullable=True)

    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
 

class RiskHistory(Base):
    """
    One row per risk-scoring run for a corridor. This is what powers the trend chart.
    Corridor.current_risk_score is just a cached copy of the LATEST row here.
    """
    __tablename__ = "risk_history"

    id = Column(Integer, primary_key=True)

    corridor_id = Column(Integer, ForeignKey("corridors.id"), nullable=False)
    corridor = relationship("Corridor", back_populates="risk_history")

    score = Column(Integer, nullable=False)

    confidence = Column(Float, nullable=True)

    justification = Column(Text, nullable=True)

    scored_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class EnergyMetric(Base):
    """
    A single data point from an EIA time series (e.g. WTI crude spot price).
    Generic on purpose — one table handles any EIA series by series_id,
    so adding a new metric later needs no schema change.
    """
    __tablename__ = "energy_metrics"

    id = Column(Integer, primary_key=True)
    series_id = Column(String(50), nullable=False)      # e.g. "RWTC" (WTI spot price)
    description = Column(String(255), nullable=True)     # human-readable label
    period = Column(String(20), nullable=False)           # EIA's date string, e.g. "2026-08-18"
    value = Column(Float, nullable=True)                  # the actual number
    unit = Column(String(50), nullable=True)               # e.g. "$/BBL"
    fetched_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))