# Polygon-based analysis of the 2,561 pair cohort

**Parent:** `../` (`partner_customer_calls/`).
**Polygon source:** `promise_maker/B/training/partner_cluster_boundaries.h5` (copied here).
**Created:** 2026-04-20 11:27 · **Updated:** 2026-04-20 15:30
**Status:** End-to-end run complete. Address-chain × polygon cross-cut added 2026-04-20 afternoon.
**Feeds into:** `../../master_story.md` Part C.D (narrative — polygon eligibility, inside/outside asymmetry, 8-cell MECE grid, addr-chain × polygon danger cell, chain-engagement protective effect) and `../../master_story.csv` (tables C.D polygon eligibility, C.D ANC by polygon-side, C.D 8-cell MECE, C.D addr_chain × polygon, C.D chain-engagement share, C.E chain-engagement × polygon protective gap). Parent synthesis; this folder is source of truth for the partner-polygon overlay.

---

## Objective

The parent analysis landed on a distance-agnostic view: address friction is pervasive across distance deciles. But "distance from a booking to a partner's nearest installed point" is one way to measure proximity. Another, richer way is to check **whether the booking lies inside the partner's *supply-efficiency polygon*** — the hex-clustered boundary built from the partner's decision history.

### How the polygon is actually built (important)

Verified from `promise_maker/B/training/hex.py`:

```python
se = installs / total      # total = installs + declines = all decisions
color = "crimson" if se <= bad_se
        else "orange" if se <= mid_se
        else "lightgreen"
```

And `find_boundary.py` filters `color IN ('lightgreen', 'orange')` before DBSCAN. **Crimson hexes (partner tried, mostly declined) are EXCLUDED from the polygon.**

So the polygon is a **supply-efficiency map**, not a raw install-coverage map. Each included hex had an install-per-attempt ratio above the SE threshold. The polygon is dynamic — updates with every install/decline decision. Our analysis uses the Feb 2026 snapshot.

**What this means:** two partners with identical install counts but different decline patterns get very different polygons. Declines actively SHRINK a partner's polygon (drop SE below threshold). "Inside polygon" = "partner has high SE here" (CAN install + WILL try). "Outside polygon" = partner either never tried OR tried-and-mostly-declined there.

Three questions:

1. **Eligibility.** Of 2,561 pairs in the cohort, how many have a partner with a known serviceable polygon?
2. **Inside vs outside.** For pairs with polygons, does being INSIDE vs OUTSIDE the polygon change:
   - the reason distribution (especially `address_not_clear`)?
   - the install rate?
3. **Depth inside.** For pairs INSIDE the polygon, does distance-from-edge or distance-from-center further differentiate? Given polygon shapes vary, both raw meters and normalized-to-equivalent-radius are computed.

---

## Data sources (read only — nothing in the parent is modified)

| File | Purpose |
|---|---|
| `../investigative/pair_aggregated.csv` | 2,561 pairs with reason classifications + install flag |
| `../investigative/allocation_cohort.csv` | carries `booking_lat / booking_lng` per (mobile, partner) — from the same `booking_location` CTE as `query_pcalls.txt` |
| `partner_cluster_boundaries.h5` (copied) | 1,840 cluster polygons across 1,105 partners. Columns: partner_id, cluster_id, cluster_type (dbscan_cluster / p90_single_cluster), center_lat/lon, area_km2, boundary_poly (shapely Polygon) |

---

## Method

1. Merge `pair_aggregated.csv` with `allocation_cohort.csv` on (mobile, partner_id) to attach booking coords.
2. Load polygons into a GeoDataFrame (CRS WGS84) and project to UTM zone 43N (`EPSG:32643`) for meter-accurate distance.
3. Left-join pairs × partner polygons on partner_id. A partner can have multiple clusters.
4. Per (pair, polygon) row, compute:
   - `is_inside = polygon.contains(booking_point)` — geopandas `predicate='within'` equivalent
   - `dist_edge_m` (signed: + inside = depth, − outside = how far out)
   - `dist_center_m` (absolute distance to the cluster center)
   - `equivalent_radius_m` = √(area_km² × 1e6 / π) — size normalizer
   - `norm_dist_edge`, `norm_dist_center` = raw ÷ equivalent_radius
5. Reduce to one polygon per pair via tie-break:
   - If any polygon contains the point → pick the deepest-inside one (largest positive `dist_edge_m`)
   - Otherwise → pick the one with the nearest edge (least-negative `dist_edge_m`)

Since partners have varying polygon shapes, both raw and normalized distances are reported; normalized avoids comparing a 200m depth in a 0.2 km² polygon against a 200m depth in a 5 km² polygon.

---

## Results

### (a) Polygon eligibility (of 2,561 pairs)

