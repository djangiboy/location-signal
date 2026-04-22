# Solution Frame — Location Signal Integrity

**Drafted:** 2026-04-21
**Author:** Maanas (articulated draft by agent; content is Maanas's intent)
**Predecessor:** `possible_architecture.txt` (raw notes)
**Backbone:** `master_story.md` + `master_story.csv`
**Scope:** capability-level frame. Not an engineering design. Not a system spec.

---

## How to read this

This is a **solution frame**, not a system design. It names WHAT the system does at the capability and signal layer — not HOW any component is built. Engineering concerns (decay mechanics, confidence bands, write-contracts, state management, retry logic, intervention-specific trigger design) are explicitly out of scope. They land when components are built.

A system spec — including which capability lives in which OS, how packets flow between systems, and contract rules — comes later, when we move from frame to solutioning.

---

## Promise Maker — what it is today

The Promise Maker is Wiom's commitment engine: it decides whether Wiom promises to install internet at a customer's home, based on the GPS coordinates captured at booking time. Today:

- Input: a single `booking_lat/lng` captured when the customer submits the fee
- Gate: `distance(booking_lat/lng, nearest historical install or splitter) ≤ 25m` — a binary infrastructure-proximity test
- On pass: the promise is made, the fee is captured, the lead flows to Allocation

Promise Maker also has an R&D belief model — **`promise_maker/B/`** — a full ML pipeline that models partner behaviour across geographies (install/decline history, supply-efficiency hex grid, partner cluster boundaries in `partner_cluster_boundaries.h5`, cause-coded learning). **This belief model is built but not deployed** — it is not consulted by the production 25m gate.

---

## The structural problem in one sentence

Wiom promises on a single un-interrogated GPS fix, keeps no record of the customer's structured knowledge (landmark, gully, floor, locality), and never shows the partner a customer-verified address before asking them to decide.

---

## What the master story surfaced

Three orphan knowledge stocks, one loop that closes theoretically (in R&D), one open loop.

### Three orphan stocks (exist in the world, unconsumed by Promise Maker in production today)

1. **Customer mental model.** Landmark, gully, floor, locality, nearest visible markers. Wiom captures none of this before committing. Master story C.C: 46% of `address_not_clear` calls are one-sided — customer is clear, partner is confused. Structure exists at the source; we never elicit it.

2. **Partner serviceability intelligence.** Master story C.D: install rate **+16.7pp inside vs outside** (55.3% vs 38.6%); gali-stuck × outside-polygon = **25.4% install** (the sharpest single-cell gap in the audit). Two things exist in R&D but are not deployed to production:
   - **Partner serviceable boundaries** — polygons built from each partner's SE-weighted install/decline history, stored in `partner_cluster_boundaries.h5`. Feeds the belief model.
   - **The Promise Maker belief model itself** (`promise_maker/B/`) — an ML pipeline that already models partner behaviour across geographies using install + decline edges. The entire B-layer is an orphan: built, tested, not consulted at promise time.

   **Note on the belief model's integrity.** The Composite score and GNN are built on partner-side decision edges (accept, decline). These express partner willingness to serve a geographic area — a signal generated independently of whether the customer's submitted GPS was accurate. Customer-side noise is an input-side issue, not a signal-side one. Activating the B-layer in production does not require customer-side capture to be clean first; the two workstreams are orthogonal. Cleaner captures will sharpen the model's precision over time, not resurrect it from corruption.

   **The master story validates this independently:**
   - **Install rate separates 44pp across coord-distance deciles** — partners respond systematically to coord-based geometry.
   - **Area-decline rate ladders monotonically pre-accept (19.64pp on distance, 23.43pp on GNN prob)** — partners decline far or unfamiliar areas before seeing anything else.
   - **The GNN's +3.79pp edge on area-decline concentration** reflects partner-specific area knowledge picked up from install + decline history, beyond what raw geometry carries.
   - **At notification time, text address is hidden until click-through** (master story C.A) — so decline decisions are literally made without any text input. The signal that ladders across deciles is pure partner-will about real geography, not text-reading.

3. **Per-mobile jitter profile.** Stage A computed worst-case jitter for 8,317 mobiles; 70% worst-case ≤25m. A repeat mobile has a knowable jitter prior; Promise Maker doesn't read it.

### The one loop that closes (theoretically, in R&D)

In the R&D models, install outcomes flow back into the supply-efficiency hex grid, which updates partner boundaries on the next snapshot. In production, where these models aren't consulted, this loop is not operating.

### The one loop that does NOT close

Install outcomes do NOT flow back to the capture apparatus. The single GPS fix, the post-payment free-text address, and the booking UX never receive signal from how drift or address-discovery played out downstream — whether in R&D or production.

### Data grounding (all from `master_story.md`)

- **25.7% of installs** drift beyond Stage A apparatus p95 (154.76m). This fraction cannot be produced by GPS physics. Cause #2: customer captured GPS from not-home. Two sub-populations: near-home-but-not-home bulk (~22%) and hygiene tail (~3%).
- **40.7% of partner-customer pairs** have a location-reason first call (36.2% `address_not_clear` + 4.5% `partner_reached_cant_find`).
- **77.5% of ANC calls** end in confusion (46% one-sided partner-confused-customer-clear + 31.5% mutual).
- **Install time does not discriminate** address vs non-address call topics. Cost of address friction is paid in conversion, not in install hours.

---

## Solution anchors (non-negotiable invariants)

The frame fails if any of these break.

1. **No verification → no promise.** Promise Maker refuses if inputs cannot be verified. The 25m gate alone is not sufficient.
2. **Partners serve in zones around landmarks they recognize.** Serviceability is partner-specific and landmark-anchored, not only infrastructure-anchored.
3. **Customer gives GPS from home.** If they don't, the system has a corrective loop to elicit it properly before committing.
4. **Every signal the system consumes has a feedback channel visible to someone.** Customer-side signals route back to customer; partner-side signals route back to partner.
5. **The customer-confirmed landmark is a dual-purpose flow — first-class field downstream.** The same customer interaction (A3) that feeds Belief Model 1 at the gate must populate the partner notification (C1). Same capture, dual purpose. Without this propagation, the customer does the work but only Belief Model 1 benefits — leverage halves.

---

## System flow

The capabilities below chain together in five sequential stages, with a control pane running alongside. Each stage's output is the next stage's input; a failure at any stage routes to a corrective branch or rejects the booking.

```
            Customer inputs (GPS + landmark + gully/floor + photos)
                                    │
                                    ▼
            ┌──────────────────────────────────────────────┐
            │  1. GATE — input verification                │   ← A1–A9
            │     jitter check, landmark relatability,      │
            │     corrective loops, fallback text, photo    │
            └──────────────────────┬───────────────────────┘
                                   │  only verified inputs move downstream
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  2. BELIEF MODEL 1 — can we service this?    │   ← B1, B4, B5
            │     serviceability + confidence tier          │
            │     "can ANY partner service this booking,    │
            │      and at what confidence?"                 │
            └──────────────────────┬───────────────────────┘
                                   │  confidence tier
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  3. GOVERNANCE — tier-based decision          │   ← B2
            │     promise / defer / reject                  │
            └──────────────────────┬───────────────────────┘
                                   │  on promise
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  4. ACTIVE PROMISE EXPOSURE STOCK             │   ← B3
            │     bookings + confidence + landmark anchor   │
            └──────────────────────┬───────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  5. BELIEF MODEL 2 — who is the best partner?│   ← B6
            │     partner ranking for this booking          │
            │     "among eligible partners, who ranks       │
            │      highest to actually install?"            │
            └──────────────────────┬───────────────────────┘
                                   │                                ┌──────────────┐
                                   └──────────────────────────────► │ Partner-side │
                                                                    │  C1 – C7     │
                                                                    └──────┬───────┘
                                                                           │
                                   ┌◄──────────────────────────────────────┘
                                   │  on closure (install / cancel / decline)
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  6. IMMUTABLE MEMORY — full booking trace     │   ← D5
            │     GPS pings, landmarks, gully/floor,        │
            │     partner calls + topics + actions          │
            └──────────────────────────────────────────────┘

    ╔════════════════════════════════════════════════════════════════════════╗
    ║  CONTROL PANE — runs alongside all six stages                          ║
    ║  D1–D7: monitors, triggers interventions, trains both belief models    ║
    ║  back. night-GPS divergence · visit-tracking · customer-difficulty     ║
    ║  signals · on-ground assist · training loop · landmark confidence      ║
    ╚════════════════════════════════════════════════════════════════════════╝
```

### Stage-by-stage summary

1. **Gate — input verification** (capabilities A1–A9). Raw customer inputs arrive. Jitter profile checks, landmark relatability, gully/floor capture, photo, Street View confirmation. If any signal fails, the gate fires a corrective loop (A6/A7/A8) or triggers manual intervention. Only verified inputs move downstream.

2. **Belief Model 1 — can we service this?** (B1, B4, B5). Scores whether the booking can be serviced at all, and at what confidence. Answers the gate-side question. Inputs: partner-boundary containment, landmark match against partner-familiar landmarks, per-mobile jitter prior, partner team/executive GPS movement, inferred-or-contract-confirmed landmark serviceability. Output: confidence tier (high / mid / low).

3. **Governance — tier-based decision** (B2). Belief Model 1's output maps to a decision — promise / defer / reject. Defer routes to re-capture, manual check, or await partner availability. Reject exits the funnel.

4. **Active promise exposure stock** (B3). Promised bookings sit here with their confidence tier, landmark anchor, and dispatch state. This is the durable handoff point between promise-making and allocation.

5. **Belief Model 2 — who is the best partner?** (B6). A separate belief model running on top of the active promise stock. Answers the allocation-side question: among partners eligible to install this booking, who ranks highest? This is the existing GNN / Composite-score territory — enriched now with A3 landmarks, A4 gully/floor, B5 landmark-grounded serviceability, and B4 team-GPS signals. Output: ranked partner list for notification.

6. **Immutable memory on closure** (D5). When a booking closes — install, cancellation, or decline — the full trace lands in immutable memory: GPS pings, landmark picked, gully/floor, photos, partner calls and topics, partner actions. This memory feeds D3 (training) and D4 (landmark confidence accumulation), closing the learning loop back to **both** belief models — the gate-side serviceability model AND the allocation-side ranking model.

### The control pane (parallel to all stages)

Not a stage itself. Monitors signals across the pipeline and triggers interventions:

- **D1** — night-GPS vs booking-GPS divergence
- **D2** — partner visit-not-happened by SLA
- **D3** — install outcome → belief model training (closes loop to stages 1–2)
- **D4** — landmark confidence accumulation → sharpens A3's picker over time
- **D5** — immutable memory (the durable stock)
- **D6** — customer-side difficulty signals → interventions (slot change, direct contact, detail nudge)
- **D7** — partner on-ground navigation assist (real-time help)

---

## Solution capabilities

Capabilities are grouped by customer-facing / Promise-making / partner-facing / control-pane. The **Nature** column flags the type of change needed to ship: `BE` = backend (service / pipeline / data), `FE` = frontend (UI / UX flow), `CN` = content (copy, microcopy, messaging framing). A capability often spans multiple.

### A. Customer-facing capabilities (pre-promise)

| # | Capability | Nature |
|---|---|---|
| A1 | Capture GPS at booking time (home-GPS) | BE + FE |
| A2 | Capture GPS at night, passively (nightly pings) | BE + FE |
| A3 | **Show 3-5 nearby landmarks to the customer** (from public landmark data + Wiom install history — install-history anchors cover hyperlocal Indian landmarks like mandirs, kiranas, gali names that public data misses). Customer prompt: *"Which of these is within 2-3 min walk of your HOME specifically?"* **Requires ≥2 confirmations** (intersection of "near home" + "geographically literate" narrows to actual home; defuses the customer-booking-from-near-landmark-not-home case). Includes **20-25% false-landmark probes** for gaming defence — confirming a nonexistent landmark flags gaming. **Core mechanism:** landmark relatability is the at-home inference gate — if customer cannot confirm ≥2 landmarks after two rounds, fire A6. **Output is dual-purpose:** the same confirmed-landmark record feeds both Belief Model 1 (gate) and C1 (partner notification). | BE + FE + CN |
| A4 | Capture gully + floor as structured chat input | FE + CN |
| A5 | Capture home-exterior photo / short video (customer-uploaded) | BE + FE |
| A6 | **Corrective loop — two-round, structurally-different re-capture.** Round 1: A3 shows public-data landmarks. On all-denied: Round 2 uses Wiom install-history anchors (hyperlocal fallback). If Round 2 still fails: *"You're not at home — please go home and submit again."* **CRE callback available as a parallel path, not only post-failure** — customer can opt for human help at any point. Max N attempts → CRE_callback_queue (no infinite loop). **The re-capture itself must be structurally different from the initial capture** — not "confirm your earlier submission" (which invites doubling-down if customer is committed to a wrong location). Different surface area: force live GPS re-acquisition with stationary ≥10 seconds, accuracy self-report within threshold, time-of-day validation. | BE + FE + CN |
| A7 | **Fallback text capture.** When customer cannot relate to any shown landmark and A6 still fails, allow free-text landmark / locality input. Last-mile capture path. | FE + CN |
| A8 | **Jitter-handling path.** If the captured booking-GPS is flagged noisy (per-mobile jitter profile for repeat mobiles; `booking_accuracy` self-report for first-timers), customer is asked to recapture from open area, OR manual intervention triggered. | BE + FE + CN |
| A9 | **Google Street View pull for visual confirmation (customer-side).** Given the customer-submitted GPS, pull Street View imagery via Google API and show to customer: "is this your area?" On yes → stored as a confirmed visual anchor tied to the booking; later rendered to partner via C6 when he opens the booking to navigate. On no → route to A5 (customer uploads own photo) or A6 (re-capture GPS). On zero-coverage → skip to A5. | BE + FE + CN |
| A10 | **Structured address parsing (NER) for fallback text.** Open-source NER parser extracts structured fields — unit, building, landmark, locality, pincode — from free-text address input. Activated primarily when A7 (fallback text capture) fires because the customer couldn't relate to any shown landmark. NER-parsed fields flow to C1 but are **tagged with lower confidence** than customer-picked landmarks (A3). The partner sees that the address was parsed from text, not confirmed by the customer, and adjusts trust accordingly. | BE + FE |

### B. Promise-making capabilities

| # | Capability | Nature |
|---|---|---|
| B1 | **Belief Model 1 — can this booking be serviced?** Gate-side model. Scores serviceability ease per booking and outputs a confidence tier. Inputs: partner-boundary containment, customer-confirmed landmark match against partner-familiar landmarks, per-mobile jitter prior, partner team / executive GPS movement (B4), landmark-grounded serviceability (B5). Activates the existing R&D model (`promise_maker/B/`) in production. | BE |
| B2 | **Promise Maker decision — promise / defer / reject.** No fallback to 25m-only gate. Defer = await night-GPS / manual intervention **OR** all eligible partners are blocked (no currently-free partner can service this area). Reject = no promise made. | BE + FE (defer UX) |
| B3 | Active-promise exposure stock tracking what was promised, under which belief-tier | BE |
| B4 | **Partner team / executive GPS as a belief model signal.** Where a partner's team (executives, Rohits) physically roam is where he actually CAN service — independent of his accept/decline history. Feeds both B1 (can-service decision) and B6 (best-partner ranking) as a richer supply-side signal. (Master story flagged this as unobservable today — becomes observable with this capability.) | BE + FE (partner consent UX) |
| B5 | **Landmark-grounded serviceability.** Two modes: (a) **inferred** — landmarks within a partner's install history are scored as "serviceable by him" from pattern-match on his past installs (no partner cooperation needed, ships day-1); (b) **explicit contract** — partner actively confirms which landmarks he will service, creating a partner-facing commitment stock (upgrade path when partner cooperation exists). Feeds both B1 and B6. Leverage: changes Promise Maker's decision input from hex-only to landmark-grounded, and creates a new information stock. | BE + FE + CN |
| B6 | **Belief Model 2 — who is the best partner for this booking?** Allocation-side model. Separate from B1. Runs on top of the active promise exposure stock (B3) — among partners eligible to install this already-promised booking, who ranks highest? This is the existing GNN / Composite-score ranking territory, enriched with the new inputs: A3 landmarks, A4 gully/floor, B4 team-GPS, B5 landmark-grounded serviceability. Output: ranked partner list for notification. | BE |

### C. Partner-facing capabilities (post-promise)

| # | Capability | Nature |
|---|---|---|
| C1 | Partner notification includes customer-confirmed landmark (A3), gully + floor (A4), photos (A5). **Each field carries an explicit confidence tier visible to the partner** — high for customer-confirmed landmarks (≥2 confirmations in A3), high for structured gully/floor chat capture, lower for NER-parsed fallback text (A10 when A7 was used). Partner sees content AND how much to trust each anchor. Notification is **framed in terms of the partner's own existing install base** — "between your Install X and Install Y on Gali Z" — so the partner recognises the location through his own memory, not via absolute landmarks he may or may not know. | BE + FE + CN |
| C2 | Partner sees his own serviceable-area map: which hexes / boundaries he currently services | BE + FE |
| C3 | **Partner sees the decline-zones he is creating.** Visualisation of his own historical decline pattern on a map — the boundaries he has drawn via his own decisions | BE + FE + CN |
| C4 | Partner sees what happens when he declines: customer-side experience + zone-reddening signal | FE + CN |
| C5 | **Zones turning red** (low install rate / high decline) surface in partner app. Derivation capability-intent: when a partner repeatedly does not install in a hex despite being dispatched, that hex's serviceability score moves toward red for him — the red surface IS the visible shadow of this derivation. Engineering of the specific rule (threshold, decay, window) is out of scope here. | BE + FE |
| C6 | **Google Street View visible inside the booking (partner-side).** Not at notification time — partner sees the Street View render only when he opens the booking to navigate for install. Helps him locate the home on the ground. Feeds off A9 when customer confirmed the pull; otherwise fetched fresh from Google at open-time. | BE + FE |
| C7 | **Edge-polygon "ask partner" flow.** When a booking lands at the margin of a partner's serviceability polygon (not clearly inside, not clearly outside), Wiom does not unilaterally dispatch. Instead it ASKS: "can you install at this landmark?" Two closure patterns: (a) partner marks negative → signal strengthens his polygon edge for future decisions (he has clarified where he won't serve); (b) partner is unsure → trigger manual check that explains the details and decides routing. | BE + FE + CN |

