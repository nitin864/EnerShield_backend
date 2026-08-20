"""
Corridor Pulse — Backend entrypoint.
PS1: AI-Driven Energy Supply Chain Resilience.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.jobs.scheduler import start_scheduler, stop_scheduler

app = FastAPI(
    title="EnerShield API",
    description="AI-driven energy supply chain resilience backend",
    version="0.1.0",
)

@app.on_event("startup")
def on_startup():
    start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"service": "ener-shield-api", "status": "running", "env": settings.env}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    """
    Liveness + DB connectivity check.
    Hit this first after every deploy  if this is green, everything downstream
    has a working DB connection to build on.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok",
        "database": db_status,
        "claude_model": settings.claude_model,
    }

 
