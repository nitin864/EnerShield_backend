# EnerShield — Backend

AI-driven energy supply chain resilience API. Backend for PS1 (hackathon submission).

**One-line problem:** India's energy imports depend heavily on a handful of geopolitical
chokepoints (Hormuz, Red Sea) with only ~9.5 days of reserve buffer — disruptions surface
too late for procurement teams to react.

**One-line solution:** A live pipeline that scores corridor risk from real news/sanctions
data, simulates cascading impact of disruption scenarios, and recommends ranked alternate
routes — with Claude as the reasoning/explanation layer on top of deterministic calculations.

## Status

Backend is being built module by module. Check off as each lands:

- [x] Module 1 — Core scaffold (FastAPI app, config, DB connection, health check)
- [x] Module 2 — Data models (corridors, suppliers, headlines, risk_history)
- [x] Module 3 — Ingestion pipeline (GDELT, NewsAPI, EIA, OFAC)
- [ ] Module 4 — Risk scoring engine (`/risk-score`)
- [ ] Module 5 — Scenario simulator (`/simulate`)
- [ ] Module 6 — Procurement orchestrator (`/recommend`)
- [ ] Module 7 — Wiring + resilience (fallback, error handling)
- [ ] Module 8 — Deploy config

## Architecture

```
Frontend (Next.js, separate repo)
        │  REST API
        ▼
FastAPI backend (this repo)
  ├── /health              → liveness + DB check
  ├── /risk-score           → Claude scores corridors from cached headlines
  ├── /simulate              → deterministic impact model + Claude narrative
  ├── /recommend             → ranking formula + Claude reasoning
  └── scheduled job          → pulls news/sanctions/energy data every N min
        │
        ▼
Supabase Postgres (corridors, suppliers, headlines, risk_history)
```

Design principle: **Claude explains and synthesizes, it never invents the numbers.**
Risk scores, impact %, and rankings come from deterministic formulas / cached real data;
Claude's job is scoring justification, narrative, and procurement-officer-style reasoning
on top of that. This is the answer when judges ask "how do you know that number is real."

## Project structure

```
app/
├── main.py            # FastAPI entrypoint, health check
├── core/
│   ├── config.py       # env-based settings (pydantic-settings)
│   └── database.py     # SQLAlchemy engine/session
├── models/             # SQLAlchemy ORM tables
├── schemas/            # Pydantic request/response schemas
├── routers/            # API route handlers, one file per feature
├── services/           # business logic (scoring, simulation, ranking, Claude calls)
└── jobs/                # scheduled data ingestion jobs
tests/
```

## Setup (local)

1. Clone and enter the repo:
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
3. Copy `.env.example` to `.env` and fill in real values:
   ```bash
   cp .env.example .env
   ```
   Required keys: `DATABASE_URL` (Supabase), `ANTHROPIC_API_KEY`. News/energy API keys
   are needed once Module 3 (ingestion) lands.
4. Run the dev server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
5. Verify: open `http://localhost:8000/health` — should return
   `{"status": "ok", "database": "connected", ...}`.

## Known limitations

_(updated as modules land — being upfront here is graded)_

- Currently only the scaffold + health check exist; no data endpoints yet.

## Links

- Hosted prototype: _TBD_
- Demo video: _TBD_
