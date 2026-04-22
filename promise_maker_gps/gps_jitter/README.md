# GPS Jitter Baseline — Stage A of Promise Maker GPS Audit

**Parent:** `../` (`promise_maker_gps/`) — see parent README for the full two-stage methodology (Stage A jitter baseline + Stage B booking-vs-install drift).
**Scope of this folder:** Stage A only — estimate the intrinsic noise floor of the GPS apparatus itself, using `wifi_connected_location_captured` as a repeat-measurement experiment.

**Analysis period:** **2025-09-01 → 2026-01-26** (query date range — every `wifi_connected_location_captured` event emitted in this window is the input).
**Cohort scope:** pan-India mobiles that emitted this event in the window (unit of analysis = mobile, not booking).
**Status:** Stage A complete as of 2026-04-20. `STORY.csv` committed. Stage B is next.
**Feeds into:** `../../master_story.md` Part A (narrative) and `../../master_story.csv` (tables A.1a per-ping quantile, A.1b per-ping decile, A.1c per-mobile worst-case). Parent synthesis; this folder is source of truth for Stage A.

---

## The question this folder answers

**How much does a GPS fix jitter when the *same home* is sampled repeatedly?**

That number is the floor. No downstream analysis of booking-vs-install drift can claim "the signal is corrupted" below this floor — it's just how GPS works.

---

## Why `wifi_connected_location_captured` works as the apparatus

Every Wiom router broadcasts a **unique SSID** (unique per household). The Wiom app emits `wifi_connected_location_captured` every time it connects to that SSID — once at first install, and again on every subsequent reinstall/reconnect (phone replacement, troubleshooting, app cleanup).

- **First ping per mobile (`row_cnt = 1`)** → the SSID-validated first fix at the home. This is the canonical anchor — location confirmed by SSID match, not user-stated.
- **Subsequent pings (`row_cnt ≥ 2`)** → same physical home, later moment, fresh GPS fix. The spread of these vs the anchor, across the population, *is* the apparatus noise floor.

Anchoring on `row_cnt = 1` is deliberate: it's the earliest validated fix, taken at install time when conditions are typically most favorable. Later fixes sample the same home under varied conditions (indoor, late-night, low battery, cache hit) — exactly the noise surface we want to characterize.

---

## Cleaning rules (before pings are treated as independent samples)

| # | Rule | Reason |
|---|---|---|
| 1 | **15-min dedup** — within any 15-min window for the same mobile, keep only the earliest ping | Phone can return a cached GPS fix; app has a known re-emit bug on the same connection. Not independent draws. |
| 2 | **250m home-move cap** — drop any subsequent ping > 250m from the anchor | Delhi cohort has high rental turnover; >250m is almost certainly a home change, not jitter. Real location change, not apparatus noise. |
| 3 | **≥2 surviving pings per mobile** | A mobile with only the anchor contributes nothing to the jitter distribution. |

The 0m spike gets its own diagnostic cut (cache-hit detection by time-gap bucket) — drives rule 1.

---

## Headline metrics

**Per-ping jitter distribution** (across all surviving subsequent pings, all mobiles):
- `p50 / p75 / p95 / p99` of `haversine(anchor, subsequent_ping)` in meters.
- **p95** is the operational threshold used downstream in Stage B: `excess_drift = max(install_drift − p95_jitter, 0)`.

**Per-mobile uncertainty radius** (operational bound per mobile):
- For each mobile, `max_dist_m = max(haversine(anchor, each subsequent ping))`.
- Across mobiles, report `p50 / p75 / p95 of max_dist_m`.
- **p75 of `max_dist_m`** is the headline: "for 75% of mobiles, the worst jitter fix is within X meters of the true home." This is the radius Promise Maker can trust even on a bad single reading.

---

## Artifacts

| File | Role |
|---|---|
| `query_getlatlong.txt` | Snowflake query. Pulls every `wifi_connected_location_captured` event per mobile between **2025-09-01 and 2026-01-26**, with `row_number() over (partition by mobile order by added_time) as row_cnt`. |
| `db_connectors.py` | Shared Snowflake connector (copied from sibling folders — key-pair auth). |
| `pull_wifi_pings.py` | Runs the query, writes `investigations/wifi_pings_raw.csv`. Prints row counts, unique mobiles, date range. |
| `build_jitter.py` | Loads raw → builds v1 (anchor + haversine) → v2 (+ time gap) → v3 (15-min dedup) → v4 (250m cap). Writes per-step CSVs and a funnel-attrition table. |
| `headline_jitter.py` | Reads v4, prints and saves decile + quantile tables for per-ping, max_dist, median_dist. Confirms every v4 mobile has ≥3 total pings. |
| `build_jitter_ge5.py` | Sensitivity cut restricted to mobiles with ≥5 total pings (≥4 subsequent). Emits side-by-side comparison vs v4. |
| `build_jitter_consecutive.py` | Consecutive-ping distance (temporal-correlation companion). Reuses v4 cohort, computes haversine between temporally-adjacent pings. Emits deciles, quantiles, and consec-vs-anchor comparison. |
| `write_story.py` | Assembles `STORY.csv` — full narrative, sections 1–13, sourced from intermediate CSVs. |
| `STORY.csv` | Human-readable narrative of Stage A findings. This is the handoff artifact for future sessions. |
| `investigations/` | Intermediate CSVs — raw pings, pairs, per-mobile aggregates, funnel attrition, decile/quantile tables, GE5 comparison. |

