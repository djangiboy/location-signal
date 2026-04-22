# Problem 2 — Address Translation for CSP (Point B: Partner's Decision) — v3

**Contract type:** Gate 0 thinking contract (per Wiom's Gate 0 Submission Template).
**Owner:** Maanas
**Build team:** Genie
**Drafted:** 2026-04-22
**Primary engines:** Genie — Coordination (transcript ground truth) + Promise Maker (capture schema) + Allocation (notification payload)
**Data backbone:** `master_story.md` + `master_story.csv`
**Companion contract:** `problem_1_location_estimation_v3.md`

---

## SECTION A — Problem Definition

### 1. Observed / Expected / Evidence

**Observed.** On **40.7%** of classifiable partner-customer pairs (n=2,024 after removing 21% noise/empty transcripts from the raw 2,561-pair cohort), the first partner-customer call is a location-reason call — the partner cannot commit to install without first resolving location on voice. The packet's unstructured text blob forces him to rebuild landmark → gali → floor in conversation instead of reading it from the packet. 1.92 calls per pair once calling starts.

**Expected.** First-level objective: the partner should not *need* to call. Structured address (landmark + gali + floor) arrives in the packet pre-call, partner commits or declines without voice. **First-call-location-reason rate: 40.7% → <20%** (caveat: IVR coverage is incomplete, so this tracks drift rather than an absolute ceiling). **Calls per pair: <1.3** when calls do happen. Gali-stuck, landmark-stuck, and within-call ANC confusion are downstream symptoms that collapse when the need-to-call collapses; they are not separate objectives.

**Evidence.** Delhi Jan-Mar 2026 non-BDO, raw n=2,561 / **classifiable n=2,024 after noise-or-empty exclusion (21% of raw)** / 4,930 calls (`master_story.md` Part C.B, C.C). Translation failure is independent of coord accuracy and ranking quality — transcript-level address friction is flat across distance deciles (range 6.5pp) and GNN probability deciles (range 7.1pp), confirming a structure problem, not a location or routing problem. **Scope exclusion:** Problem 2 does not solve coord accuracy (Problem 1) or partner serviceability (Gate 2).

---

## SECTION B — Project Definition

### 2. Objective

Reduce first-call-location-reason rate from **40.7% → <20%** within one release cycle.

### 3. Classification + Rationale

**Capability Build.**

- **Not Hygiene** — text capture and notification payload work as designed.
- **Not Efficiency** — no "cleaner" version of an unstructured blob.
- **Not Outcome Shift alone** — a nudge changes behaviour but the partner still receives a blob.
- **IS Capability Build** — a structured address model (landmark / gali / floor as separate fields, preserved end-to-end) is a new system stock.

### 4. Root Cause

Wiom has no structured address stock. Customer types free text; Wiom stores it as a single string; partner reads the blob and rebuilds landmark → gali → floor on a voice call. There is no schema-level representation of the address that carries structure through the Wiom → partner → technician handoffs. 46% one-sided ANC confusion (customer clear, partner confused) proves the structure exists at source — it's the capture that drops it.

### 5. Leverage Level

**LP4 — rule change + new information flow.**

- **Not LP1** — better-worded notification copy doesn't help if the payload is an unstructured blob.
- **Not LP5** — Wiom's purpose stays the same.
- **IS LP4** — new information flows between parties (structured landmark / gali / floor replacing free text, preserved through every handoff), and the rules of partner-customer coordination change (voice call becomes confirmation, not discovery).

---

## SECTION C — Measurement

### 6. Measurement Stack

| Layer | Metric |
|---|---|
| **L5** | Install rate (installs / promises made) at held promise volume |
| **L4** | Calls per partner-customer pair |
| **L3** | **First-call-location-reason rate** on classifiable pairs |
| **L2** | Structured-address coverage (landmark + gali + floor populated pre-notification) |
| **L1** | Structured-capture widget up; notification payload carries structured fields; partner UI renders them; event schema clean |

### 7. Tracking Table

| Metric | Layer / Category | Baseline | Target | Frequency | Source |
|---|---|---:|---:|---|---|
| First-call-location-reason rate (classifiable pairs) | L3 primary | 40.7% | <20% | Weekly | Coordination call-analysis pipeline (classifiable-pairs denominator) |
| Structured-address coverage | **Leading** (L2) | 0% | >90% | Daily | New event in booking event log |
| Calls per partner-customer pair (when calls happen) | L4 | 1.92 | <1.3 | Weekly | Call aggregation by pair |
| Verify-visit success rate (reached-door / all verify-visits) | **Learning** | — (new) | >60% | Weekly | B9 outcome capture |
| Technician landmark-arrival correctness (field GPS within 50m of confirmed primary landmark) | **Learning** | — (new) | TBD Sprint 1 | Weekly | D7 field-GPS pipeline |
| Install rate (installs / promises made) | L5 | 35% | ≥55% (+20pp) | Monthly | Booking event log funnel |

*Caveat on Learning signals: baselines not available today. Verify-visit success rate measurable once B8 + B9 ship (Phase 1). Technician landmark-arrival correctness requires A3 + B4 both live — Phase 2+ signal. First full baselines and target calibration are Sprint-1 deliverables for verify-visit success and Phase-2-entry deliverables for landmark-arrival correctness.*

*Measurement discipline for L5: install rate is measured at held promise volume. The gate cannot "improve" L5 by rejecting more bookings — volume is the control, calibration is the test.*

---

## SECTION D — Leading Signal (Critical)

### 8. Leading Signal

- **Primary L3 signal.** First-call-location-reason rate on classifiable pairs. 40.7% → <20%.
- **Leading indicator (real-time).** Structured-address coverage. 0% → >90%. *Ensures capture fires and the packet carries structure end-to-end.*
- **Learning signals (separate, tracked in C.7).**
  - Verify-visit success rate — feeds partner-serviceability zoning and landmark-confidence (Loops 1/2).
  - Technician landmark-arrival correctness — feeds landmark-confidence per hex (Loop 1).

### 9. Signal Validity

Proof of validity for the **Leading indicator** (structured-address coverage):

| Dimension | One-line proof |
|---|---|
| **Observability** | Structured-address event fires when all three fields (landmark + gali + floor) populate in the capture flow; written to booking event log. **Observable in minutes.** |
| **Causality** | A structured packet removes the need for the partner to rebuild landmark → gali → floor on voice; first-call-location-reason rate drops because the partner can commit or decline on packet content alone. 46% one-sided ANC confusion (customer clear, partner confused) proves structure exists at source — this signal tests whether it crosses the membrane end-to-end. |
| **Sensitivity** | The capture schema (required vs optional fields, free-text overflow rules, round-2 install-history fallback) directly determines coverage. Form changes translate to measured coverage movements within a day. |

### 10. Signal Timing

| Signal | Timing |
|---|---|
| Leading — Structured-address coverage | Minutes per booking; aggregate rate readable within a day of deployment |
| L3 primary — First-call-location-reason rate | ~24-48h per booking (call + transcribe + classify); aggregate readable weekly |
| Learning — Verify-visit success rate | ~24-72h per verify-visit; rate readable weekly once B8 + B9 ship |
| Learning — Technician landmark-arrival correctness | Per-install basis; aggregate readable weekly once A3 + B4 both live (Phase 2+) |

### 11. Scope Constraint

**Yes.** Leading indicator (structured-address coverage) observable within a day. L3 primary (first-call-location-reason rate) readable weekly inside the 2-3 sprint window. Learning signals lag (verify-visit Phase 1; landmark-arrival Phase 2+) but do not gate Gate-0 qualification — the leading indicator passes the scope test.

---

## SECTION E — Ownership & Mapping

### 12. Owner

**Maanas** (one person, not a team). Build team: Genie.

### 13. Driver Mapping

**Install rate (installs / promises made).** Baseline 35%, target ≥55%.

### 14. NUT Chain

**Structured address preserved end-to-end → Install rate → Installed paying customer revenue.**

### 15. Validation Path

1. Structured-address coverage rises to >90% (leading)
2. First-call-location-reason rate drops toward <20% (L3)
3. Calls per pair drops toward <1.3 (L4)
4. Install rate rises toward ≥55% (L5)

**Disconfirmation branches:**
- Step 1 moves, step 2 doesn't → partners not using the structured address (UI / trust issue).
- Step 2 moves, step 3 doesn't → capture taxonomy wrong (fields captured aren't the ones partners need).
- Step 3 moves, step 4 doesn't → shared with P1 — bottleneck is further downstream.

