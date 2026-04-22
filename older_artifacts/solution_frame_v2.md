# Solution Frame v2 — Location Signal Integrity

**Drafted:** 2026-04-21
**Predecessor:** `solution_frame.md` (v1, kept untouched)
**Raw notes:** `possible_architecture.txt`
**Data backbone:** `master_story.md` + `master_story.csv`
**Companion design:** `solution_synthesis.md`, `solution_diagrams.md`
**Scope:** capability-level frame. Not a system spec. Not engineering.

---

## How to read this

This is a **frame**, not a system design. It states what the solution is for (§1), the principles of its construction (§2), the object it redesigns (§3-§4), the evidence that grounds the redesign (§5), what the redesigned world feels like lived (§6), the invariants the build must never violate (§7), the flow the system takes (§8), the capabilities that implement it (§9), and the signals by which we know it's working (§10). Engineering mechanics — thresholds, decay formulas, write-contracts, API shapes, retry logic — are explicitly out of scope (§11) and pass to the system spec that follows.

The v1 structure loaded capabilities heavily and the front half thinly. v2 rebalances. Front half carries objective, principles, and journey with the weight they deserve; back half preserves v1's strong capability tables unchanged.

---

## §1 — Objective

Two customer pains, both at Wiom's front door, both rooted in the same leak:

> *"Mujhe Wifi chahiye but Wiom mana kar raha hai."* (I want WiFi but Wiom is refusing me.)
> *"Mera connection aaj lagna tha, but koi lagane nahi aaya."* (My connection was supposed to be installed today, but nobody came.)

5-Why, compressed: the refusal and the no-show both happen because Wiom commits — takes Rs. 100 — on a single un-interrogated GPS fix and never transmits the customer's structured knowledge (which mandir, which gali, which floor) to the partner who must actually install. The customer has ground truth about his own home. The partner has ground truth about where he actually services. The system sits between them and lets neither speak before the promise is made.

**What this solution is for.** To turn promise-making from an act of gambling against un-interrogated inputs into an act of committing against evidence. The build elicits the customer's own location knowledge before committing, routes that knowledge forward to the partner as a packet he can recognise in his own install memory, checks that some real partner actually services that landmark (not merely that infrastructure sits near the coord), and closes outcomes back to both the capture apparatus and the serviceability belief.

**Who wins what.**
- *Customer:* gets a promise that actually lands — no refusal on a coord he didn't know was wrong, no no-show on a gali his partner never learned.
- *Partner:* gets a lead framed in his own install history, decides on content rather than geometry, and sees the consequences of his own decline decisions evolve over time.
- *Wiom:* gets a learning loop that tightens capture with every install. The 25.7% drift, the 40.7% location-reason first-calls, the 77.5% within-ANC confusion are not permanent taxes; they are what the system pays today because nothing flows back.

**What this is not.** Not a partner-motivation system (that is Partner Management). Not a general coordination fix (that is Coordination). Not a task-scheduling fix (that is Task Management). This solution is specifically the location-signal pillar inside Promise Maker + its downstream partner-facing surface.

**The north star is calibration, not growth.** Success is a promise that is true, not an install rate pumped by holding promise volume constant while drift stays structural. Engineering mechanics — thresholds, decay rules, write-contracts, API shapes — are the subject of the system spec that follows this frame.

---

## §2 — Principles of build

These are the rules of construction the build must follow. They are the lens through which §6 (journey) and §9 (capabilities) read as necessary rather than arbitrary. Each follows from the structure of the problem, not from preference.

**P1. Elicit before committing.** The build asks the customer for his own structured knowledge (landmark, gali, floor) *before* Wiom takes the fee. A promise on an un-interrogated input is a commitment of reputation against noise. Verification is a precondition for commitment, not a follow-up.

**P2. Capture is not verification.** A geometric check against infrastructure (the current 25m test) passes equally well for "customer at home" and "customer standing next to a splitter 2km from home." A test that operates only on the same untrusted input cannot lift trust. Verification requires a second, independent channel — the customer's own confirmation, or a night-time ping, or both.

