"""
Thin abstraction over LLM providers. risk_scoring.py (and later, scenario
narrative / recommendation reasoning) call complete_json() and don't need
to know or care whether Groq or Claude actually answered.

Switch providers via LLM_PROVIDER in .env — no code changes needed elsewhere.
"""
from groq import Groq
from anthropic import Anthropic

from app.core.config import settings

_groq_client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None
_anthropic_client = Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None


def complete(prompt: str, max_tokens: int = 300) -> str:
    """
    Sends prompt to whichever provider is configured, returns the raw
    text response. Raises on failure — callers (like score_corridor)
    handle fallback behavior, this function just does the call.
    """
    provider = settings.llm_provider

    if provider == "groq":
        if not _groq_client:
            raise RuntimeError("GROQ_API_KEY not set in .env")
        response = _groq_client.chat.completions.create(
            model=settings.groq_model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},  # forces valid, complete JSON only
        )
        return response.choices[0].message.content

    elif provider == "claude":
        if not _anthropic_client:
            raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
        response = _anthropic_client.messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
