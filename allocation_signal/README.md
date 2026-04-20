# Allocation Signal — Distance-Decile Analysis

**Engine:** Allocation (post-promise, pre-acceptance)
**Parent:** `../` (`location_signal_audit/`) — one of three engine-scoped audits of location signal fidelity across Wiom's matchmaking funnel.
**Cohort:** Delhi, Dec 2025 bookings · **Non-BDO filter applied throughout**
**Last run:** 2026-04-19 · **Status:** Analysis complete. Primary answers below.

## Where this sits in the funnel

Location signals travel through three engines. Each can corrupt or preserve the signal independently. This folder is stage 2:

| Stage | Sibling folder | Question |
|---|---|---|
| 1 — pre-promise | `../promise_maker_gps/` | Is the booking GPS reliable at capture? |
| **2 — post-promise, pre-acceptance** | **this folder** | **Does the partner↔booking distance predict installs?** |
| 3 — post-acceptance | `../coordination/` | Once the partner has accepted, where does address resolution break on the ground? |

The three folders share a CTE skeleton (delhi_mobiles / bdo_mobiles / booking_location / allocation flatten) but differ by which slice of the signal they interrogate.

## Session resume — where we left off

If you're returning to this directory fresh, read in this order:
1. **This Status + Operational Context section** (just below) — anchors everything
2. **Separation matrix + Core findings** — the headline data
3. **Recommendations — merged Monday actions** — what to actually do
4. **Timeline** (bottom) — how we got here, chronologically

The analysis question is **answered**. Outstanding items are in the "Open / future work" section. All intermediate artifacts are in `investigative/`. `STORY.csv` is the single-file narrative; `README.md` is this file.

**Upstream sibling (in progress)**: `../promise_maker_gps/` — validates the booking GPS signal that *feeds* the 25m serviceability gate. Tests whether the GPS jitter is low enough for Promise Maker to rely on it. Separate cohort (Dec 2025 + sibling period), separate question (signal provenance, not signal utility). If the GPS input is untrustworthy, every downstream ranking in this folder sits on corrupted geometry.

**Downstream sibling (complete)**: `../coordination/` — extends the dropdown-level decile findings here with transcript-level ground truth from 4,930 partner↔customer calls. Confirmed empirically that the 48%→2.5% `address_not_clear` prob-decile pattern found here is a decline-channel artifact, not a real per-call address-friction gradient.

## Operational context — where these models actually run

Allocation runs **before any partner takes action on a booking.** The inference sequence:

1. A booking enters Allocation (post-Promise-Maker — customer location already confirmed serviceable).
2. Allocation computes a **ranking** over candidate partners using GNN `probability` (or any alternative signal we might compare it against, e.g. raw `nearest_distance`).
3. The top-ranked partner is notified first.
4. That partner decides (accept / decline / no-action).
5. If no accept, the next partner is notified (or the booking is re-ranked, per system policy).

**Implication for distance-vs-GNN comparison**: the production-relevant comparison is **unconditional** — which signal better identifies partners likely to install, *before* any decision on this booking has been made. That's the point at which Allocation must decide who to notify.

**The "conditional-accept" slice we computed** (filter to `decision_event IN ('INTERESTED','ASSIGNED')`, recompute separation) is a **diagnostic tool only** — it helps us decompose *where* probability's edge over distance comes from (decline-likelihood variance vs install-physics variance). It does **NOT** reflect what Allocation does at inference time. Read below with that distinction in mind.

## Scope note — what stage of the funnel this analyzes

Wiom's matchmaking funnel has two distinct engines:

1. **Promise Maker** — evaluates a **lead** (raw demand). If historical install decision / splitter within 25m exists, it makes a promise. Lead becomes a **booking**.
2. **Allocation** — takes a **booking** and decides which partner to rank first for notification (GNN ranks partners, emits `probability` per partner-booking pair).

**This analysis is entirely post-Promise-Maker.** Every row in our cohort already passed the 25m serviceability gate (`t_serviceability_logs.response.serviceable = TRUE` in the `booking_location` CTE). We are evaluating **Allocation** — *not* Promise Maker.

Promise-Maker-level questions (gate calibration, GPS input reliability) live in the sibling `../promise_maker_gps/`.

## What we are doing

Testing whether `nearest_distance` (partner's nearest installed connection OR
splitter point to the booking lat/lng) predicts:

1. **Installability** — does the booking install?
2. **Decline behavior** — when the partner rejects the notification, what
   does the decline reason look like?
3. **Partner tenure confound** — does the signal survive once we split by
   `nearest_type` (active_base vs splitter) and by GNN `probability`?

