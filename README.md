# URIE — Unified Relational Intelligence Engine

Relationship Intelligence (RI) core: bounded voice debriefs → structured facts + graph →
constraint-gated ghost-mode action feed.

This repository implements the **vertical slice** of the engine described in
`docs/Production-Grade_Technical_Specification.md`:

```
debrief text → parse → entity resolution → fact/graph write saga → reasoning → feed
```

Neo4j, Kafka, Redis, and live STT/LLM/TTS are deferred behind ports. The core runs on
**Postgres + pgvector** with mock providers and a transactional outbox.

## Quick start

```bash
# 1. Start Postgres (pgvector)
docker compose up -d

# 2. Install
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 3. Copy env
cp .env.example .env

# 4. Migrate (or let the app create tables in development)
alembic upgrade head

# 5. Run API
uvicorn urie.main:app --reload --app-dir src

# 6. Tests
pytest
```

## Dev auth

Mint a JWT for an agent (also available via `POST /v1/auth/token` in development):

```bash
curl -X POST http://localhost:8000/v1/auth/token \
  -H 'Content-Type: application/json' \
  -d '{"agent_id":"agt_demo","name":"Demo Agent"}'
```

Use the returned bearer token on subsequent requests.

## Frontend development

The production UI is a React + TypeScript application in `frontend/`. Vite proxies `/v1`
requests to the FastAPI server during development and writes production assets directly to
`src/urie/static/`.

```bash
cd frontend
npm install
npm run dev      # http://127.0.0.1:5173
npm run build    # rebuild the FastAPI-served static bundle
npm test
```

Run the API on port `8000` while using the Vite development server. All product copy,
source identifiers, comments, and frontend documentation are maintained in English.

## Core endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/v1/debriefs` | Start interview (default) or oneshot (`mode=oneshot` + transcript) |
| `POST` | `/v1/debriefs/{id}/turn` | Submit an interview answer; returns next gap-driven question |
| `POST` | `/v1/debriefs/{id}/finish` | End the interview early |
| `GET` | `/v1/debriefs/{id}` | Session status / turns / staged mutations |
| `POST` | `/v1/debriefs/{id}/resolve` | Challenge-loop resolution |
| `GET` | `/v1/nodes` | Search relationship nodes |
| `GET` | `/v1/nodes/{id}` | Node profile |
| `GET` | `/v1/nodes/{id}/context` | Depth-2 sub-graph |
| `GET` | `/v1/feed` | Ghost-mode action feed |
| `POST` | `/v1/feed/{id}/ack` | Ack / dismiss a suggestion |
| `GET/POST` | `/v1/constraints` | Read / set DND windows |
| `POST` | `/v1/crm/writeback` | Idempotent CRM note stub |

## LLM gateway

Provider-agnostic clients live in `src/urie/llm/`. Default is **`mock`** (deterministic,
zero-config). Set env to point at a real model when ready:

| Variable | Default | Notes |
|----------|---------|-------|
| `LLM_PROVIDER` | `mock` | `mock` \| `openai` \| `anthropic` |
| `LLM_API_KEY` | _(empty)_ | Required for openai/anthropic; missing key falls back to mock |
| `LLM_BASE_URL` | _(provider default)_ | OpenAI-compatible gateway override |
| `LLM_MODEL` | _(provider default)_ | e.g. `gpt-4o-mini`, `claude-sonnet-4-20250514` |
| `LLM_TEMPERATURE` | `0.2` | |
| `LLM_TIMEOUT_S` | `45` | |
| `LLM_MAX_RETRIES` | `3` | Exponential backoff on timeout/rate-limit |
| `LLM_MAX_INTERVIEW_TURNS` | `8` | Cost bound for multi-turn debriefs |

**Prompt architecture** (`src/urie/llm/prompts/`): shared persona + ghost-mode guardrails in
`persona.py`; versioned templates for extraction, interview planning, ghost scripts, and
challenge phrasing. Structured outputs validated via Pydantic schemas in `llm/schemas.py`.
`PromptedLLM` (`adapters/providers/prompted.py`) implements `LLMPort` over any `LLMClient`.

Dynamic interviews (`InterviewService`): open with a gap-driven question → extract each turn
→ existing ER/challenge/write saga → `detect_gaps` → `plan_interview` → next question (or
finish when gaps exhausted / max turns).

## Tests

```bash
# Domain + in-memory vertical slice (no Docker required)
pytest tests/unit tests/integration/test_vertical_slice_memory.py -v

# Postgres-backed integration (requires docker compose up -d)
pytest tests/integration/test_vertical_slice.py tests/integration/test_rls.py -v
```

## Pilot UI

See [docs/PILOT_RUNBOOK.md](docs/PILOT_RUNBOOK.md) for the full setup.

```bash
docker compose up -d
alembic upgrade head
uvicorn urie.main:app --reload --app-dir src
# → http://127.0.0.1:8000/
python scripts/seed_demo.py
```

## Architecture

Hexagonal (ports & adapters): pure domain in `src/urie/domain/`, application services in
`src/urie/services/`, Postgres/mock/in-memory adapters in `src/urie/adapters/`.

The port-injected `VerticalSliceEngine` (`src/urie/services/pipeline.py`) runs the full loop
against any store implementation. The FastAPI layer uses the Postgres-backed
`IngestionService` + `ReasoningWorker`. Authenticated requests bind Postgres RLS via
`app.agent_id` (non-superuser role `urie_app`).
