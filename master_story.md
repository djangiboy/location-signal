# Master Story — Location Signal in Wiom's Matchmaking Funnel

**Drafted:** 2026-04-21
**Source outline:** `narration_master_story.txt`
**Data source:** 5 sub-folder STORY.csv files + READMEs across `promise_maker_gps/`, `allocation_signal/`, `coordination/`, `coordination/polygon_analysis/`
**Companion structured extract:** `master_story.csv`

## How to read this

**One-line frame.** The promise is made on a single unverified GPS fix gated by 25m infrastructure proximity; every downstream engine compensates for what that single fix does not carry. This document walks the signal from left to right and reports what the data says at each handoff.

One location signal travels through four handoffs — capture → allocation → coordination → install. **Denominators differ by cohort** and are called out at each beat. Unless otherwise stated: non-BDO only, Delhi, recent months. Discrepancies against the source outline are listed at the end.

### Cohort map

| Cohort | n | Source | Used in |
|---|---:|---|---|
| Per-mobile / per-ping GPS jitter | 8,317 mobiles / 20,231 pings | `promise_maker_gps/gps_jitter/` | Part A |
| Booking → install drift (installed, non-BDO, Delhi Dec-2025) | 3,855 installs | `promise_maker_gps/booking_install_distance/` | Part D |
| Allocation decisions (non-BDO pairs) | 11,870 pairs (11,020 after NULL-prob drop) | `allocation_signal/` | Part B |
| Coordination pairs (non-BDO Delhi Jan-Mar 2026) | 2,561 pairs / 4,930 calls | `coordination/` | Part C |
| Polygon-eligible pairs | 2,499 (97.6% of 2,561) | `coordination/polygon_analysis/` | Part C.D |

---

## Part A — Customer gives GPS

### A.1 Is there jitter?

**Cohort:** 8,317 mobiles, 20,231 subsequent pings, 2025-09-01 to 2026-01-26. Cleaned with 15-min dedup, 250m home-move cap, and a ≥2-ping survival filter.

Per-ping jitter (haversine anchor vs subsequent ping):

| Quantile | Distance (m) |
|---|---:|
| p50 | 7.66 |
| p75 | 19.98 |
| **p95** | **154.76** ← adopted as Stage B structural-drift threshold |
| p99 | 227.89 |

Per-mobile worst-case radius (the largest jitter any individual mobile ever produces):

| Quantile | Value |
|---|---:|
| p50 | 11.71 m |
| p75 | 31.79 m |
| p95 | 175.60 m |

**70% of mobiles (5,821 / 8,317) have their worst single fix within 25m of their anchor.** Device-and-environmental jitter is not a large cohort-level problem. The apparatus is not the leak for most of the population. The p95 tail (155m) carries the error; 5% of mobiles can produce >175m on their worst fix.

### A.2 Flow as it exists today