### D. Feedback / control-pane capabilities

Specific trigger logic and intervention design for D1, D2, D6, D7 are long-term — to be designed once data starts flowing. For now, the **capability itself** is what's named.

| # | Capability | Nature |
|---|---|---|
| D1 | Night-GPS vs booking-GPS divergence triggers notification to both customer and partner; manual intervention can step in | BE + FE |
| D2 | Partner visit tracking → nudge intervention if visit has not happened before SLA | BE + FE |
| D3 | Install outcome feeds back to belief model training, closing the install → capture loop | BE |
| D4 | Address-confidence per landmark / gully accumulates from successful installs; informs A3's landmark pick suggestions over time | BE |
| D5 | Immutable memory of: GPS pings (booking + night), landmark picked, gully + floor, photos, partner calls + topics + actions (install/decline/visit) | BE |
| D6 | **Customer-side difficulty signal monitoring.** Control pane watches signals of partner struggling with an address (repeat calls on same booking, stuck on gully/locality, `partner_reached_cant_find`) and triggers customer-side interventions — change slot, push customer and partner into direct conversation, nudge customer to add detail, escalate to manual ops. Intervention specifics to be designed once data flows. | BE + FE + CN |
| D7 | **Partner on-ground navigation assist.** When partner is physically at the location and struggling, a help channel opens — live customer call trigger, push A5 photos to partner's screen, request live GPS ping from customer. Real-time assist capability. Intervention specifics to be designed once data flows. | BE + FE |
| D8 | **Post-install landmark validation — four signals.** Closes the loop on whether A3's customer-confirmed landmarks actually functioned as navigation anchors in the field. Signals: (a) **call-transcript mining** — did the partner reference a different landmark on-call than the customer-confirmed one? (negative-signal-only: can decrement confidence, cannot increment); (b) **second-call escalation** — ≥2 calls on the same install = compounding failure, lowers the landmark's validation; (c) **partner field GPS trail** — did partner pass through confirmed-landmark radius? Stratified by partner-familiarity (use only non-local partners' trails; local partners don't need the anchor); (d) **time-to-door distribution** — partner enters 500m radius → technician-at-door delta; good confirmations shift this distribution left at the population level. Signals feed a factorised estimate: `install_outcome = partner_effect + landmark_effect + residual` — a landmark is "bad" only if its effect is negative AFTER controlling for partner. Output flows back to A3's landmark-pick suggestions (via D4) and to both belief models' training (via D3). | BE |

