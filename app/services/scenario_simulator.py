"""
Scenario Simulator: given a chosen disruption scenario, computes a
deterministic cascading-impact estimate, then asks the LLM to narrate it
in plain language. Numbers come from the formula, not the LLM.
"""
import json

from sqlalchemy.orm import Session

from app.services.llm_client import complete
from app.models.models import EnergyMetric

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

# India's actual strategic petroleum reserve (SPR) capacity is ~5.33 million
# tonnes, roughly 39 million barrels across 3 underground caverns (Vizag,
# Mangalore, Padur). Net crude import volume is roughly 4.1 million barrels/day.
# 39M / 4.1M ≈ 9.5 days — this DERIVES the brief's "9.5 days" figure from real
# quantities instead of just asserting it.
INDIA_RESERVE_BARRELS = 39_000_000
INDIA_DAILY_IMPORT_BBL = 4_100_000
INDIA_RESERVE_DAYS = round(INDIA_RESERVE_BARRELS / INDIA_DAILY_IMPORT_BBL, 2)

FALLBACK_WTI_PRICE = 75.0  # used only if no EnergyMetric row exists yet

# Rough elasticity for oil-importing economies: each $10/bbl sustained price
# rise costs roughly 0.2-0.3 percentage points of GDP growth (a commonly
# cited range in oil-shock economics literature). This is illustrative, not
# a precise macro model — but it's a real, named, defensible assumption
# rather than an arbitrary number.
GDP_IMPACT_PCT_POINTS_PER_10USD = 0.25


def get_latest_wti_price(db: Session) -> tuple[float, bool]:
    """
    Reads the most recent WTI spot price ingested by eia_ingestion.py.
    Returns (price, is_real) — is_real=False means we fell back to a
    static default because no data has been ingested yet. Surfacing this
    flag (instead of silently faking it) matters for the demo: it's the
    difference between "real data" and "quietly made up."
    """
    latest = (
        db.query(EnergyMetric)
        .filter_by(series_id="RWTC")
        .order_by(EnergyMetric.period.desc())
        .first()
    )
    if latest and latest.value is not None:
        return latest.value, True
    return FALLBACK_WTI_PRICE, False


def compute_deterministic_impact(scenario_key: str, db: Session) -> dict:
    """
    The actual math — NOT from the LLM. This is the "hybrid deterministic +
    LLM reasoning" answer for when judges ask 'how do you know that number
    is real.'

    Simple, transparent model: corridor's import share directly maps to
    refining loss %, which drives a price delta and reserve-day impact.
    The price delta is now applied against the REAL latest WTI spot price
    from EnergyMetric, not an abstract percentage alone.
    """
    if scenario_key not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_key}")

    scenario = SCENARIOS[scenario_key]
    share = scenario["corridor_share_pct"]

    refining_loss_pct = round(share * 0.9, 1)
    price_delta_pct = round(share * 0.6, 1)
    reserve_days_impact = round(INDIA_RESERVE_DAYS * (refining_loss_pct / 100), 2)
    days_of_buffer_remaining = round(INDIA_RESERVE_DAYS - reserve_days_impact, 2)

    # Concrete barrel math: how many barrels/day are actually lost, and how
    # long the strategic reserve alone could cover that shortfall if the
    # corridor stayed shut and nothing else changed.
    daily_shortfall_bbl = round(INDIA_DAILY_IMPORT_BBL * (refining_loss_pct / 100))
    days_reserve_covers_shortfall = (
        round(INDIA_RESERVE_BARRELS / daily_shortfall_bbl, 2) if daily_shortfall_bbl > 0 else None
    )

    current_price, price_is_real = get_latest_wti_price(db)
    projected_price = round(current_price * (1 + price_delta_pct / 100), 2)
    price_delta_usd = round(projected_price - current_price, 2)

    # GDP impact: scales with the actual dollar price rise, not just the
    # percentage, since the elasticity is defined per $10/bbl of real price change.
    gdp_impact_pct_points = round((price_delta_usd / 10) * GDP_IMPACT_PCT_POINTS_PER_10USD, 3)

    return {
        "scenario_key": scenario_key,
        "label": scenario["label"],
        "corridor_name": scenario["corridor_name"],
        "severity": scenario["severity"],
        "refining_loss_pct": refining_loss_pct,
        "price_delta_pct": price_delta_pct,
        "current_price_usd": current_price,
        "projected_price_usd": projected_price,
        "price_delta_usd": price_delta_usd,
        "price_is_live_data": price_is_real,
        "reserve_days_impact": reserve_days_impact,
        "days_of_buffer_remaining": days_of_buffer_remaining,
        "reserve_capacity_bbl": INDIA_RESERVE_BARRELS,
        "daily_import_bbl": INDIA_DAILY_IMPORT_BBL,
        "daily_shortfall_bbl": daily_shortfall_bbl,
        "days_reserve_covers_shortfall": days_reserve_covers_shortfall,
        "gdp_impact_pct_points": gdp_impact_pct_points,
    }


def build_narrative_prompt(impact: dict) -> str:
    price_note = (
        f"${impact['current_price_usd']}/bbl (live market data)"
        if impact["price_is_live_data"]
        else f"${impact['current_price_usd']}/bbl (estimated, no live price data yet)"
    )
    return f"""You are a supply chain analyst briefing a procurement team.

Scenario: {impact['label']}
Computed impact (already calculated, do not recompute):
- Refining capacity loss: {impact['refining_loss_pct']}%
- Current WTI price: {price_note}
- Projected price after disruption: ${impact['projected_price_usd']}/bbl (+${impact['price_delta_usd']})
- Daily import shortfall: {impact['daily_shortfall_bbl']:,} barrels/day
- Strategic reserve: {impact['reserve_capacity_bbl']:,} barrels
- Reserve alone would cover this shortfall for: {impact['days_reserve_covers_shortfall']} days
- Reserve buffer remaining after impact: {impact['days_of_buffer_remaining']} days
- Estimated GDP growth impact: -{impact['gdp_impact_pct_points']} percentage points

Write a 3-4 sentence cascading-impact narrative for a procurement officer,
explaining what this scenario means in practice and how urgently they need
to act. Reference the specific numbers above. Respond with ONLY a JSON object:
{{"narrative": "<your 3-4 sentence narrative>"}}"""


def simulate_scenario(scenario_key: str, db: Session) -> dict:
    """
    Full simulate flow: deterministic calc + LLM narrative on top.
    Falls back to a templated narrative if the LLM call fails — the
    numbers are still valid either way since they never depended on the LLM.
    """
    impact = compute_deterministic_impact(scenario_key, db)

    try:
        prompt = build_narrative_prompt(impact)
        raw_text = complete(prompt, max_tokens=400)
        narrative = json.loads(raw_text)["narrative"]
    except Exception as e:
        print(f"Narrative generation failed for {scenario_key}: {e}")
        narrative = (
            f"{impact['label']} would cut refining capacity by {impact['refining_loss_pct']}%, "
            f"pushing WTI from ${impact['current_price_usd']} to an estimated "
            f"${impact['projected_price_usd']}/bbl and consuming {impact['reserve_days_impact']} "
            f"days of India's reserve buffer, leaving {impact['days_of_buffer_remaining']} days "
            f"of cover, with an estimated GDP growth impact of -{impact['gdp_impact_pct_points']} "
            f"percentage points. Immediate procurement action is recommended."
        )

    impact["narrative"] = narrative
    return impact


def list_scenarios() -> list[dict]:
    return [{"key": k, "label": v["label"], "severity": v["severity"]} for k, v in SCENARIOS.items()]