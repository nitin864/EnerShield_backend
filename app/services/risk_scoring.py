"""
Risk scoring engine: reads recent headlines for a corridor, asks Claude
to score disruption probability (0-100) with justification, saves the
result. Falls back to the last known-good score if the live call fails.
"""
import json
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import Corridor, Headline, RiskHistory
from app.services.llm_client import complete

# How many recent headlines to feed Claude per scoring call — enough
# context without an unnecessarily large/costly prompt.
HEADLINES_PER_SCORE = 10


def build_scoring_prompt(corridor_name: str, headlines: list[Headline]) -> str:
    """
    Builds the prompt sent to Claude. Explicit about the JSON shape and
    that ONLY JSON should come back — this is what makes the response
    reliably parseable by json.loads() rather than needing to strip out
    conversational text.
    """
    headline_lines = "\n".join(
        f"- [{h.source or 'unknown source'}] {h.title}" for h in headlines
    )
    if not headline_lines:
        headline_lines = "(no recent headlines available)"

    return f"""You are a geopolitical risk analyst for energy supply chains.

Corridor: {corridor_name}

Recent headlines about this corridor:
{headline_lines}

Based ONLY on these headlines, assess the probability of a significant
supply disruption to this corridor in the near term.

Respond with ONLY a JSON object in this exact shape, no other text:
{{
  "score": <integer 0-100, where 0 = no disruption risk, 100 = active severe disruption>,
  "justification": "<2-3 sentence explanation citing what in the headlines drove this score>",
  "confidence": <float 0.0-1.0, how confident you are given the headline volume/quality>
}}"""


def call_claude_for_score(corridor_name: str, headlines: list[Headline]) -> dict:
    """
    Makes the actual API call and parses the JSON response.
    Raises an exception on any failure (network, API error, bad JSON) —
    the caller (score_corridor, below) is responsible for catching that
    and falling back gracefully. Keeping this function "fail loud" makes
    it easy to unit test and reason about independently of the fallback logic.
    """
    prompt = build_scoring_prompt(corridor_name, headlines)

    raw_text = complete(prompt, max_tokens=300)

    result = json.loads(raw_text)  # will raise if the LLM didn't return clean JSON

    # Basic validation — don't trust the number blindly even if JSON parsed fine.
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
    Scores one corridor: fetches its recent headlines, calls Claude,
    saves a new RiskHistory row, updates the corridor's cached current score."""

    
    headlines = (
        db.query(Headline)
        .filter_by(corridor_id=corridor.id)
        .order_by(Headline.published_at.desc())
        .limit(HEADLINES_PER_SCORE)
        .all()
    )

    try:
        result = call_claude_for_score(corridor.name, headlines)

    except Exception:
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
                "justification": (
                    "Live scoring unavailable — showing last known score."
                ),
            }
        else:
            result = {
                "score": 50,
                "confidence": 0.0,
                "justification": (
                    "No prior data and live scoring unavailable."
                ),
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

    except Exception as e:
    print(f"Live scoring failed for {corridor.name}: {e}")
    last_history = (


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