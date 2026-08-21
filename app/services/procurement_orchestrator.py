"""
Procurement Orchestrator: ranks alternate suppliers/routes by a
deterministic formula (distance, cost, current corridor risk), then asks
the LLM to explain the ranking in procurement-officer language.
"""
import json

from sqlalchemy.orm import Session

from app.models.models import Supplier, Corridor
from app.services.llm_client import complete


def compute_supplier_ranking(db: Session) -> list[dict]:
    """
    Deterministic ranking — NOT from the LLM. Lower composite score = better
    (safer, cheaper, closer) option.
    """
    suppliers = db.query(Supplier).all()
    ranked = []

    for s in suppliers:
        corridor = db.query(Corridor).filter_by(id=s.corridor_id).first()
        risk = corridor.current_risk_score if corridor and corridor.current_risk_score is not None else 50
        distance = s.distance_km or 0
        cost = s.cost_proxy or 0

        composite_score = (risk * 0.5) + (distance * 0.01 * 0.3) + (cost * 0.2)

        ranked.append({
            "supplier_id": s.id,
            "supplier_name": s.name,
            "corridor_name": corridor.name if corridor else "Unknown",
            "corridor_risk": risk,
            "distance_km": distance,
            "cost_proxy": cost,
            "composite_score": round(composite_score, 2),
        })

    ranked.sort(key=lambda x: x["composite_score"])
    return ranked


def build_reasoning_prompt(ranked: list[dict]) -> str:
    top_3 = ranked[:3]
    lines = "\n".join(
        f"{i+1}. {r['supplier_name']} (via {r['corridor_name']}) — "
        f"risk={r['corridor_risk']}, distance={r['distance_km']}km, cost_index={r['cost_proxy']}"
        for i, r in enumerate(top_3)
    )
    return f"""You are advising a procurement officer on alternate energy suppliers,
already ranked by a scoring formula (lower composite = better).

Top ranked options:
{lines}

Write a short reasoning explanation for EACH of the top 3, in procurement-
officer language, referencing their specific risk/distance/cost numbers.
Respond with ONLY a JSON object in this shape:
{{"reasoning": [
  {{"supplier_name": "...", "explanation": "<1-2 sentences>"}},
  {{"supplier_name": "...", "explanation": "<1-2 sentences>"}},
  {{"supplier_name": "...", "explanation": "<1-2 sentences>"}}
]}}"""


def recommend_suppliers(db: Session) -> dict:
    """
    Full recommend flow: deterministic ranking + LLM reasoning layered on
    top. Falls back to ranking-only if the LLM call fails.
    """
    ranked = compute_supplier_ranking(db)

    if not ranked:
        return {"ranked_suppliers": [], "reasoning_available": False}

    try:
        prompt = build_reasoning_prompt(ranked)
        raw_text = complete(prompt, max_tokens=500)
        reasoning = json.loads(raw_text)["reasoning"]

        reasoning_map = {r["supplier_name"]: r["explanation"] for r in reasoning}
        for r in ranked[:3]:
            r["explanation"] = reasoning_map.get(r["supplier_name"], "")

        reasoning_available = True
    except Exception as e:
        print(f"Recommendation reasoning failed: {e}")
        for r in ranked[:3]:
            r["explanation"] = "Reasoning unavailable — ranked by risk, distance, and cost score."
        reasoning_available = False

    return {"ranked_suppliers": ranked, "reasoning_available": reasoning_available}
