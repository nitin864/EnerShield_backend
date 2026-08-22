"""
Background scheduler — runs ingestion jobs automatically on an interval,
so the DB stays fresh without anyone manually running scripts.

Wired into app startup/shutdown in main.py.
"""
from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.services.news_ingestion import ingest_all_corridors
from app.services.eia_ingestion import ingest_eia_data
from app.services.ofac_ingestion import ingest_sanctions_data

scheduler = BackgroundScheduler()


def run_all_ingestion_jobs():
    """
    Wraps all ingestion jobs with individual error handling — if one
    source throws, the others still run. One flaky source should never
    take down the whole pipeline (same "never let the demo break on one
    dead call" principle from the build guide).
    """
    try:
        ingest_all_corridors()
    except Exception as e:
        print(f"News ingestion job failed: {e}")

    try:
        ingest_eia_data()
    except Exception as e:
        print(f"EIA ingestion job failed: {e}")

    try:
        ingest_sanctions_data()
    except Exception as e:
        print(f"OFAC ingestion job failed: {e}")


def start_scheduler():
    scheduler.add_job(
        run_all_ingestion_jobs,
        trigger="interval",
        minutes=settings.ingest_interval_minutes,
        id="ingestion_job",
        replace_existing=True,
        next_run_time=None,  # don't fire instantly on startup; wait one full interval first
    )
    scheduler.start()
    print(f"Scheduler started — ingestion runs every {settings.ingest_interval_minutes} min")


def stop_scheduler():
    scheduler.shutdown(wait=False)