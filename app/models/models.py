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

   cost_proxy = column(Float, nullable=True)

   created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Headline(Base):
    """
    A single news headline that fed into a corridor's risk score.
    Lets the frontend show "here's WHY this corridor is red" when clicked.
    """
    __tablename__ = "headlines"

    id = Column(Integer, primary_key=True)

    # TODO: corridor_id — ForeignKey to corridors.id (this headline is ABOUT which corridor)
    # TODO: corridor — relationship("Corridor", back_populates="headlines")
    #   Note: back_populates must match the name you used in Corridor.headlines above

    # TODO: title — the headline text itself. Headlines can be long — consider String(500) or Text

    # TODO: source — e.g. "Reuters", "GDELT" (String, shortish)

    # TODO: url — link to the original article (String, longer — urls can be long)

    # TODO: published_at — when the article was published (DateTime, nullable — not all sources give this cleanly)

    # TODO: fetched_at — when YOUR ingestion job pulled it (default=lambda: datetime.now(timezone.utc))


class RiskHistory(Base):
    """
    One row per risk-scoring run for a corridor. This is what powers the trend chart.
    Corridor.current_risk_score is just a cached copy of the LATEST row here.
    """
    __tablename__ = "risk_history"

    id = Column(Integer, primary_key=True)

    # TODO: corridor_id — ForeignKey to corridors.id
    # TODO: corridor — relationship("Corridor", back_populates="risk_history")

    # TODO: score — the 0-100 disruption probability (Integer)

    # TODO: confidence — how confident was the LLM in this score? (Float, e.g. 0.0-1.0)

    # TODO: justification — the LLM's reasoning text for this score (Text — this can be long, Text has no length limit unlike String)

    # TODO: scored_at — when this scoring run happened (default=lambda: datetime.now(timezone.utc))