Everything sliced by **distance decile** and, separately, by **probability
decile** (1 = lowest, 10 = highest). Separation (D1 rate − D10 rate) is
the headline metric.

## Why

The Allocation engine (GNN) keys on `nearest_distance` to rank partners. If
distance is a weak or non-monotonic predictor, or is confounded with partner
tenure (splitter partners look "far" from every booking), the ranking sits on
a shaky signal. GNN `probability` is our model's compressed view of
partner-booking fit — we want to know how much of distance's signal it
already captures, and how much is residual.

## Data

| Source | Connection | What it gives |
|--------|-----------|---------------|
| `booking_logs` | Snowflake | Dec 2025 Delhi mobiles; `bdo_lead` flag |
| `t_allocation_logs` | Snowflake, `mysql_rds_genie_genie2` | Notification → partner_id, nearest_distance, nearest_lat/lng, **nearest_type** (`active_base`/`splitter`), **probability** (GNN score) |
| `task_logs` | Snowflake | Decision events: INTERESTED, ASSIGNED, DECLINED, OTP_VERIFIED |
| `t_serviceability_logs` | Snowflake, `mysql_rds_genie_genie1` | Booking lat/lng |

Connector: `db_connectors.py` → `get_snow_connection()`.

## Two analysis pipelines

The directory holds two scripts that share the same cohort philosophy but
produce different cuts:

| Pipeline | Script | Cohort |
|----------|--------|--------|
| **V1: separate install / decline slices** | `decile_install_rate.py` | Two cohorts — INTERESTED/ASSIGNED and DECLINED — run independently, each sliced by distance decile. Non-BDO filter applied inside `main()`. |
| **V2: unified cohort + GNN + nearest_type** | `unified_decile_analysis.py` | One cohort — (mobile, partner_id) pairs with rn=1 on first decision (INTERESTED / ASSIGNED / DECLINED-non-72h). Non-BDO filter. Adds probability-decile slice and nearest_type groupby. |

V1 answered "does distance matter?" V2 answers "is the distance signal
confounded with GNN fit and partner tenure?"

## Queries

| File | Purpose |
|------|---------|
| `query_install_correl.txt` | V1 install cohort: `event_name IN ('INTERESTED','ASSIGNED')` |
| `query_decline_correl.txt` | V1 decline cohort: `event_name = 'DECLINED'`, excl. `System_Force_Declined_Post_Assigned_72hours` |
| `query_unified_correl.txt` | V2 unified cohort. Adds `nearest_type` + `probability` extraction from allocation JSON |

All three: same CTE skeleton (delhi_mobiles → allocation → decisions →
booking_location → booking_type → installed_decision → cohort). Install
join is **same-partner match** (`mobile × partner_id`), not booking-level.

## V1 — Separate slices by distance decile (non-BDO)

### Slice 1. Install rate (n = 7,726)

| decile | total | installed | d_median | install_rate |
|-------:|------:|----------:|---------:|-------------:|
| 1  |  774 | 486 |  1.58 | 62.79% |
| 2  |  772 | 479 |  5.46 | 62.05% |
| 3  |  772 | 444 |  8.43 | 57.51% |
| 4  |  775 | 461 | 11.72 | 59.48% |
| 5  |  771 | 412 | 14.94 | 53.44% |
| 6  |  773 | 416 | 18.62 | 53.82% |
| 7  |  771 | 353 | 23.07 | 45.78% |
| 8  |  773 | 360 | 30.33 | 46.57% |
| 9  |  772 | 281 | 44.63 | 36.40% |
| 10 |  773 | 174 | 74.16 | 22.51% |

**Separation: 40.28%.** Monotonic-ish, softer than the pre-BDO-filter run (was 49.90%).

### Slice 2. Area decline rate (n = 6,299)

| decile | total | flagged | d_median | area_decline_rate |
|-------:|------:|--------:|---------:|------------------:|
| 1  | 631 | 185 |  3.30 | 29.32% |
| 2  | 630 | 190 |  9.13 | 30.16% |
| 3  | 630 | 188 | 14.33 | 29.84% |
| 4  | 630 | 182 | 19.00 | 28.89% |
| 5  | 629 | 188 | 24.20 | 29.89% |
| 6  | 629 | 194 | 31.97 | 30.84% |
| 7  | 630 | 224 | 43.44 | 35.56% |
| 8  | 630 | 214 | 57.51 | 33.97% |
| 9  | 630 | 262 | 75.28 | 41.59% |
| 10 | 630 | 243 | 94.82 | 38.57% |

**Separation: 12.70%.** Flat through D6, lifts at D7+.

