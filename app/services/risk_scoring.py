"""
Risk scoring engine: reads recent headlines for a corridor, asks Claude
to score disruption probability (0-100) with justification, saves the
result. Falls back to the last known-good score if the live call fails.
"""
import json
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import Corridor, Headline, RiskHistory, SanctionsSignal
from app.services.llm_client import complete
 
HEADLINES_PER_SCORE = 10

def build_scoring_prompt(corridor_name: str, headlines: list[Headline], sanctions_count: int = 0, sanctions_keywords: str = None) -> str:
    headline_lines = "\n".join(
        f"- [{h.source or 'unknown source'}] {h.title}" for h in headlines
    )
    if not headline_lines:
        headline_lines = "(no recent headlines available)"

    sanctions_line = (
        f"OFAC sanctions data: {sanctions_count} sanctioned entities currently listed under program(s) related to this corridor ({sanctions_keywords})."
        if sanctions_count > 0
        else "OFAC sanctions data: no directly relevant sanctions entries currently listed."
    )

    return f"""You are a geopolitical risk analyst for energy supply chains.

Corridor: {corridor_name}

Recent headlines about this corridor:
{headline_lines}

{sanctions_line}

Based on the headlines AND the sanctions signal above, assess the probability of a significant
supply disruption to this corridor in the near term.

Respond with ONLY a JSON object in this exact shape, no other text:
{{
  "score": <integer 0-100, where 0 = no disruption risk, 100 = active severe disruption>,
  "justification": "<2-3 sentence explanation citing what in the headlines AND sanctions data drove this score>",
  "confidence": <float 0.0-1.0, how confident you are given the headline volume/quality>
}}"""


def call_claude_for_score(corridor_name: str, headlines: list[Headline], sanctions_count: int = 0, sanctions_keywords: str = None) -> dict:
    prompt = build_scoring_prompt(corridor_name, headlines, sanctions_count, sanctions_keywords)

    raw_text = complete(prompt, max_tokens=600)

    result = json.loads(raw_text)   

    
    score = int(result["score"])
    if not (0 <= score <= 100):
        raise ValueError(f"Score out of range: {score}")

    return {
        "score": score,
        "justification": result.get("justification", ""),
        "confidence": float(result.get("confidence", 0.5)),
    }

def score_corridor(db, corridor: Corridor) -> dict:
    """
    Scores one corridor: fetches its recent headlines, calls the LLM,
    saves a new RiskHistory row, updates the corridor's cached current score.
    """
    headlines = (
        db.query(Headline)
        .filter_by(corridor_id=corridor.id)
        .order_by(Headline.published_at.desc())
        .limit(HEADLINES_PER_SCORE)
        .all()
    )

    sanctions = db.query(SanctionsSignal).filter_by(corridor_id=corridor.id).first()
    sanctions_count = sanctions.entity_count if sanctions else 0
    sanctions_keywords = sanctions.matched_keywords if sanctions else None

    try:
        result = call_claude_for_score(corridor.name, headlines, sanctions_count, sanctions_keywords)

    except Exception as e:
        print(f"Live scoring failed for {corridor.name}: {e}")

        last_history = (
            db.query(RiskHistory)
            .filter_by(corridor_id=corridor.id)
            .order_by(RiskHistory.scored_at.desc())
            .first()
        )

        if last_history:
            result = {
                "score": last_history.score,
                "confidence": last_history.confidence,
                "justification": "Live scoring unavailable showing last known score.",
            }
        else:
            result = {
                "score": 50,
                "confidence": 0.0,
                "justification": "No prior data and live scoring unavailable.",
            }

    risk_history = RiskHistory(
        corridor_id=corridor.id,
        score=result["score"],
        confidence=result["confidence"],
        justification=result["justification"],
        scored_at=datetime.now(timezone.utc),
    )

    corridor.current_risk_score = result["score"]
    corridor.last_scored_at = datetime.now(timezone.utc)

    db.add(risk_history)

    return result
 


def score_all_corridors():
    """Entrypoint — scores every corridor. Called by the scheduler."""
    db = SessionLocal()
    try:
        corridors = db.query(Corridor).all()
        for corridor in corridors:
            result = score_corridor(db, corridor)
            print(f"{corridor.name}: score={result['score']} (confidence={result['confidence']})")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    score_all_corridors()
