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

    # TODO: query the corridor back and assert it has exactly one headline
    #   via the relationship — NOT by querying Headline directly.
    #   Hint: db_session.query(Corridor).filter_by(name="Red Sea").first()
    #   then check .headlines (the relationship from your reference model)

    # TODO: also assert headline.corridor.name == "Red Sea" — this proves
    #   the relationship works in BOTH directions (Corridor -> Headline
    #   and Headline -> Corridor)


def test_risk_history_ordering(db_session):
    """
    Simulates two scoring runs over time for one corridor — proves the
    trend-chart use case: querying history back in chronological order.
    """
    corridor = Corridor(name="Hormuz", region="Middle East")
    db_session.add(corridor)
    db_session.commit()

    # TODO: create two RiskHistory rows for this corridor with different
    #   scores (e.g. 40 and then 65), commit both.

    # TODO: query all RiskHistory rows for this corridor
    #   (db_session.query(RiskHistory).filter_by(corridor_id=corridor.id).all())
    #   and assert len(...) == 2