---

## SECTION F — Execution

### 16. Time Class

**Capability Build → 2-3 sprints.**

- **Sprint 1** — Pull landmark / gali / floor taxonomy from Coordination transcripts; design structured address schema.
- **Sprint 2** — Ship structured capture (A3, A4, A5); update notification payload (C1) to carry structured address with per-field confidence; wire landmark-grounded serviceability (B5).
- **Sprint 3** — Roll out partner-side UI; monitor; iterate schema.

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

**If** we replace the free-text address field with structured capture (landmark + gali + floor) and propagate the structure end-to-end to the partner's notification,
**then** first-call-location-reason rate on classifiable pairs will drop from **40.7% → <20%**
**within 6 weeks of full rollout**
**because** the partner sees the chain he navigates by (landmark → gali → floor) in the packet rather than rebuilding it on voice — the need-to-call collapses at source.

### 19. Risk Check

| Risk | Mitigation |
|---|---|
| Customer drop-off if structured capture flow too long | A/B test schema (3-field minimal vs 5-field full); measure completion before payment |
| Taxonomy too rigid — not every Delhi address fits landmark → gali → floor | Free-text overflow preserved; structured fields nudged, not forced |
| Partner adoption — partners still call out of habit | Sprint 3 partner UI shows "confirmed structurally" + confidence flag; reward loop via C7 verify-visit visibility |
| L3 flat despite high coverage | Partners not using structured fields — UI or trust problem, not capture problem |
| L3 moves but L5 flat | Bottleneck is downstream — hand off to Partner Management (task-routing / tech scheduling) |

