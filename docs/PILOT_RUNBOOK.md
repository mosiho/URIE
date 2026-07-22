# URIE Pilot Runbook

How to run the local stack and pilot the debrief-adoption hypothesis
(Open Risk #1 in [MANIFESTO.md](MANIFESTO.md)):

> Will a busy solo agent take a short AI debrief call once or twice a day,
> indefinitely, without feeling it as more work?

This milestone validates that habit with **text debriefs** (voice deferred).

---

## Prerequisites

- Docker Desktop running
- Python 3.9+ with a venv (`python3 -m venv .venv && source .venv/bin/activate`)
- Repo dependencies: `pip install -e ".[dev]"`

---

## Start the stack

```bash
# 1. Postgres + pgvector
docker compose up -d

# First-time (or after volume wipe): ensure non-superuser app role exists
docker compose exec -T postgres psql -U urie -d urie -f - < scripts/init_app_role.sql

# 2. Env
cp .env.example .env   # if you don't already have .env

# 3. Migrations (run as admin role via DATABASE_URL_ADMIN)
alembic upgrade head

# Re-grant table privileges to urie_app after migrations
docker compose exec -T postgres psql -U urie -d urie -c \
  "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO urie_app;"

# 4. API + UI
uvicorn urie.main:app --reload --app-dir src --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/** — sign in with any `agent_id` (e.g. `agt_demo`).

API docs: http://127.0.0.1:8000/docs

---

## Seed a demo book of business

With the API running:

```bash
python scripts/seed_demo.py
```

This walks through:

1. Budget fact for John  
2. Contradiction → challenge-loop resolution  
3. Do-Not-Disturb constraint  
4. Life-event trait (baby) → held ghost-mode suggestion  

Then open the UI, sign in as `agt_demo`, and inspect **Feed** / **Clients**.

---

## What to watch in a pilot (metrics)

| Metric | How to measure | Target signal |
|--------|----------------|---------------|
| **Answer / start rate** | Days agent opened the app and started a debrief ÷ days invited | ≥ 4 / 7 in week 1 |
| **Completion rate** | Debriefs with `status=completed` (incl. after resolve) ÷ started | ≥ 80% |
| **Challenge friction** | Resolves completed without abandonment | Agents finish the "why did it change?" prompt |
| **Time-to-first-feed-item** | Clock from first completed debrief → first feed script | Same session |
| **Perceived effort** | 1–5 Likert after each session: "Did this feel like extra work?" | Median ≤ 2 |

If answer rate collapses by day 3–4, **stop building features** and redesign the trigger/cadence before investing in voice or CRM.

---

## Suggested pilot protocol (2–3 agents)

1. 10-minute setup: sign in, run seed demo together, show Feed.  
2. Ask them to run **one text debrief/day for 5 business days** (≤ 2 min).  
3. Daily check: did they complete? Any challenge-loop confusion?  
4. End of week: review feed usefulness + Likert on effort.  

Recording boundary reminder (from the manifesto): only agent↔AI audio/text is in scope. Never record client calls.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Postgres tests skip / connection refused | `docker compose up -d`, wait for healthy |
| `permission denied` / RLS weirdness | App must use `urie_app` (see `.env`); superuser `urie` bypasses RLS |
| Tables missing after pytest | `alembic stamp base && alembic upgrade head`, then re-GRANT to `urie_app` |
| UI loads but API 401 | Re-sign in; token is stored in `localStorage` |

---

## Explicitly out of scope for this pilot

- Live telephony / STT / TTS  
- Production CRM write-back  
- Neo4j / Kafka / Redis  
- GDPR legal review (required before storing real client books)

## LLM wiring (optional for habit test)

The pilot defaults to `LLM_PROVIDER=mock` — deterministic extraction/interview planning with
no API key. That is enough for the debrief-habit test.

When you want a real model:

1. Set `LLM_PROVIDER=openai` (or `anthropic`) and `LLM_API_KEY=…` in `.env`.
2. Optionally set `LLM_MODEL`, `LLM_BASE_URL` (OpenAI-compatible gateways), `LLM_TEMPERATURE`.
3. Bound cost with `LLM_MAX_INTERVIEW_TURNS` (default 8) — interviews stop when gaps are
   closed or the turn cap is hit.
4. Restart the API. `PromptedLLM` uses the same prompts/schemas; no code change required.

See README **LLM gateway** for the full env table and prompt layout under `src/urie/llm/`.

---

*End of pilot runbook*
