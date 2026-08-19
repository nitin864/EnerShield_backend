"""
Seeds the corridors table with the initial set to model (per the build guide:
pick 3-5 corridors, not the whole global network).

Usage:
    python -m app.core.seed_data
"""
from app.core.database import SessionLocal
from app.models.models import Corridor

# Coordinates are the rough midpoint of each chokepoint/route — good enough for map pins.
CORRIDORS = [
    {"name": "Strait of Hormuz", "region": "Middle East", "latitude": 26.5, "longitude": 56.25},
    {"name": "Red Sea / Bab-el-Mandeb", "region": "Middle East / Horn of Africa", "latitude": 13.0, "longitude": 43.3},
    {"name": "Suez Canal", "region": "Egypt", "latitude": 30.5, "longitude": 32.35},
    {"name": "Strait of Malacca", "region": "Southeast Asia", "latitude": 2.5, "longitude": 101.4},
    {"name": "Cape of Good Hope", "region": "Southern Africa", "latitude": -34.35, "longitude": 18.47},
]


def seed_corridors():
    db = SessionLocal()
    try:
        for c in CORRIDORS:
            # Idempotency check — same principle you'll use for headlines next.
            # Without this, re-running the script would try to insert duplicates
            # and fail on the unique constraint on `name`.
            existing = db.query(Corridor).filter_by(name=c["name"]).first()
            if existing:
                print(f"Skipping (already exists): {c['name']}")
                continue

            corridor = Corridor(**c)
            db.add(corridor)
            print(f"Adding: {c['name']}")

        db.commit()
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_corridors()