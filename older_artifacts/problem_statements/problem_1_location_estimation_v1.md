# Problem 1 — Location Estimation (Point A: Wiom's Promise Decision)

**Contract type:** Gate 0 thinking contract (per `../Gate 0 Submission Template (explained).docx`)
**Owner:** Maanas
**Narrator:** `story_teller_part1`
**Drafted:** 2026-04-20
**Parent synthesis:** `../README.md` (cross-engine flow + three-engine findings)
**Primary engine this addresses:** `../promise_maker_gps/` (Stage A + Stage B)

---

## Framing — where this problem sits

Satyam's decomposition of the matchmaking problem:

> There are two decision points: **Point A** where Wiom makes a promise using GPS location, and **Point B** where the partner makes a decision. Three parties are involved: Wiom, partner, customer.
>
> Two guiding questions:
> 1. **What is the best way to take location from the customer?** ← this contract (Problem 1)
> 2. How do we ensure consistency / understanding of the location across all parties? ← Problem 2

**This contract is about Point A.** The input signal to Wiom's promise. If this signal is wrong, every downstream decision — partner ranking, partner navigation, install feasibility — operates on a corrupted coordinate, regardless of how good the downstream systems get.

The third party (customer) is the upstream source for Point A. The "best way to take location from the customer" is the core capability this contract builds.

---

## SECTION A — Problem Definition

### 1. Observed / Expected / Evidence

**Observed** (from Satyam):
> User location inferred by system is inaccurate in X% of cases (e.g., mismatch between estimated and actual install location).

**Observed** (quantified from `../promise_maker_gps/booking_install_distance/` · Stage B, Delhi Dec-2025 installed non-BDO, n = 3,855):
- p50 of `install_drift_m` = **22.5 m**
- p75 = **162.7 m** · p95 = 767.2 m · max = 213 km
- **25.7% of installs (991) have drift beyond Stage A apparatus p95 (154.76m)** — this is the X%. These drifts cannot be explained by GPS physics; they are structural capture error.
- 3.2% have drift > 1 km · 0.4% have drift > 10 km — hard data-hygiene tail
- `excess_drift_m` (drift net of Stage A p95): p50 excess = 186 m, p99 excess = 2,716 m

**Expected** (from Satyam):
> User location should be accurate enough to support correct downstream decisions (e.g., booking fee eligibility, serviceability).

**Expected — quantified:**
- `install_drift_m` p95 should be within Stage A apparatus p95 (~155 m) or below
- % of installs with structural drift (> 155 m): **<5%** (down from 25.7%)
- Data-hygiene tail (>1 km): **<0.5%** (down from 3.2%)