**P3. The customer is the only ground truth for home-proximity.** GPS knows where the phone is; only the customer knows whether the phone is at home. 46% one-sided confusion in ANC calls (customer clear, partner confused) proves the customer has the signal — we have simply never asked for it in a form that travels.

**P4. Re-capture uses a different surface than initial capture.** If a customer got it wrong because they're committed to a wrong location, asking them to "confirm your earlier input" invites doubling down. Same question twice has no information value. Round 2 must be structurally different — different anchors, live re-acquisition, new evidence — or the loop is theatre.

**P5. The partner decides on content, not geometry.** Today the notification shows map + straight-line distance; the text address is hidden until click-through. The decline decision is made on geometry alone. Whatever capture work happens upstream is invisible at the exact moment the partner chooses. Content must ride at the top of the notification, or capture leverage halves.

**P6. Every signal consumed has a feedback channel back to its source.** A signal with no return path is a stock that can only degrade. Install-outcome → polygon closes in R&D. Install-outcome → capture-apparatus closes nowhere today. That asymmetry is why capture stays noisy — nothing tells the customer app "your last fix was wrong, ask differently next time."

**P7. Cause-code fidelity is the learning-loop linchpin.** If every downstream failure is tagged `SPATIAL_FAILURE`, the belief models cannot distinguish bad capture from unserviceable area from unresolvable address. Three distinct physical phenomena collapse into one feedback signal. New capture mechanisms without new cause codes produce no new learning.

**P8. Decay is mandatory on all partner-visible behavioural feedback.** A single decline in a low-evidence hex that permanently reddens that hex is a self-fulfilling prophecy — the partner never gets routed there, never calibrates, the hex stays red. Time-decay and evidence-weighting are not refinements; they are the difference between a learning signal and a calcification mechanism. (The *need* for decay is first-principles; the *shape* is empirical and calibrates in engineering.)

**P9. Scoring artifacts stay internal; only facts cross membranes.** Trust scores, gaming scores, belief probabilities are Genie's internal instruments. If they cross into the partner app or D&A OS, downstream systems optimise against the score and Goodhart eats the signal. Facts cross: verified lat/lng, confirmed landmark, gali, floor, photo URL. Scores do not.

**Frame vs engineering.** These principles sit at the frame level. The engineering phase picks thresholds, decay half-lives, probe rates, retry limits, and state machines — all constrained by the principles above but not specified here.

---

## §3 — Promise Maker, as it stands today

Promise Maker is Wiom's commitment engine: it decides whether Wiom promises to install at a customer's home, based on the GPS captured at booking. Today:

- **Input:** a single `booking_lat/lng` captured when the customer submits the fee.
- **Gate:** `distance(booking_lat/lng, nearest historical install or splitter) ≤ 25m` — a binary infrastructure-proximity test, partner-agnostic by construction.
- **On pass:** promise made, fee captured, lead flows to Allocation.
- **Text address:** collected *after* the 25m gate passes and *after* the fee is captured (flow step 8).

Promise Maker also has an R&D belief model — **`promise_maker/B/`** — a full ML pipeline that models partner behaviour across geographies: install/decline history, supply-efficiency hex grid, partner cluster boundaries (`partner_cluster_boundaries.h5`), cause-coded learning, Bayesian shrinkage. **The belief model exists but is not consulted at the production gate.** The 25m check is alone in front of the customer's money.

Everything §1-§2 targets rests on one observation: the system's gate is cheap and partner-blind, and its richer models are built but unused.

---

## §4 — The structural problem

**One sentence.** Wiom promises on a single un-interrogated GPS fix, keeps no record of the customer's structured knowledge (landmark, gali, floor, locality), and never shows the partner a customer-verified address before asking them to decide.

**Three orphan stocks.** Knowledge that exists in the world but is unconsumed at promise time:

1. **Customer mental model** — landmark, gali, floor, nearest visible markers. Never elicited before commitment.
2. **Partner serviceability intelligence** — polygons from SE-weighted install/decline history (`partner_cluster_boundaries.h5`) and the full `promise_maker/B/` belief model. Built, not deployed to the gate.
3. **Per-mobile jitter profile** — Stage A computed worst-case jitter for 8,317 mobiles. A repeat mobile has a knowable jitter prior. The gate doesn't read it.

