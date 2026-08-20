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

