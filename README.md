# Location Signal Audit — Promise Maker → Allocation → Coordination

**Owner:** Maanas
**Narrator / storyteller:** `story_teller_part1` (session dedicated to assembling the cross-engine storyline)
**Scope:** cross-engine audit of location signal fidelity across Wiom's matchmaking funnel, and the solution storyline built on top of it for Satyam's problem statements.

---

## Purpose

One funnel, three engines, one question:

> **Does the location coordinate that enters Promise Maker survive cleanly enough through Allocation and Coordination to actually land a technician at the customer's home?**

If the coordinate is noisy at capture, every downstream decision (25m gate, GNN `nearest_distance`, partner notification geometry, address-chain resolution on-call) inherits the noise. You can't fix upstream signal loss with downstream cleverness.

---

## Canonical master story (data backbone)

The cross-engine audit is synthesized into a single narrative + structured data backbone. These are the canonical reads once all four sub-folder stories are complete:

| File | What it is |
|---|---|
| [`master_story.md`](./master_story.md) | Narrative walk-through of the signal from capture → allocation → coordination → install. Reads end-to-end. Stripped of solution framing (that lives in `solution_frame.md`). |
| [`master_story.csv`](./master_story.csv) | Structured data backbone — every table in the MD (deciles, quantiles, cross-cuts, eligibility splits) in proper wide-table form, with source citations pointing to the sub-folder STORY.csv files. |
| [`narration_master_story.txt`](./narration_master_story.txt) | Original outline Maanas authored; the MD and CSV were built from this spine. |

Sub-folder STORY.csv + README files remain the source of truth for their respective engines. The master story synthesizes and never duplicates — if a number is in the master, the sub-folder is its origin.

---

## Solution frame + accountability docs (capability-level, built on the master story)

Once the data backbone is in place, the solution frame names WHAT the system does at the capability and signal layer — not HOW any component is engineered. The Gate 0 contracts (one per problem) and the L5 derivation memo sit alongside it.

| File | What it is |
|---|---|
| [`solution_frame_v6.md`](./solution_frame_v6.md) | **Current solution frame.** Two-confidence gates (User Address Confidence + Serviceability Confidence), sequential evaluation, phased rollout (Phase 1 polygon-only; Phase 2 BM1; Phase 3 BM2), payment mechanics with 48h auto-refund SLA, six feedback loops with decay declared, 42 body capabilities across four groups. Partner Integrity Channel scoped to Appendix C as a separate cross-OS workstream. Older frames (v1-v5) are archived in `older_artifacts/`. |
| [`problem_statements/problem_1_location_estimation_v3.md`](./problem_statements/problem_1_location_estimation_v3.md) | **Gate 0 contract for Problem 1** (Location Estimation, Point A). Filled against Satyam's Gate 0 template. L5 target: install rate 40% → ≥49% (P1 + P2 joint). |
| [`problem_statements/problem_2_address_translation_v3.md`](./problem_statements/problem_2_address_translation_v3.md) | **Gate 0 contract for Problem 2** (Address Translation, Point B). Same template. L5 target: install rate 40% → ≥49% (P1 + P2 joint). |
| [`l5_target_derivation.md`](./l5_target_derivation.md) | **L5 attribution memo.** Derives the shared 40% → ≥49% target from master story lifts: P1 alone +7pp, P2 alone +4pp, joint overlap-adjusted +9pp. Explicitly excludes model activation (BM1/BM2) and partner expansion — those stack on top in separate contracts. |
| [`implementation_plan_and_impact.md`](./implementation_plan_and_impact.md) | **Lean phase plan.** 4 phases, complexity rises across phases, no timelines yet. Phase 1 ships capture substrate + UI (both Leading indicators live). Phase 2 ships partner-facing + governance. Phase 3 ships learning pipelines (L5 joint target met). Phase 4 ships long-poles (BM2 + on-ground assist + post-install validation). |
| [`possible_architecture.txt`](./possible_architecture.txt) | Raw-notes predecessor from Maanas. Retained for provenance. |
| [`older_artifacts/`](./older_artifacts/) | Archive of earlier solution frames (v1-v5) and earlier Gate 0 contracts (v1, v2). Retained for audit trail. |