**One loop closed only in R&D.** Install outcomes → supply-efficiency hex grid → partner boundary update. This runs in `promise_maker/B/`; in production, where B isn't consulted, the loop doesn't operate.

**One loop open everywhere.** Install outcomes → capture apparatus. The single GPS fix, the post-payment free-text address, and the booking UX never receive signal from how drift or address-discovery played out downstream. This is the structural leak. Capture stays as noisy as yesterday because nothing ever tells it otherwise.

**The capture layer is the leak; everything downstream is compensation.** Allocation, coordination, install-time: every engine has built heroics to absorb bad capture. They succeed partially. ~26% of bookings still carry structural capture error no downstream engine can recover.

---

## §5 — What the master story surfaced

The full data backbone is `master_story.md`. Five facts that anchor this frame:

- **25.7% of installs** drift beyond Stage A's apparatus p95 (154.76m). Cannot be produced by GPS physics. Cause: customer captured GPS from not-home. Two sub-populations — near-home-but-not-home bulk (~22%) and hygiene tail (~3%).
- **40.7% of partner-customer pairs** have a location-reason first call: 36.2% `address_not_clear` + 4.5% `partner_reached_cant_find`.
- **77.5% of within-ANC calls** end in confusion — 46% one-sided (partner confused, customer clear) + 31.5% mutual failure. Only 20% resolve on-call.
- **+16.7pp install-rate gap** inside vs outside partner polygon (55.3% vs 38.6%). ANC *touch* rates are similar (43.9% vs 48.2%). The polygon governs *recovery from confusion*, not the occurrence of confusion.
- **+37.1pp** — gali-stuck × outside-polygon = 25.4% install; gali-stuck × inside = 62.5%. The sharpest single-cell difference in the audit. Outside the polygon the partner doesn't know the lane grid.

Install-rate separation across distance deciles is 43.81pp (D1 50.46% → D10 6.66%); the GNN probability separation is 56.77pp. The signal *is* there — the partner responds to geography. What's missing is structured capture to sharpen it, and a loop back to the capture apparatus.

---

## §6 — Journey vision

The system as lived. Two narratives — one customer, one partner — each covering a happy path and an edge path. The principles are not named; they should show.

### Customer — Priya

Priya lives on the third floor of a walk-up in Lajpat Nagar-III. She downloads the Wiom app at 7:42pm from her office in Nehru Place, cab waiting, thinking she can finish the booking before she reaches home.

She opens the app. It asks her to confirm her GPS. She hits confirm. The app does not show her a 25m gate passing silently. Instead it shows her five places near the captured coord: Andhra Bank, Agarwal Sweets, a mandir she has never heard of, Lajpat Nagar Metro Gate 3, and "Sharma General Store." The prompt reads: *"Which of these are within a 2-3 minute walk of your HOME — not your office, not where you are right now. Pick the ones you'd actually walk past at home."*

She knows the metro gate, but it's fifteen minutes from her home. She taps it. The app asks for at least two. She pauses. Of the five, only the metro gate is one she'd claim at home, and she's stretching on that. She taps Andhra Bank on a guess. The app thanks her and runs a quiet second check: one of the landmarks she confirmed does not exist at that coord. It's a probe.

The app doesn't tell her she failed a probe. It says: *"It looks like you may not be home right now. That's okay — please try again once you're home. We promise more accurately that way."* A second link, already present, reads: *"Or speak with someone from our team — they'll help you book."* She takes the callback. She's tired.

The next morning she's home. She re-submits. This time the GPS takes ten seconds — the app asks her to stand still until the accuracy bar settles. Five landmarks, different ones because the coord is different. She recognises three immediately: the park across the gali, Sharma General Store, the mandir she'd dismissed the day before. She taps all three. No probe fails. The app asks her gali name (she types *Third Gali Right of Main Market*), her floor (3), an optional staircase photo. She uploads it.

The app says: *promise made.* Confidence tier on the backend: high. The fee captures now, not yesterday.