**Evidence** (Satyam's list + where it maps in our analyses):

| Satyam's evidence item | Where we measure it | Current state |
|---|---|---|
| % bookings rejected incorrectly due to location mismatch | Stage B declined cohort (pending) vs installed cohort drift comparison | Installed cohort: 25.7% structural drift. Declined cohort pull is the next step — will tell us if Promise Maker rejects low-quality GPS captures at a higher rate or randomly |
| % installs requiring manual correction | Partner-reported address corrections post-install (not yet sourced; app event or BDO log) | To source |
| Cases where CSP reports location mismatch | `../coordination/` transcripts — `primary_reason = address_not_clear` + call-level stuck_at = landmark/gali | 20% of calls are `address_not_clear` at transcript level; 8.7% stuck at landmark step (before gali reachable) |

Two of three evidence items are partially measured today. The third needs sourcing.

### The evidence cross-checks itself across engines

Three independent findings converge on "booking coord is noisy at capture":

1. **`promise_maker_gps/` Stage B:** 25.7% of bookings have drift beyond apparatus noise.
2. **`allocation_signal/`:** 448 km D10 tail on `nearest_distance` flagged as likely data hygiene (Monday action #9).
3. **`coordination/`:** transcript-level address friction is **flat** across distance deciles (~20% everywhere) — mechanically consistent with upstream GPS noise washing out decile ordering.

Three engines, one signal: the coordinate entering Promise Maker is noisy.

---

## SECTION B — Project Definition

### 2. Objective

**Reduce the structural drift rate (% of bookings where `install_drift_m` exceeds Stage A p95) from 25.7% to <5% within one release cycle.**

Secondary:
- Data-hygiene tail (drift > 1 km): 3.2% → <0.5%
- p75 of `install_drift_m`: 162.7 m → <100 m

### 3. Classification + Rationale

**Capability Build.**

Rationale (confirmed with Satyam — this *can* be argued as Capability Build):

- **Not Hygiene** — hygiene fixes a broken thing that used to work. The home-GPS capture is not "broken"; it's working exactly as designed (take one GPS fix, pass/fail against the 25m gate). The problem is the design itself lacks validation.
- **Not Efficiency** — efficiency improves an existing mechanism. We are adding a mechanism (cross-validation of the captured coordinate against independent signals) that does not exist today. There's nothing to make faster.
- **Not Outcome Shift alone** — although the downstream outcome (promise quality, install conversion) will shift, the *mechanism* is a new system layer. Outcome Shift without a capability build would be tuning the 25m gate threshold, which Stage B shows is a category error (the gate doesn't test drift).
- **IS Capability Build** — Wiom currently has no pre-promise location validation beyond the 25m infrastructure-graph test. Building a "validate the captured coord against independent signals before committing" capability is genuinely new system ability.

### 4. Root Cause

Structural, not superficial:

**Root cause:** The home-GPS submission (flow step 4) is a **single-shot capture with no cross-validation**. The promise (step 7) fires on the sole basis of that one GPS fix passing the 25m infrastructure test. There is no independent corroborating signal before the commit.

Contributing factors identified in the data:
1. **No structured address available before promise** — text address is collected in step 8, *after* the fee is captured. So the GPS cannot be reconciled against a typed address / pincode / landmark pre-commit.
2. **No environmental context in the GPS capture** — indoor / night / low-battery / cached-fix conditions degrade GPS reliability, and we don't measure or react to them. (Stage A evidence: per-ping jitter varies hugely across time-gap buckets; prior notebook work by Rohan explored night-indoor-GPS hypothesis.)
3. **`booking_accuracy` (device self-report) is captured but not gated on** — if self-report is correlated with actual drift (pending Stage B slice), this is a free signal we're not consuming.
4. **The 25m gate gives false confidence** — it tests coordinate-vs-infrastructure, not coordinate-vs-truth. A noisy coordinate that happens to land near an infrastructure point passes the gate anyway.

### 5. Leverage Level

**LP4 — rule change + new information flow** (Meadows hierarchy).

Not LP2 (parameter change): tightening the 25m gate to e.g. 10m does nothing if the coord itself is 100m off.
Not LP5 (system purpose change): Wiom's matchmaking purpose stays the same.
IS LP4 because we are changing the **rules of promise-making** — adding a pre-commit validation step that does not exist today, consuming new information (pincode, text, time-of-day risk score) that the current rule ignores.

---

## SECTION C — Measurement

### 6. Measurement Stack

| Layer | Meaning | Metric for this project |
|---|---|---|
| **L5** — final outcome | Company-level value | Promise→install conversion rate (# installs / # promises made) |
| **L4** — driver | System-level driver | % promises where all downstream engines (Allocation, Coordination) succeed without location-driven friction |
| **L3** — **SIGNAL** (most important) | Fast measurable proxy of this project working | **% of installed bookings with `install_drift_m > Stage A p95`** — the 25.7% that Stage B identified as structural capture error. Target: <5%. |
| **L2** — execution proof | Coverage of the intervention | % of bookings where the pre-promise validator ran (validator coverage) |
| **L1** — system correctness | Wiring works | Validator service up, events emitted, no data gaps |

### 7. Tracking Table

| Metric | Baseline | Target | Frequency | Source |
|---|---:|---:|---|---|
| Structural drift rate (% installs with drift > 155 m) | **25.7%** | <5% | Weekly | `promise_maker_gps/booking_install_distance/` (recomputed on new cohort post-intervention) |
| Drift p75 | 162.7 m | <100 m | Weekly | same |
| Data-hygiene tail (drift > 1 km) | 3.2% | <0.5% | Weekly | same |
| Validator coverage (% bookings that ran through validator) | 0% | >95% | Daily | Promise Maker event log |
| Promise→install conversion | TBD (to baseline) | +Xpp | Weekly | `booking_logs` funnel: `booking_verified` → `wifi_connected_location_captured` |
| CSP-reported address mismatches (call-level) | 20% (transcript-level `address_not_clear`) | <10% | Weekly | `../coordination/` pipeline re-run |

---

## SECTION D — Leading Signal (Critical)

### 8. Leading Signal

**% of newly captured `booking_lat/lng` values that the pre-promise validator flags as high-risk** (before the commit, not after).

Why *this* metric, not `install_drift_m`: drift can only be measured *post-install*, which is lagged by days-to-weeks. The validator's flag fires at capture time (step 4/6 of the flow), giving us sub-hour observability of whether the intervention is running.

### 9. Signal Validity (must prove three properties)

**Observability:**
- The validator runs inline in the booking flow. Its output (flag / no-flag) is written to `booking_logs` as a new event.
- Observable within **minutes** of a booking.
- We already have the SQL patterns (see `promise_maker_gps/booking_install_distance/query_install_drift.txt`) — adding validator-flag columns is additive.

**Causality:**
- Validator flag → block promise OR request re-capture → bookings that complete have passed validator → lower structural drift downstream → higher promise→install conversion
- The causal chain is direct: flag is a gate; the gate directly affects which bookings reach commit.
- Counter-test: if the validator is wired but has no block/re-capture behavior (monitor-only), drift should not change — isolating the effect to the block, not the measurement.

**Sensitivity:**
- Validator features (pincode cross-check, `booking_accuracy` threshold, time-of-day risk, text-address consistency once available) are chosen because Stage B showed structural drift is NOT random — it correlates with identifiable capture conditions.
- A move on the flag rate should directly move the drift distribution.
- Dose-response: stricter threshold → higher flag rate → tighter downstream drift.

### 10. Signal Timing

**Flag rate:** observable within **hours** of deployment.
**Structural drift (L3):** observable within **2-4 weeks** (cohort needs to accumulate installs — Stage B's 2-month lookahead).

### 11. Scope Constraint

**Yes** — the leading signal is fully observable within a sprint timeline. The L3 outcome metric lags by one install-window (~1 month), but the operational signal (flag rate, validator coverage) is real-time.

---

## SECTION E — Ownership & Mapping

### 12. Owner

**Maanas** (one person, not a team).

### 13. Driver Mapping

**Promise fulfillment rate** (core Wiom driver). Downstream beneficiaries:
- Allocation (`../allocation_signal/`) — `nearest_distance` becomes more trustworthy, tail-km bookings drop out of the ranker's input
- Coordination (`../coordination/`) — fewer gali-stuck calls, because the partner arrives at a coord that is actually near the home

### 14. NUT Chain

```
Pre-promise location validator
    ↓
Structural drift rate drops (25.7% → <5%)
    ↓
Promise→install conversion rises
    ↓
Lower CAC per installed customer + higher LTV capture
    ↓
Net installed paying customers (company value)
```

*(NUT = Net installed paying customer revenue. Placeholder — Maanas to override with Wiom's canonical NUT metric if different.)*

### 15. Validation Path

**If L3 signal moves as predicted, the NUT chain is proven:**

1. Validator fires and flags high-risk captures (L2 coverage > 95%)
2. Flagged captures are blocked / re-captured (L1 correctness)
3. Installed-cohort `install_drift_m` distribution tightens (L3 structural drift drops)
4. Promise→install conversion rises (L4/L5)
5. CSP-reported mismatches (`../coordination/` transcript rate) drop (cross-engine confirmation)

If step 3 moves but step 4 does not, the bottleneck has shifted downstream — Problem 2's territory.
If step 3 does not move, the validator features are wrong — re-investigate using Stage B slices (time_bucket, booking_accuracy) not yet closed.

---

## SECTION F — Execution

### 16. Time Class

**Capability Build → 2-3 sprints.**
- Sprint 1: close Stage B open slices (time_bucket, booking_accuracy correlation) to identify the validator features
- Sprint 2: build the validator (rule-based MVP first, learned model later), wire it into the booking flow in shadow mode
- Sprint 3: switch to blocking mode, monitor, iterate

### 17. Execution Plan

| Step | Agent does | Human does |
|---|---|---|
| 1 | Close Stage B slices: drift × `time_bucket` (night-indoor hypothesis), drift × `booking_accuracy` (self-report calibration), declined-cohort comparison | Maanas reviews outputs, picks validator feature set |
| 2 | Build pre-promise validator as a rule engine: (a) `booking_accuracy` threshold, (b) time-of-day risk lookup, (c) pincode reverse-geocode consistency check against captured lat/lng, (d) Stage B first-ping comparison if a prior install exists for the mobile | Maanas + Wiom product: design re-capture UX, decide threshold values, approve rollout |
| 3 | Instrument validator events, build weekly drift-cohort report | Maanas monitors L2/L3/L4 weekly |
| 4 | If L3 moves, propose learned-model upgrade (features from step 1 → classifier) | Maanas + Wiom ML: review before ship |

*(Specific validator architecture, routing bands, and thresholds — design choices explored in the sibling solution synthesis, not in this contract.)*

---

## SECTION G — Learning Logic

### 18. Hypothesis

**If we add a pre-promise location validator that flags bookings where the captured coord is high-risk against independent signals, and routes those bookings through a re-capture or human-confirmation path before the promise is committed, then the structural drift rate (% bookings with `install_drift_m` > Stage A p95) will drop from 25.7% to <5% within 4 weeks of deployment.**

Mechanism: replace a single-shot, un-validated GPS capture with a cross-validated one. The specific validator features, routing bands, and thresholds are design choices explored separately (see sibling solution synthesis, not this contract).

### 19. Risk Check

| Risk | Mitigation |
|---|---|
| Customer drop-off if re-capture friction is too high | Shadow-mode first → measure flag rate → only enable blocking when flag rate is tolerable (<15%). Optimize re-capture UX. |
| Validator false positives (flags clean captures) | Hold-out cohort runs validator in monitor-only mode; measure Stage B drift in flagged vs non-flagged to confirm discrimination. |
| Pincode reverse-geocode dependency (external API) | Cache pincode→lat/lng polygons offline; fall back to self-report check only if API fails. |
| Validator can't explain structural drift because root cause is different (e.g., customer fraud on GPS — uploading spoofed coords) | If L3 doesn't move despite high flag rate, investigate fraud / gaming — flag for A3 (mobile bimodality segmentation in `../promise_maker_gps/gps_jitter/`). |
| The 25m gate itself becomes the next leak (tighter input, same gate = different failure mode) | Stage B validator's output should *feed* the gate, not run in parallel. Gate should reject on (gate fail) OR (validator high-risk). |

### 20. Learning Path

| Outcome | Decision |
|---|---|
| Flag rate high + L3 drift drops + L4/L5 conversion rises | **Scale** — roll out to all cities. Plan learned-model upgrade. |
| Flag rate high + L3 drift drops + L4/L5 flat | Problem 1 is solved; remaining conversion loss lives at Point B. **Hand off to Problem 2 / Coordination.** |
| Flag rate high + L3 flat | Validator features are wrong. **Re-investigate** using Stage B slices (time_bucket, booking_accuracy) and customer-side qualitative research. |
| Flag rate low | Validator is too permissive. **Tighten thresholds**, re-test. |
| Flag rate very high (>40%) + customer drop-off | UX is wrong, not the validator. **Redesign re-capture flow.** |

---

## FINAL RULE (per template)

- ✅ Clear problem: 25.7% of bookings have structural capture error beyond apparatus noise — quantified three ways across three engines
- ✅ Measurable signal: validator flag rate (real-time) + structural drift rate (weekly)
- ✅ Testable hypothesis: pre-promise validator → drift drops in 4 weeks

**This is a project.**

---

## Open pre-requisites before build starts

These should close in Sprint 1 of the execution plan. They are tracked in the sibling subfolder status checklists:

| Pre-requisite | Sits in | Blocks |
|---|---|---|
| Stage B × `time_bucket` slice — validate night-indoor hypothesis | `../promise_maker_gps/booking_install_distance/` | Validator feature #2 (time-of-day risk) |
| Stage B × `booking_accuracy` correlation | same | Validator feature #1 (self-report threshold) |
| Declined-cohort Stage B comparison | same | Understanding whether Promise Maker today rejects low-quality GPS at all |
| Mobile bimodality labels (A3) | `../promise_maker_gps/gps_jitter/` | Validator feature #4 (prior-install ping comparison for repeat mobiles) |
| Ilaaka-GPS vs home-GPS drift analysis (flow step 2 vs step 4) — not yet sourced | TBD — new analysis | Understanding whether ilaaka captures are a pre-signal for home-capture quality |

---

## Cross-link: relation to Problem 2

Problem 1 solves the **input quality at Point A**. Problem 2 solves the **signal consistency across parties between Point A and Point B**. The two problems are complementary — solving only one leaves the other's failure mode dominant. Joint storyline in `../README.md` once both contracts ship.