**Principle:** the solution frame stays at capability level. Engineering mechanics (decay half-lives, confidence triplet internals, state-machine transitions, API shapes, text-reverse-lookup internals) are explicitly out-of-scope in the frame and land at build time. Specific intervention triggers for control-pane signals (night-GPS divergence, partner visit nudges, customer-difficulty interventions, on-ground navigation assist) are designed once data flows.

---

## The three engines

| Stage | Subfolder | Question | Status |
|---|---|---|---|
| 1 — pre-promise | `promise_maker_gps/` | Is the booking GPS reliable at capture? | Stage A (jitter baseline) complete · Stage B (booking→install drift) first cut complete · declined cohort + slices pending |
| 2 — post-promise, pre-acceptance | `allocation_signal/` | Does the partner↔booking distance predict installs? | Complete. GNN `probability` beats raw distance; splitter-gaming identified; D10 = Shannon physics limit. |
| 3 — post-acceptance | `coordination/` | Once the partner accepts, where does address resolution break on the ground? | Complete. Transcript-level address friction is flat across distance deciles; dropdown's 48→2.5% prob-decile pattern was a decline-channel artifact; gali is the biggest call-level bottleneck. |

Each subfolder has its own `README.md` and `STORY.csv`. This parent README is the **synthesis layer** — it ties the engines together, hosts the current customer flow, and captures solution storylines as problem statements arrive.

---

## Current customer flow (as-is, 2026-04)

This is the flow the analysis is auditing. Numbered for cross-reference in thinking contracts below.

### Pre-promise phase