1. **GPS captured once** at `fee_captured_at` (booking time). Next validated fix is at install — `wifi_connected_location_captured` via SSID connection, days later.
2. **25m infrastructure-proximity gate.** Promise Maker gates every lead on `distance(booking_lat/lng, nearest historical install or splitter) ≤ 25m`. Pass → promise. The gate is partner-agnostic by construction; the partner-serviceable polygon (built from each partner's install/decline history, `partner_cluster_boundaries.h5`) is not consulted at this gate.
3. **Text address collected** as a free-text string *after* the 25m gate passes and *after* the fee is captured (flow step 8, per parent README).

Today the signal feeding serviceability decisioning is one reading per booking; a trajectory of fixes is not captured.

---

## Part B — Allocation

We now rank partners for each booking. Despite the jitter documented above, the ranker produces real install-rate separation and real decline-decision structure across distance. But it is also recovering a signal that upstream noise has smeared.

### B.1 Install-rate rank-order on distance deciles

**Cohort:** 11,870 non-BDO (mobile, partner_id) pairs with decision events. Denominator across all decisions (accept + decline).

| Decile | n pairs | d_median (m) | Install rate | Area-decline rate | Addr-not-clear (dropdown) |
|---:|---:|---:|---:|---:|---:|
| D1 | 1,189 | 2.09 | **50.46%** | 6.39% | 9.76% |
| D2 | 1,188 | 6.52 | 46.72% | | |
| D3 | 1,188 | 10.24 | 45.20% | | |
| D4 | 1,184 | 14.01 | 42.74% | | |
| D5 | 1,187 | 17.97 | 37.07% | | |
| D6 | 1,188 | 22.64 | 30.72% | | |
| D7 | 1,185 | 29.47 | 28.95% | | |
| D8 | 1,187 | 41.47 | 22.66% | | |
| D9 | 1,187 | 60.20 | 12.81% | | |
| D10 | 1,187 | 88.06 | **6.66%** | 26.03% | 28.48% |
| **Separation D1→D10** | | | **43.81pp** | **19.64pp** | **19.38pp** |

Install rate rank-orders on distance. Area-decline (strict + feasibility regex) and the address-not-clear dropdown also rank with distance. D10 has a d_max of 448m — the long tail is a hygiene flag pointing back at Part A's capture issue.

**Official separation metric for addr-not-clear dropdown on distance: 19.38pp** (source: `allocation_signal/STORY.csv` §5 line 101). The D1-to-D10 literal endpoint gap of 18.72pp differs because the official separation uses max-min across all deciles.

**Polygon signal is present in Allocation but not at the gate.** Part C.D shows install rate differs by 16.7pp between inside-polygon and outside-polygon pairs (1,939 vs 560, on 2,499 eligible). The GNN below implicitly prices partner-polygon fit; Promise Maker's 25m gate does not.

### B.2 When we use a GNN that learns from historic install + decline decisions

**Cohort:** same 11,870 pairs; ~7% with NULL probability dropped from prob-decile view.

| Prob decile | n | p_median | d_median (m) | Install rate | Area-decline | Addr-not-clear |
|---:|---:|---:|---:|---:|---:|---:|
| D1 | 1,101 | 0.0072 | 42.81 | **3.72%** | 25.79% | 47.68% |
| D5 | 1,101 | 0.3989 | 22.05 | 29.79% | 10.72% | 10.54% |
| D10 | 1,101 | 0.9723 | 9.12 | **60.49%** | 2.36% | 2.54% |
| **Separation** | | | | **56.77pp** | **23.43pp** | **45.14pp** |

**Side-by-side:**

| Signal | Install-rate separation | Area-decline separation | Addr-not-clear separation |
|---|---:|---:|---:|
| Raw distance | 43.81pp | 19.64pp | 19.38pp |
| GNN probability | **56.77pp** | **23.43pp** | **45.14pp** |
| GNN edge | +12.96pp | +3.79pp | +25.76pp |

*Denominators: distance separations on 11,870 pairs; prob separations on 11,020 (NULL-prob dropped).*

**The GNN wins every operational metric.** Install-rate separation is 13pp better, and address-not-clear dropdown concentrates 2.5× more sharply in the bottom deciles.

---

## Part C — Coordination after a partner accepts

### C.A What the partner sees, and what they lose

At FPN, the partner sees a map with nearby install pins — spatial context about their own serviceable area. At ASSIGN, the map is not retained; the partner's remaining handle on the booking is the customer's free-text address string captured at flow step 8. The voice call that follows originates against that string, not against the FPN's map. Coordination is a voice call between ASSIGN and OTP-verified install.

### C.B What are partner and customer talking about?

**Cohort:** 2,561 (mobile, partner_id) pairs, 4,930 IVR calls, Delhi Jan-Mar 2026 non-BDO, Haiku-classified.

Primary reason of the first call, pair-level:

| Primary reason (first call) | Pairs | % | Install rate |
|---|---:|---:|---:|
| **address_not_clear** | 927 | **36.2%** | 59.0% |
| noise_or_empty | 537 | 21.0% | 50.5% |
| slot_confirmation | 255 | 10.0% | 64.7% |
| customer_postpone | 140 | 5.5% | 47.9% |
| customer_unreachable | 130 | 5.1% | 43.8% |
| **partner_reached_cant_find** | 114 | **4.5%** | **71.1%** |
| wrong_customer | 98 | 3.8% | 31.6% |
| customer_cancelling | 85 | 3.3% | 2.4% |
| others (11 buckets) | 195 | 7.6% | — |

**36.2% ANC + 4.5% can't-find = 40.7% of pairs have a location-reason first call** (pair-level, over 2,561 pairs). Install rates differ: once the partner is *at* the house and still can't find (71.1% install), things usually resolve; when they're stuck trying to parse the address from a call (59% install), they do worse.

**Denominator bridge before C.C.** Pair-level ANC = 927 / 2,561 pairs (first-call primary reason). Call-level ANC = 1,023 / 4,930 calls (any call in any pair). The 1,023 is the denominator for the 77.5% headline below.

### C.B (continued) — Monotonicity collapse post-acceptance

Address-not-clear rate at the *transcript* level, by decile of the pre-accept signals:

**By distance decile:**

| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 19.5% | 18.0% | 20.1% | 20.6% | 19.9% | 21.4% | 20.6% | 24.3% | 23.1% | 20.3% |

Range: 6.5pp. **Flat.**

**By GNN probability decile:**

| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 17.9% | 18.2% | 23.2% | 24.2% | 19.6% | 20.4% | 19.6% | 21.6% | 18.7% | 20.9% |

Range: 7.1pp. **Flat.**

Pre-accept, the *dropdown* "address not clear" moves from 47.7% (D1) to 2.5% (D10) — a 45pp monotonic drop. Post-accept, the same signal measured on transcripts is flat at ~20% everywhere. **The pre-accept monotonicity was a decline-channel artifact** — partners click "address not clear" as a polite exit on low-prob bookings; after acceptance, every partner faces roughly the same per-call address friction regardless of rank. Monotonicity seen pre-accept is no longer evident post-accept.

### C.C Communication quality — how the call goes when ANC happens

We roll per-call `comm_quality` up to the pair using a pessimistic rule:

> `mutual_failure > one_sided_confusion > clear > not_applicable`

The question this answers: **did this pair EVER have a mutual breakdown?**

**Cohort-wide distribution (2,561 pairs):**

| comm_quality_worst | Pairs | % | Install rate |
|---|---:|---:|---:|
| mutual_failure | 1,028 | 40.1% | 50.8% |
| one_sided_confusion | 845 | 33.0% | 53.1% |
| clear | 414 | 16.2% | 59.4% |
| not_applicable | 274 | 10.7% | 36.5% |

**Restricted to the 1,023 address_not_clear calls** (what the outline cites):

| comm_quality within ANC | Calls | % | Install rate |
|---|---:|---:|---:|
| one_sided_confusion (partner confused, customer clear) | 471 | **46.0%** | 54.6% |
| mutual_failure | 322 | **31.5%** | 48.4% |
| clear (resolved) | 209 | 20.4% | 62.2% |

**Headline: within address-not-clear calls, 46% + 31.5% = 77.5% still end in confusion** (one-sided or mutual; denominator = 1,023 ANC calls within 4,930 total). Only 20% resolve on-call. The 46% one-sided case is: **customer is clear, partner is confused.**

**Install-rate gap by clarity (cohort-wide):**
- Clear: 59.4% install
- One-sided: 53.1% install (gap -6.3pp vs clear)
- Mutual: 50.8% install (gap -8.6pp vs clear)

Outline claims a 10pp gap; actual gap is ~8pp. Clarity on the IVR call lifts install rate meaningfully but not by 10pp.

### C.D Overlay partner serviceable boundaries (polygons from SE-weighted install history)

Built via DBSCAN on high-supply-efficiency hexes per partner. Eligible pairs: 2,499 (97.6% of cohort).

| Polygon side | Pairs | Share | Install rate | ANC touch rate |
|---|---:|---:|---:|---:|
| **Inside** | 1,939 | 75.7% | **55.3%** | 43.9% |
| **Outside** | 560 | 21.9% | **38.6%** | 48.2% |
| Total | 2,499 | | 51.5% | 44.9% |

**Inside beats outside on install rate by +16.7pp.** Crucially, ANC *touch* rate is slightly *higher* inside (43.9% vs 48.2% — 4pp spread) — confusion *appears* to happen at similar rates on either side. **But recovery from ANC is dramatically different.**

**Restricted to pairs where primary_reason = address_not_clear:**

| Polygon side | Pairs | Install rate |
|---|---:|---:|
| Inside | 690 | **63.2%** |
| Outside | 217 | **43.8%** |
| **ANC recovery gap** | | **+19.4pp inside** |

Inside the polygon, ANC recovers to 63% install. Outside, it collapses to 44%. **The polygon governs whether resolution is possible, not whether confusion occurs.**

**Comm-quality × address-family × polygon-side (8-cell MECE grid) — the "recovery" picture:**

| comm_quality | address-family | Inside n | Inside install % | Outside n | Outside install % | Gap |
|---|---|---:|---:|---:|---:|---:|
| mutual_failure | address_related | 387 | 60.5% | 124 | 39.5% | +21.0pp |
| mutual_failure | non_address | 373 | 49.3% | 112 | 35.7% | +13.6pp |
| one_sided | address_related | 297 | 64.0% | 98 | 46.9% | +17.1pp |
| one_sided | non_address | 342 | 50.3% | 91 | 34.1% | +16.2pp |
| clear | address_related | 119 | 68.1% | 26 | 50.0% | +18.1pp |
| clear | non_address | 211 | 58.8% | 49 | 49.0% | +9.8pp |

**Inside beats outside in every cell.** The bottom of the outside column is worse than the bottom of the inside column by order of 10-20pp consistently. Whether the call was mutual failure, one-sided, or clear — the polygon matters more than the conversation quality.

**Chain-engagement × polygon cross-cut (from `coordination/polygon_analysis/`):**

| addr_chain_stuck_at_mode | Inside pairs | Inside install % | Outside pairs | Outside install % | Gap |
|---|---:|---:|---:|---:|---:|
| na (no chain reached) | 1,458 | 52.6% | 412 | 39.8% | +12.8pp |
| landmark stuck | 172 | 62.2% | 59 | 42.4% | +19.8pp |
| **gali stuck** | 168 | **62.5%** | 59 | **25.4%** | **+37.1pp ← danger cell** |
| none (chain resolved) | 103 | 62.1% | 23 | 34.8% | +27.3pp |
| floor stuck | 38 | 76.3% | 7 | 57.1% | +19.2pp |

**Gali-stuck × outside-polygon = 25.4% install** (n=59). Same cell inside polygon = 62.5%. **+37.1pp — the sharpest single-cell difference in the entire audit.** Gali-stuck means the partner is in the locality but can't find the lane. Outside the polygon, the partner doesn't know the area's lane grid; inside, they do.

**Landmark-step is co-equal with gali at the call level.** Engagement shares (inside / outside): landmark 8.9% / 10.5%; gali 8.7% / 10.5%; floor 2.0% / 1.3%. Call-level stuck rates: landmark 8.7%, gali 7.4%. ~40% of ANC pairs never reach the gali step — their chain breaks at or before landmark. Landmark friction and gali friction are co-equal in volume; the gali × outside danger cell is where the compounding bites hardest.

### C.E Chain-engagement protective effect — standalone observation

When the landmark → gali → floor chain gets touched on any call in a pair, install rate lifts:

| polygon_side | chain_engaged | pairs | install_rate % |
|---|---|---:|---:|
| inside | no | 1,231 | 51.2% |
| inside | **yes** | 708 | **62.4%** (+11.2pp) |
| outside | no | 359 | 37.6% |
| outside | yes | 201 | 40.3% (+2.7pp) |

**Chain engagement adds +11.2pp install inside polygon and +2.7pp outside.** Structure on the call tracks polygon side.

### C.G Install time does not discriminate address vs non-address call topics

When we trace pairs that eventually install and compare their decision-to-install time by whether the primary call reason was address-related or not — across all quantiles (p25, median, p75, p90, p95, p99) — the distributions are indistinguishable. Address-related pairs are actually median *faster* (18.97h vs 21.63h). Full table in Part D.B. The cost of address friction on call is not paid in install hours; it is paid in the conversion cohort (some pairs never install at all) and in the coordination overhead itself (1.92 calls per pair). When a pair does convert, address vs non-address primary reason drops out as a predictor of elapsed time.

### C.F What the data DOES close a loop on

Install outcomes flow back into the supply-efficiency hex grid (installs / total decisions per hex), which updates the partner-serviceable polygon on the next snapshot — i.e., the install → polygon loop **does** close. What the data does NOT show: any channel by which install outcomes flow back to the capture apparatus (the single GPS fix, the post-payment free-text address). The install → capture loop is not observed in any engine.

### C. What is missing in the coordination view

1. **Not every partner coordinates on IVR.** They exchange numbers, use direct dial, WhatsApp. Monthly no-call share: Jan 72.8%, Feb 56.9% (Feb 7-9 at >92% for 3 consecutive days — acute outage), Mar 34.9%. March is the cleanest read; Jan-Feb attribution to UCCL ingestion is directional. IVR is directional, not complete.
2. **No partner GPS stream** — we cannot observe whether the partner actually reached the locality, detoured, or never left another job.
3. **No technician-level (Rohit) GPS stream** — we cannot separate partner vs. on-ground technician movement during the visit.

---

## Part D — Post-install

### D.A Booking-vs-install drift distribution

**Cohort:** 3,855 Delhi Dec-2025 non-BDO installs. Haversine distance between `booking_lat/lng` and first `wifi_connected_location_captured`.

| Decile | n | d_min (m) | d_max (m) | d_median (m) |
|---:|---:|---:|---:|---:|
| D1 | 386 | 0.00 | 2.64 | 1.40 |
| D2 | 385 | 2.64 | 5.30 | 3.93 |
| D3 | 386 | 5.30 | 8.88 | 7.03 |
| D4 | 385 | 8.88 | 14.10 | 11.01 |
| D5 | 386 | 14.10 | 22.52 | 17.58 |
| D6 | 385 | 22.52 | 47.05 | 30.90 |
| D7 | 385 | 47.21 | 117.57 | 74.76 |
| D8 | 386 | 118.04 | 232.74 | 162.65 |
| D9 | 385 | 232.86 | 477.62 | 340.73 |
| D10 | 386 | 479.29 | 213,846.05 | **767.78** |

Summary quantiles:

| Quantile | Drift |
|---|---:|
| p50 | 22.52 m |
| p75 | 162.65 m |
| **p95** | **767.16 m** |
| p99 | 2,870.83 m |

**Comparison to Stage A apparatus:**

| Quantile | Apparatus per-ping | Booking→install drift | Ratio |
|---|---:|---:|---:|
| p50 | 7.66 | 22.52 | 2.9× |
| p75 | 19.98 | 162.65 | 8.1× |
| p95 | 154.76 | 767.16 | 5.0× |
| p99 | 227.89 | 2,870.83 | 12.6× |

Booking-to-install drift is 3-8× wider than apparatus jitter at every quantile. GPS physics does not produce this.

**Decomposition (two causes, one with two sub-populations):**

1. **GPS apparatus jitter** — 74.3% of installs (2,864): drift within Stage A p95 (≤155m). Explainable by device/environment physics.
2. **Customer captured GPS from not-home** — 25.7% (991): drift beyond what a single-moment apparatus reading can produce. Customers don't realise they need to give location from home, so the fix is taken from wherever they are at booking time. Two sub-populations:
   - **Near-home-but-not-home bulk** (~22%): drift 155m–1km. Café, shop, street, neighbour's house.
   - **Hygiene tail** (~3%): 3.2% drift >1km, 0.4% drift >10km, max 213.8km. Wrong-locality or tap errors — distinct from the near-home-but-not-home bulk.

### D.B Does address friction on the call burn install time?

**Cohort:** 1,317 installed pairs with decision→install timestamps. Decision-to-install time in hours, full quantile breakdown:

| Bucket | n | min | p25 | median | mean | p75 | p90 | p95 | p99 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL_INSTALLED | 1,317 | 0.29 | 5.57 | 20.80 | 27.76 | 28.39 | 49.56 | 70.52 | 182.06 | 1,388.65 |
| address_related | 642 | 0.29 | 5.53 | 18.97 | 26.52 | 27.82 | 49.54 | 70.38 | 179.21 | 847.55 |
| non_address_related | 675 | 0.45 | 5.68 | 21.63 | 28.95 | 29.07 | 49.46 | 70.68 | 180.05 | 1,388.65 |

**Null finding — install time does not discriminate between address and non-address call topics.** Every quantile agrees: p25 differs by 0.15h, median by 2.66h (address actually *faster*), p75 by 1.25h, p90 by 0.02h, p95 by 0.30h, p99 by 0.84h. Cost of address friction is not paid in decision-to-install hours. Address issues, when they land in install, resolve at roughly the same pace as non-address issues that also land in install.

Range across all primary_reasons at median: 18.8h (ANC) to 25.1h (customer_postpone). 6.3h spread on a ~21h median. Non-address terminal issues (cancellation negotiation, price dispute) that still end in install drag longer on the tail (max 1,388h vs 847h).

---

## Closing — the one-line frame

The location signal is noisy at capture (Part A), smeared into allocation (Part B), discovered rather than confirmed on-call (Part C), and lands at a physical point that differs from the booking coord (Part D). Each engine's compensation is local. What the upstream structure would carry, and how it would be consumed, is the subject of the companion inferences document.

---

## Methodology notes

- **Cohort boundaries differ.** See Cohort map at top. Denominators called out inline at each beat.
- **All install-rate separation uses D1 vs D10** (not means). Per durable principle: deciles > means. Binary-partition comparisons (inside vs outside polygon, address-related vs non-address) are labelled as such; not to be read as decile separations.
- **The 25.7% figure** uses Stage A per-ping p95 (154.76m) as the apparatus ceiling. Any install with drift > 154.76m is attributed to cause #2 (customer-not-at-home) rather than sensor noise.
- **Polygon-side analysis** excludes ~2.4% of pairs with no eligible polygon.
- **BDO excluded.** All beats are non-BDO. BDO is ~60% of raw installed volume; its drift/install-rate characteristics are not measured in this backbone. Queued for segmentation work.
- **Declined-cohort drift is a known gap.** Stage B measures drift on installed bookings only (no `wifi_connected_location_captured` exists on declined bookings). Solutioning = ensure verified customer location; success measure = booking-to-install drift declines on the installed cohort. Building a drift-on-declines analysis is not first-level solutioning work.

## Discrepancies logged against `narration_master_story.txt`

| Claim in outline | Actual data | Resolution |
|---|---|---|
| "36% (area not understandable) + 4% (partner reached can't find)" | 36.2% + 4.5% = 40.7% | ✅ matches within 1pp |
| "77.5% confusion (46% one-sided + 31.5% mutual)" | Within ANC calls: 46% + 31.5% = 77.5%. Cohort-wide (all pairs): 40.1% + 33.0% = 73.1% | ✅ matches when denominator is ANC calls (outline was implicitly within-ANC) |
| "10% higher install rates when clear on IVR" | Clear 59.4% vs one-sided 53.1% = +6.3pp; clear vs mutual = +8.6pp | Directionally correct; magnitude ~8pp not ~10pp |

---

## Companion files

- `master_story.csv` — structured backbone (one row per beat with metric / value / source / note)
- `narration_master_story.txt` — original outline
- Sub-folder STORY.csv files — raw data source per engine

---

## Appendix — Splitter-share gaming (partner-side upstream corruption)

Separate from Parts A-D's customer-side capture story. Source: `allocation_signal/STORY.csv` §10.

Within a single GNN probability decile (same `probability` bin), partners sort by splitter-share — the fraction of their historical bookings whose `booking_lat/lng` fell suspiciously close to a splitter. At prob_decile 4:

| Splitter share | Install rate |
|---|---:|
| <10% splitter-share partners | 35.8% |
| >90% splitter-share partners | 5.0% |
| **Gap at same GNN prob** | **−30.8pp** |

A 31pp install-rate gap exists at the *same* modelled probability — meaning some partners submit bookings whose coords are coincident with splitters (an upstream-coord corruption channel the GNN cannot price without a splitter-proximity feature). This is a partner-side story, complementary to the customer-side capture story in Part A. Flagged here for completeness; not in the main narrative.
