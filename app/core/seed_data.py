"""
Seeds the corridors table with the initial set to model (per the build guide:
pick 3-5 corridors, not the whole global network).

Usage:
    python -m app.core.seed_data
"""
from app.core.database import SessionLocal
from app.models.models import Corridor, Supplier

# Coordinates are the rough midpoint of each chokepoint/route — good enough for map pins.
CORRIDORS = [
    {"name": "Strait of Hormuz", "region": "Middle East", "latitude": 26.5, "longitude": 56.25},
    {"name": "Red Sea / Bab-el-Mandeb", "region": "Middle East / Horn of Africa", "latitude": 13.0, "longitude": 43.3},
    {"name": "Suez Canal", "region": "Egypt", "latitude": 30.5, "longitude": 32.35},
    {"name": "Strait of Malacca", "region": "Southeast Asia", "latitude": 2.5, "longitude": 101.4},
    {"name": "Cape of Good Hope", "region": "Southern Africa", "latitude": -34.35, "longitude": 18.47},
]

# Alternate suppliers/routes for the Procurement Orchestrator to rank.
# distance_km and cost_proxy are illustrative — replace with real figures
# from PPAC/EIA if time allows before demo.
SUPPLIERS = [
    {"name": "Saudi Aramco (Hormuz route)", "corridor_name": "Strait of Hormuz", "distance_km": 2100, "cost_proxy": 40},
    {"name": "UAE ADNOC (Hormuz route)", "corridor_name": "Strait of Hormuz", "distance_km": 2000, "cost_proxy": 42},
    {"name": "Nigeria Bonny Light (Cape route)", "corridor_name": "Cape of Good Hope", "distance_km": 11500, "cost_proxy": 55},
    {"name": "US Gulf Coast WTI (Cape route)", "corridor_name": "Cape of Good Hope", "distance_km": 14800, "cost_proxy": 65},
    {"name": "Russia ESPO (Malacca route)", "corridor_name": "Strait of Malacca", "distance_km": 6200, "cost_proxy": 38},
]


def seed_corridors_and_suppliers():
    db = SessionLocal()
    try:
        corridor_map = {}
        for c in CORRIDORS:
            existing = db.query(Corridor).filter_by(name=c["name"]).first()
            if existing:
                print(f"Skipping corridor (already exists): {c['name']}")
                corridor_map[c["name"]] = existing
                continue
            corridor = Corridor(**c)
            db.add(corridor)
            db.flush()  # assigns corridor.id before we need it for suppliers below
            corridor_map[c["name"]] = corridor
            print(f"Adding corridor: {c['name']}")

        for s in SUPPLIERS:
            existing = db.query(Supplier).filter_by(name=s["name"]).first()
            if existing:
                print(f"Skipping supplier (already exists): {s['name']}")
                continue
            corridor = corridor_map.get(s["corridor_name"])
            if not corridor:
                print(f"Corridor not found for supplier {s['name']}, skipping")
                continue
            supplier = Supplier(
                name=s["name"],
                corridor_id=corridor.id,
                distance_km=s["distance_km"],
                cost_proxy=s["cost_proxy"],
            )
            db.add(supplier)
            print(f"Adding supplier: {s['name']}")

        db.commit()
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_corridors_and_suppliers()