| Step | What happens | Data captured | Engine touched |
|---|---|---|---|
| 1. App install | Customer installs Wiom app for the first time | — | — |
| 2. **Ilaaka GPS submission** | App asks for customer's neighbourhood (ilaaka) GPS — a rough "where do you live?" capture | **GPS fix #1** (ilaaka lat/lng) | Promise Maker (pre-filter) |
| 3. City / serviceability pre-filter | Unserviceable cities filtered out based on ilaaka coordinate | — | Promise Maker |
| 4. **Home GPS submission** | App asks customer to submit a **second** GPS — explicitly prompted to do this from home | **GPS fix #2** (home lat/lng) → this is the coord captured at `lead_state_changed` · `lead_state = 'serviceable'` | Promise Maker |
| 5. **25m serviceability gate** | If a historical install or splitter point exists within 25m of the home GPS, pass | — | Promise Maker (this is the gate Stage B's drift analysis interrogates) |
| 6. **Booking fee — Rs. 100** | On pass, collect Rs. 100 | `lead_state = 'booking_verified'` event fires | Promise Maker |
| 7. **Promise made** | Wiom commits to install at this home | — | Promise Maker |

### Post-promise phase

| Step | What happens | Data captured | Engine touched |
|---|---|---|---|
| 8. **Text address collection (post-payment)** | Customer types the full home address into a **single free-text field, in one flow** — no structured sub-fields for landmark / gali / floor | Address string (unstructured) | Promise Maker → passed downstream |
| 9. **Allocation** | Allocation engine ranks candidate partners and sends notifications | Notification events, partner decisions | Allocation |
| 10. **Notification to partner** | Full-page push notification with a **rudimentary map image** showing the booking location and the partner's historical install points, plus the straight-line distance from their base. **Text address is NOT shown at this stage** — partner must click through to see it. | `decision_event` = INTERESTED / ASSIGNED / DECLINED | Allocation |
| 11. **First-come-first-locked** | First partner to mark interest / assign takes ownership; others can no longer act on that booking | — | Allocation |

### Post-acceptance phase

| Step | What happens | Data captured | Engine touched |
|---|---|---|---|
| 12. **Partner opens notification → sees text address** | After click-through, partner finally has access to the unstructured text address | — | Coordination |
| 13. **Partner assigns technician** | Internal assignment within the partner's team | — | Coordination |
| 14. **Partner calls customer** | Voice call to resolve: locality → gali → floor. Floor detail matters because it determines whether the install is a height-wiring job (different tooling, different time cost). | Call transcript (post-hoc via UCCL) | Coordination (the transcripts analyzed in `coordination/`) |
| 15. **Technician lays wire, installs** | Physical install | `wifi_connected_location_captured` event fires when the router powers up and connects to the home's unique SSID | — (but this event is the ground truth for Stage A/B in `promise_maker_gps/`) |

---

## Structural observations from the flow (pre-problem-statement)

Worth capturing before problem statements arrive, because they are the *raw material* for any solution storyline:

1. **Two separate GPS captures exist** (ilaaka in step 2, home in step 4). They are used for different gates (city filter vs 25m serviceability). Their reliability profiles may differ systematically — ilaaka is likely lower effort (customer not prompted to be at home); home is higher intent but still degraded by indoor / night / cache conditions (see `promise_maker_gps/` Stage B: 25.7% have structural capture error beyond apparatus noise).

2. **Text address is captured AFTER payment, not before.** Implications:
   - Text address cannot be used to validate the GPS before the promise is made
   - No pre-promise address↔GPS cross-check is possible with the current flow
   - Customer has already committed financially, so any late address-based re-check can only *cancel* (refund) or *re-route*, not prevent a bad promise

3. **Text address is a single free-text field.** Implications:
   - Allocation has no structured signal on landmark / gali / floor at ranking time
   - Partner's first structured encounter with address detail is the voice call (step 14)
   - The coordination bottleneck (gali-stuck at 7.4% of calls per `coordination/`) is structurally baked in by this capture choice

4. **Notification to partner (step 10) shows map + distance but not text address.** Implications:
   - Partner's accept/decline decision is based on geometry + their own history, not address content
   - High decline-on-address-unclear rates downstream are not "partner refusing bad addresses" — partner hasn't seen the address yet when they decide
   - GNN `probability` wins over raw distance at Allocation partly because it encodes decline-history — not because distance is uninformative

5. **First-come-first-locked in Allocation (step 11)** means top-k notification is a *soft ranking*, not a hard ranking. Whichever partner is fastest to tap wins — ranking informs *who gets pinged first*, not *who gets the booking*. The decline signal the GNN learns from is therefore asymmetric: declines are observable, non-latches are not easily distinguishable from "didn't see in time."

6. **Floor detail (step 14) surfaces only during the call.** Implications:
   - Height/wiring complexity is invisible to Allocation — a partner fit for a 2nd-floor job and a 7th-floor job are ranked identically
   - `partner_reached_cant_find` (11.1% on splitters per `coordination/`) + the floor-resolution bottleneck both live here

---

## Key events ↔ flow steps mapping (for SQL grounding)

| Flow step | Event / source | Captured in which analysis? |
|---|---|---|
| 2 (ilaaka GPS) | ? (not yet sourced in any analysis) | — |
| 4 (home GPS) | `lead_state_changed` · `lead_state='serviceable'` | `promise_maker_gps/` Stage B (`booking_lat/lng`) |
| 6 (fee captured) | `lead_state_changed` · `lead_state='booking_verified'` | `promise_maker_gps/` (cohort anchor) |
| 10 (notification) | `t_allocation_logs` + `task_logs` | `allocation_signal/` |
| 14 (voice call) | `USER_CONNECTION_CALL_LOGS` + Exotel recordings | `coordination/` |
| 15 (install) | `wifi_connected_location_captured` | `promise_maker_gps/` (Stage A repeat pings + Stage B first ping) |

---

## What we know so far — cross-engine synthesis (pre-problem-statement)

The sibling findings, placed on the flow:

- **Stage A (apparatus):** the GPS hardware itself is tight — per-ping p50 = 7.7m, p95 = 154.8m over days-apart drift. 70% of mobiles have worst-case ≤ 25m. Hardware is **not** the leak.
- **Stage B (capture):** booking→install drift is **3-8× wider** than Stage A at every quantile. 25.7% of installs have drift beyond Stage A p95 — structural capture error at step 4, unexplainable by GPS physics. Likely drivers: night/indoor captures, user misunderstanding of the "be at home" prompt, cached fixes.
- **Allocation:** GNN `probability` dominates raw distance on every operational metric that matters at ranking time (install-rate separation 57% vs 44%; area-decline concentration in the worst-3 prob deciles 59% vs 48%; splitter-composition monotonically routed 38%→12% on prob vs scattered with 41% peak at D7 on distance). **GNN runs once, pre-decision — ingesting install AND decline edges as first-class messages** to produce the notification ranking *before* any partner acts on this booking. It wins because it prices partner-knowledge signals (local serviceability, gali navigability, gaming-partner avoidance) that a static geometric cut gives up by construction. The conditional-accept diagnostic slice (filtering to `INTERESTED/ASSIGNED` collapses prob and distance to ~40% each) is **not a critique** — it's the designed leverage channel being subtracted out in analysis, which is exactly the channel GNN is built to price. The collapse confirms the architecture, not a flaw in the score. Distance remains useful as a **tail-refusal primitive** around the ~50km fiber-reach Shannon limit (D10 conditional-accept install rate = 22.8%, a physics ceiling no ranker punches through) and as a co-signal orthogonal to willingness — never as a ranking substitute. The 448km D10 tail on raw distance is a data-hygiene artifact; the Stage B finding above may partially explain it.
- **Coordination:** Allocation's **pre-assign dropdown** `address_not_clear` (the decline-time click partners select from a fixed reason list when declining a notification, BEFORE they've accepted) showed 48%→2.5% separation across prob deciles. Coordination's **post-assign transcript analysis** (4,930 calls, Haiku-classified) revealed transcript-level address friction is flat (~20% across all deciles) — confirming the dropdown pattern was a **decline-channel artifact at the Allocation stage**, not genuine address friction at the call stage. Two different signal sources, two different funnel stages, two different conclusions. Gali is the single biggest call-level bottleneck at the transcript level (7.4% of calls stuck there). 46% of transcript `address_not_clear` calls are one-sided (partner confused, customer clear). Chain engagement is protective (+10pp install rate for pairs that engage landmark → gali → floor at any point).