### Slice 3. Address-not-clear rate (n = 6,299)

| decile | total | flagged | d_median | address_not_clear_rate |
|-------:|------:|--------:|---------:|-----------------------:|
| 1  | 631 | 179 |  3.30 | 28.37% |
| 2  | 630 | 192 |  9.13 | 30.48% |
| 3  | 630 | 195 | 14.33 | 30.95% |
| 4  | 630 | 209 | 19.00 | 33.17% |
| 5  | 629 | 221 | 24.20 | 35.14% |
| 6  | 629 | 210 | 31.97 | 33.39% |
| 7  | 630 | 216 | 43.44 | 34.29% |
| 8  | 630 | 231 | 57.51 | 36.67% |
| 9  | 630 | 218 | 75.28 | 34.60% |
| 10 | 630 | 231 | 94.82 | 36.67% |

**Separation: 8.30%.** Very flat when denominator is declines-only.

### Slice 4. Post-decline install rate (n = 6,299)

Same (mobile, partner_id) later produced `OTP_VERIFIED` after decline.
Observation window: declines through 2025-12-31, installs to 2026-01-31.

| decile | total | flagged | d_median | post_decline_install_rate |
|-------:|------:|--------:|---------:|--------------------------:|
| 1  | 631 | 5 |  3.30 | 0.79% |
| 2  | 630 | 0 |  9.13 | 0.00% |
| 3–10 | — | 0–3 | — | ≤0.48% |

**Overall: ~0.18%.** Post-decline recovery is effectively zero for non-BDO.
Window-limited per Donna's caveat.

## V2 — Unified cohort with GNN probability + nearest_type (non-BDO)

