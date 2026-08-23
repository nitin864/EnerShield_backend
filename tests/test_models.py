 """
Tests for ORM models. Uses an in-memory SQLite DB — fast, isolated,
never touches your real Supabase data.

Run with:
    pytest tests/test_models.py -v
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.core.database import Base
from app.models.models import Corridor, Headline, RiskHistory, Supplier


@pytest.fixture
def db_session():
    """
    Creates a fresh in-memory SQLite DB for each test function, builds
    all tables, yields a session, then throws it away. This is why tests
    can run in any order and never interfere with each other.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_corridor(db_session):
    """Sanity check: can we insert and read back a single row?"""
    corridor = Corridor(name="Strait of Hormuz", region="Middle East")
    db_session.add(corridor)
    db_session.commit()

    result = db_session.query(Corridor).filter_by(name="Strait of Hormuz").first()
    assert result is not None
    assert result.region == "Middle East"


def test_corridor_headline_relationship(db_session):
    """
    This is the important one: proves the FK + relationship actually
    links the two tables, not just that both tables independently work.
    """
    corridor = Corridor(name="Red Sea", region="Middle East")
    db_session.add(corridor)
    db_session.commit()   # commit first so corridor.id exists

    headline = Headline(
        corridor_id=corridor.id,
        title="Houthi attacks disrupt Red Sea shipping",
        source="Reuters",
    )
    db_session.add(headline)
    db_session.commit()

    # Query the corridor back and assert it has exactly one headline
    # via the relationship — NOT by querying Headline directly.
    result = db_session.query(Corridor).filter_by(name="Red Sea").first()
    assert result is not None
    assert len(result.headlines) == 1
    assert result.headlines[0].title == "Houthi attacks disrupt Red Sea shipping"

    # Also assert headline.corridor.name == "Red Sea" — this proves the
    # relationship works in BOTH directions (Corridor -> Headline and
    # Headline -> Corridor).
    assert headline.corridor is not None
    assert headline.corridor.name == "Red Sea"


def test_risk_history_ordering(db_session):
    """
    Simulates two scoring runs over time for one corridor — proves the
    trend-chart use case: querying history back in chronological order.
    """
    corridor = Corridor(name="Hormuz", region="Middle East")
    db_session.add(corridor)
    db_session.commit()

    # Create two RiskHistory rows for this corridor with different scores,
    # committing each separately so they mirror two real scoring runs
    # happening one after another.
    first_score = RiskHistory(
        corridor_id=corridor.id,
        score=40,
        confidence=0.6,
        justification="Initial baseline read on limited headline volume.",
    )
    db_session.add(first_score)
    db_session.commit()

    second_score = RiskHistory(
        corridor_id=corridor.id,
        score=65,
        confidence=0.8,
        justification="Escalation reported in follow-up headlines.",
    )
    db_session.add(second_score)
    db_session.commit()

    # Query all RiskHistory rows for this corridor and confirm both were saved.
    history = (
        db_session.query(RiskHistory)
        .filter_by(corridor_id=corridor.id)
        .order_by(RiskHistory.scored_at.asc())
        .all()
    )
    assert len(history) == 2
    assert history[0].score == 40
    assert history[1].score == 65


def test_corridor_supplier_relationship(db_session):
    """
    Suppliers reference a corridor via corridor_id — confirm the FK holds
    and that we can look a supplier's corridor back up.
    """
    corridor = Corridor(name="Strait of Malacca", region="Southeast Asia")
    db_session.add(corridor)
    db_session.commit()

    supplier = Supplier(
        name="Russia ESPO (Malacca route)",
        corridor_id=corridor.id,
        distance_km=6200,
        cost_proxy=38,
    )
    db_session.add(supplier)
    db_session.commit()

    result = db_session.query(Supplier).filter_by(name="Russia ESPO (Malacca route)").first()
    assert result is not None
    assert result.corridor.name == "Strait of Malacca"
