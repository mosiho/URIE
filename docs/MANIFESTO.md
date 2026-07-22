# Relationship Intelligence (RI) Platform

**An autonomous voice-debrief memory layer for high-value client relationships.**

| | |
|---|---|
| **Beachhead vertical** | Solo high-value real estate agents |
| **Document version** | 2.0 (supersedes v1.0) |
| **Status** | Working strategy — figures require independent verification |

---

## Contents

0. [A Note on This Version](#0-a-note-on-this-version)
1. [Executive Summary & Category Definition](#1-executive-summary--category-definition)
2. [The Real Differentiator](#2-the-real-differentiator)
3. [Ideal Customer Profile](#3-ideal-customer-profile)
4. [The Core Loop](#4-the-core-loop)
5. [Architecture & Data Engine](#5-architecture--data-engine)
6. [Reasoning & Recommendation Logic](#6-reasoning--recommendation-logic)
7. [Monetization — Solo Tier](#7-monetization--solo-tier)
8. [Go-To-Market — the Overlay Wedge](#8-go-to-market--the-overlay-wedge)
9. [Defensibility — the Relational Moat](#9-defensibility--the-relational-moat)
10. [Open Risks & What to Validate First](#10-open-risks--what-to-validate-first)

---

## 0. A Note on This Version

This document replaces the original manifesto. Four structural decisions changed the model and are reflected throughout:

1. **Debrief cadence is now bounded** — at most one to two calls per day, user-configurable — rather than one call per interaction.
2. **Recording scope is limited** to the conversation between the agent and our own AI. We never record the agent's calls or meetings with clients or third parties.
3. **Pricing collapses** to a single solo-agent tier, benchmarked against what solo agents actually pay today.
4. **Positioning sharpens** from "knowledge graph vs. database" to a concrete promise: we capture the conversation that never got written down.

---

## 1. Executive Summary & Category Definition

The product is **not** a CRM, a note-taking app, or a meeting transcription tool. It defines an adjacent category — **Relationship Intelligence (RI)** — that sits on top of the CRM an agent already uses, rather than replacing it.

### The paradigm shift

| Traditional CRMs | This platform |
|---|---|
| **Systems of Record** | **Systems of Intelligence** |
| Static databases that only ever hold what a human took the time to type | An event-driven engine that captures, structures, and reasons about the fluid state of a relationship — including the things that were never written anywhere |

### Core thesis

> High-value relationships are won on details that never make it into a CRM field. The agent who remembers them wins. We make that memory automatic.

### The mission

To build a living, autonomous second brain that maintains, reasons about, and grows an agent's high-value network — **without adding a single minute of data-entry fatigue**.

---

## 2. The Real Differentiator

The competitive landscape is crowded, but the crowd clusters around one activity: **organizing digital exhaust** — email, calendar, MLS records, CRM fields. Every tool in that cluster is powerful, and every tool can only see what was already captured somewhere.

The mechanism is a knowledge graph, but **the graph is not the pitch**. The pitch is the promise a client feels: that their agent remembered the thing they mentioned once, in passing, months ago.

---

## 3. Ideal Customer Profile

**Beachhead:** solo, high-value real estate agents.

- High-ticket, low-frequency transactions where a single remembered detail can swing a deal.
- Trust- and emotion-driven relationships rather than transactional ones.
- Highly mobile — they run their day from a phone, rarely from a desk.
- Structurally poor at manual software upkeep, and aware of it.

### Future verticals (post-validation)

Venture investors, executive recruiters, wealth advisors, corporate lawyers, and enterprise sales leaders — all networks where relational memory compounds into revenue.

> These stay **explicitly out of scope** until the solo real-estate motion is proven.

---

## 4. The Core Loop

The platform runs a continuous, self-reinforcing flywheel. The change from v1 is at the top of the loop: the trigger is now **time-bounded and batched**, not fired per event.

```
Real-world interactions accumulate through the day
        |
        v
Bounded debrief (<= 1–2×/day, user-set)
  → AI interviews the agent, not the client
        |
        v
Knowledge extraction
  → updates structured DB + knowledge graph
        |
        v
Reasoning engine
  → evaluates sentiment shifts, constraints, contradictions
        |
        v
Ghost-mode recommendation
  → script the agent executes themselves
```

---

## 5. Architecture & Data Engine

### 5.1 The Ingestion Engine — the Debrief Call

Rather than background-scraping the agent's messages (which breaks OS sandboxes, violates privacy, and invites legal risk), the system uses an **active debrief model**.

| | |
|---|---|
| **Trigger** | A configurable daily window, or the agent tapping "debrief now." Bounded at one to two calls per day. |
| **Action** | The AI initiates a short outbound call or voice-note exchange with the agent. |
| **Pattern** | A dynamic, targeted interview driven by known knowledge gaps — not a static questionnaire. It asks about what it doesn't yet understand. |

### 5.2 Dual-Layer Storage

- **Structured DB** — queryable facts, constraints, and CRM-ready fields.
- **Knowledge graph** — entities, relationships, behavioral traits, and temporal edges that compound over time.

### 5.3 Meta-Attributes of Memory

Every datum is a dynamic object, not a flat value, so the system can reason about how much to trust it and when it may be stale:

```json
{
  "entity": "Budget",
  "value": "EUR 5,000,000",
  "confidence_score": 0.98,
  "source": "Voice debrief",
  "timestamp": "2026-07-10T16:30:00Z",
  "is_hypothesis": false
}
```

---

## 6. Reasoning & Recommendation Logic

### 6.1 Operational vs. relational splitting

The engine classifies every insight into one of two streams:

| Stream | Nature | Example |
|---|---|---|
| **Operational constraints** (transactional) | Explicit blocks and triggers | "Don't contact next week — workload is high." The system locks out automated recommendations during that window. |
| **Relational traits** (human) | Personal and psychological context | A child on the way, a move driven by a life change, specific tastes and hobbies. |

### 6.2 Conflict-resolution loop

When new input contradicts stored data, the AI **never silently overwrites**. It challenges the contradiction live.

This captures the human narrative behind the data shift — a buyout, a spouse's preference, a changed timeline — preserving an accurate **trajectory** of the relationship rather than just its latest snapshot.

### 6.3 Ghost mode

The system stays entirely in the background. It **never contacts the client**. It hands the agent a hyper-personalized script and the reasoning behind it, so the agent executes the moment themselves and keeps all the relational credit.

> The output is prestige for the agent, never a robotic touchpoint for the client.

---

## 7. Monetization — Solo Tier

The three-tier structure from v1 is retired. Launch is a **single, simple solo-agent plan**, priced against what solo agents already spend.

### 7.1 Market anchors (2026)

- Solo agents typically spend roughly **$30–$150 / month** on CRM tooling.
- **Follow Up Boss** — the default CRM for many agents — starts around **$69 / user / month** on its entry plan.
- The closest overlay comparable (an AI agent that layers on top of the existing CRM) markets tiers at roughly **$99 / $219 / $349 / $599** per month.

### 7.2 The plan

**$99 / month** — solo agent.

$99 sits at the entry price of the nearest overlay comparable and comfortably inside existing solo spend, so it reads as an easy "yes" rather than a new budget line.

Defer per-minute overage pricing and any gifting-marketplace margin until core usage is validated — they add pricing-page complexity before there is a product people are paying for.

---

## 8. Go-To-Market — the Overlay Wedge

The hardest objection in this market is *"we already have a CRM and won't migrate."* The wedge sidesteps it entirely by **not asking anyone to migrate**.

### Phase 1 — the intelligence layer (zero data migration)

**Pitch:** *"Keep the corporate CRM your brokerage requires. Use us to actually win the client."*

**Execution:** we read contact names from the existing CRM, run the debriefs, build the intelligence graph on our side, and push clean, structured notes back into the corporate CRM via webhooks. The agent gets the second brain without changing the company's tech stack.

### Phase 2 — the prestige growth loop

When an agent remembers a client's specific personal milestone or boundary at exactly the right moment, the client feels a world-class relationship. That client refers other high-net-worth people; the agent, asked how they do it, shares their "secret weapon" within their boutique circle. Acquisition becomes peer-to-peer and organic.

---

## 9. Defensibility — the Relational Moat

Features get copied. The asset that compounds — and creates steep switching costs — is the **accumulated relational memory** itself.

| Moat | Why it sticks |
|---|---|
| **Multi-relational knowledge graph** | A 3D graph of behavioral traits, interconnected networks, and confidence-decay parameters does not export cleanly to a flat CSV the way a contact list does. |
| **Compound confidence engine** | Over months, the system masters the specific nuances of an agent's network. Leaving means losing a trained cognitive model of that exact book of business. |
| **Temporal data moat** | By recording how preferences, budgets, and life states evolve over years, the platform builds a behavioral timeline no new entrant can reconstruct on day one. |

---

## 10. Open Risks & What to Validate First

The strategy is sound; these are the assumptions that decide whether it works. Each should be tested **before scaling spend**.

| # | Assumption to validate | Why it matters |
|---|---|---|
| 1 | Agents will take a daily debrief call (≤1–2×/day) without feeling it as more work | Top-of-funnel habit; if cadence fails, the flywheel never spins |
| 2 | Voice debrief yields richer relational data than typed CRM notes | Core product thesis |
| 3 | Ghost-mode scripts produce measurable lift in client response / referral | Proof that intelligence → revenue, not just "nice notes" |
| 4 | CRM overlay + webhook write-back is enough to close without migration | GTM wedge; if agents still demand a full CRM, positioning breaks |
| 5 | $99/mo clears willingness-to-pay for solo high-value agents | Monetization anchor |

---

*End of manifesto · v2.0*
