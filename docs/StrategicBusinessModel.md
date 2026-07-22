# Strategic Business Model Document

> **Category:** Relationship Intelligence (RI) Platform
> **Beachhead vertical:** Solo, high-value real estate agents
> **Document version:** 2.0 (supersedes v1.0)
> **Status:** Working strategy — figures are directional and require independent verification before use.

---

## 0. Reading Notes (for humans and machines)

This file is the machine-readable strategy document for the project. It is intended to sit
in the project root and be read by tooling, agents, and contributors as the single source of
truth for **why the product exists** and **how it makes money**. Architecture and API specs
live in separate documents.

**Four structural decisions define this version** (changed from v1):

1. **Debrief cadence is bounded** — at most 1–2 calls per day, user-configurable — not one call per interaction.
2. **Recording scope is limited** — only the conversation between the agent and our own AI is recorded. We never record the agent's calls or meetings with clients or third parties.
3. **Pricing collapses to a single solo-agent tier**, benchmarked against what solo agents actually pay today.
4. **Positioning sharpens** from "knowledge graph vs. database" to a concrete promise: *we capture the conversation that never got written down.*

> ⚠️ **Verification note.** Pricing figures and competitor tiers below are drawn from public
> 2026 market sources and vendor marketing pages. They are directional benchmarks, not audited
> numbers. Unit-cost assumptions must be re-quoted against live vendor pricing, and all
> data-protection points must be reviewed with qualified legal counsel before launch.

---

## 1. Executive Value Proposition

Traditional SaaS tools are **Systems of Record** — passive repositories that only ever hold
what a human took the time to type. This platform is a **System of Intelligence** — an
autonomous agent that acts as a proactive chief of staff for a human network, and that
captures the things which never made it into any system at all.

It does **not** replace the CRM. It sits **on top of** the CRM the agent already uses.

### 1.1 The Value Matrix

| Dimension | Traditional CRM | Relationship Intelligence Platform |
|---|---|---|
| **Friction** | Manual data entry, typing, form-filling | Zero entry — a short voice debrief captures data by speech |
| **Data structure** | Flat tables, isolated contact cards, text notes | Knowledge graph linking people, traits, contexts, and temporal events |
| **Focus** | Pipeline metrics, deal stages, tasks | Relational health, trust, prestige, cognitive memory |
| **Output** | Static reminders ("Call John today") | Behavioral scripts ("Call John — his busy week just ended; mention X to show you remembered") |
| **Visibility** | Only what was typed somewhere | Also what was *said* and never written down |

---

## 2. The Real Differentiator

The market is crowded, but competitors cluster around one activity: **organizing digital
exhaust** (email, calendar, MLS, CRM fields). Every one of them can only see what was already
captured somewhere.

| Competitor class | What it actually does | What it cannot see |
|---|---|---|
| **AI CRM overlays** (e.g. B.Claw) | Reads Gmail, calendar, MLS, CRM to draft emails, CMAs, morning briefings referencing existing contacts | Anything the agent didn't already type or send digitally |
| **Predictive enrichment** (e.g. Likely.AI) | Statistically scores which contacts are likely to sell within ~90 days; enriches missing fields | The human narrative — *why* someone is moving, who decides, what they care about |
| **Built-in CRM AI** (Lofty, kvCORE) | Lead scoring, drip-plan selection, 24/7 texting assistants for inbound leads | Relationship memory. It automates the pipeline, not the relationship |

> **Positioning line:**
> **Everyone else organizes what your CRM already knows. We remember what your CRM never even saw — the conversation that never got written down.**

The knowledge graph is the *mechanism*, not the pitch. The pitch is the promise a client
feels: that their agent remembered the thing they mentioned once, in passing, months ago.

---

## 3. Ideal Customer Profile (ICP)

**Beachhead:** solo, high-value real estate agents.

- High-ticket, low-frequency transactions where a single remembered detail can swing a deal.
- Trust- and emotion-driven relationships rather than transactional ones.
- Highly mobile — they run their day from a phone, rarely from a desk.
- Structurally poor at manual software upkeep, and aware of it.

**Future verticals (post-validation, explicitly out of scope for now):** venture investors,
executive recruiters, wealth advisors, corporate lawyers, enterprise sales leaders — all
networks where relational memory compounds into revenue.

---

## 4. Monetization & Pricing Architecture

The three-tier structure from v1 is retired. Launch is a **single, simple solo-agent plan**,
priced against what solo agents already spend.

