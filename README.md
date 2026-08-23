
# Ener Shield  Backend
  

![Python 3.13](https://img.shields.io/badge/python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![Status: hackathon build](https://img.shields.io/badge/status-hackathon%20build-orange)

AI-driven energy supply-chain resilience API, built for the **PS1: Energy Resilience** hackathon track. This is the backend that powers Corridor Pulse — a dashboard that watches the shipping chokepoints India's crude oil imports depend on, and tells procurement teams when to worry.

**The problem:** a large share of India's energy imports pass through a handful of geopolitical chokepoints (the Strait of Hormuz, the Red Sea) while the country holds only around 9.5 days of reserve buffer. By the time a disruption is obvious, it's often too late to react.

**The approach:** a live pipeline that scores corridor risk from real news headlines, simulates the cascading impact of specific disruption scenarios, and ranks alternate suppliers/routes — with an LLM (Claude or Groq) layered on top purely as the explanation and reasoning engine, never as the source of the numbers themselves.

## Why it's useful

- [x] Module 1 — Core scaffold (FastAPI app, config, DB connection, health check)
- [x] Module 2 — Data models (corridors, suppliers, headlines, risk_history)
- [x] Module 3 — Ingestion pipeline (GDELT, NewsAPI, EIA, OFAC)
- [x] Module 4 — Risk scoring engine (`/risk-score`)
- [x] Module 5 — Scenario simulator (`/simulate`)
- [x] Module 6 — Procurement orchestrator (`/recommend`)
- [x] Module 7 — Wiring + resilience (fallback, error handling)
- [x] Module 8 — Deploy config
- **Deterministic-first, LLM-second.** Risk scores, impact percentages, and supplier rankings all come from transparent formulas over real cached data. The LLM's only job is to justify a score or narrate a scenario in plain language — so every number on the dashboard can be traced back to a calculation, not a hallucination.
- **Pluggable LLM provider.** Swap between Anthropic Claude and Groq with one config value (`LLM_PROVIDER`) — no code changes required. Useful for keeping a fast/free provider during development and switching to Claude for the polished demo.
- **Resilient by design.** Every external call (news API, EIA API, LLM) is wrapped so a single failure degrades gracefully instead of crashing the pipeline — a flaky headline source shouldn't take down risk scoring, and a failed LLM call falls back to the last known-good score rather than showing nothing.
- **Self-refreshing data.** A background scheduler pulls fresh headlines and crude oil price data on a configurable interval, so the dashboard stays current without manual intervention.
 

## How it works

```
Frontend (Next.js, separate repo)
        │  REST API
        ▼
FastAPI backend (this repo)
  ├── GET  /health                    → liveness + DB check
  ├── GET  /corridors                 → corridors + cached risk scores, for the map
  ├── GET  /corridors/{id}/headlines  → headlines driving a corridor's score
  ├── POST /risk-score/run            → score all corridors on demand
  ├── GET  /risk-score/{id}/history   → score trend over time
  ├── GET  /simulate/scenarios        → list pre-defined disruption scenarios
  ├── POST /simulate/{scenario_key}   → run a scenario (deterministic impact + narrative)
  ├── GET  /recommend                 → ranked alternate suppliers + reasoning
  └── scheduled job                   → pulls news + EIA data every N minutes
        │
        ▼
Postgres (Supabase) — corridors, suppliers, headlines, risk_history, energy_metrics
```

See [`res/db_schema.png`](res/db_schema.png) for the full table/relationship diagram, and [`res/PS1_Energy_Resilience_Build_Guide.pdf`](res/PS1_Energy_Resilience_Build_Guide.pdf) for the original problem brief this project was built against.

### Project structure

```
app/
├── main.py               # FastAPI entrypoint, health check, router wiring
├── core/
│   ├── config.py          # env-based settings (pydantic-settings)
│   ├── database.py        # SQLAlchemy engine/session
│   ├── init_db.py         # creates tables from the ORM models
│   └── seed_data.py       # seeds starter corridors + suppliers
├── models/                # SQLAlchemy ORM tables
├── schemas/                # Pydantic request/response schemas
├── routers/                 # API route handlers, one file per feature
├── services/                # business logic: scoring, simulation, ranking, ingestion, LLM client
└── jobs/                     # background ingestion scheduler
tests/                         # pytest suite (in-memory SQLite, no live DB needed)
res/                            # DB schema diagram + hackathon build guide
```

## Getting started

### Prerequisites

- Python 3.13
- A Postgres database (the project is built against [Supabase](https://supabase.com))
- API keys for whichever pieces you want live: Anthropic and/or Groq (LLM reasoning), NewsAPI.org (headlines), EIA.gov (crude oil price data)

### Installation

1. Clone the repo and enter it:
   ```bash
   git clone https://github.com/nitin864/EnerShield_backend.git
   cd EnerShield_backend
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy the env template and fill in real values:
   ```bash
   cp .env.example .env
   ```
   At minimum you need `DATABASE_URL`. To exercise the LLM-backed endpoints, set `LLM_PROVIDER` to `groq` or `claude` and provide the matching API key (`GROQ_API_KEY` / `ANTHROPIC_API_KEY`). `NEWSAPI_KEY` and `EIA_API_KEY` are needed for the ingestion jobs to pull live data.
4. Create the database tables:
   ```bash
   python -m app.core.init_db
   ```
5. Seed starter corridors and suppliers:
   ```bash
   python -m app.core.seed_data
   ```
6. Run the dev server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
7. Verify it's up: open `http://localhost:8000/health` — you should see `{"status": "ok", "database": "connected", ...}`.

### Usage examples

List corridors and their current risk scores:
```bash
curl http://localhost:8000/corridors
```

Run a scenario simulation (deterministic impact + LLM narrative):
```bash
curl -X POST http://localhost:8000/simulate/hormuz_closure
```

Get ranked alternate suppliers with reasoning:
```bash
curl http://localhost:8000/recommend
```

Interactive API docs (Swagger UI) are available at `http://localhost:8000/docs` once the server is running.

### Running tests

```bash
pytest tests/ -v
```

## Current status

This backend is being built module by module for the hackathon submission. Core scaffolding, data models, the scenario simulator, and the procurement orchestrator are working end to end. 



## Getting help

- **API reference:** interactive docs at `/docs` (Swagger) and `/redoc` on a running instance
- **Design context:** [`res/PS1_Energy_Resilience_Build_Guide.pdf`](res/PS1_Energy_Resilience_Build_Guide.pdf) has the original problem statement and design principles this backend follows
- **Issues:** open a GitHub issue on this repository for bugs or questions

## Maintainers & contributing

Maintained by [@nitin864](https://github.com/nitin864). This is an active hackathon build  issues and pull requests are welcome, especially for the stubbed functions listed above under [Current status](#current-status).

Licensed under the terms in the repository's `LICENSE` file (add one if it's missing before publishing).