**Cohort:** 27,303 raw → 11,870 after non-BDO. Decision mix: 64.7% INTERESTED,
35.3% DECLINED, 1 ASSIGNED. Denominator for all rates = **total_obs** (causal read per Geoff's Leak B).

### Distance decile

| decile | total | %install | %area | %addr | d_min | d_max | d_median |
|-------:|------:|---------:|------:|------:|------:|------:|---------:|
| 1  | 1,189 | 50.46% |  6.39% |  9.76% |  0.00 |   4.39 |   2.09 |
| 2  | 1,188 | 46.72% |  7.49% |  9.09% |  4.40 |   8.26 |   6.52 |
| 3  | 1,188 | 45.20% |  8.67% | 10.69% |  8.27 |  12.07 |  10.24 |
| 4  | 1,184 | 42.74% |  7.77% | 12.33% | 12.09 |  15.92 |  14.01 |
| 5  | 1,187 | 37.07% |  8.85% | 13.98% | 15.93 |  20.24 |  17.97 |
| 6  | 1,188 | 30.72% | 10.19% | 16.75% | 20.25 |  25.20 |  22.64 |
| 7  | 1,185 | 28.95% | 13.25% | 17.30% | 25.21 |  34.86 |  29.47 |
| 8  | 1,187 | 22.66% | 15.00% | 20.05% | 34.87 |  49.36 |  41.47 |
| 9  | 1,187 | 12.81% | 16.60% | 25.70% | 49.37 |  73.13 |  60.20 |
| 10 | 1,187 |  6.66% | 26.03% | 28.48% | 73.14 | 448.22 |  88.06 |

**Separations: install 43.81% · area 19.64% · address 19.38%.**

### Probability decile

| decile | total | %install | %area | %addr | p_median | d_median |
|-------:|------:|---------:|------:|------:|---------:|---------:|
| 1  | 1,101 |  3.72% | 25.79% | 47.68% | 0.0072 |  42.81 |
| 2  | 1,101 |  6.09% | 22.98% | 33.79% | 0.0384 |  37.87 |
| 3  | 1,101 | 13.53% | 21.25% | 26.07% | 0.1131 |  30.44 |
| 4  | 1,100 | 23.82% | 14.73% | 17.45% | 0.2348 |  24.23 |
| 5  | 1,101 | 29.79% | 10.72% | 10.54% | 0.3989 |  22.05 |
| 6  | 1,101 | 37.42% |  6.99% |  8.27% | 0.5743 |  19.58 |
| 7  | 1,100 | 43.00% |  6.64% |  6.09% | 0.7393 |  17.46 |
| 8  | 1,101 | 53.13% |  4.18% |  4.18% | 0.8616 |  14.93 |
| 9  | 1,101 | 57.31% |  2.45% |  3.27% | 0.9292 |  12.20 |
| 10 | 1,101 | 60.49% |  2.36% |  2.54% | 0.9723 |   9.12 |

**Separations: install 56.77% · area 23.43% · address 45.14%.**

Probability dominates distance on every metric. Address-not-clear
separation on prob (45.14%) is **more than 2x** the distance version —
when the GNN thinks a match is poor, partners dismiss via "address unclear"
almost half the time.

### Nearest type groupby

| nearest_type | total | %install | %area | %addr | d_median |
|:-------------|------:|---------:|------:|------:|---------:|
| active_base  | 8,289 | 36.94% | 10.19% | 13.96% | 17.91 |
| splitter     | 3,581 | 21.89% | 16.25% | 22.09% | 24.92 |

Splitter = partners with no prior install; system uses a fixed splitter
point as proxy. 30% of non-BDO allocations are splitter. Raw install gap
is 15pp, but d_median is 7 km higher — partially distance-driven.

### Prob decile × nearest_type — does GNN already encode type?

**Composition** (% splitter per prob decile): monotonic decline
**38% → 12%** (D1 → D10). The GNN does route splitters to lower prob deciles. (Check a: passes.)

**Side-by-side install rate gap:**

| prob_decile | active_base | splitter | gap (pp) |
|:-----------:|------------:|---------:|---------:|
| 1  |  4.86% |  1.90% |   2.96 |
| 2  |  7.58% |  3.61% |   3.97 |
| 3  | 19.28% |  4.63% | **14.65** |
| 4  | 29.76% | 13.04% | **16.72** |
| 5  | 33.42% | 22.28% |  11.14 |
| 6  | 41.28% | 29.14% |  12.14 |
| 7  | 45.78% | 36.16% |   9.62 |
| 8  | 54.77% | 47.91% |   6.86 |
| 9  | 58.68% | 52.76% |   5.92 |
| 10 | 60.91% | 57.46% |   3.45 |

(Check b: partial pass.) At every prob decile, splitters install less. Gap
collapses at extremes, is 10–17pp at mid-prob (D3–D6). GNN absorbs the
splitter signal *partially* but leaves a residual cold-start penalty where
splitters aren't yet in the model's confident regions.

## Key findings

1. **Distance predicts installability** — non-BDO install rate 50% → 7% across distance deciles. Separation 44%.
2. **Probability appears to dominate distance unconditionally (57% vs 44% separation)**. But this is compositional — see finding 3.
3. **Conditional-accept collapses probability's edge to match distance (40% vs 40%).** Slicing on `decision_event IN ('INTERESTED','ASSIGNED')` strips out partner declines. The GNN probability was largely encoding decline-likelihood, not install-physics. Once you remove declines, prob and distance carry the same signal.
4. **Distance at D10 is a physical ceiling**, not a willingness gate. Conditional install at D10 is 22.79% — even accepted bookings fail 3 of 4 times. This is Wiom's fiber-reach Shannon limit.
5. **Address-not-clear is a dismissal channel, not a parsing failure.** 48% at low-prob, 2.5% at high-prob. When GNN rates the match poorly, partners use address-unclear as the exit door.
6. **The splitter vs active_base install gap (10–17pp at mid-prob) is NOT tenure-driven.** 730d+ partners still show 18pp gap. Cold-start hypothesis rejected.
7. **The gap IS partner-splitter-share-driven.** At prob_decile 4, partners with splitter_share <10% install at 35.77%; partners with splitter_share >90% install at 5.00%. **31pp gap at the same GNN probability.** High-splitter-share partners are roaming-app gamers — submit many self-claimed splitter lat/lngs to attract bookings, then fail to install.
8. **Post-decline recovery is ~0%.** Once declined, the (partner, booking) pair is effectively dead inside the 31-day window.
9. **Decile 10 has a 448 km tail** (879 km in the full cohort) — almost certainly data hygiene.
10. **Non-BDO has a shallower distance gradient than the raw (BDO-included) cohort.** Non-BDO install separation 44% vs pre-filter 50%. BDO bookings were driving ~6pp of the raw distance signal. Worth knowing when BDO is re-included or when comparing to other markets with different BDO mix.

## How to look at the data now — revised read

Geoff and Donna independently converged on a re-factoring.

**Geoff (first-principles):** `P(install) = P(accept) × P(install | accept)`. Distance predicts the *second* term (physics). Probability predicts the product but mostly loads on the *first* (willingness). Conditional-accept kills term 1 → prob and distance collapse to the same geometric signal. The D10 conditional ceiling of 22.79% is a physical cable-reach limit; no ranking punches through it.

**Donna (systems):** Splitter submission is a reinforcing "success to the successful" loop. More splitters submitted → wider notification footprint → more allocations → occasional installs → partner perceives gaming as rational → more splitters. No balancing loop exists because splitter points never expire or get validated against installs. The stock being gamed is *perceived serviceability*.

**Convergent inferences:**

1. **Allocation objective should factorize**: (a) `accept model = P(accept | notification)`, (b) `conditional-install model = P(install | accept)`. Rank on the product but inspect each leg.
2. **The current GNN `probability` is a decline-likelihood predictor wearing fit-predictor clothes.** Distance is an orthogonal geometric signal governing the physics leg.
3. **Adding `splitter_share` as a GNN feature is a band-aid.** Gamers will mutate the pattern. Durable fix: validate splitter points against install outcomes — turn the unbounded stock into one with a decay flow.
4. **The training label itself is contaminated** — gamers generate splitter points AND fail to install. Every retrain re-inherits the pathology. Real fix is upstream, before `nearest_distance` computation.
5. **Does Allocation need a *refusal primitive*?** Today every booking routes; losses absorb as declines. A way to kick a booking back saying "no partner I rank can clear the physics bar" may be the architectural fix for the D10 tail.

## Core analytical answer — distance vs GNN probability for Allocation ranking

Both signals meaningfully separate install / area-decline / address-not-clear outcomes. Neither is random on any category. **But GNN probability wins on the operationally decisive metrics** — install-rate separation AND decline-concentration.

### Unconditional separation matrix (non-BDO, D1 → D10 spread) — the production-relevant table

| Category | Distance sep | GNN prob sep | Winner | Shape on distance |
|----------|-------------:|-------------:|--------|-------------------|
| **Install rate** | 44% | **57%** | Prob by 13pp | Monotonic decay |
| **Area decline rate** | 20% | 23% | Roughly tied on separation | Step function (flat D1–D5, step D6, jump D10) |
| **Address not clear rate** | 19% | **45%** | Prob by 26pp | Smooth monotonic rise (~3pp per decile) |

### Concentration in the worst 3 deciles — the decision-utility metric for top-k notification

Allocation's operational decision is binary (notify / don't notify the top-k partners). What matters is: **if I cut the bottom-ranked 30% of partners, how many bad matches do I avoid?**

