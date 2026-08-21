"""
Pulls WTI crude oil spot price (series RWTC) from EIA's v2 API and saves
new data points into the energy_metrics table.

EIA v2 docs: https://www.eia.gov/opendata/documentation.php
"""
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import EnergyMetric

EIA_URL = "https://api.eia.gov/v2/petroleum/pri/spt/data/"

SERIES_ID = "RWTC"
SERIES_DESCRIPTION = "WTI Crude Oil Spot Price, Cushing OK ($/BBL)"


def fetch_eia_series(series_id: str = SERIES_ID, length: int = 5) -> list[dict]:
    """
    Calls EIA's v2 petroleum spot price endpoint.
    Returns a list of raw data-point dicts, each shaped roughly like:
        {"period": "2026-08-18", "series": "RWTC", "value": "78.42", "units": "$/BBL", ...}
    """
    params = {
        "api_key": settings.eia_api_key,
        "frequency": "daily",
        "data[0]": "value",
        "facets[series][]": series_id,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": length,
    }
    try:
        response = httpx.get(EIA_URL, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        return data.get("response", {}).get("data", [])
    except httpx.HTTPError as e:
        print(f"EIA request failed for series '{series_id}': {e}")
        return []


def save_metric_if_new(db, series_id: str, description: str, point: dict) -> bool:
    """
    Given one raw EIA data point dict, save it as an EnergyMetric row IF
    a row with this series_id + period doesn't already exist.
    Returns True if a new row was inserted.

    point dict has: point["period"] (date string), point["value"] (string
    number, may need float() conversion), point.get("units") (string).

    YOUR TURN — no line-by-line this time. Plan:
    1. Query EnergyMetric filtered by series_id AND period — does a row
       already exist for this exact date?
    2. If yes, return False.
    3. If no, create a new EnergyMetric with series_id, description,
       period=point["period"], value=float(point["value"]),
       unit=point.get("units"), fetched_at=now.
    4. db.add() it, return True.

    Same shape as save_headline_if_new — just different fields.
    """
    pass  # <- your implementation


def ingest_eia_data():
    """Entrypoint — fetches latest WTI price points, saves new ones."""
    db = SessionLocal()
    try:
        points = fetch_eia_series()
        new_count = 0
        for point in points:
            if save_metric_if_new(db, SERIES_ID, SERIES_DESCRIPTION, point):
                new_count += 1
        db.commit()
        print(f"EIA ingestion: {new_count} new data points (of {len(points)} fetched)")
    finally:
        db.close()


if __name__ == "__main__":
    ingest_eia_data()
