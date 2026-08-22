"""
Pulls the free public OFAC Specially Designated Nationals (SDN) list and
counts how many listed entities are tied to each corridor's associated
sanctions program — e.g. Iran-program entities for the Strait of Hormuz.

This is a coarse heuristic signal (keyword match on the Program field),
not entity-level geolocation — it's meant to feed risk scoring as one more
real data point, not to be a precise sanctions database.

OFAC SDN CSV: https://www.treasury.gov/ofac/downloads/sdn.csv (no API key, public)
"""
import csv
import io

import httpx

from app.core.database import SessionLocal
from app.models.models import Corridor, SanctionsSignal

SDN_CSV_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"

# Heuristic mapping: which OFAC sanctions program keywords are relevant to
# each corridor's real-world geopolitical exposure. Corridors not listed
# here get a count of 0 — that's an honest "no direct program mapped yet,"
# not a missing feature.
CORRIDOR_SANCTIONS_KEYWORDS = {
    "Strait of Hormuz": ["IRAN"],
    "Red Sea / Bab-el-Mandeb": ["YEMEN", "HOUTHI"],
    "Cape of Good Hope": ["RUSSIA"],
}

# The SDN.CSV file has no header row. These are the 12 columns in order.
SDN_COLUMNS = [
    "ent_num", "sdn_name", "sdn_type", "program", "title",
    "call_sign", "vess_type", "tonnage", "grt", "vess_flag",
    "vess_owner", "remarks",
]


def fetch_sdn_entries() -> list[dict]:
    """
    Downloads and parses the SDN CSV. Returns a list of row dicts.
    Returns an empty list on any failure — sanctions data is a bonus
    signal, not critical path, so a failed download should never crash
    the rest of the ingestion run.
    """
    try:
        response = httpx.get(SDN_CSV_URL, timeout=20.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as e:
        print(f"OFAC SDN list request failed: {e}")
        return []

    entries = []
    reader = csv.reader(io.StringIO(response.text))
    for row in reader:
        if len(row) < 4:
            continue
        entries.append(dict(zip(SDN_COLUMNS, row)))
    return entries


def count_matches(entries: list[dict], keywords: list[str]) -> int:
    """Counts SDN entries whose Program field mentions any of the given keywords."""
    count = 0
    for entry in entries:
        program = (entry.get("program") or "").upper()
        if any(keyword in program for keyword in keywords):
            count += 1
    return count


def upsert_signal(db, corridor: Corridor, keywords: list[str], count: int):
    """
    One row per corridor — update in place if it exists, insert if not.
    This is a snapshot (current count), not an append-only log like
    headlines, so upsert is the right pattern here, not insert-if-new.
    """
    existing = db.query(SanctionsSignal).filter_by(corridor_id=corridor.id).first()
    if existing:
        existing.matched_keywords = ", ".join(keywords) if keywords else None
        existing.entity_count = count
    else:
        db.add(SanctionsSignal(
            corridor_id=corridor.id,
            matched_keywords=", ".join(keywords) if keywords else None,
            entity_count=count,
        ))


def ingest_sanctions_data():
    """Entrypoint — fetches SDN list once, counts matches per corridor, saves."""
    db = SessionLocal()
    try:
        entries = fetch_sdn_entries()
        if not entries:
            print("OFAC ingestion: no entries fetched, skipping this run.")
            return

        corridors = db.query(Corridor).all()
        for corridor in corridors:
            keywords = CORRIDOR_SANCTIONS_KEYWORDS.get(corridor.name, [])
            count = count_matches(entries, keywords) if keywords else 0
            upsert_signal(db, corridor, keywords, count)
            print(f"{corridor.name}: {count} sanctioned entities matched ({keywords or 'no mapping'})")

        db.commit()
        print(f"OFAC ingestion complete. {len(entries)} total SDN entries scanned.")
    finally:
        db.close()


if __name__ == "__main__":
    ingest_sanctions_data()