| Signal | % area-declines in worst 3 deciles | Interpretation |
|--------|-----------------------------------:|----------------|
| **GNN probability** (D1+D2+D3, lowest prob) | **59.3%** | Drop 30% of volume, avoid 59% of area declines |
| **Distance** (D8+D9+D10, farthest) | 47.9% | Drop 30% of volume, avoid 48% of area declines |

**GNN is 11pp more concentrated on bad outcomes.** For a notify-top-k decision, concentration matters more than separation spread.

### Splitter-composition — whether the signal *isolates* gaming

| Prob decile | %splitter | | Distance decile | %splitter |
|--:|--:|--|--:|--:|
| D1 (lowest prob) | 38.33% | | D1 (nearest) | 11.61% |
| D10 (highest prob) | **12.17%** | | D7 (~29km) | **41.18%** (peak) |

- **GNN probability** monotonically routes splitter-heavy partners to low-prob deciles (38% → 12%). Top-ranked partners are predominantly active_base.
- **Distance** scatters splitters across D4–D10 with the peak at D7. Ranking top-k by distance would still pick splitter-heavy partners frequently.

Distance is a **gameable** axis — partners submit their own splitter lat/lngs, which directly affect the `nearest_distance` they see. GNN integrates **decline history** that gamers cannot fake, creating an active balancing loop on gaming behavior.

### Why GNN wins: it learns from decline signals, distance doesn't

A **distance-based approach is a fixed geometric cut** — it cannot adapt to partner behavior. It does not price the decline signals partners send. A partner who declines 80% of their allocations looks identical to one who installs 80%, if they're at the same distance.