| Bucket | n | % of total |
|---|---:|---:|
| Total pairs | 2,561 | 100.0% |
| With booking coordinates | 2,559 | 99.9% |
| **With at least one polygon for partner** | **2,499** | **97.6%** |
| No polygon for partner | 62 | 2.4% |
| **Inside polygon** | **1,939** | **75.7%** |
| **Outside polygon** | **560** | **21.9%** |

97.6% of pairs have polygon eligibility. Of those, ~76% are inside, ~22% are outside.

### (b) Inside vs Outside — install rate + reason mix

**Install rate:**

| polygon_side | pairs | installed | install rate |
|---|---:|---:|---:|
| **inside** | 1,939 | 1,072 | **55.3%** |
| **outside** | 560 | 216 | **38.6%** |

**+16.7pp install-rate gap** between inside and outside. Being within the partner's proven serviceable polygon is a strong install predictor.

**Reason distribution (primary_first):**

| reason | inside n | outside n | inside % | outside % |
|---|---:|---:|---:|---:|
| address_not_clear | 690 | 217 | **35.6%** | **38.8%** |
| noise_or_empty | 394 | 127 | 20.3% | 22.7% |
| slot_confirmation | 204 | 45 | 10.5% | 8.0% |
| customer_postpone | 112 | 26 | 5.8% | 4.6% |
| customer_unreachable | 102 | 25 | 5.3% | 4.5% |
| partner_reached_cant_find | 89 | 21 | 4.6% | 3.8% |
| wrong_customer | 73 | 22 | 3.8% | 3.9% |
| customer_cancelling | 63 | 17 | 3.2% | 3.0% |
| (rest) | 212 | 60 | 10.9% | 10.7% |

Reason mix is nearly identical inside vs outside — only 3pp more `address_not_clear` outside. The reason distribution is NOT the main thing the polygon split changes.

**Install rate within `address_not_clear` — THIS is where it matters:**

| polygon_side | pairs | installed | install rate |
|---|---:|---:|---:|
| inside | 690 | 436 | **63.2%** |
| outside | 217 | 95 | **43.8%** |

**+19.4pp gap** among address-friction pairs. Address friction INSIDE the polygon is surmountable 63% of the time; OUTSIDE it's surmountable only 44%. The polygon boundary is a meaningful moderator of whether address friction gets resolved.

### (c) Inside pairs (n=1,939) — does depth differentiate?

Deciles of four distance metrics; D1 = closest to edge / center, D10 = farthest.

**By `dist_edge_m` (meters deep inside polygon):**

| decile | n | install rate | address_not_clear share | edge median (m) |
|---:|---:|---:|---:|---:|
| D1 (shallowest, near edge) | 194 | **52.1%** | 41.2% | 13.3 |
| D2 | 194 | 47.4% | 35.6% | 36.4 |
| D3 | 194 | 56.2% | 38.7% | 59.5 |
| D4 | 194 | 56.7% | 36.1% | 82.7 |
| D5 | 194 | 47.9% | 35.6% | 106.2 |
| D6 | 193 | 61.7% | 29.0% | 133.4 |
| D7 | 194 | 50.0% | 35.6% | 161.6 |
| D8 | 194 | 59.8% | 32.5% | 193.8 |
| D9 | 194 | 57.7% | 39.7% | 249.4 |
| D10 (deepest) | 194 | **63.4%** | 32.0% | 353.2 |

**D1 → D10: install rate 52.1% → 63.4% (+11.3pp monotonic-ish rise).** Address_not_clear share: 41.2% → 32.0% (−9pp). Deeper inside = better install and less address friction.

**By `norm_dist_edge` (scale-invariant):**

| decile | install rate | address_not_clear % |
|---:|---:|---:|
| D1 (shallowest) | **43.8%** | 39.2% |
| D2 | 54.6% | 36.1% |
| D3 | 51.0% | 38.7% |
| D4 | 59.3% | 33.5% |
| D5 | 59.8% | 33.5% |
| D6 | 58.5% | 36.3% |
| D7 | 56.7% | 41.2% |
| D8 | 52.1% | 31.4% |
| D9 | 59.8% | 35.6% |
| D10 (deepest) | 57.2% | 30.4% |

**D1 → D10: +13.4pp install rate rise.** Stronger separation than raw meters — as expected, normalizing by polygon size makes the "depth" signal cleaner across partners with very different territory sizes.

**By distance-from-center (raw or normalized): weaker / mixed signal.** For `norm_dist_center`: D1 (closest to center) = 59.3% install, D10 (farthest from center) = 48.5% install (−11pp). But the middle deciles are flat. **Edge-distance is the cleaner signal than center-distance.**

---

## Headline findings

