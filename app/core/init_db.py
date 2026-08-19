"""
Run this once (and again any time you add/change a model) to sync your
Supabase DB schema with what's defined in app/models/models.py.

Usage:
    python -m app.core.init_db
"""
from app.core.database import Base, engine
# Import every model module here — SQLAlchemy only knows about a table
# if the class has been imported somewhere, since that's what registers
# it onto Base.metadata.
from app.models import models  # noqa: F401


def init_db():
    print("Creating tables (skips any that already exist)...")
    Base.metadata.create_all(bind=engine)
    print("Tables created:", list(Base.metadata.tables.keys()))


if __name__ == "__main__":
    init_db()