**The through-line**: the booking coord is noisy, the text address is unstructured, the partner doesn't see the address at notification time, the gali resolution happens on a phone call, and the floor detail surfaces only after that. Every stage operates on a less-structured signal than it could, because the structure was never captured upstream.

---

## Reframes — load-bearing architectural shifts

Frame-level realignments that shaped the design. New reframes accumulate here; older ones aren't deleted — they become foundational. **Durable rule (Maanas, 2026-04-20): every reframe that emerges in a session must be captured in this README, not only in downstream synthesis docs.**

1. **The promise is structurally premature.** (Geoff, Problem 1 RCA.) The real pain at Point A is not bad GPS — Stage A proved the apparatus is fine. The pain is that Wiom makes a promise on an input it has never interrogated. Genie's own founding principle says *"promise-making and promise-fulfillment are structurally separated."* Today they aren't, in spirit — the promise fires on pre-evidence.

2. **Structural asymmetry — customer has gali knowledge Wiom never captured.** (Geoff, Problem 2 RCA.) The real pain at Point B is an upstream capture failure, not a partner-navigation failure. Every downstream intervention (photos, videos, voice calls) is compensating for the free-text-field post-payment capture design.

3. **Address intelligence → place intelligence.** (Maanas, via AI conversation.) The system should not send a partner an address. It should send a verified, behaviorally grounded, partner-recognizable install location.

4. **GNN runs pre-decision; decline-signal integration is a FEATURE, not a bug.** (Maanas, correcting an earlier misframe.) GNN computes ranking before any partner acts on a booking. Pricing decline risk *is* pricing install likelihood — not separable in production because production doesn't condition on accept. The conditional-accept diagnostic is a decomposition, not an operational comparison.

5. **Dropdown (pre-assign, Allocation-stage) ≠ Transcript (post-assign, Coordination-stage).** (Maanas, distinction discipline.) Two different signal sources, two different funnel stages, two different conclusions. Don't conflate the decline-time click with the voice-call content.

