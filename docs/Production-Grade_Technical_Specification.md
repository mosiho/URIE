# Production-Grade Technical Specification

> **System:** Unified Relational Intelligence Engine (URIE)
> **Product:** Relationship Intelligence (RI) Platform
> **Aligned to:** Business Model v2.0 (single **Solo** tier)
> **Spec version:** 2.0 (supersedes v1.0)
> **Status:** Engineering blueprint. Performance targets and cost-bearing choices are design
> intent and must be validated by load testing and live vendor quotes before commitment.

---

## 0. Scope & Alignment Notes

This document is the machine- and human-readable engineering source of truth for the project.
It sits alongside `STRATEGIC_BUSINESS_MODEL.md` and is intended to be read by tooling, agents,
and contributors as the definitive description of **how the system is built**.

**Alignment with Business Model v2 — what changed from the v1 spec:**

1. **Single-tenant-per-agent model.** The v1 "Syndicate Mesh" (multiple agents sharing one
   regional graph via graph-role overlap) is **removed** from the core. Every agent owns an
   isolated relational graph. The multi-agent shared-topology path is deferred and sketched
   only in [§11 Future Work](#11-future-work--the-mesh-path).
2. **No live client-call streaming.** The system **never** taps, joins, or transcribes the
   agent's calls or meetings with clients. The only audio the platform ever processes is the
   **agent↔AI debrief** — the agent narrating what happened. This reshapes the ingestion
   pipeline (see [§3](#3-ingestion--the-debrief-pipeline)).
3. **Bounded debrief cadence.** At most 1–2 debriefs per day, user-configurable and batched.
   This is both a UX and a cost-control invariant, and it drives capacity planning in
   [§8](#8-non-functional-requirements--capacity).

> ⚠️ **Verification note.** Latency numbers, model choices, and per-user cost implications are
> engineering targets, not measured results. Treat every third-party product named here
> (Postgres, Neo4j, Redis, Kafka, Deepgram, ElevenLabs, etc.) as a *candidate* to be confirmed
> against current pricing, SLAs, and EU data-residency options before it becomes load-bearing.

---

## 1. System Overview

URIE is an event-driven engine with three planes:

- **Ingestion plane** — turns a spoken agent debrief into structured records and graph mutations.
- **Reasoning plane** — reacts to graph changes asynchronously and produces "ghost-mode" scripts.
- **Serving plane** — answers the mobile app with sub-100ms reads from a hot cache.

```text
                         ┌────────────────────────────┐
                         │        Mobile App          │
                         │  (debrief trigger + feed)  │
                         └───────┬───────────┬────────┘
                                 │           │
                       debrief   │           │  reads
                        audio    │           │ (<100ms)
                                 ▼           ▼
        ┌────────────────────────────┐   ┌────────────────────────┐
        │   INGESTION PLANE          │   │   SERVING PLANE        │
        │   (VUI → structured data)  │   │   (Redis hot cache +   │
        │                            │   │    read APIs)          │
        └────────────┬───────────────┘   └───────────┬────────────┘
                     │ graph mutations                │ cache fill
                     ▼                                 ▲
        ┌────────────────────────────────────────────────────────┐
        │              TRI-ENGINE DATA FABRIC                     │
        │   PostgreSQL   ·   Neo4j   ·   pgvector (HNSW)          │
        └────────────┬───────────────────────────────────────────┘
                     │ change events (Kafka)
                     ▼
        ┌────────────────────────────┐
        │   REASONING PLANE          │
        │   (constraint check +      │
        │    ghost-mode synthesis)   │
        └────────────────────────────┘
```

---

## 2. The Tri-Engine Data Fabric

A single ingestion orchestrator writes into three specialized stores, each chosen for one job.
Because the product is single-agent, **isolation is per-tenant-agent** and enforced at every layer.

```text
              ┌────────────────────────────────────────┐
              │      Unified Ingestion Orchestrator     │
              └───────────────────┬────────────────────┘
                                  │
       ┌──────────────────────────┼──────────────────────────┐
       ▼                          ▼                          ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ 1. Relational    │     │ 2. Graph Store   │     │ 3. Vector Index  │
│    (PostgreSQL)  │     │    (Neo4j)       │     │    (pgvector)    │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ Auth, billing,   │     │ Human relational │     │ Semantic lookup  │
│ subscription,    │     │ topology, multi- │     │ + entity match   │
│ listings,        │     │ degree traversal │     │ over names/attrs │
│ appointments     │     │ per agent        │     │ (HNSW)           │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

### 2.1 Store responsibilities

| Store | Engine (candidate) | Owns | Isolation model |
|---|---|---|---|
| **Relational core** | PostgreSQL | Tenant/agent auth, billing, subscription state, structured transactional entities (listings, appointments), the deterministic "safe baseline" of every fact | Row-level security keyed on `agent_id`; one logical schema per agent optional at scale |
| **Semantic network** | Neo4j | People, traits, constraints, preferences, and the edges between them — the relationship graph | One graph namespace **per agent**; no cross-agent edges in the core product |
| **Embedding space** | pgvector + HNSW | Vector embeddings of node names, aliases, and deep-context descriptions for fast fuzzy/semantic match | Vectors partitioned by `agent_id`; queries always filtered to the caller's partition |

### 2.2 Why three stores

- SQL gives **deterministic, auditable** truth for anything billing- or compliance-sensitive.
- The graph gives **cheap multi-hop reasoning** ("who does John trust, who introduced them").
- Vectors give **name/entity disambiguation** without brittle exact-match logic.

The orchestrator keeps them consistent: SQL is the system of record for a fact's *baseline
value*; Neo4j holds its *relational context*; pgvector holds its *searchable representation*.
A write that touches more than one store is wrapped in a saga (see [§6.3](#63-consistency--the-write-saga)).

---

## 3. Ingestion — The Debrief Pipeline

Zero data-entry friction comes from the **agent debrief**, not from surveilling client calls.
The pipeline converts the agent's spoken narration into structured records and graph mutations.

```text
[Agent Voice: the debrief]
        │
        ▼
[Streaming STT]  ──►  [LLM Structured Parser]  ──►  [Context Schema Sink]
        │                                                    │
        │                                                    ▼
        │                                          [Graph State Mutations]
        │                                                    │
        └──────────────── live interception ◄────────────────┘
                         (contradiction handling)
```

> **Boundary invariant.** The audio source is always the agent's own debrief session. There is
> no code path that ingests a third party's voice. Any feature request implying client-call
> capture must be rejected at design review.

### 3.1 Stages

1. **Streaming STT** — low-latency partial transcripts as the agent speaks.
2. **LLM structured parser** — a fast, cheap model extracts entities, attributes, and candidate
   graph mutations into a strict schema (see [§4](#4-data-model)).
3. **Context schema sink** — validates the parse, resolves entities ([§5](#5-entity-resolution)),
   and stages mutations.
4. **Graph state mutations** — committed via the write saga after entity resolution passes.

### 3.2 The Live Interception State Machine (Challenge Loop)

When the parser detects a semantic contradiction mid-debrief (e.g. a budget or location shift),
ingestion pauses and the AI asks the agent to explain — capturing the *narrative*, not just the
new value.

```text
[Normal Debrief] ──► Contradiction Detected ──► [Freeze Ingestion]
       ▲                                                │
       │                                                ▼
[Resume Debrief] ◄── User Resolution ◄── [Inject VUI Prompt: "why the change?"]
```

- **Freeze ingestion.** Downstream graph writes for the contradicting field are held.
- **Inject VUI prompt.** A prioritized instruction goes to TTS, e.g. *"Ask why the budget moved
  from 3B to 5B."*
- **User resolution.** The answer is tagged `is_conflict_resolution: true` and the resulting
  fact is written with a **0.95 baseline confidence** because a human explicitly verified it.

---

## 4. Data Model

The core object is a **Fact** — never a bare value. Every fact carries provenance and a
confidence score so the reasoning plane can decide how much to trust it and when it is stale.

### 4.1 Fact object (canonical)

```json
{
  "fact_id": "fct_9c2a...",
  "agent_id": "agt_001",
  "entity": "Budget",
  "subject_node_id": "node_client_john",
  "value": { "amount": 5000000000, "currency": "IRT" },
  "confidence_score": 0.95,
  "source": "voice_debrief",
  "is_hypothesis": false,
  "is_conflict_resolution": true,
  "created_at": "2026-07-10T16:30:00Z",
  "superseded_by": null
}
```

- `is_hypothesis` — true when the agent speculates ("I *think* he wants…").
- `superseded_by` — points to the fact that replaced this one; old facts are **never deleted**,
  preserving the temporal moat.

### 4.2 Conditional / fuzzy numeric fields

Real speech is messy: *"around 3–4 billion, maybe 5 if his bonus comes through."* The parser
emits a **conditional field** rather than forcing a single number.

```json
{
  "field_name": "purchasing_power",
  "base_metric":    { "value": 3500000000, "currency": "IRT" },
  "ceiling_metric": { "value": 5000000000, "currency": "IRT" },
  "variables": [
    {
      "trigger_condition": "company_bonus_payout",
      "impact": "increases_ceiling",
      "associated_node_id": "node_trait_bonus_2026"
    }
  ]
}
```

The **base metric** is written to PostgreSQL as the safe, queryable baseline. The **conditional
branch** is attached to Neo4j as an edge to a trait node, so the record stays clean *and*
reasoning can later fire when the trigger resolves.

### 4.3 Graph schema (core node & edge types)

| Kind | Type | Notes |
|---|---|---|
| Node | `Person` | Client, spouse, lawyer, referrer, etc. Carries aliases for disambiguation |
| Node | `Trait` | Preference, life event, hobby, condition-trigger |
| Node | `Constraint` | e.g. *Do-Not-Disturb: high workload*, with a time window |
| Edge | `RELATES_TO` | Person↔Person, typed (`spouse`, `attorney`, `referred_by`) |
| Edge | `HAS_TRAIT` | Person→Trait, carries `fact_id` + confidence |
| Edge | `CONSTRAINED_BY` | Person→Constraint, gates ghost-mode output |
| Edge | `DECIDES_FOR` | Person→Person (captures the real decision-maker) |

---

## 5. Entity Resolution & Ambiguity Matrix

Common names ("Ali") must resolve to the right node without adding latency or silently merging
two different people.

```text
              [Incoming Entity Input]
                        │
                        ▼
          ┌───────────────────────────┐
          │ Context Enrichment Lookup │
          └─────────────┬─────────────┘
                        ▼
          ┌───────────────────────────┐
          │ Tri-Factor Scoring Filter │
          └─────────────┬─────────────┘
                        ▼
                 [Match Score]
             ╱          │          ╲
      ≥ 0.85       0.45–0.85        < 0.45
        ╱               │              ╲
[Upsert & Merge]  [Flag to VUI]   [Create new node]
```

### 5.1 Scoring formula

```
Match Score = w1 · JaroWinkler(name)
            + w2 · Jaccard(local_graph_overlap)
            + w3 · exp(−λ · Δt)
```

- **`JaroWinkler(name)`** — string similarity between the spoken token and a node alias.
- **`Jaccard(local_graph_overlap)`** — shared neighbors (same lawyer, same neighborhood) between
  the mention's context and the candidate node.
- **`exp(−λ · Δt)`** — recency decay; nodes touched recently score higher.

### 5.2 Thresholds

| Score | Action |
|---|---|
| **≥ 0.85** | Instant automatic upsert & merge |
| **0.45 – 0.85** | Ambiguity — queue a VUI clarification: *"Ali Hosseini from Ferhadije, or Ali Rezai?"* |
| **< 0.45** | Create a new isolated node immediately |

Weights `w1, w2, w3` and decay `λ` are configuration, tuned per locale, and versioned in the
relational store so scoring is reproducible.

---

## 6. Reasoning Plane — Event-Driven Ghost Mode

The reasoning engine never scans the whole database. It reacts to graph changes via a broker.

```text
[Graph State Mutation] ──► [Kafka Topic] ──► [Reasoning Consumer]
                                                    │
                                                    ▼
[User Action Feed] ◄── [Ghost-Mode Synthesis] ◄── [Constraint Check]
```

### 6.1 Action lifecycle

1. **Mutation event.** e.g. *"John's wife is expecting a baby"* → a `HAS_TRAIT` edge is added.
2. **Kafka ingestion.** The mutation is published to a per-agent-partitioned topic.
3. **Constraint filtering.** The consumer inspects adjacent edges. If a
   `CONSTRAINED_BY → Do-Not-Disturb` edge is active, it **logs the opportunity window but
   suppresses all outward suggestions** until the window clears.
4. **Ghost-mode synthesis.** With no blocking constraint, a fine-tuned LLM reads the relevant
   sub-graph and produces a high-prestige script and, where relevant, a gifting suggestion —
   for the **agent to execute themselves**. The system never contacts the client.

### 6.2 Constraint gating (worked example)

```text
[John] ──(HAS_TRAIT)──► [Expecting a baby]        ← opportunity
[John] ──(CONSTRAINED_BY)──► [Do-Not-Disturb: high workload, until 2026-07-28]

Result: opportunity stored, suggestion HELD until 2026-07-28, then released.
```

### 6.3 Consistency — the write saga

A debrief mutation can touch SQL + Neo4j + pgvector. The orchestrator runs a saga:

1. Write baseline fact to Postgres (source of truth).
2. Apply graph mutation in Neo4j.
3. Upsert embedding in pgvector.
4. Emit the Kafka event **only after** 1–3 succeed.

If any step fails, prior steps are compensated and the event is not emitted, so the reasoning
plane never fires on a half-written state.

---

## 7. API Surface

REST/JSON over HTTPS, versioned under `/v1`. Every request is scoped to the authenticated
agent; there is no cross-agent read path in the core product. Auth is OAuth2 bearer + short-lived
JWT carrying `agent_id`.

### 7.1 Core endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/debriefs` | Start a debrief session; returns a session + WebSocket URL for streaming audio |
| `GET` | `/v1/debriefs/{id}` | Session status, transcript, and staged mutations |
| `POST` | `/v1/debriefs/{id}/resolve` | Submit a Challenge-Loop resolution answer |
| `GET` | `/v1/nodes` | List/search relationship nodes (vector-backed) |
| `GET` | `/v1/nodes/{id}` | Full node profile: facts, traits, constraints, edges |
| `GET` | `/v1/nodes/{id}/context` | Depth-2 sub-graph for a client dashboard (hot-cache read) |
| `GET` | `/v1/feed` | Ghost-mode action feed (ranked, constraint-filtered) |
| `POST` | `/v1/feed/{id}/ack` | Mark a suggestion actioned/dismissed (training signal) |
| `GET` | `/v1/constraints` / `POST` | Read/set do-not-disturb and other gating windows |
| `POST` | `/v1/crm/writeback` | Push clean structured notes back to the external CRM |

### 7.2 Ambiguity resolution response (example)

```json
{
  "type": "ambiguity",
  "field": "person_reference",
  "spoken_token": "Ali",
  "candidates": [
    { "node_id": "node_ali_hosseini", "score": 0.71, "hint": "Ferhadije" },
    { "node_id": "node_ali_rezai",    "score": 0.68, "hint": "attorney" }
  ],
  "vui_prompt": "Ali Hosseini from Ferhadije, or Ali Rezai?"
}
```

### 7.3 CRM write-back contract

The overlay wedge depends on pushing **clean notes** into the agent's existing CRM (Follow Up
Boss, kvCORE, etc.) via webhook. Write-back is one-directional (URIE → CRM), idempotent
(keyed on `fact_id`), and never exports the raw graph — only human-readable summaries — which
also protects the [relational moat](STRATEGIC_BUSINESS_MODEL.md).

---

## 8. Non-Functional Requirements & Capacity

### 8.1 Latency budgets (design targets)

```text
[App Action]                                  [Debrief Audio Turn]
     │                                                │
     ▼                                                ▼
[Redis hot read]   ~15ms                     [STT → LLM → TTS]
     │                                                │
     ▼                                                ▼
[Neo4j depth-2]    ~35ms                     [End-to-end audio] < 1.2s
     │
     ▼
[UI render]        < 100ms total
```

| Path | Target | Rationale |
|---|---|---|
| Hot-cache dashboard read (Redis) | **< 15 ms** | Client card must feel instant |
| Graph traversal, depth ≤ 2 (Neo4j) | **< 35 ms** | Keeps match + context fast |
| Total UI render | **< 100 ms** | Perceived as immediate on mobile |
| End-to-end VUI turn (STT→LLM→TTS) | **< 1.2 s** | Natural phone rhythm, no awkward gaps |

> These are targets. Validate under realistic concurrency; the VUI budget in particular depends
> on vendor round-trip times outside our control.

### 8.2 Capacity & cost invariant

Because debriefs are capped at **1–2/day per agent** and batched, per-agent voice minutes are
bounded and predictable. This cap is the **primary gross-margin lever** and must not be silently
relaxed by product changes without re-running the cost model in `STRATEGIC_BUSINESS_MODEL.md`.

### 8.3 Scaling posture

- Stateless API + ingestion workers scale horizontally.
- Kafka topics partitioned by `agent_id` for ordered, isolated per-agent processing.
- Neo4j per-agent namespaces keep traversals small regardless of total tenant count.
- Reasoning is asynchronous, so ingestion latency is never coupled to synthesis time.

---

## 9. Security, Privacy & Compliance

The platform stores **special-category personal data about third parties** (clients' family,
health, financial situation). The operator is EU-based, so this is treated as **GDPR-governed
from day one**, not as an afterthought.

- **Isolation.** Per-agent row-level security in Postgres; per-agent graph namespaces in Neo4j;
  partitioned vectors. No core code path crosses agent boundaries.
- **Data-subject rights.** Because facts are versioned (`superseded_by`) rather than mutated in
  place, export and erasure operate on a traceable history; erasure tooling must also purge
  embeddings and Kafka-retained payloads.
- **Recording boundary.** Only agent↔AI audio is processed; client-call capture is architecturally
  excluded (see [§3](#3-ingestion--the-debrief-pipeline)).
- **Lawful basis & roles.** The agent↔platform relationship (controller vs. processor for the
  client data) and the lawful basis for special-category data are **open legal questions** and
  must be settled with counsel before launch. This spec does not resolve them.
- **Encryption.** TLS in transit; encryption at rest for all three stores and for stored audio;
  audio retained only as long as needed to produce the parse, then purged on a fixed schedule.

---

## 10. Technology Stack (candidates)

| Layer | Candidate | Chosen for | Confirm |
|---|---|---|---|
| Relational | PostgreSQL | RLS, JSONB, mature ecosystem | EU-region hosting + backup/restore SLAs |
| Graph | Neo4j | Native multi-hop traversal | Licensing at single-tenant scale; namespace isolation approach |
| Vector | pgvector (HNSW) | Co-locates with Postgres, one less system | Recall/latency at expected node counts |
| Cache | Redis | Sub-15ms hot reads | Eviction policy for dashboard payloads |
| Broker | Kafka | Ordered, partitioned event streams | Kafka vs. lighter broker for early scale |
| STT | Deepgram / Whisper-class | Streaming, low latency | Per-minute cost + EU processing |
| Extraction LLM | Fast/cheap model (Flash/mini-class) | High-volume structured parse | Accuracy on messy multilingual speech |
| Reasoning LLM | Frontier model, batched | Deep sub-graph synthesis | Cost per synthesis at real volume |
| TTS | ElevenLabs-class | Natural debrief voice | Per-minute cost + latency |

> Every row is a **candidate**. Nothing here is committed until confirmed against current
> pricing, EU data-residency, and measured latency.

---

## 11. Future Work — The Mesh Path

Deferred, not designed-in. Kept here so the core doesn't accidentally foreclose it.

- **Syndicate Mesh (team topology).** Multiple agents securely sharing a regional market graph
  without leaking private personal context. Would require: cross-agent edge types with
  per-edge visibility ACLs, a graph-role/token model, and a redesign of the isolation invariants
  in [§2](#2-the-tri-engine-data-fabric) and [§9](#9-security-privacy--compliance). **Do not
  build until the solo motion is validated.**
- **Network-overlap detection** (Agent A's contact ↔ Agent B's prospect) depends on the above.

---

## 12. Changelog

| Version | Change |
|---|---|
| 2.0 | Aligned to Solo business model: removed Syndicate Mesh from core, excluded client-call streaming, made debrief cadence a cost invariant. Added data model, API surface, tech-stack candidates, GDPR section, and Future-Work mesh path |
| 1.0 | Original tri-engine spec with Syndicate Mesh and live phone-stream ingestion |

---

*End of technical specification · v2.0*