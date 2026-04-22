# Problem 1 — Location Estimation (Point A: Wiom's Promise Decision) — v2

**Contract type:** Gate 0 thinking contract (per Wiom's Gate 0 Submission Template).
**Owner:** Maanas
**Drafted:** 2026-04-21
**Primary engine this addresses:** Wiom's Promise Maker (GPS apparatus-noise analysis — Stage A — and booking-to-install drift analysis — Stage B).
**Data backbone:** `master_story.md` + `master_story.csv` (shared alongside).

---

## Framing — where this problem sits

Satyam's decomposition of the matchmaking problem:

> Two decision points: **Point A** where Wiom makes a promise using GPS location, and **Point B** where the partner makes a decision. Three parties: Wiom, partner, customer.
>
> Two guiding questions:
> 1. **What is the best way to take location from the customer?** ← this contract
> 2. How do we ensure consistency / understanding of location across all parties? ← companion contract

This contract is about **Point A**. The input signal to Wiom's promise. If this signal is wrong, every downstream decision — partner ranking, partner navigation, install feasibility — operates on a corrupted coordinate, regardless of how good the downstream systems get.

The third party (customer) is the upstream source for Point A. The "best way to take location from the customer" is the core capability this contract builds.

---

## SECTION A — Problem Definition

### 1. Observed / Expected / Evidence

**Stage A / Stage B — what these mean (used throughout this contract).**

- **Stage A** is the measurement of the **GPS apparatus's own noise** — how much a mobile's fix jitters from ping to ping under real-world conditions. Computed across **8,317 mobiles × 20,231 subsequent pings** (`master_story.md` Part A). Produces a per-ping jitter distribution — p50 = 7.7m, p75 = 20m, **p95 = 154.76m**. This p95 is the ceiling GPS physics alone can plausibly produce. Anything wider is not apparatus noise.
- **Stage B** is the measurement of **booking-to-install drift** — the distance between the GPS captured at booking and the WiFi-connected GPS observed when the install actually happens (the latter being ground-truth for the home's true location). Computed on the Delhi Dec-2025 installed non-BDO cohort (n = 3,855). When a booking's Stage-B drift exceeds Stage-A's p95, we call it **structural drift** — wider than apparatus physics can explain, therefore attributable to something else (customer captured GPS from not-home).

**Observed (from Satyam):**
> User location inferred by system is inaccurate in X% of cases (mismatch between estimated and actual install location).

**Observed (quantified, from `master_story.md` Part D.A; cohort: Delhi Dec-2025 installed non-BDO, n = 3,855):**

- `install_drift_m` p50 = 22.5m, p75 = 162.7m, p95 = 767.2m, max = 213km
- **25.7% of installs (991)** drift beyond Stage A apparatus p95 (154.76m). These drifts cannot be explained by GPS physics — they are structural capture error.
- 3.2% drift > 1km; 0.4% drift > 10km — hard data-hygiene tail
- Mechanism attribution: **customer captured GPS from not-home.** Two sub-populations:
  - Near-home-but-not-home bulk (~22% of installs, drift 155m–1km): café, shop, street, neighbour's house.
  - Hygiene tail (~3%, drift >1km): wrong-locality or tap errors.

**Expected (from Satyam):**
> User location should be accurate enough to support correct downstream decisions (booking fee eligibility, serviceability).

**Expected — quantified:**
- `install_drift_m` p95 ≤ Stage A apparatus p95 (~155m)
- % installs with structural drift (>155m): **<5%** (down from 25.7%)
- Data-hygiene tail (>1km): **<0.5%** (down from 3.2%)

**Evidence (Satyam's list + where it maps):**

| Satyam's evidence item | Where measured | Current state |
|---|---|---|
| % bookings rejected incorrectly due to location mismatch | Stage B declined-cohort (pending) vs installed-cohort drift comparison | Installed cohort: 25.7% structural drift |
| % installs requiring manual correction | Upstream proxy from Stage A per-mobile jitter distribution (`master_story.md` Part A). A noisy mobile produces fixes unreliable enough that downstream correction becomes likely. Captures the capture-side source of correction need, upstream of whether the correction actually happens. | **~30% of mobiles (2,496 of 8,317)** have worst-case single fix >25m; **~25%** have per-mobile median jitter >20m. This is an upper bound on % installs where capture-side quality would warrant correction. Complements the `partner_reached_cant_find` ground-residue signal in Row 3 (which captures the subset where correction *attempts* actually surface on-ground). |
| Cases where CSP reports location mismatch | Proxied by `partner_reached_cant_find` at pair-level, restricted to the P1-attributable subset (partner lost at locality/landmark, not at gali/floor — the latter is the companion contract's territory). Denominator excludes `noise_or_empty` pairs (21% of cohort, unusable transcripts). Broader proxy available via `primary_reason = address_not_clear` (36% of pairs) — kept as secondary signal. | **Primary proxy:** 4.4% of classifiable pairs (90 of 2,024) — "partner reached, can't find the block" on first call. Install rate in this bucket is 71%, so this is a friction indicator, not a failure rate. **Secondary proxy:** 20% transcript-level `address_not_clear`; 8.7% of calls stuck at landmark step. |

### The evidence cross-checks itself across engines

Findings across two engines converge on "booking coord is noisy at capture, and the noise lands on the ground":

1. **Promise Maker GPS analysis (capture predisposition and booking-time outcome):** Stage A shows ~30% of mobiles carry unreliable GPS — worst-fix exceeds 25m on 2,496 of 8,317 mobiles (capture-side predisposition). Stage B shows 25.7% of installed bookings drift beyond Stage A's own p95 of 155m — wider than apparatus physics can explain, consistent with customer-not-at-home capture at booking time.
2. **Coordination call analysis (two complementary findings):**
   - **(a) Pre-accept dropdown pattern is an artifact, not a gradient.** Transcript-level address friction is flat across distance deciles (~20% everywhere). Post-analysis (`master_story.md` Part C.B) confirms the dropdown's 48% → 2.5% prob-decile pattern is a **decline-channel artifact** — partners click "address not clear" as a polite exit on low-prob bookings, not a measurement of real address ambiguity.
   - **(b) Ground residue confirms capture failure lands on-ground.** 4.4% of classifiable pairs (90 of 2,024, P1-attributable cut) carry a `partner_reached_cant_find` signal with address-chain stuck at locality or landmark — partners arriving at the wrong block as a direct consequence of upstream capture noise.

Two engines, one causal chain: noisy capture at the mobile (Stage A) → structural drift at booking time (Stage B) → location mismatch on the ground (Coordination residue). Allocation-side evidence was previously cited here but resolves to a partner-record data-hygiene anomaly rather than a customer-capture-quality signal — dropped to keep the chain clean.

---

## SECTION B — Project Definition

### 2. Objective

**Objective (measurable shift):** reduce structural drift rate on the installed cohort from **25.7% → <5%** within one release cycle. Secondary: p75 `install_drift_m` 162.7m → <100m; data-hygiene tail >1km 3.2% → <0.5%.

*Framed as:* inputs should be verified before making a promise — the customer's self-report that he is at home is not enough evidence to commit on.

### 3. Classification + Rationale

**Capability Build.**

Rationale:

- **Not Hygiene** — hygiene fixes something that used to work. Home-GPS capture is working exactly as designed (one GPS fix, pass/fail against 25m gate). The design itself lacks verification.
- **Not Efficiency** — efficiency improves an existing mechanism. This contract adds a mechanism (independent verification of the customer's self-report at capture) that does not exist today.
- **Not Outcome Shift alone** — the downstream outcome (promise quality, install conversion) will shift, but the *mechanism* is a new system layer. Outcome Shift without a capability build would be tuning the 25m threshold, which is a category error (the gate doesn't test drift — `master_story.md` Part D.A).
- **IS Capability Build** — Wiom currently has no pre-promise verification channel beyond the 25m infrastructure check. Building an independent-verification layer is genuinely new system ability.

### 4. Root Cause

Structural, not superficial.

**Root cause.** Wiom commits (takes the fee) on the customer's self-report ("yes, I am at home") without any independent channel confirming the self-report is true. The system asks, the customer answers, Wiom takes the answer at face value. One lat/long + text address is the entire evidence basis at commit. There is no structured representation of the customer's mental model (landmark, gali, floor) at the gate — so verification has nothing to be verified against.

**Contributing mechanisms (re-ordered post-analysis):**

1. **No independent second channel at the gate.** Verification substrate does not exist. Self-report and coord arrive from the same uninterrogated source.
2. **Single point-in-time fix when home-presence is a multi-observation property.** A phone at one location once is ambiguous; a phone at home at 7am, 11pm, and the next morning is at home.
3. **Available signals not consumed.** `booking_accuracy` (device self-report), per-mobile jitter profile (Stage A — would flag ~30% of mobiles as unreliable), night-time GPS, pincode reverse-geocode — all feasible, none gated at commit.
4. **25m infrastructure check mistaken for verification.** It tests coord-vs-infrastructure, not coord-vs-truth. A noisy coord that happens to fall near an install passes regardless of whether the customer is at home.

### 4.1 Why trust-without-verification is the root, not single-shot-capture

V1's root-cause statement ("single-shot capture with no cross-validation") was a *symptom* framing. Single-shot capture is one mechanism by which trust-without-verification manifests — not the cause.

The distinction matters for the fix: a validator on top of an un-interrogated self-report still asks the customer to confirm what he just said. That fails Principle P4 (re-capture must be structurally different). The real move is to never commit on self-report alone — build an independent channel that tests home-presence before the fee fires.

This is why the intervention is classified as Capability Build: we are not improving validation on existing inputs; we are **creating new verification signals that don't exist today** (structured customer knowledge — landmark / gali / floor — captured at flow steps 4-6).

### 5. Leverage Level

**LP4 — rule change + new information flow** (Meadows hierarchy).

- Not LP2 (parameter change) — tightening the 25m threshold does nothing if the coord itself is 100m off.
- Not LP5 (system purpose change) — Wiom's matchmaking purpose stays the same.
- **IS LP4** — the rule of promise-making changes: "commit requires corroboration of self-report by an independent channel." New information flows consumed: ≥2 customer-confirmed landmarks, night-GPS agreement, per-mobile jitter prior. The current rule ignores all of these at commit.

---

## SECTION C — Measurement

### 6. Measurement Stack

| Layer | Meaning | Metric for this project |
|---|---|---|
| **L5** — final outcome | Company-level value | Promise → install conversion rate |
| **L4** — driver | System-level driver | % promises where downstream engines (Allocation, Coordination) succeed without location-driven friction. Populating metric: CSP-reported location mismatch on-ground — P1-attributable `partner_reached_cant_find` rate on classifiable pairs. |
| **L3** — **SIGNAL** | Fast measurable proxy | **% of installed bookings with `install_drift_m > Stage A p95`** (target <5%). Leading execution signal: **% bookings with verification completed at capture** (target >90%). |
| **L2** — execution proof | Coverage of intervention | % of bookings where verification channel ran end-to-end |
| **L1** — system correctness | Wiring works | Verification service up, events emitted, no data gaps |

### 7. Tracking Table

| Metric | Baseline | Target | Frequency | Source |
|---|---:|---:|---|---|
| Structural drift rate (drift > 155m) | **25.7%** | <5% | Weekly | `master_story.md` Part D.A (recomputed on post-intervention cohort) |
| Drift p75 | 162.7m | <100m | Weekly | same |
| Data-hygiene tail (drift > 1km) | 3.2% | <0.5% | Weekly | same |
| Verification-completion rate (≥2 landmark confirmations OR fallback loop completed) | 0% | >90% | Daily | New event in booking event log |
| Promise → install conversion | TBD (to baseline) | +Xpp | Weekly | Booking event log funnel |
| CSP-reported address mismatches (transcript-level) | 20% | <10% | Weekly | Coordination call-analysis pipeline re-run |
| CSP-reported location mismatch on-ground — P1-attributable (pair-level; filter: `primary_first = partner_reached_cant_find` AND `addr_chain_stuck_at_mode ∈ {na, landmark}`; denominator excludes `noise_or_empty` pairs) | **4.4%** | <2% directional | Weekly | Coordination call-analysis pipeline re-run. Friction indicator (install rate in this bucket is 71%), not a failure rate — tracks how often partners arrive at wrong-block as a downstream residue of capture failure. |

---

## SECTION D — Leading Signal (Critical)

### 8. Leading Signal

**% of bookings where the customer's self-report ("yes at home") was independently corroborated by a second channel before the fee captured** — measured as ≥2 confirmed landmarks near home (via A3 picker) OR fallback corrective loop completed (A6).

Why this metric, not `install_drift_m`: drift is measurable only post-install, lagged by days-to-weeks. The verification-completion event fires at capture time, giving sub-hour observability of whether the intervention is running and directly tests whether the root cause has been addressed.

### 9. Signal Validity

**Observability.**
*One-line proof:* verification-completion event fires in real-time, measurable within minutes of booking.

Fires inline in the booking flow. Output (complete / incomplete / gaming-flagged) written to the booking event log as a new event. SQL patterns additive from existing install-drift analysis queries.

**Causality.**
*One-line proof:* verification-completion directly gates the fee; bookings that commit have passed verification; drift drops because committed bookings only fire when the customer is demonstrably at home.

Chain: self-report → independent channel check (landmark confirmations or night-GPS agreement) → verification-complete or corrective loop → commit only if complete → drift tightens downstream. Counter-test: run verification in monitor-only mode (no commit gating); drift should not change — isolating the effect to the gate.

**Sensitivity.**
*One-line proof:* dose-response — stricter verification threshold → higher incomplete rate → tighter downstream drift.

Verification features (landmark relatability, `booking_accuracy` threshold, per-mobile jitter prior, time-of-day) are chosen because `master_story.md` shows structural drift is not random — it correlates with identifiable capture conditions.

### 10. Signal Timing

- Verification-completion rate: observable within **hours** of deployment.
- L3 structural drift rate: observable within **2-4 weeks** (install cohort accumulation).

### 11. Scope Constraint

**Yes.** The leading signal fires within a sprint timeline. L3 outcome metric lags by one install-window (~1 month), but operational signal (verification-completion rate, coverage) is real-time.

---

## SECTION E — Ownership & Mapping

### 12. Owner

**Maanas** (one person, not a team).

### 13. Driver Mapping

**Promise fulfilment rate** (core Wiom driver).

Downstream beneficiaries:
- Allocation engine — `nearest_distance` becomes trustworthy; tail-km bookings drop out of ranker's input.
- Coordination engine — fewer gali-stuck calls because the partner arrives at a coord actually near the home.

*Belief-model note.* The existing R&D Promise Maker belief model becomes useful in production once this capability ships — the structured capture this problem requires is the substrate the belief model needs. Supporting, not primary.

### 14. NUT Chain

**Verified capture at commit → Promise → install conversion rate → Net installed paying customer revenue.**

Verification substrate raises the quality of what Wiom commits on → more promises convert to installs → cost per installed customer drops and retention rises → NUT grows.

*(NUT = Net installed paying customer revenue. Override with Wiom's canonical NUT metric if different.)*

### 15. Validation Path

**If the L3 signal moves as predicted, the NUT chain is proven:**

1. Verification fires and completes for >90% of bookings (L2 coverage)
2. Incomplete verifications route through corrective loop or reject (L1 correctness)
3. Installed-cohort `install_drift_m` distribution tightens (L3 structural drift drops)
4. Promise → install conversion rises (L4/L5)
5. CSP-reported mismatches (coordination-transcript rate) drop (cross-engine confirmation)
6. **CSP-reported location mismatch rate (P1-attributable) drops** — if drift tightens AND partners stop arriving at the wrong block (the `partner_reached_cant_find` proxy, P1-attributable cut), the fix has landed all the way to the ground.

If step 3 moves but step 4 does not, the bottleneck has shifted downstream — companion contract's territory.
If step 3 moves but step 6 does not, the verification is catching a different sub-cohort than the one producing on-ground friction — investigate cohort composition (which captures are being filtered by verification vs which ones are producing `partner_reached_cant_find`).
If step 3 does not move, verification features are wrong — re-investigate using Stage B slices (time_bucket, booking_accuracy) not yet closed.

---

## SECTION F — Execution

### 16. Time Class

**Capability Build → 2-3 sprints.**

- Sprint 1: close Stage B open slices (time_bucket, `booking_accuracy` correlation, declined-cohort comparison). Identify verification feature set.
- Sprint 2: build the independent-verification channel (landmark picker + ≥2 confirmation + two-round corrective loop) in shadow mode.
- Sprint 3: switch to commit-gating mode. Monitor. Iterate.

### 17. Execution Plan

| Step | Agent does | Human does |
|---|---|---|
| 1 | Close Stage B slices: drift × `time_bucket`, drift × `booking_accuracy`, declined-cohort comparison | Maanas reviews, picks verification feature set |
| 2 | Build independent-verification channel: landmark picker (Google Address Descriptors + Wiom install-history fallback), ≥2 confirmation requirement, two-round structurally-different corrective loop, false-landmark probe rate | Maanas + Wiom product: decide UI, thresholds, rollout |
| 3 | Instrument verification events; build weekly drift-cohort report | Maanas monitors L2/L3/L4 weekly |
| 4 | If L3 moves, propose learned-model upgrade (verification features → classifier) | Maanas + Wiom ML: review before ship |

*(Specific verification architecture, confidence bands, and thresholds — design choices for the system spec, not this contract.)*

---

## SECTION G — Learning Logic

### 18. Hypothesis

**If we require the customer's self-report of home-presence to be independently corroborated by at least one additional channel (≥2 confirmed landmarks near home, or night-GPS agreement, or fallback corrective loop completion) before committing the fee, then the structural drift rate on installed cohort will drop from 25.7% to <5% within 4 weeks — because the commit only fires when self-report is verified, not asserted.**

Mechanism: replace a one-witness commit (self-report + coord) with a two-witness commit (self-report + independent corroboration).

### 19. Risk Check

| Risk | Mitigation |
|---|---|
| Customer drop-off if verification friction is too high | Shadow-mode first → measure incomplete rate → only gate when rate is tolerable (<15%). Optimise UX. |
| Verification false positives (flags clean captures as incomplete) | Hold-out cohort runs verification in monitor-only mode; measure drift in complete vs incomplete to confirm discrimination. |
| Gaming — customer confirms landmarks he does not actually live near | 20-25% false-landmark probe rate; gaming-score channel kept structurally separate from the verification-completion channel — different feature sets, different downstream treatment (re-capture vs human review). |
| External-API dependency (Google Address Descriptors, pincode reverse-geocode) | Cache responses per hex; fallback to install-history anchors + self-report check only if API fails. Fail-open, never fail-closed on external dependency. |
| Root cause is different for a sub-cohort (e.g., structural drift concentrated in spoofed coords, not at-home/not-at-home) | If L3 doesn't move despite high verification-completion rate, investigate fraud / spoofing — flag for mobile-bimodality work in GPS-jitter analysis. |

### 20. Learning Path

| Outcome | Decision |
|---|---|
| Verification-completion rate high + L3 drift drops + L4/L5 conversion rises | **Scale** — roll out to all cities. Plan learned-model upgrade. |
| Verification-completion rate high + L3 drift drops + L4/L5 flat | P1 is solved; remaining conversion loss lives at Point B. **Hand off to companion contract / Coordination.** |
| Verification-completion rate high + L3 flat | Verification features are wrong. **Re-investigate** via Stage B slices (time_bucket, `booking_accuracy`) and customer-side qualitative research. |
| Verification-completion rate low | Thresholds too permissive or UX too heavy. **Tighten or redesign**, re-test. |
| Incomplete rate very high (>40%) + customer drop-off | UX is wrong, not the verification logic. **Redesign corrective loop.** |

---

## FINAL RULE (per template)

- ✅ Clear problem: 25.7% of installed bookings carry structural drift beyond apparatus noise — quantified across two engines (Promise Maker capture/outcome + Coordination on-ground residue), and grounded upstream in per-mobile jitter profile (Stage A).
- ✅ Measurable signal: verification-completion rate (real-time) + structural drift rate (weekly).
- ✅ Testable hypothesis: independent corroboration of self-report → drift drops in 4 weeks.

**This is a project.**

---

## Open pre-requisites before build starts

These should close in Sprint 1:

| Pre-requisite | Sits in | Blocks |
|---|---|---|
| Stage B × `time_bucket` slice (night-indoor hypothesis) | Install-drift analysis cohort | Verification feature: time-of-day risk |
| Stage B × `booking_accuracy` correlation | same | Verification feature: self-report threshold |
| Declined-cohort Stage B comparison | same | Understanding whether Promise Maker today rejects low-quality GPS at all |
| Mobile bimodality labels | GPS-jitter analysis | Verification feature: prior-install ping comparison for repeat mobiles |

---

## Cross-link: relation to companion contract

This contract solves **input verification at Point A**. The companion contract (`problem_2_address_translation_v2.md`) solves **signal consistency across parties between Point A and Point B**. The two problems are **parallel workstreams** resting on a **shared upstream element** — structured landmark / gali / floor capture at flow steps 4-6. Captured once, consumed by both.

Solving only this contract: cleaner GPS, but the address is still unstructured — partner still calls to parse landmark → gali → floor.
Solving both: the three parties hold the same location model at the same quality at every handoff.