6. **Interrogate the customer, not the coord.** (This round — landmark-confirmation revision.) A technical trust-score classifier asks *"is this coord statistically reasonable?"* — system-talking-to-system. Landmark confirmation asks *"is the human who submitted this coord actually standing where they claim?"* — system-talking-to-human, the only entity with ground truth. Different question, different answer.

7. **Every intervention must produce an impact signal flowing back, measured by users' actions positive or negative.** (Maanas, durable principle.) Without a measurable feedback channel tied to real user behavior, an intervention is a hope, not a design. Specific trackers (e.g. *"% calls where a different landmark was discussed"*, *"% times technician reached the confirmed landmark"*, *"% required return visits"*) need further articulation — but the **principle is non-negotiable.**

---

## Durable design principles (non-negotiables)

Structural invariants that must survive every iteration. Breaking any of these breaks the architecture, not just a feature. Each originated from a specific agent round or pushback and is preserved here because the risk they guard against keeps re-emerging.

1. **Decay is mandatory on every behavioral-reinforcement mechanism.** (Donna, first round.) Applies to hex-reddening, the already-in-system Bayesian shrinkage K=30, landmark quality scores — anything where a signal influences future routing. Without decay, a single bad day in a hex poisons priors indefinitely.

2. **Downstream propagation is mandatory for dual-purpose interactions.** (Donna, landmark-confirmation round.) `confirmed_landmarks_per_booking` MUST flow into Problem 2 packet as a first-class field. If one customer interaction can validate upstream AND enrich downstream, it must do both — otherwise the customer did the work and only one stage benefits.

3. **Separate `quality` from `confidence` in any quality-scored stock.** (Donna, validation-loop round.) Collapsing them into one scalar allows reinforcing loops to concentrate attention on popular items while leaving low-observation items indistinguishable from poor-quality ones. Always store as `(quality, confidence, last_observed)` triplet.

4. **Every intervention produces an impact signal flowing back.** (Maanas, this round.) See Reframe #7 above. The articulation of specific trackers is pending; the principle itself is architecturally binding.

5. **Scoring artifacts stay internal to Genie.** (Satyam, SAT-01.) Trust scores, gaming flags, classifier outputs never ride in Promise Packet. They are consumed by internal stocks (B/R/E/S) and by D&A OS's `genie_context_manager` for downstream enrichment.

6. **The pre-promise gate is PMBM-independent.** (Donna, landmark-confirmation round.) Containment checks read polygons only, not KDE fields. KDE can enrich the Problem 2 packet post-promise, but must not couple to the gate.

7. **Use NUT-linked outcome metrics as primary targets; proxy metrics only as operational health.** (Geoff, metrics round.) *"<5% structural drift"* or *"<1.3 calls/pair"* can be gamed — tighten the gate to reject everyone and drift drops while the business breaks. Primary targets: promise-to-install conversion rate at held promise volume (P1); first-visit-install rate + minutes-to-door (P2). Proxy metrics monitor operational health, not outcome.

---

## Solution storyline — thinking contracts + end-to-end solutions

### Satyam's framing of the matchmaking decision surface

Two decision points. Three parties.

| Decision point | Decider | Question the decision hinges on | Contract |
|---|---|---|---|
| **Point A** | Wiom | Should we make a promise to install at this location? | `problem_statements/problem_1_location_estimation.md` |
| **Point B** | Partner | Should I accept this booking, and once accepted, can I reach and install? | `problem_statements/problem_2_address_translation.md` |

Satyam's two guiding questions:
1. **What is the best way to take location from the customer?** → Problem 1 (Point A, capture quality)
2. **How do we ensure consistency / understanding of the location across all parties?** → Problem 2 (Point B, cross-party translation)

The customer is the upstream source for Point A and the downstream validator for Point B. Same asset (location), two different quality questions — one about the *coord itself*, one about how that coord + its surrounding context *survives handoff* across Wiom → partner → customer.

### Filed Gate 0 contracts (current: v3)

