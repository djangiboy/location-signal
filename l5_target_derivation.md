# L5 Target Derivation — Booking → Install Rate

**Drafted:** 2026-04-22
**Referenced by:** `problem_statements/problem_1_location_estimation_v3.md`, `problem_statements/problem_2_address_translation_v3.md`, `implementation_plan_and_impact.md`
**Data backbone:** `master_story.md` + `master_story.csv`

---

## §1 — What this document is

Both v3 Gate 0 contracts (P1 and P2) converge at a shared L5 target: **booking → install rate, 40% → ≥49% (+9pp)**. This document explains how that number was derived, what it includes, and what it deliberately excludes.

**Key scope clause:** the 49% target is the **joint P1 + P2 contribution**. It does **not** incorporate lifts from:
- BM1 (Promise Maker belief model) activation — separate contract, Phase 2 per `solution_frame_v6.md`
- BM2 (GNN ranking model) activation — separate contract, Phase 3
- Partner expansion — cross-team workstream, indefinite timeline

Those contributions land on top of 49% and are tracked independently.

---

## §2 — Baseline

| Metric | Rate | Source |
|---|---:|---|
| Booking → Assignment (partner accepts allocation) | **85%** | Wiom ops |
| Assignment → Install | **~47%** | Derived = 40 / 85 |
| **Booking → Install** | **40%** | Wiom ops — the L5 target |

The 40% is the "held promise volume" denominator-preserving figure — measured at current booking inflow without tightening the gate artificially.

---

## §3 — The funnel decomposition

Two distinct leakage points:

1. **Booking → Assignment (15% leak):** partner notified, partner declines, booking never gets assigned. Pre-accept behaviour.
2. **Assignment → Install (53% leak on 85 assigned):** partner accepts, but booking never installs. Post-accept behaviour.

P1 and P2 bite at these points differently:

| Workstream | Pre-accept leak | Post-accept leak |
|---|---|---|
| **P1** (clean capture) | ✅ bites — distance-driven decline drops when coord is real | ✅ bites — PRCF drops, gali-stuck-outside-polygon drops |
| **P2** (structured packet) | ❌ doesn't bite — structure is inside the packet, which partner sees post-accept | ✅ bites — partner can commit on content without rebuilding chain on voice |

---

## §4 — Per-workstream lift estimation

All lifts derived from `master_story.md` Parts B, C, D — relative effects anchored in the Delhi cohort, applied to the 40% baseline.

### §4.1 — P1 alone

**Assignment-rate lift: 85% → ~88% (+3pp).**

