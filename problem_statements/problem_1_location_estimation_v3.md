# Problem 1 — Location Estimation (Point A: Wiom's Promise Decision) — v3

**Contract type:** Gate 0 thinking contract (per Wiom's Gate 0 Submission Template).
**Owner:** Maanas
**Build team:** Genie
**Drafted:** 2026-04-22
**Primary engine:** Genie — Promise Maker
**Data backbone:** `master_story.md` + `master_story.csv`
**Companion contract:** `problem_2_address_translation_v3.md`

---

## SECTION A — Problem Definition

### 1. Observed / Expected / Evidence

**Observed.** 25.7% of installed bookings drift beyond GPS apparatus noise — attributable to the customer not being at home when the booking coord was captured, not to GPS physics.

**Expected.** Capture drift (drift beyond apparatus p95 of 155m): <5%. Residual drift stays within apparatus physics.

**Evidence.** Delhi Dec-2025 installed non-BDO, n=3,855 (`master_story.md` Part D.A). Apparatus p95 = 155m across 8,317 mobiles × 20,231 pings (Part A). Installed-cohort drift: 25.7% beyond 155m, 3.2% beyond 1km. Cross-engine: 4.4% of partner-customer pairs show `partner_reached_cant_find` at locality/landmark (Part C) — capture drift lands on-ground.

---

## SECTION B — Project Definition

### 2. Objective

Reduce capture drift (drift beyond apparatus p95 of 155m) from **25.7% → <5%** within one release cycle.

### 3. Classification + Rationale

**Capability Build.**

- **Not Hygiene** — nothing broken; today's one-GPS-fix + 25m gate works as designed.
- **Not Efficiency** — no existing verification mechanism to improve.
- **Not Outcome Shift alone** — tuning the 25m threshold would be Outcome Shift, but the gate doesn't test drift.
- **IS Capability Build** — independent-verification of home-presence is a new system ability.

### 4. Root Cause

Wiom commits on an un-interrogated self-report. One lat/long + one customer tap on "yes, I am at home" is the entire evidence basis at commit — there is no independent channel testing whether the self-report is true. Single-witness commit systems cannot filter false reports.

### 5. Leverage Level

**LP4 — rule change + new information flow.**

- **Not LP1** — tightening the 25m threshold doesn't help if the coord itself is 100m off.
- **Not LP5** — Wiom's purpose (match supply to demand) stays the same.
- **IS LP4** — the rule of promise-making changes: "commit requires corroboration of self-report by an independent channel." New information flows consumed: ≥2 customer-confirmed landmarks, night-GPS agreement, per-mobile jitter prior.

---

## SECTION C — Measurement

### 6. Measurement Stack

| Layer | Metric |
|---|---|
| **L5** | Install rate (installs / promises made) at held promise volume |
| **L4** | CSP-reported location mismatch on-ground — `partner_reached_cant_find` (P1-attributable: stuck at locality / landmark) |
| **L3** | **Capture drift rate** — % of installed bookings with drift > apparatus p95 (155m) |
| **L2** | Verification-completion rate at capture |
| **L1** | Verification service up; event emissions clean; no data gaps in `booking_accuracy`, landmark-pick, night-GPS streams |

### 7. Tracking Table

| Metric | Layer / Category | Baseline | Target | Frequency | Source |
|---|---|---:|---:|---|---|
| Capture drift rate (drift > 155m) | L3 primary | 25.7% | <5% | Weekly | `master_story.md` Part D.A, recomputed on post-intervention cohort |
| Verification-completion rate (≥2 landmarks OR corrective loop OR SR-OS resolution) | **Leading** (L2) | 0% | >90% | Daily | New event in booking event log |
| `partner_reached_cant_find` rate (P1-attributable cut) | L4 | 4.4% | <2% | Weekly | Coordination call-analysis pipeline re-run |
| Verify-visit success rate (reached-door / all verify-visits) | **Learning** | — (new) | >60% | Weekly | B9 outcome capture |
| Install rate (installs / promises made) | L5 | 35% | ≥55% (+20pp) | Monthly | Booking event log funnel |

*Caveat on Learning signals: baseline not available today. Verify-visit success rate becomes measurable once B8 + B9 ship (Phase 1). First baseline calibrated in Sprint 1.*

*Measurement discipline for L5: install rate is measured at held promise volume. The gate cannot "improve" L5 by rejecting more bookings — volume is the control, calibration is the test.*

---

## SECTION D — Leading Signal (Critical)

### 8. Leading Signal

- **Primary L3 signal.** Capture drift rate. 25.7% → <5%.
- **Leading indicator (real-time).** Verification-completion rate. 0% → >90%. *Ensures customers make the effort to give the right address.*
- **Learning signal (separate, tracked in C.7).** Verify-visit success rate. *Generates partner-serviceability signals feeding belief-model calibration and expansion-scope decisions; not predictive of P1's L3.*

### 9. Signal Validity

Proof of validity for the **Leading indicator** (verification-completion rate):

| Dimension | One-line proof |
|---|---|
| **Observability** | Verification-completion event fires inline in the booking flow; written to booking event log the moment the ≥2-landmark check passes or the corrective loop completes. **Sub-hour observability.** |
| **Causality** | Verification-completion gates the fee — only corroborated bookings commit; un-corroborated ones re-capture or reject. Installed cohort therefore only contains corroborated commits; drift drops because the bookings that produce drift no longer reach install. |
| **Sensitivity** | The verification rule (number of landmarks required, probe failure threshold, jitter-prior cutoff) is an engineering knob. Tightening directly lowers completion rate; loosening raises it. Monitor-only mode on a hold-out cohort isolates the effect on drift. |

### 10. Signal Timing

| Signal | Timing |
|---|---|
| Leading — Verification-completion rate | Sub-hour per booking; aggregate rate readable within days of deployment |
| L3 primary — Capture drift rate | ~48h per install (current median time-to-install); aggregate readable weekly |
| Learning — Verify-visit success rate | ~24-72h per verify-visit; rate readable weekly once B8 + B9 ship |

### 11. Scope Constraint

**Yes.** Leading indicator (verification-completion rate) observable sub-hour per booking; aggregate readable in days. L3 primary (capture drift rate) readable within a week of first installs landing — comfortably inside the 2-3 sprint Capability Build window.

---

## SECTION E — Ownership & Mapping

### 12. Owner

**Maanas** (one person, not a team). Build team: Genie.

### 13. Driver Mapping

**Install rate (installs / promises made).** Baseline 35%, target ≥55%.

### 14. NUT Chain

**Verified capture at commit → Install rate → Installed paying customer revenue.**

### 15. Validation Path

1. Verification-completion rate rises to >90% (leading)
2. Capture drift rate drops toward <5% (L3)
3. `partner_reached_cant_find` rate drops toward <2% (L4)
4. Install rate rises toward ≥55% (L5)

**Disconfirmation branches:**
- Step 1 moves, step 2 doesn't → verification features wrong.
- Step 2 moves, step 3 doesn't → P2's territory (translation failure on-ground).
- Step 3 moves, step 4 doesn't → bottleneck is downstream of Point B (partner task-routing / technician scheduling).

---

## SECTION F — Execution

### 16. Time Class

**Capability Build → 2-3 sprints.**

- **Sprint 1** — Close Stage B open slices (drift × `time_bucket`, drift × `booking_accuracy`, declined-cohort comparison). Decide verification feature set + thresholds.
- **Sprint 2** — Build independent-verification channel (A3 landmark picker + A11 UAC v0 scorer + A6 corrective loop + A14 SR-OS queue) in shadow mode.
- **Sprint 3** — Switch to commit-gating; monitor; iterate thresholds.

### 17. Execution Plan

| Step | AI does | Human does |
|---|---|---|
| 1 | Generate solution architecture options, stress-test against the RCA, surface trade-offs | Pick the architecture, lock design decisions |
| 2 | Code capabilities (schema, pipelines, UI scaffolds, event instrumentation) | Review code, approve ship |
| 3 | Monitor metrics (L2 coverage, L3 signal, L4 driver) in near real-time; flag drifts | Review insights weekly, course-correct |
| 4 | Enable learning loops — feed install outcomes + verify-visit outcomes + transcripts back into belief models and landmark-confidence stock | Decide on scale / hand-off / redesign per G.20 |

---

## SECTION G — Learning Logic

### 18. Hypothesis

**If** we require the customer's self-report of home-presence to be independently corroborated (≥2 confirmed landmarks, or corrective loop completion, or SR-OS resolution) before committing the fee,
**then** capture drift rate on the installed cohort will drop from **25.7% → <5%**
**within 4 weeks of full rollout**
**because** commits only fire when self-report is verified, not asserted — replacing a one-witness commit with a two-witness commit.

### 19. Risk Check

| Risk | Mitigation |
|---|---|
| Customer drop-off if verification friction is too high | Shadow-mode first → measure completion → only gate when completion ≥85% |
| Gaming — customer confirms landmarks he doesn't live near | 20-25% false-landmark probe rate; probe failure drops confidence |
| Google Address Descriptors API failure | Round-2 fallback to Wiom install-history anchors; fail-open, never fail-closed |
| L3 flat despite high completion | Verification features wrong — re-investigate Stage B slices (time_bucket, `booking_accuracy`) |

### 20. Learning Path

| Leading (verification-completion) | L3 (capture drift) | L5 (install rate) | Decision |
|---|---|---|---|
| ≥90% | drops to <5% | rises to ≥55% | **Scale** — roll out all cities; plan learned-model upgrade |
| ≥90% | drops to <5% | flat | P1 solved — remaining loss at Point B; **hand off to P2 or further downstream** |
| ≥90% | flat | — | **Re-investigate** — verification features wrong; close Stage B slices |
| <90% | — | — | **Redesign** — thresholds too tight or UX too heavy |

---

## FINAL RULE (per template)

- ✅ Clear problem: 25.7% of installed bookings carry capture drift beyond apparatus noise — attributable to not-at-home capture, not GPS physics.
- ✅ Measurable signal: verification-completion rate (real-time) + capture drift rate (weekly).
- ✅ Testable hypothesis: independent corroboration of self-report → drift drops from 25.7% to <5% in 4 weeks.

**This is a project.**

---

## Cross-link: relation to companion contract

This contract solves **input verification at Point A**. The companion contract (`problem_2_address_translation_v3.md`) solves **signal consistency across parties between Point A and Point B**.

The two problems are **parallel workstreams** resting on a **shared upstream element** — structured landmark / gali / floor capture at flow steps 4-6. Captured once, consumed by both:
- This contract uses ≥2 landmark confirmations as the **independent second channel** that verifies home-presence.
- The companion uses the same confirmed landmark / gali / floor as the **structured fields in the partner's notification**.

Both contracts converge at L5: **install rate 35% → ≥55%.**
