""" 
Background Scheduler, creating scheduler to run ingestion jobs automatically 
on an interval, so DB stayes updated withouth anyone manually running scripts

wiring into main.py
"""

from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import settings

from app.services.news_ingestion import ingest_all_corridors
from app.services.eia_ingestion import ingest_eia_data

scheduler = BackgroundScheduler()

def run_all_ingestion_jobs():
    """
    warping both ingestion jobs with each having individual error handeling,
    if NewsAPI ingestion throw, EIA ingestion should still run.
    error from any one source should not take down the whole pipeline"""

    try: 
        ingest_all_corridors()
    except Exception as e:
        print(f"News ingestion job failed {e}")

    try:
        ingest_eia_data()
    except Exception as e:
        print(f"EIA ingestion job failed {e}")

    