Two days later a partner calls. He says: *"Main Agarwal Sweets ke peeche wala mandir dhoondh raha hoon."* Priya: *"Haan, mandir ke saamne se right, teesra ghar, teesri manzil."* Seventy-second call. He installs that afternoon.

Compare yesterday's flow: the promise would have been made against her Nehru Place GPS. The partner would have arrived at a commercial block, Priya would have cancelled, and Wiom would have logged a `SPATIAL_FAILURE` against a problem that wasn't spatial at all.

### Partner — Ramesh (P0213)

Ramesh runs a three-technician team in south Delhi, eighteen months with Wiom. His polygon covers most of Lajpat Nagar, part of New Friends Colony, edges of East of Kailash.

10:14am. A notification arrives. Not a map with a pin. The top of the card:

> *Gali Z, third floor, between your Install I8831213 (Agarwal Sweets side, 12 days ago) and Install I8844901 (park side, 6 days ago). Customer confirmed: Sharma General Store. Gali: Third Gali Right of Main Market. Floor: 3.*
> *Confidence: high. Inside your polygon. Photo available.*

He doesn't open a map. He doesn't read a text blob. He recognises the frame the booking sits in because it references his own recent work. He knows Gali Z — he installed there two weeks ago. He taps accept.

He doesn't call. The technician leaves at 2pm with the packet on his phone, walks from Sharma General Store down the gali to the third house on the right, third floor. Rings the bell. Priya opens the door. He installs.

Ramesh's decline map, which he can open anytime, shows hexes he has declined going soft-red, with a line underneath: *"Decline weight from this hex fades in 90 days if you don't decline again."* He sees his polygon evolving — not as a verdict Wiom has passed on him, but as the visible shadow of his own choices. A hex he declined last week has dimmed slightly. He knows that if he accepts a lead there next month, the dimming reverses.

Now the edge path. A different lead, same day. Confidence tier: medium. The notification reads: *"Edge of your polygon. Near your Install I8801122 on Block C, but we are not sure. Customer landmark: 'Green Water Tank' — you have not installed near this landmark before. Can you install at this landmark?"* Three buttons: *yes, no, not sure.* He taps *not sure*. He vaguely knows the tank but is unclear how the gali grid runs there.

The booking does not auto-dispatch to him. A manual check fires. Someone from ops pings him an hour later with two past-install reference points and he decides yes. Had he tapped *no*, his polygon edge would have sharpened — Wiom would know, cleanly, where he won't serve, the customer would have routed elsewhere rather than entering the coordination-call grinder.

Third path. He is on the ground for a different install, in a gali he thought he knew, but can't find the house. Normally he'd call the customer three times. Today he taps *stuck*. The app pushes the customer's staircase photo to his screen, pings her for a live GPS share, offers a three-way CRE call. The technician finds the house in four minutes.

End of day, install closes. The trace lands in immutable memory: GPS fixes (booking + night-time ping), the landmark Priya picked, her gali, her floor, her photo, Ramesh's accept, his technician's route, the time-to-door. Two weeks later, when another customer two streets away books, *Sharma General Store* sits slightly higher in her landmark picker — because it functioned as a real navigation anchor in a real install. The loop closes.

**The shift the journeys show.** From a blind promise made against a coord + discovery-on-call, to a verified promise made against the customer's own knowledge + a partner notification framed in the partner's own memory. Thresholds, retry limits, and specific triggers are engineering; the structure above is frame.

---

## §7 — Non-negotiable invariants

These are what the built system must never violate in operation. Distinct from §2 principles (which guide construction): invariants hold the running system in calibration against the pressures that will try to bend it.