---

## Funnel discipline

Every script prints attrition in ALL-CAPS breadcrumbs so any intermediate count can be tied back to the source:

```
RAW PINGS              : N_raw
UNIQUE MOBILES (raw)   : M_raw
AFTER ≥3 pings filter  : N1, M1  (M1 / M_raw = X%)
AFTER 15-min dedup     : N2, M2
AFTER 250m cap         : N3, M3
FINAL PAIRS (v4)       : N_v4 across M_v4 mobiles
```

`investigations/jitter_funnel.csv` stores the same table for `STORY.csv` to consume.

---

## Status

- [x] Folder scaffolded, query moved here, connector copied (2026-04-20)
- [x] `pull_wifi_pings.py` — 278,986 raw pings / 145,355 unique mobiles (2026-04-20)
- [x] `build_jitter.py` — v1 → v4 pipeline. Final v4 = **8,317 mobiles / 20,231 subseq pings**. Reproduces Rohan's notebook bit-for-bit.
- [x] `headline_jitter.py` — deciles + quantiles for per-ping, max_dist, median_dist
- [x] `build_jitter_ge5.py` — sensitivity cut on mobiles with ≥5 total pings (736 mobiles)
- [x] `build_jitter_consecutive.py` — consecutive-ping distribution; uniformly tighter than anchor-based across every percentile (temporal-correlation signature)
- [x] `write_story.py` — `STORY.csv` committed (Stage A narrative, 389 rows)
- [ ] 0m-spike diagnostic (A2) — cache vs stable-GPS decomposition by time-gap bucket
- [ ] Mobile bimodality segmentation (A3) — "clean" (median_dist ≤ 10m) vs "drifty" (> 50m) labels for Stage B

## Headline numbers (v4 cohort, n = 8,317 mobiles / 20,231 subseq pings)

### Anchor-based jitter — used for Stage B subtraction

| Metric | Value | Interpretation |
|---|---|---|
| Per-ping **p50** jitter | 7.7 m | Half of independent GPS fixes land within 7.7m of anchor. Core apparatus is tight. |
| Per-ping **p95** jitter | **154.8 m** | **Stage B threshold.** Any booking-vs-install drift < 155m is indistinguishable from apparatus noise. |
| Per-mobile **p75** `max_dist_m` | 31.8 m | For 75% of mobiles, the *worst* single fix stays within ~32m. |
| Mobiles with max_dist ≤ 25m | **5,821 / 8,317 (70.0%)** | 70% of devices clear the Promise Maker 25m gate on their worst recorded fix. |
| Per-mobile **p75** `median_dist_m` | 20.7 m | For 75% of mobiles, the *typical* drift is within ~21m. |

### Consecutive-ping jitter — temporal-correlation companion (n = 20,231 consec pairs)

| Metric | Anchor-based | Consecutive | Gap |
|---|---:|---:|---:|
| p50 | 7.7 m | **5.9 m** | −23% |
| p75 | 20.0 m | **14.9 m** | −25% |
| p90 | 88.6 m | **49.8 m** | −44% |
| p95 | 154.8 m | **110.6 m** | −29% |
| Pairs within 25m | — | **16,962 / 20,231 (83.8%)** | — |

Consecutive-ping distance is uniformly tighter than anchor-based across every percentile. This is the signature of **temporal correlation in GPS noise**: temporally-adjacent fixes share recent satellite geometry / multipath conditions, so their errors correlate. Over long anchor gaps (days to months) those correlations break and errors compound independently.

**Why anchor-based p95 (154.8m) remains the Stage B threshold — not consec p95 (110.6m):** booking lat/lng is captured at fee-capture time; install lat/lng is captured at the first `wifi_connected_location_captured` event. Those are separated by **days** (fee capture → scheduling → install). The relevant noise model for a days-apart comparison is long-gap drift, not consecutive-reading precision.

The consec distribution is the complementary story: **the apparatus itself is tight** (p50 = 5.9m, 84% within 25m). The problem downstream is not instantaneous hardware noise — it's day-to-day drift.