Reasoning:
- Master story Part B: per-partner-notification decline rates rise monotonically with distance. D1 total decline (area + addr-not-clear dropdown) ≈ 16%; D10 ≈ 55%.
- If 25.7% of today's bookings are drift-disproportionately in D7-D10 (avg per-notification decline ~40%) and 74.3% in D1-D6 (~20%), cohort-average per-notification decline ≈ **25%**.
- Removing drift at Gate 1 shifts all bookings to D1-D5 range. Per-notification decline drops to ~18%. Improvement: **7pp per-notification**.
- Translation to booking-level assignment rate depends on N = number of partners notified per booking (data we don't have — see §8). Assuming N ≈ 2-3, the 7pp per-partner drop translates to roughly **2-3pp booking-level assignment lift**. Midpoint: **+3pp → 88%**.

**Install-on-assignment lift: 47% → ~53% (+6pp).**

Reasoning:
- Master story Part C.D: inside-polygon install rate 55.3% vs outside 38.6%. Clean coord → more bookings land inside polygon → higher post-accept install.
- PRCF (`partner_reached_cant_find`): 4.5% of pairs install at 71.1%. If P1 cuts PRCF rate from 4.5% → 2% (saves 2.5pp of cohort at +24pp vs cohort average), direct lift ≈ **+0.6pp**.
- Distance-decile shift: if bookings concentrate in D1-D5 (install rate 50.46% → 37.07% from D1 to D5; avg ~44%) vs today's D1-D10 mix (avg ~32%), install-on-assignment lifts by ~**5pp** from this effect alone.
- Combined: **+6pp on install-on-assignment**.

**Booking → Install under P1 only:**
0.88 × 0.53 = **46.6%** → **+6.6pp from 40% baseline** (~47%).

### §4.2 — P2 alone

**Assignment-rate lift: 0 (stays at 85%).**

P2 doesn't touch pre-accept mechanics. Allocation's map + distance are what the partner sees at notification time; structured-address fields populate inside the packet post-accept. So pre-accept decline behaviour is unchanged.

**Install-on-assignment lift: 47% → ~52% (+5pp).**

Reasoning — three mechanisms:
1. **ANC → clear conversion.** Within-ANC calls: clear 62.2% install vs weighted-average 54.6% install. If P2 converts most ANC pairs to clear: **+1.1pp** on cohort (after 36.2% ANC-incidence weighting).
2. **Chain-engagement default.** Master story C.E: chain engagement inside polygon lifts install rate by **+11.2pp**. Today ~36.5% of inside-polygon pairs engage the chain. If P2 raises this to ~80%:
   - Inside-polygon share of cohort: 75.7%
   - Incremental chain-engaged: 43.5% of inside pairs
   - Lift: 0.757 × 0.435 × 0.112 = **+3.7pp** on cohort.
3. **Gali-stuck reduction.** Gali-stuck outside polygon: 25.4% install (danger cell); structured packet reduces gali-stuck incidence. Small effect, **+0.3pp** on cohort.

Combined: **+5pp on install-on-assignment**.

**Booking → Install under P2 only:**
0.85 × 0.52 = **44.2%** → **+4.2pp from 40% baseline** (~44%).

### §4.3 — Joint P1 + P2 (overlap-adjusted)

P1 and P2 lifts are not additive. They overlap because:
- **Drifted bookings often also surface as ANC pairs.** Partners call because the coord is wrong AND the packet is a blob. Fixing either alone recovers some of these bookings; fixing both doesn't get double credit.
- **Structured capture feeds both gates.** The same ≥2-landmark substrate serves P1's verification channel and P2's packet structure — one build, two outputs.

**Joint rates:**
- Assignment rate: **85% → 88%** (P1-driven; P2 doesn't move this)
- Install-on-assignment: **47% → 56%** — sum of per-workstream lifts (+6 P1 + +5 P2 = +11) minus ~2pp overlap absorption = **+9pp**

**Booking → Install joint:**
0.88 × 0.56 = **49.3%** → **+9.3pp from 40% baseline**.

Rounded: **≥49% (+9pp)** is the target.

---

## §5 — What's NOT in the 49% target

Everything below is downstream of a different contract/workstream and stacks on top of 49%:

| Addition | Estimated Lift | Where |
|---|---:|---|
| BM1 activation (polygon + KDE tier enrichment) | +2-3pp | Phase 2; separate contract |
| BM2 / GNN activation (ranking) | +3-5pp | Phase 3; separate contract |
| Partner expansion | +? | Cross-team; indefinite |

**Fully-stacked projected booking-install rate: ~55-58%.** That's the aspirational number `solution_frame_v6.md` §14 references — but it's not the P1+P2 accountability.

---

## §6 — Attribution discipline

**Shared L5 target = 49% for both contracts jointly.** Implications:

- If L5 rises to ≥49% and both L3s moved (P1's drift rate + P2's first-call rate), **both contracts pass**.
- If L5 rises above 49% without model activation, both contracts pass and we document the compounding (the +1-2pp tailwind above math).
- If L5 rises to 49% with only one L3 moving, **attribution falls to the contract whose L3 moved**; the other contract is effectively absent from the lift.
- If L5 rises above 49% *because* of model activation (measured via shadow-mode holdout), the contribution is booked against the model contract, not P1/P2.

This is why the contracts' G.20 Learning Path tables pivot on L3 movement, not just L5 movement. L5 alone cannot attribute.

---

## §7 — Gameability control (held promise volume)

The 49% target is measured **at held promise volume** — the booking inflow that feeds the system cannot shrink to artificially lift the rate.

**Two requirements for the held-volume discipline:**

1. **Absolute volume held** — total promises made per unit time ≥ pre-intervention volume.
2. **Pre-intervention install-rate distribution held across declared cohort slices** — geography, BDO/non-BDO, booking channel. A gate that rejects differently (holding total volume constant but shifting rejection toward bookings that would have dropped out anyway) can game absolute-volume discipline. Slice-level holds prevent this.

Both requirements ship as Sprint-1 dashboards.

---

## §8 — Open data point (carried forward)

**N = average number of partners notified per booking.**

This parameter directly governs the translation from per-partner-notification decline rate (measured in master story Part B) to booking-level assignment rate. My current estimate assumes N ≈ 2-3, giving a 2-3pp booking-level assignment lift per 7pp per-partner decline reduction.

If N is closer to 1, P1's assignment-rate lift is materially higher (more like +7pp instead of +3pp), and the joint target would be revised upward.
If N is closer to 4-5, P1's assignment-rate lift is smaller (~+1pp), and the joint target would revise downward slightly.

**Sprint-1 deliverable: pull N from allocation event log and refine this derivation.**

---

## §9 — Summary table

| Workstream | Assignment | Install-on-Assignment | Booking → Install | Lift |
|---|---:|---:|---:|---:|
| **Baseline (today)** | 85% | 47% | **40%** | — |
| P1 alone | 88% | 53% | 46.6% | +6.6pp |
| P2 alone | 85% | 52% | 44.2% | +4.2pp |
| **P1 + P2 joint** (overlap-adjusted) | **88%** | **56%** | **≈49%** | **+9pp** ← **the target** |
| + BM1 | 88% | ~58-59% | ~51-52% | +11-12pp |
| + BM1 + BM2 | ~89% | ~61-63% | ~54-56% | +14-16pp |
| + Partner expansion | ? | ? | 55-60%+ | +15-20pp |

---

## §10 — What this document is not

- Not a sprint plan (see `implementation_plan_and_impact.md`)
- Not a solution design (see `solution_frame_v6.md`)
- Not a problem statement (see `problem_statements/*_v3.md`)

This is a **derivation memo** — a defensible audit trail of how the shared L5 target arrived at 49%. If Satyam asks "where does the 49% come from?" this file answers end-to-end.