1. **No verification → no promise.** If the customer's inputs cannot be interrogated (landmark confirmation, jitter check, or an equivalent second channel), the system does not commit. No fallback to 25m-only geometry.
2. **Customer-confirmed anchors are first-class in the partner packet.** The same interaction that verifies the gate populates the partner notification. Same capture, dual purpose — without this propagation, the customer does the work and only the gate benefits, halving the leverage.
3. **Partners serve in zones around landmarks they recognise.** Serviceability is partner-specific and landmark-anchored, not only infrastructure-anchored. Assignment respects this or it manufactures coordination failures.
4. **All partner-visible behavioural feedback decays.** Hex-reddening, decline-zone visualisations, and polygon-edge signals always apply time-decay and evidence-weighting. A feedback mechanism without decay calcifies service zones and blocks market expansion.
5. **Failure modes are tagged by type.** Closure outcomes distinguish `GPS_TRUST_FAILURE`, `ADDRESS_RESOLUTION_FAILURE`, `SPATIAL_FAILURE`, and `OPERATIONAL_FAILURE`. Lumping them silently deletes the learning the new capabilities produce.
6. **Install outcomes return to both the capture apparatus and the belief models.** The open loop closes. Every install, decline, and drift event feeds forward to update landmark confidence, jitter priors, and polygon boundaries.
7. **Scoring artifacts never cross system boundaries.** Trust scores, gaming scores, belief probabilities remain inside Genie. Facts cross; instruments of reasoning don't.
8. **Re-capture is structurally different from initial capture.** The system never asks a customer to "confirm your earlier submission." Round 2 uses different anchors, forces live re-acquisition, or otherwise changes the surface the customer is answering against.

---

## §8 — System flow

The capabilities below chain through five sequential stages plus a control pane alongside. Each stage's output is the next stage's input; a failure at any stage routes to a corrective branch or rejects the booking.

```
            Customer inputs (GPS + landmark + gully/floor + photos)
                                    │
                                    ▼
            ┌──────────────────────────────────────────────┐
            │  1. GATE — input verification                │   ← A1–A10
            │     jitter check, landmark relatability,     │
            │     corrective loops, fallback text, photo   │
            └──────────────────────┬───────────────────────┘
                                   │  only verified inputs move downstream
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  2. BELIEF MODEL 1 — can we service this?    │   ← B1, B4, B5
            │     serviceability + confidence tier         │
            └──────────────────────┬───────────────────────┘
                                   │  confidence tier
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  3. GOVERNANCE — tier-based decision         │   ← B2
            │     promise / defer / reject                 │
            └──────────────────────┬───────────────────────┘
                                   │  on promise
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  4. ACTIVE PROMISE EXPOSURE STOCK            │   ← B3
            │     bookings + confidence + landmark anchor  │
            └──────────────────────┬───────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  5. BELIEF MODEL 2 — best partner ranking    │   ← B6
            └──────────────────────┬───────────────────────┘
                                   │                            ┌──────────────┐
                                   └──────────────────────────► │ Partner-side │
                                                                │  C1 – C7     │
                                                                └──────┬───────┘
                                                                       │
                                   ┌◄──────────────────────────────────┘
                                   │  on closure
                                   ▼
            ┌──────────────────────────────────────────────┐
            │  6. IMMUTABLE MEMORY — full booking trace    │   ← D5
            └──────────────────────────────────────────────┘

    ╔════════════════════════════════════════════════════════════════════════╗
    ║  CONTROL PANE — alongside all six stages                               ║
    ║  D1–D8: monitors, triggers interventions, trains both belief models    ║
    ║  back. night-GPS divergence · visit-tracking · customer-difficulty     ║
    ║  signals · on-ground assist · training loop · landmark confidence      ║
    ╚════════════════════════════════════════════════════════════════════════╝
```

**Stages.** (1) Gate verifies raw inputs; only verified inputs pass. (2) Belief Model 1 scores serviceability into a confidence tier. (3) Governance maps tier to promise / defer / reject. (4) Active promise exposure stock holds committed bookings with their confidence tier and landmark anchor. (5) Belief Model 2 ranks eligible partners for notification. (6) On closure, the full trace lands in immutable memory, which feeds both belief models' training.

**The control pane** is not a stage. It monitors across the pipeline and fires interventions (D1 night-GPS divergence, D2 partner visit tracking, D3 training loop, D4 landmark confidence accumulation, D5 memory, D6 customer-side difficulty signals, D7 on-ground assist, D8 post-install landmark validation).

---

## §9 — Solution capabilities

