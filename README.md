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

### Filed Gate 0 contracts

| # | Title | Decision point | Primary engine | File |
|---|---|---|---|---|
| 1 | Location Estimation | Point A — Wiom's promise | `promise_maker_gps/` | [`problem_statements/problem_1_location_estimation.md`](./problem_statements/problem_1_location_estimation.md) |
| 2 | Address Translation for CSP | Point B — Partner's decision | `coordination/` | [`problem_statements/problem_2_address_translation.md`](./problem_statements/problem_2_address_translation.md) |

### Solution substrate and synthesis

Thinking contracts above are intentionally lean on design — the Gate 0 template is about the problem, not the solution. Solution content (Maanas's own notes, the Gate 0 HTML precedent report, Promise Maker system context, and my own critique/innovation layer) lives separately:

- `possible_solutioning_approaches/Possible_Solutioning_Approaches.txt` — Maanas's own notes on the intervention design (PMBM, gating, feedback loops, place-intelligence reframe)
- `possible_solutioning_approaches/wiom_location_address_gate0_report.html` — precedent-grounded Gate 0 submission (Swiggy / Dunzo / Pidge / Shiprocket / DTDC / India Post / Google Maps India playbooks)
- `../../../promise_maker/` — the ML belief model these problems plug into (B_spatial with KDE fields, Bayesian shrinkage, PMBM, cause-coded self-learning)
- `solution_synthesis.md` *(being assembled by `story_teller_part1`)* — my cross-engine synthesis, critique of Maanas's approach, and innovation proposals on top, grounded in the Promise Maker architecture

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