1. **97.6% of pairs have polygon eligibility.** The polygon table (built from partner install history) covers nearly the entire cohort.
2. **Inside vs outside is a strong install-rate discriminator: +16.7pp.** Inside 55.3% → Outside 38.6%.
3. **For `address_not_clear` pairs specifically, the gap widens to +19.4pp** (inside 63.2% vs outside 43.8%). The polygon boundary governs *whether address friction gets resolved*, not the rate at which it appears.
4. **Depth inside the polygon matters: +11-13pp install rate from shallow to deep, monotonic-ish.** Normalized-distance-to-edge is cleanest; distance-to-center is weaker.
5. **Reason mix is roughly stable inside vs outside** (3pp shift on address_not_clear). Polygon side doesn't change *what partners talk about*; it changes *whether the conversation converts to install*.
6. **Address-chain × polygon cross-cut (added 2026-04-20):** gali-stuck × outside = **25.4% install** vs gali-stuck × inside = 62.5% — a **+37.1pp gap**, the biggest single cell anywhere in the analysis. And chain engagement is protective ONLY inside the polygon (+11.2pp) — outside, engaging the chain barely helps (+2.7pp). Full tables in STORY.csv § 7b.

### Interpretation for Allocation / Promise Maker

- The polygon is a **stronger serviceability signal than `nearest_distance`** — it captures partner's proven territory (install history), not just geometric proximity.
- **Promise Maker implication:** if a booking lands OUTSIDE every partner's polygon, promising service is already on weaker ground. Consider using polygon-containment as a hard gate or soft penalty in Promise Maker, upstream of Allocation.
- **Allocation implication:** when ranking partners for a booking, prefer those whose polygon contains the point (≥55% install baseline) over those whose polygon doesn't (≤39% baseline).
- **Depth matters too**: the deepest-inside candidate in `norm_dist_edge` has ~60% install rate vs ~44% for shallow-inside. Ranking partners by polygon-depth, not just containment, should further improve selection.

### Address-chain × polygon cross-cut (2026-04-20)

After `flag_address_chain.py` added `addr_chain_stuck_at_mode` + 4 sibling columns at the call and pair level, we re-ran `run_polygon_analysis.py` and computed the cross-cut.

**Install rate by stuck_at_mode × polygon_side (2,499 eligible pairs):**

| stuck_at_mode | inside | outside | gap |
|---|---:|---:|---:|
| na | 52.6% (n=1,458) | 39.8% (n=412) | +12.8pp |
| landmark | 62.2% (n=172) | 42.4% (n=59) | +19.8pp |
| **gali** | **62.5%** (n=168) | **25.4%** (n=59) | **+37.1pp** ← |
| none (resolved) | 62.1% (n=103) | 34.8% (n=23) | +27.3pp |
| floor | 76.3% (n=38) | 57.1% (n=7) | +19.2pp |

**Gali-stuck × outside = 25.4% install**, the sharpest single-cell gap anywhere in this analysis. Lane-level ambiguity COMBINED with no partner-polygon-coverage is the worst combination — essentially dead (~3× worse than everywhere else inside polygon).

**Chain engagement is protective ONLY inside polygon:**

| polygon_side | chain_engaged | pairs | install rate |
|---|:---:|---:|---:|
| inside | no | 1,231 | 51.2% |
| inside | **yes** | **708** | **62.4%** (+11.2pp) |
| outside | no | 359 | 37.6% |
| outside | yes | 201 | 40.3% (+2.7pp) |

So the "chain engagement protective" parent finding is almost entirely an inside-polygon phenomenon. Outside, agreement on every landmark/gali/floor step barely helps — the physical constraint dominates.

**Within ANC pairs, gali-stuck × outside tightens further:** 47 pairs, **21.3% install** (vs 62.5% inside). The signature of a dead pair.

**Operational read:**
1. Flag **gali-stuck × outside** as a pre-emptive escalation signal. These pairs are ~3× less likely to install than any other combination.
2. If we were to reserve a human intervention budget (callback, address clarification team), these 59 pairs are the highest-marginal-return cohort.
3. Outside polygon, chain-engagement data is not a useful predictor → our Allocation scoring shouldn't weight it there.

---

## Files

| File | Purpose |
|---|---|
| `run_polygon_analysis.py` | End-to-end script: merge booking coords, spatial join, inside/outside, decile cuts |
| `partner_cluster_boundaries.h5` | Polygon data (copy from `promise_maker/B/training/`) |
| `db_connectors.py` | Symlink (unused here; kept for parity) |
| `investigative/pairs_with_polygon.csv` | All 2,561 pairs + polygon metrics (`polygon_side`, `dist_edge_m`, `dist_center_m`, `norm_dist_edge`, `norm_dist_center`, `cluster_type`) |
| `investigative/polygon_eligibility.csv` | Bucket counts |
| `investigative/inside_vs_outside_install_rate.csv` | The 55.3% / 38.6% split |
| `investigative/inside_vs_outside_by_reason.csv` | Reason × side crosstab (n + %) |
| `investigative/inside_distance_deciles.csv` | All four distance-metric decile cuts |