Grouped by surface: customer-facing pre-promise (A), promise-making (B), partner-facing post-promise (C), control pane (D). The **Nature** column flags `BE` = backend, `FE` = frontend, `CN` = content.

### A. Customer-facing capabilities (pre-promise)

| # | Capability | Nature |
|---|---|---|
| A1 | Capture GPS at booking time (home-GPS) | BE + FE |
| A2 | Capture GPS at night, passively (nightly pings) | BE + FE |
| A3 | **Show 3-5 nearby landmarks to the customer** (public landmark data + Wiom install history — install-history anchors cover hyperlocal Indian landmarks like mandirs, kiranas, gali names that public data misses). Customer prompt: *"Which of these is within 2-3 min walk of your HOME specifically?"* **Requires ≥2 confirmations** (intersection of "near home" + "geographically literate" narrows to actual home; defuses the customer-booking-from-near-landmark-not-home case). Includes **20-25% false-landmark probes** for gaming defence — confirming a nonexistent landmark flags gaming. **Core mechanism:** landmark relatability is the at-home inference gate — if customer cannot confirm ≥2 landmarks after two rounds, fire A6. **Output is dual-purpose:** the same confirmed-landmark record feeds both Belief Model 1 (gate) and C1 (partner notification). | BE + FE + CN |
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

## §10 — Signals

### Leading signals (observable within days of a booking)

- Night-GPS vs booking-GPS divergence rate
- Partner visits location prior to install date (visit-before-install rate)
- On-call address clarity rate (transcripts continue to feed this)
- Photo-relatability confirmation rate when partner is near home
- Fraction of bookings where A3 landmark-pick completed first-try vs required A6 re-capture or A7 text fallback
- "Go home and try again" abandonment rate (instrument from day 1 per Donna; if >8-10%, soften the flow)

### Lagging signals (observable weeks after)

- Booking-to-install drift distribution tightens (baseline: 25.7% beyond apparatus p95)
- Installs per week rise at held promise volume
- Calls per pair drop (baseline 1.92; no target set here — engineering phase)
- Partner decline-zone map stabilises (declines concentrate in known-unserviceable zones, not scattered)

---

## §11 — Out of scope, open questions, companion files

### Out of scope for this document (explicit)

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
- **Specific intervention trigger design for D1, D2, D6, D7** — will be designed once the data starts flowing; long-term solutioning
- **"Address shady" persistent status flag to partner when night-GPS diverges** — specific UX and rule to be designed once data starts flowing; not in this frame
- **Business-model questions** — when the fee captures under defer / reject, refund policy, partner SLA definitions
- **Street View coverage scoping for Indian residential bookings** — data-pull task before A9 locks in behavioural assumptions. Google Street View coverage is patchy for Indian residential colonies / interior galis; metadata API first-check is mandatory. Sample ~1,000 Delhi bookings to measure `ZERO_RESULTS` rate before committing the A9 path to user-facing rollout.

### Open questions (carried forward to solutioning)

Decisions that need to be made before build, but not in this document:

1. When does the fee capture in the defer path? Is the promise conditional on night-GPS validation (refund if fails) or does fee capture only after validation?
2. A3 landmark picker — how many landmarks shown? How many must the customer confirm? What's the re-capture limit before A6 fires?
3. A8 jitter threshold for "noisy" — learned per mobile, or a population floor?
4. C3 decline-zone visibility — real-time or daily snapshot? Own-partner view only, or cross-partner (with privacy mask)?
5. Promise Maker's belief model output — binary (promise/defer/reject) or tiered (High/Mid/Low confidence with different downstream paths)?
6. Medium-confidence C7 "ask partner" routing — what's the ops throughput ceiling before this becomes its own queue bottleneck? (Flagged in Geoff's self-critique.)

### Companion files

- `solution_frame.md` — v1 predecessor (kept untouched; this is v2)
- `master_story.md` · `master_story.csv` — the data backbone this frame rests on
- `possible_architecture.txt` — the raw-notes predecessor both versions articulate
- `solution_synthesis.md` · `solution_diagrams.md` — deeper synthesis and visual companion
- `narration_master_story.txt` — the original narrative outline