### 20. Learning Path

| Leading (structured coverage) | L3 (first-call-reason) | L5 (install rate) | Decision |
|---|---|---|---|
| ≥90% | drops to <20% | rises to ≥55% | **Scale** — roll out all cities |
| ≥90% | drops to <20% | flat | P2 solved — bottleneck elsewhere; **hand off to Partner Management** |
| ≥90% | flat | — | Partners not using structured address — **fix UI / trust**, not capture |
| <90% | — | — | **Redesign capture** — schema too heavy or flow too long |

---

## FINAL RULE (per template)

- ✅ Clear problem: 40.7% of classifiable partner-customer pairs carry a location-reason first call because the packet is an unstructured blob.
- ✅ Measurable signal: structured-address coverage (real-time) + first-call-location-reason rate (weekly).
- ✅ Testable hypothesis: structured address preserved end-to-end → first-call-reason rate drops from 40.7% to <20% in 6 weeks.

**This is a project.**

---

## Cross-link: relation to companion contract

This contract solves **signal consistency across parties between Point A and Point B**. The companion contract (`problem_1_location_estimation_v3.md`) solves **input verification at Point A**.

The two problems are **parallel workstreams** resting on a **shared upstream element** — structured landmark / gali / floor capture at flow steps 4-6. Captured once, consumed by both:
- Companion contract uses ≥2 landmark confirmations as the **independent second channel** that verifies home-presence.
- This contract uses the same confirmed landmark / gali / floor as the **structured fields in the partner's notification**.

Both contracts converge at L5: **install rate 35% → ≥55%.**
