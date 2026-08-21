"""
Scenario Simulator: given a chosen disruption scenario, computes a
deterministic cascading-impact estimate, then asks the LLM to narrate it
in plain language. Numbers come from the formula, not the LLM.
"""
import json

from app.services.llm_client import complete

# Pre-defined scenarios (per build guide: 2-3 pre-defined, not a full sim engine).
# refining_loss_pct / price_delta_pct / reserve_days_impact are illustrative
# multipliers based on the corridor's share of India's crude import flow —
# tune these with real PPAC/EIA figures if you have time before demo.
SCENARIOS = {
    "hormuz_closure": {
        "corridor_name": "Strait of Hormuz",
        "label": "Strait of Hormuz Closure",
        "corridor_share_pct": 40,       # % of India's crude imports transiting this corridor
        "severity": "severe",
    },
    "red_sea_suspension": {
        "corridor_name": "Red Sea / Bab-el-Mandeb",
        "label": "Red Sea Shipping Suspension",
        "corridor_share_pct": 12,
        "severity": "moderate",
    },
    "suez_blockage": {
        "corridor_name": "Suez Canal",
        "label": "Suez Canal Blockage",
        "corridor_share_pct": 8,
        "severity": "moderate",
    },
}

INDIA_RESERVE_DAYS = 9.5  # from the build guide's own framing numbers


def compute_deterministic_impact(scenario_key: str) -> dict:
    """
    The actual math — NOT from the LLM. This is the "hybrid deterministic +
    LLM reasoning" answer for when judges ask 'how do you know that number
    is real.'

    Simple, transparent model: corridor's import share directly maps to
    refining loss %, which drives a price delta and reserve-day impact.
    """
    if scenario_key not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_key}")

    scenario = SCENARIOS[scenario_key]
    share = scenario["corridor_share_pct"]

    # Illustrative formulas — deliberately simple and explainable in the demo.
    refining_loss_pct = round(share * 0.9, 1)          # assume ~90% of that share is lost during closure
    price_delta_pct = round(share * 0.6, 1)              # partial pass-through to price
    reserve_days_impact = round(INDIA_RESERVE_DAYS * (refining_loss_pct / 100), 2)
    days_of_buffer_remaining = round(INDIA_RESERVE_DAYS - reserve_days_impact, 2)

    return {
        "scenario_key": scenario_key,
        "label": scenario["label"],
        "corridor_name": scenario["corridor_name"],
        "severity": scenario["severity"],
        "refining_loss_pct": refining_loss_pct,
        "price_delta_pct": price_delta_pct,
        "reserve_days_impact": reserve_days_impact,
        "days_of_buffer_remaining": days_of_buffer_remaining,
    }


def build_narrative_prompt(impact: dict) -> str:
    return f"""You are a supply chain analyst briefing a procurement team.

Scenario: {impact['label']}
Computed impact (already calculated, do not recompute):
- Refining capacity loss: {impact['refining_loss_pct']}%
- Estimated price impact: +{impact['price_delta_pct']}%
- Reserve days consumed: {impact['reserve_days_impact']} days
- Reserve buffer remaining after impact: {impact['days_of_buffer_remaining']} days

Write a 3-4 sentence cascading-impact narrative for a procurement officer,
explaining what this scenario means in practice and how urgently they need
to act. Reference the specific numbers above. Respond with ONLY a JSON object:
{{"narrative": "<your 3-4 sentence narrative>"}}"""


def simulate_scenario(scenario_key: str) -> dict:
    """
    Full simulate flow: deterministic calc + LLM narrative on top.
    Falls back to a templated narrative if the LLM call fails — the
    numbers are still valid either way since they never depended on the LLM.
    """
    impact = compute_deterministic_impact(scenario_key)

    try:
        prompt = build_narrative_prompt(impact)
        raw_text = complete(prompt, max_tokens=400)
        narrative = json.loads(raw_text)["narrative"]
    except Exception as e:
        print(f"Narrative generation failed for {scenario_key}: {e}")
        narrative = (
            f"{impact['label']} would cut refining capacity by {impact['refining_loss_pct']}%, "
            f"pushing prices up an estimated {impact['price_delta_pct']}% and consuming "
            f"{impact['reserve_days_impact']} days of India's reserve buffer, leaving "
            f"{impact['days_of_buffer_remaining']} days of cover. Immediate procurement "
            f"action is recommended."
        )

    impact["narrative"] = narrative
    return impact


def list_scenarios() -> list[dict]:
    return [{"key": k, "label": v["label"], "severity": v["severity"]} for k, v in SCENARIOS.items()]
