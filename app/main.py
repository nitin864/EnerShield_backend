"""
Corridor Pulse — Backend entrypoint.
PS1: AI-Driven Energy Supply Chain Resilience.
"""
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.routers import corridors, risk, simulate, recommend

app = FastAPI(
    title="Corridor Pulse API",
    description="AI-driven energy supply chain resilience backend",
    version="0.1.0",
)

app.include_router(corridors.router)
app.include_router(risk.router)
app.include_router(simulate.router)
app.include_router(recommend.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches anything unhandled so the frontend always gets clean JSON,
    never a raw 500 HTML traceback — important for a live demo where an
    edge case shouldn't visibly break the UI.
    """
    print(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Something went wrong processing this request.", "path": str(request.url.path)},
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
    return {"service": "enerShield-backend-api", "status": "running", "env": settings.env}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    """
    Liveness + DB connectivity check.
    Hit this first after every deploy — if this is green, everything downstream
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


 