| # | Title | Decision point | Primary engine | File |
|---|---|---|---|---|
| 1 | Location Estimation | Point A — Wiom's promise | `promise_maker_gps/` | [`problem_statements/problem_1_location_estimation_v3.md`](./problem_statements/problem_1_location_estimation_v3.md) |
| 2 | Address Translation for CSP | Point B — Partner's decision | `coordination/` | [`problem_statements/problem_2_address_translation_v3.md`](./problem_statements/problem_2_address_translation_v3.md) |

Earlier drafts (v1, v2) are archived at `older_artifacts/problem_statements/`.

### Solution substrate and synthesis

The Gate 0 contracts stay lean — they define the problem, not the solution. Solution content lives in:

- [`solution_frame_v6.md`](./solution_frame_v6.md) — current solution frame (successor to v1-v5, archived).
- [`l5_target_derivation.md`](./l5_target_derivation.md) — bottom-up math for the shared L5 target.
- [`implementation_plan_and_impact.md`](./implementation_plan_and_impact.md) — phase plan with cumulative-impact projections.
- `../../../promise_maker/` — the ML belief model these problems plug into (B_spatial with KDE fields, Bayesian shrinkage, PMBM, cause-coded self-learning).

### Shared infrastructure across the two contracts

The two projects are complementary, not parallel. They share:

- **Pincode / reverse-geocode validator** — Problem 1 uses it for GPS cross-check; Problem 2 uses it for landmark confirmation. Build once, consume twice.
- **Canonical structured-address representation** — introduced by Problem 2. If captured pre-promise rather than post-payment, this representation also becomes a pre-promise validator input for Problem 1.
- **`../coordination/` transcript taxonomy** — the landmark→gali→floor chain already tagged on 4,930 calls is the ground-truth taxonomy for designing any structured-address schema in Problem 2.
- **Promise Maker belief model (`../../../promise_maker/B/`)** — the ML asset that both problems' outputs feed into. Cleaner booking coord (Problem 1) → cleaner spatial field in B_spatial. Structured address (Problem 2) → richer feature set for the model to condition on.

### Disconfirmation handoff

- Solve Problem 1 only: cleaner GPS, still ambiguous text address → partner still calls to resolve gali and floor.
- Solve Problem 2 only: cleaner address, GPS still drifts → partner arrives at the wrong block despite perfect address text.
- Solve both: the three parties hold the *same* location model, at the *same* quality, at every handoff.

### Open pre-requisites (blocking build, tracked in subfolders)

From both contracts' "Open pre-requisites" sections:

| Pre-requisite | Sits in | Which contract it blocks |
|---|---|---|
| Stage B × `time_bucket` slice (night-indoor hypothesis) | `promise_maker_gps/booking_install_distance/` | Problem 1 — validator feature #2 |
| Stage B × `booking_accuracy` correlation | same | Problem 1 — validator feature #1 |
| Declined-cohort Stage B comparison | same | Problem 1 — understanding current-state gate behavior |
| Mobile bimodality labels (A3) | `promise_maker_gps/gps_jitter/` | Problem 1 — validator feature #4 |
| Ilaaka-GPS vs home-GPS drift analysis | TBD — new analysis (flow step 2 not yet sourced) | Problem 1 — optional pre-signal input |
| Landmark/gali/floor taxonomy frequency table | `coordination/` | Problem 2 — structured capture schema |
| Re-slice install-rate by `n_calls` bucket | `coordination/pair_aggregated.csv` | Problem 2 — L3 baseline |
| Customer-side capture UX research | Wiom product | Problem 2 — schema design scope |
| Option A vs Option B capture-timing decision | Satyam + Wiom product | Problem 2 — Sprint 1 scope |

---

## Session handoff notes

- This file is the hub. Subfolder READMEs are the source of truth for their respective engines; this README only synthesizes.
- Problem statements and thinking contracts are appended below in the order Satyam raises them.
- Solutions may span multiple engines — cross-reference sibling folder findings liberally.
- When a solution implies an analysis not yet done, add it to the appropriate subfolder's "Status" checklist, not here.