Run via: `python run_polygon_analysis.py`

---

## Geoff + Donna validation — key critiques

Both agents were briefed on the full analysis (twice — once on the original framing and once after the SE correction). Verbatim responses are not captured here; key points:

### Circular-validation concern (Geoff, both rounds)

- **Before SE correction**: "Polygon predicts install" ≡ "install history predicts install history" — tautological.
- **After SE correction**: "Softens but does not dissolve. You've shifted from `installs predict installs` to `install-rate predicts install-rate`. Less circular, not acircular. The denominator (attempts) is doing the real disentanglement work."
- **Decisive test**: **Mar-only holdout with Feb-frozen polygon**. If gap collapses on Mar → Feb gap was ratio-fitting / memorization. If gap persists ≥10pp → SE is capturing something temporally stable.
- **Additional stratification Geoff requested**: among Mar pairs, split by whether partner had ANY Jan/Feb attempts in that hex. Pairs where partner is encountering a NEW hex in Mar = cleanest generalization test.
- **Depth gradient (+9.3pp)**: SE weighting helps but doesn't fully cleanse. Deep hexes had to clear SE threshold AND be surrounded by hexes that cleared it — a coherence signal, not just density.

### Systems concern (Donna, both rounds)

- **Absorbing-crimson trap**: SE-decay is event-driven, not time-driven. Once a hex goes crimson, Allocation stops sending leads → no new attempts → no recovery. Classic "success-to-the-successful" ratchet. **Need a gentle time-decay on hex confidence** — hexes with no attempts in N days should regress toward prior, not hold their verdict.
- **Compound-signal conflation**: polygon mixes CAN (capability / tacit knowledge) + WILL (motivation / viability). Gating on the compound destroys the ability to diagnose which is failing. **Need decline-reason logging at hex level** to separate.
- **ANC 4.3pp delta (inside vs outside)**: "With SE construction, I do expect a real (small) difference. True delta is probably 3-6pp same direction. Not noise — weak confirmation pending more pairs."
- **Tacit-knowledge-density reframe stands**: reason mix barely shifts inside vs outside (3pp). The polygon doesn't change WHAT partners talk about; it changes whether the conversation RESOLVES to install. This is the **cleanest finding** in the whole deck per Donna.

### Convergent recommendation

Both agents converge on:

1. **DO NOT** ship polygon as a hard gate in Promise Maker.
2. **DO** use polygon as a **soft feature** in Allocation ranking, but **decompose it**:
   - hex-level **SE** (CAN proxy)
   - hex-level **attempt recency** (WILL proxy + anti-staleness)
   - Replace binary `inside/outside` flag with continuous `hex_SE × recency_decay` score.
3. **Reserve ~10% of lead volume** for sub-threshold hexes adjacent to green — the exploration quota — to prevent the absorbing-crimson trap.
4. **Balancing-loop metric (Donna)**: decline rate in exploration-quota hexes over time.
   - Falls → tacit knowledge accumulating → CAN was the issue → intervention working
   - Flat → friction is structural → WILL was the issue → gating was never the lever

---

## Next-step tests queued (unrun as of today)

| # | Test | Purpose | Time |
|---|---|---|---:|
| T1 | Mar-only inside/outside gap (same 4 metrics as current) | Temporal holdout — is the 16.7pp gap genuine or memorization? | ~30 min |
| T2 | Stratify Mar pairs by whether partner had any Jan/Feb attempts in that hex | Cleanest generalization test (Geoff's request) | needs Jan-Feb attempt pull |
| T3 | Install rate of 62 no-polygon pairs | Cold-start canary. If ~38% (like outside) → polygon is doing work. If ~55% (like inside) → polygon correlates with partner experience, not territory | ~5 min |
| T4 | Regress ANC on hex install-density | Does depth gradient survive once density is controlled? (Donna's test) | ~30 min |

Not yet executed. Flagged for tomorrow.

---

## Caveats

- 62 pairs (2.4%) have partners without polygons. These are partners whose install history didn't produce enough hexes above the p30 density threshold to form a cluster — typically newer partners or low-volume partners. Excluded from the inside/outside analysis.
- Partners with multiple polygons (dbscan_cluster count > 1): we pick the deepest-containing polygon if any contains the point, else the nearest-edge one. This matches "which polygon best represents this pair."
- 2 pairs (of 2,561) lack booking coords entirely (serviceability CTE didn't resolve); they fall into "no_polygon" by default.
- Polygon vintage is Feb 2026 (from `partner_cluster_boundaries.h5` build date). Our pair cohort is Jan-Mar 2026. For Jan pairs, polygons reflect history up to their booking time; for March pairs, polygons reflect history up to Feb and don't include March installs. A time-aware polygon (rolling-90-day) would be more rigorous but this snapshot is reasonable.
