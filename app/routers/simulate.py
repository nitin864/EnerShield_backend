"""Scenario simulator endpoints."""
from fastapi import APIRouter, HTTPException

from app.services.scenario_simulator import simulate_scenario, list_scenarios

router = APIRouter(prefix="/simulate", tags=["simulate"])


@router.get("/scenarios")
def get_scenarios():
    """List available pre-defined scenarios for the frontend's picker UI."""
    return list_scenarios()


@router.post("/{scenario_key}")
def run_simulation(scenario_key: str):
    try:
        return simulate_scenario(scenario_key)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {scenario_key}")