### 4.1 Market anchors (2026, directional)

- Solo agents typically spend roughly **$30–$150 / month** on CRM tooling.
- Follow Up Boss — the default CRM for many agents — starts around **$69 / user / month** on its entry plan.
- The closest overlay comparable (an AI agent layered on top of the existing CRM) markets tiers at roughly **$99 / $219 / $349 / $599** per month.

### 4.2 The launch plan

| Plan | Price | Includes |
|---|---|---|
| **Solo** (launch tier) | **~$99 / mo** (billed annually) | Full voice-debrief engine · core knowledge graph · relational sentiment tracking · daily ghost-mode script feed · up to ~150 active relationship nodes · write-back of clean notes to the agent's existing CRM |

**Rationale.** $99 sits at the entry price of the nearest overlay comparable and comfortably
inside existing solo spend, so it reads as an easy "yes" rather than a new budget line.

**Deferred until core usage is validated:**

- Per-minute conversational overage pricing.
- Concierge gifting marketplace margin.

> These add pricing-page complexity before there is a product people are paying for. Ship the
> single tier first.

### 4.3 Cost & margin (treat as a model, not a fact)

The voice pipeline (telephony → speech-to-text → extraction LLM → nightly reasoning LLM →
text-to-speech) carries a real per-user cost that scales with debrief minutes. **Bounding
cadence to 1–2 calls/day is itself the primary margin lever.** Re-quote every vendor line
against live pricing before publishing any gross-margin figure — the tidy ~90% number from v1
was illustrative, not verified.

---

## 5. Go-To-Market — The Overlay Wedge

The hardest objection in this market is *"we already have a CRM and won't migrate."* The wedge
sidesteps it by **not asking anyone to migrate**.

### Phase 1 — The intelligence layer (zero data migration)

- **Pitch:** "Keep the corporate CRM your brokerage requires. Use us to actually win the client."
- **Execution:** read contact names from the existing CRM → run the debriefs → build the
  intelligence graph on our side → push clean, structured notes back into the corporate CRM
  via webhooks. The agent gets the second brain without changing the company's tech stack.

### Phase 2 — The prestige growth loop

When an agent remembers a client's specific personal milestone or boundary at exactly the
right moment, the client feels a world-class relationship. That client refers other
high-net-worth people; the agent, asked how they do it, shares their "secret weapon" within
their boutique circle. Acquisition becomes peer-to-peer and organic.

---

## 6. Structural Defensibility — The Relational Moat

Features get copied. The asset that compounds — and creates steep switching costs — is the
accumulated relational memory itself.

1. **Multi-relational knowledge graph.** A graph of behavioral traits, interconnected
   networks, and confidence-decay parameters does not export cleanly to a flat CSV the way a
   contact list does.
2. **Compound confidence engine.** Over months, the system masters the specific nuances of an
   agent's network. Leaving means losing a trained cognitive model of that exact book of business.
3. **Temporal data moat.** By recording how preferences, budgets, and life states evolve over
   years, the platform builds a behavioral timeline no new entrant can reconstruct on day one.

---

## 7. Open Risks & What to Validate First

The strategy is sound; these assumptions decide whether it works. Test each before scaling spend.

| Risk | Why it matters | How to de-risk |
|---|---|---|
| **Debrief adoption** | The whole engine starves if agents won't take the call consistently | Pilot the bounded 1–2x/day cadence with real solo agents; measure answer + completion rate before anything else |
| **Data protection** | Storing clients' personal and special-category data (health, family, finances) puts you under GDPR as controller, EU-based | Legal review of lawful basis, special-category handling, retention, and the agent-as-processor relationship |
| **Unit economics** | Voice pipelines are the cost center; margins are unproven at real usage | Re-quote every vendor line; model cost at the actual cadence cap before publishing margins |
| **Differentiation drift** | Competitors could add "voice memory" as a feature | Move fast on the temporal/confidence moat — the part that can't be shipped overnight |

> **The single most important thing to validate:** will a busy solo agent take a short AI
> debrief call once or twice a day, indefinitely? Everything downstream — the graph, the moat,
> the margins — depends on that one behavioral "yes."

---

## 8. Changelog

| Version | Change |
|---|---|
| 2.0 | Bounded debrief cadence; recording limited to agent↔AI; single solo pricing tier; sharpened differentiator; added competitor analysis, market anchors, and open-risks section |
| 1.0 | Original three-tier model with per-interaction debrief calls |

---

*End of strategic business model document · v2.0*