**The GNN integrates both install and decline edge types** (per Maanas's design intent), weighted geographically and temporally. A partner with a recent history of declining matches in the booking's area gets ranked lower. This is the mechanism behind:
- The 13pp install-rate separation advantage (57% vs 44%)
- The 11pp concentration advantage (59% vs 48% of area declines in worst-3 deciles)
- The 26pp address-not-clear separation advantage (45% vs 19%)
- The monotonic splitter isolation (38% → 12% vs 11% → 41% peak → 35%)

The GNN's advantage *is* the decline-signal channel. Any signal that doesn't learn from declines (distance, rule-based geofences, static geometric cuts) gives this channel up.

### Diagnostic slice — conditional-accept (not production-relevant)

We also computed separation after filtering to accepted rows only (`decision_event IN ('INTERESTED','ASSIGNED')`). Result: distance 40%, probability 40% — they tie.

**This is a diagnostic, not an operational comparison.** Allocation does not get to see accept/decline status before ranking — the ranking *precedes* the partner's decision. The conditional-accept slice just decomposes *where* probability's pre-decision advantage comes from: it's mostly the decline-likelihood channel. In production, that channel is real and in-scope, so the unconditional comparison above is the right one to make allocation decisions against.

Earlier rounds of analysis (and two agent rounds) over-read this diagnostic as a critique of the GNN's value proposition. Retracted — the conditional-accept collapse is a *feature*, not a bug. It's the decline signal being removed from the data, which is precisely what GNN is designed to price.

### Shapes of the decline curves on distance

Even though concentration / separation favor GNN, the shapes tell us something real about the decline dynamics:

- **Area-decline on distance**: step function — flat D1–D5 (~7–9%), step up at D6 (~10%), bigger jump at D10 (+9pp). Matches the "partner coverage boundary" prior.
- **Address-not-clear on distance**: smooth monotonic rise, ~3pp per decile, 9.8% → 28.5%. **This is the dismissal-leak signature.** Pure address-parsing failure would be orthogonal to distance; it isn't. Partners farther out use "address unclear" as a polite decline regardless of actual address clarity. GNN captures this 2.4× better (45% sep vs 19%) because it directly models partner willingness.

## Recommendations — merged Monday actions, scoped to Allocation

Summarizing the convergent conclusions from the full analysis + both agents' final rounds.

| # | Action | Leverage |
|---|--------|----------|
| 1 | **Keep GNN `probability` as the Allocation ranking signal.** No distance-as-substitute bake-off — it's a category error (distance is a static geometric cut that cannot price decline signals; GNN integrates both install AND decline edges). | High |
| 2 | **Ship a hard distance cutoff (~50km) as a refusal primitive, NOT as a ranker.** D10 conditional install rate is 22.79% — the fiber-reach Shannon limit. Allocation should return the booking instead of routing it. *Systems framing: this creates the first balancing loop on partner routing. Today every booking routes; losses absorb as declines. The cutoff is the first outflow valve on the "forced-routing" stock.* | High |
| 3 | **Monitor concentration-in-worst-deciles, not just separation,** as the Allocation health metric. Concentration is the decision-utility statistic for top-k notification; separation is calibration. | High |
| 4 | **Treat splitter-composition monotonicity as a calibration invariant across GNN retrains.** If a new model breaks the 38%→12% monotonic decay of splitter-share across prob deciles, it's regressing on gaming resistance — flag before merging. | High |
| 5 | **Track `address_not_clear` rate weekly by `prob_decile`.** Cleanest dismissal-leak early warning. Drift here means Promise Maker is leaking or upstream address capture has degraded. | Medium |
| 6 | **Publish 22.79% D10 conditional-accept install ceiling as a Wiom KPI.** Any tail-allocation strategy must be measured against this physical floor, not average install rate. | Medium |
| 7 | **Add `splitter_share` as a GNN feature in the next retrain** (acknowledged band-aid). Open a parallel workstream on **upstream splitter validation** (outcome-conditioned decay on splitter stock) as the durable fix. | Medium |
| 8 | **Instrument GNN's decline-signal ingestion path.** Concrete loop-gain specs (not just cadence): (a) splitter-composition monotonicity across prob deciles must stay strictly decreasing — alert on any D_i > D_{i-1}; (b) concentration-in-worst-3-prob-deciles on area-declines must stay ≥55% — alert if it drops below; (c) the active_base vs splitter install-rate gap at fixed prob_decile 4 must not widen beyond 35pp (currently 31pp). These three are the loop-gain metrics; weekly is the cadence. | Medium |
| 9 | **Isolate decile-10 as data hygiene, not a distance bucket.** Trace 200km+ rows upstream (booking-form defaults vs stale partner lat/lngs). Independent workstream. | Medium |
| 10 | **Keep `area_decline` and `address_not_clear` as separate metrics.** Different root causes, different interventions. | Low cost, already in place |

### Stop doing

- Stop treating distance as a ranking substitute for GNN probability. It's a category error.
- Stop chasing cold-start as the tenure-gap explanation. H1 rejected by data (730d+ partners show 18pp gap).
- Stop debating `edge_attr` architecture — the code confirmed the precomputed formula is orphan at runtime (see GNN side note).

*Promise Maker recommendations remain out of scope — separate lead-level analysis.*

## GNN context (side note — parked, not load-bearing)

This analysis was not about GNN architecture. It is about the data-space question: does distance predict installability, and how do decline buckets behave on distance. Those answers stand on their own above.

For context: the GNN is a heterogeneous graph with match/task/geosplitter nodes, 30 edge types split by (distance × time × action). The model's `probability` is used as the ranking signal for Allocation. Design intent (per Maanas): learn from both install and decline decisions as geographically and temporally separated first-class edge types.

One detail worth flagging for future GNN work, surfaced during this analysis:
- `create_gnn.py` computes a precomputed attention bias per edge: `exp(-time) × 1/(1+dist) × (1 - DECLINED) × (1 + INSTALLED)` and stores it as the last column of `edge_attr`.
- The `GATConv` instances are initialized without `edge_dim`. In PyTorch Geometric, `edge_attr` passed at forward time is only consumed when `edge_dim` was set at init (which builds `lin_edge`). Otherwise the `edge_attr` is dropped (older PyG silently; newer PyG raises).
- Likely implication: the precomputed attention formula is **orphan at runtime** — computed and stored but not consumed. Message passing uses GATConv's own learned attention over node features + topology. Both install and decline edge types contribute first-class messages exactly as intended.
- Verify in code execution; if confirmed, either the HTML doc's attention-interaction claim needs revision, or the code should pass `edge_dim=1` to make the precomputed bias active.

No action required from this analysis. Logged here so the next GNN iteration has the note.

## Files

### Scripts
| File | Purpose |
|------|---------|
| `decile_install_rate.py` | V1 — separate install/decline slices |
| `unified_decile_analysis.py` | V2 — unified cohort + probability + nearest_type |
| `probe_tenure_tables.py` | One-off probe of `t_partner`, `t_active_base`, `t_node_splitter_gs` (schemas, grain, uniqueness). Output to `investigative/probe_summary.txt` |
| `investigate_tenure_gap.py` | Tests H1 (cold-start) vs H2 (splitter-gaming) for the active_base-vs-splitter install gap. Joins cohort with partner tenure + active_base counts + dedup'd splitter counts |
| `write_story.py` | Standalone — reads all result CSVs, writes `STORY.csv` |
| `db_connectors.py` | Snowflake + MySQL connectors |

### Queries
| File | Purpose |
|------|---------|
| `query_install_correl.txt` | V1 install cohort SQL |
| `query_decline_correl.txt` | V1 decline cohort SQL |
| `query_unified_correl.txt` | V2 unified cohort SQL (adds nearest_type, probability) |

### Outputs — all in `investigative/` except `STORY.csv`

| File | Produced by |
|------|-------------|
| `investigative/cohort_install_raw.csv` | V1 |
| `investigative/cohort_decline_raw.csv` | V1 |
| `investigative/decile_install_rate.csv` | V1 slice 1 |
| `investigative/decile_area_decline_rate.csv` | V1 slice 2 |
| `investigative/decile_address_not_clear_rate.csv` | V1 slice 3 |
| `investigative/decile_post_decline_install_rate.csv` | V1 slice 4 |
| `investigative/decline_reasons_summary.csv` | V1 regex QA |
| `investigative/cohort_unified_raw.csv` | V2 |
| `investigative/decile_unified_summary.csv` | V2 distance slice |
| `investigative/decile_prob_summary.csv` | V2 probability slice |
| `investigative/summary_by_nearest_type.csv` | V2 nearest_type groupby |
| `investigative/prob_decile_by_nearest_type.csv` | V2 cross-table |
| `investigative/prob_decile_splitter_composition.csv` | V2 composition |
| `investigative/probe_summary.txt` | Tenure-gap probe (schemas) |
| `investigative/cohort_enriched_tenure.csv` | Tenure-gap (cohort + tenure + splitter + active_base joined) |
| `investigative/tenure_by_nearest_type.csv` | Tenure-gap (distribution) |
| `investigative/install_by_tenure_x_type.csv` | Tenure-gap H1 test |
| `investigative/gap_by_prob_decile_x_tenure.csv` + `_ncounts` | Tenure-gap: prob × tenure × type |
| `investigative/install_by_prob_x_splitter_share.csv` + `_ncounts` | Tenure-gap H2 test (headline) |
| `investigative/partner_level_summary.csv` | Tenure-gap (per-partner descriptives) |
| `STORY.csv` | `write_story.py` — single narrative + all tables |

### Run order
```
python unified_decile_analysis.py       # (optionally) python decile_install_rate.py first
python probe_tenure_tables.py           # (optional, one-off probe)
python investigate_tenure_gap.py        # H1/H2 tenure-vs-splitter-share test
python write_story.py                   # rebuild STORY.csv from all CSVs above
```

## Timeline

| Date | Event |
|------|-------|
| 2026-04-19 | V1 — install-rate decile analysis (Slice 1). |
| 2026-04-19 | V1 — added DECLINE analysis. First regex flagged 47.6% of declines as area. |
| 2026-04-19 | V1 — filtered `System_Force_Declined_Post_Assigned_72hours` auto-declines. |
| 2026-04-19 | V1 — sampled `meters or more away` + `Couldn't understand the address` → both confirmed system dropdowns. Split `address_not_clear` into its own metric. |
| 2026-04-19 | V1 — added post-decline install slice (~0% overall). |
| 2026-04-19 | Geoff + Donna validation round 1 (on V1). Six leaks flagged — partner-tenure confound + denominator framing most load-bearing. |
| 2026-04-19 | V2 — unified cohort. All decisions in one table. Denominator switched to `total_obs` (Geoff's Leak B). |
| 2026-04-19 | Applied non-BDO filter across both pipelines. Cohort dropped 27,303 → 11,870 (56%). |
| 2026-04-19 | Added `nearest_type` + `probability` to allocation CTE. |
| 2026-04-19 | Probability decile slice: install separation 57% (vs 44% on distance). Address-unclear 48% at low-prob → 2.5% at high-prob. |
| 2026-04-19 | Prob × nearest_type cross-table: GNN partially encodes splitter signal; residual 10–17pp mid-prob penalty. |
| 2026-04-19 | Geoff + Donna validation round 2. Converged on source stratification + time-to-decline + different-partner recovery as top-3 next steps. |
| 2026-04-19 | Story CSV builder split into standalone `write_story.py`. |
| 2026-04-19 | Scope re-framed: all analysis is post-Promise-Maker. We evaluate Allocation/GNN, not Promise Maker. "lead" → "booking" across docs. |
| 2026-04-19 | Folder restructured: all intermediate CSVs moved to `investigative/` subfolder. Root stays light (scripts + queries + README + STORY.csv). |
| 2026-04-19 | Conditional-accept slice: probability separation 57% → 40% when filtered to INTERESTED/ASSIGNED. Distance also 40%. Probability = decline-predictor, not fit-predictor. |
| 2026-04-19 | Tenure-gap investigation. H1 (cold-start) rejected — 730d+ partners show 18pp gap. H2 (splitter-gaming) supported — partners with splitter_share >90% install at 5% vs 36% for share <10% (prob_decile 4). Dedup'd (partner,lat,lng) in `t_node_splitter_gs` — 0 dupes in source. |
| 2026-04-19 | Geoff + Donna validation round 3. Convergent re-factoring: `P(install) = P(accept) × P(install | accept)`. Probability loads on first term, distance on second. Splitter_share as GNN feature = band-aid; real fix is upstream data validation. Donna's "refusal primitive" + Geoff's "D10 is Shannon limit" frame the next architectural question. |
| 2026-04-19 | Geoff + Donna validation round 4 — first attempt to incorporate GNN architecture from HTML doc. Built an "architectural critique" (decline-complement, survivorship bias, three structural fixes) on the documented attention formula. Retracted in round 5 when the code was read. |
| 2026-04-19 | Round 5 — read `create_gnn.py` directly. `GATConv` is initialized without `edge_dim`, which means the precomputed attention formula is **orphan at runtime** (PyG drops or raises on `edge_attr` when `edge_dim=None`). Both install AND decline edge types propagate first-class messages via learned attention. Agents retracted the "decline-complement" and "survivorship bias" framings. Core data findings (conditional-accept, tenure-gap H2, address-not-clear dismissal-leak) stand independently. README reorganized: GNN-architecture discussion moved to a side note. |
| 2026-04-19 | Round 6 — Maanas pushed back on the "distance over GNN" framing: GNN wins because it learns from decline decisions, a signal distance cannot encode. Concentration math: GNN prob D1+D2+D3 captures 59.3% of area declines vs distance D8+D9+D10 capturing 47.9%. New splitter-composition-by-distance-decile table computed — distance SCATTERS splitters (peak 41% at D7) vs GNN ROUTES them monotonically (38% → 12% across prob deciles). Both agents fully retracted earlier distance-as-substitute framing. Final convergent stance: use GNN for ranking; distance is a physics co-signal and a tail refusal primitive, not a ranking primitive. |
| 2026-04-19 | Round 7 — documentation reorganized for session-resumption. Added "Session resume" + "Operational context" sections at top clarifying that Allocation runs pre-notification (GNN ranks BEFORE partner decisions). Conditional-accept slice explicitly reframed as a diagnostic decomposition, not an operational comparison. Recommendations section collapsed into a single "Merged Monday actions" table reflecting the final stance. |
