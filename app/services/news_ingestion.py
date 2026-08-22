"""
Pulls recent headlines from NewsAPI.org for each corridor and saves new
ones (skipping duplicates) into the headlines table.

NewsAPI docs: https://newsapi.org/docs/endpoints/everything
"""
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import Corridor, Headline

NEWSAPI_URL = "https://newsapi.org/v2/everything"

# Each corridor needs search terms that actually surface relevant news.
# "Strait of Hormuz" alone works well; broader corridors need a few OR'd terms.
CORRIDOR_SEARCH_TERMS = {
    "Strait of Hormuz": "Strait of Hormuz OR Hormuz tanker",
    "Red Sea / Bab-el-Mandeb": "Red Sea shipping OR Houthi ship attack",
    "Suez Canal": "Suez Canal",
    "Strait of Malacca": "Strait of Malacca OR Malacca shipping",
    "Cape of Good Hope": "Cape of Good Hope shipping route",
}


def fetch_headlines_for_query(query: str, page_size: int = 10) -> list[dict]:
    """
    Calls NewsAPI's /everything endpoint for a search query.
    Returns a list of raw article dicts as NewsAPI provides them.
    """
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": settings.newsapi_key,
    }
    try:
        response = httpx.get(NEWSAPI_URL, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
    except httpx.HTTPError as e:
        # A failed API call should never crash the whole ingestion run —
        # log it and move on to the next corridor. This is the "external
        # API fails during demo" risk from the build guide, handled here
        # rather than left for later.
        print(f"NewsAPI request failed for query '{query}': {e}")
        return []


def save_headline_if_new(db, corridor: Corridor, article: dict) -> bool:
    """
    Given one raw NewsAPI article dict and the Corridor it belongs to,
    save it as a Headline row IF a headline with this url doesn't already
    exist for this corridor. Returns True if a new row was inserted.

    article dict shape (NewsAPI's format), what you have available:
        article["title"]        -> str
        article["url"]          -> str
        article["source"]["name"] -> str
        article["publishedAt"]  -> str, ISO format e.g. "2026-08-19T10:15:00Z"

    TODO — implement this function:
    1. Check if a Headline with this corridor_id + url already exists
       (query Headline, filter by both fields, .first())
    2. If it exists, return False (nothing to do)
    3. If not, parse publishedAt into a datetime:
         datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00"))
       (NewsAPI gives "Z" suffix which Python's fromisoformat doesn't
       accept directly before 3.11 — this replace handles it safely)
    4. Create a new Headline object with corridor_id, title, source,
       url, published_at, and fetched_at=datetime.now(timezone.utc)
    5. db.add() it (don't commit here — let the caller batch-commit
       after processing all articles, that's more efficient)
    6. Return True
    """
    pass  # <- replace this with your implementation


def ingest_all_corridors():
    """
    Main entrypoint: loops every corridor that has search terms defined,
    fetches headlines, saves new ones. This is what the scheduler will
    call every N minutes.
    """
    db = SessionLocal()
    total_new = 0
    try:
        for corridor_name, query in CORRIDOR_SEARCH_TERMS.items():
            corridor = db.query(Corridor).filter_by(name=corridor_name).first()
            if not corridor:
                print(f"Corridor not found in DB, skipping: {corridor_name}")
                continue

            articles = fetch_headlines_for_query(query)
            new_count = 0
            for article in articles:
                if save_headline_if_new(db, corridor, article):
                    new_count += 1

            db.commit()
            print(f"{corridor_name}: {new_count} new headlines (of {len(articles)} fetched)")
            total_new += new_count

        print(f"Ingestion run complete. {total_new} new headlines total.")
    finally:
        db.close()


if __name__ == "__main__":
    ingest_all_corridors()