---

## Signals

### Leading signals (observable within days of a booking)

- Night-GPS vs booking-GPS divergence rate
- Partner visits location prior to install date (visit-before-install rate)
- On-call address clarity rate (transcripts continue to feed this)
- Photo-relatability confirmation rate when partner is near home
- Fraction of bookings where A3 landmark-pick completed first-try vs required A6 re-capture or A7 text fallback

### Lagging signals (observable weeks after)

- Booking-to-install drift distribution tightens (master story D.A baseline: 25.7% beyond apparatus ceiling)
- Installs per week rise at held promise volume
- Calls per pair drop (baseline 1.92; no target set here — engineering phase)
- Partner decline-zone map stabilises (declines concentrate in known-unserviceable zones, not scattered)

---

## Out of scope for this document (explicit)

These belong in the system spec, engineering, or existing component specs — not here:

- **Engineering mechanics:** decay, `(quality, confidence, last_observed)` triplets, write-contracts on immutable memory, state-machine design, retry logic, time windows, API shapes
- **Engineering components the build will handle (noted so readers know they exist, not spec'd here):**
  - **Layered containment logic** — three-layer test (inside partner polygon → inside city envelope → truly sparse) feeding Belief Model 1's confidence tier.
  - **Temporal navigation anchor mining** — extracting from coordination transcripts + addr_chain_evidence + install outcome the landmark phrase a successful partner actually used for the nearest recent install; ranking nearby past installs by (recency × install-success); surfacing the behaviourally validated phrase in C1's partner notification.
  - **Gaming-score vs trust-score separation** — gate emits two distinct scores from different feature sets: trust drives re-capture (A6); gaming drives human review or block. Re-capturing a gaming attempt would reward it — they cannot share a downstream treatment.
  - **Cause-code taxonomy extension** — add `GPS_TRUST_FAILURE` (upstream capture failure) and `ADDRESS_RESOLUTION_FAILURE` (coordination failure at gully/floor level, orthogonal to spatial) tags to D5's closure outcomes, so both belief models retrain with separated signal instead of a lumped `SPATIAL_FAILURE`. Without this extension, the new capabilities produce no new learning.
  - **Text-address reverse-lookup storage (optional)** — when A7 fallback text is captured and A10 NER parses it, store the parsed output against the captured GPS as an enrichment stock for future text-lookup use. **`what3words` codes and active pincode reverse-geocode cross-checks are deferred** — not part of day-1 rollout.
- **Which capability lives in which OS and how packets flow** — comes in the system spec phase
- **Algorithms inside existing components:** GNN ranking internals, coordination classifier, PM/B Bayesian shrinkage mechanics
- **Specific intervention trigger design for D1, D2, D6, D7** (night-GPS divergence + partner nudge + customer-difficulty interventions + on-ground navigation assist) — will be designed once the data starts flowing; long-term solutioning
- **"Address shady" persistent status flag to partner when night-GPS diverges** — specific UX and rule to be designed once data starts flowing; not in this frame
- **Business-model questions** — when the fee captures under defer / reject, refund policy, partner SLA definitions
- **Street View coverage scoping for Indian residential bookings** — data-pull task before A9 locks in behavioural assumptions. Google Street View coverage is patchy for Indian residential colonies / interior galis; metadata API first-check is mandatory. Sample ~1,000 Delhi bookings to measure `ZERO_RESULTS` rate before committing the A9 path to user-facing rollout.

---

## Open questions (carried forward to solutioning)

Decisions that need to be made before build, but not in this document:

1. When does the fee capture in the defer path? Is the promise conditional on night-GPS validation (refund if fails) or does fee capture only after validation?
2. A3 landmark picker — how many landmarks shown? How many must the customer confirm? What's the re-capture limit before A6 fires?
3. A8 jitter threshold for "noisy" — learned per mobile, or a population floor?
4. C3 decline-zone visibility — real-time or daily snapshot? Own-partner view only, or cross-partner (with privacy mask)?
5. Promise Maker's belief model output — binary (promise/defer/reject) or tiered (High/Mid/Low confidence with different downstream paths)?

---

## Companion files

- `master_story.md` · `master_story.csv` — the data backbone this frame rests on
- `possible_architecture.txt` — the raw-notes predecessor this draft articulates
- `narration_master_story.txt` — the original narrative outline
