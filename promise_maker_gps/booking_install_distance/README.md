# Booking vs Install Distance — Stage B of Promise Maker GPS Audit

**Parent:** `../` (`promise_maker_gps/`) — see parent README for the full two-stage methodology.
**Scope of this folder:** Stage B only — measure the drift between the **booking lat/lng** (the coordinate Promise Maker actually gates on at `lead_state = 'serviceable'`) and the **install lat/lng** (the first `wifi_connected_location_captured` fix after install). Net of Stage A's apparatus noise floor.

**Analysis period:**
- **Booking events**: **2025-12-01 → 2026-01-01** (Delhi, `lead_state_changed` where `lead_state = 'serviceable'` for `booking_lat/lng`; same window for `booking_verified` for `fee_captured_at`).
- **Install pings**: **2025-12-01 → 2026-02-28** (2-month lookahead so late installs aren't missed; first `wifi_connected_location_captured` event per mobile, post-install).
- **Cohort**: Delhi · Dec 2025 fee-captured bookings · `lead_state = 'installed'` · Python-side filtered to `bdo_lead = 0`.
- **Status**: scaffolded 2026-04-20. Query drafted. Not yet pulled.
- **Feeds into:** `../../master_story.md` Part D.A (narrative) and `../../master_story.csv` (tables D.A drift decile, D.A drift quantile, D.A Stage A vs Stage B ratio, D.A drift decomposition by cause). Parent synthesis; this folder is source of truth for Stage B.

---

## The question

**How reliable is `booking_lat/lng` as an input to downstream matchmaking systems?**

Stage A gave us the intrinsic noise floor: per-ping **p95 = 154.8m** (days-apart drift). Any booking-vs-install drift *below* 154.8m is indistinguishable from apparatus noise. Drift *above* 154.8m is structural — the booking-time capture itself was wrong.

### IMPORTANT framing — what the 25m Promise Maker gate does NOT test

The gate's rule is:

```
distance(booking_lat/lng, nearest historical install or splitter) <= 25m → pass
```

It tests the booking coordinate against the **infrastructure graph**. **It does not test drift.** Drift is invisible to the gate itself.

What Stage B measures is **input quality loss** — how far `booking_lat/lng` is from the SSID-validated true home. Every downstream consumer that trusts `booking_lat/lng ≈ true home` (Promise Maker's 25m ball, Allocation GNN's `nearest_distance`, partner navigation) operates on a point that drifts from ground truth by this amount. The gate's 25m ball is *centered* on the booking coord — if the booking coord is 100m off, the gate's 25m search is centered 100m from the true home.

---

## Why installed-only

Stage B needs ground truth for the "real" home location. The first `wifi_connected_location_captured` event — fired when the customer's Wiom app connects to the household's unique SSID after install — is the SSID-validated fix at the real home. Declined leads never install, so they have no ground-truth fix. Declined is still useful for distributional comparisons on *booking-side* fields (`booking_accuracy`, `time_bucket`) but cannot contribute to the drift metric.

---

## Methodology — what counts as "drift"

For each installed booking:

```
install_drift_m = haversine(
    booking_lat, booking_lng,        -- from lead_state='serviceable' event
    install_lat, install_lng         -- from first wifi_connected_location_captured
)
```

Then:
```
excess_drift_m = max(install_drift_m - 154.76, 0)
```
where **154.76 m = Stage A per-ping p95** (see `../gps_jitter/STORY.csv` · section 6).

`excess_drift_m = 0` → drift indistinguishable from apparatus noise. Promise Maker is fine.
`excess_drift_m > 0` → drift is structurally larger than what GPS can explain. Real capture error exists.

---

## `bdo_lead` filter

BDO bookings (ops-captured) follow a different journey from self-serve, so convention across all sibling folders is to restrict to `bdo_lead = 0`. The filter is Python-side (after the pull) so the funnel is fully visible — raw → non-BDO counts both logged in `investigations/drift_funnel.csv`.

`bdo_lead` is computed SQL-side via a `LEFT JOIN` with `bdo_mobiles` (mobiles that appeared in `event_name = 'prospect_identified'` within the cohort window).

---

## Artifacts

| File | Role |
|---|---|
| `query_install_drift.txt` | Snowflake query. Simpler than the parent's `Location capture funnel.sql` — installed-only, no decline CTEs. Pulls booking lat/lng, install lat/lng, booking_accuracy, bdo_lead, time_bucket, and haversine `install_drift_m`. |
| `db_connectors.py` | Shared Snowflake connector (copied from sibling folders — key-pair auth). |
| `pull_install_drift.py` | Runs the query, writes `investigations/install_drift_raw.csv`. Prints row counts, BDO mix, column coverage, quick drift quantiles tied back to total. |
| `build_drift.py` | *(next)* Python-side funnel: drop bdo_lead=1, drop null-coord rows. Compute `excess_drift_m = max(install_drift_m - 154.76, 0)`. Decile and quantile the full distribution. |
| `headline_drift.py` | *(next)* Final headline numbers: % installs with drift > 25m, % with drift > Stage A p95, distribution against `time_bucket`, correlation with `booking_accuracy`. |
| `write_story.py` | *(later)* Assembles `STORY.csv` for this folder. |

---

## Funnel discipline

Every script prints attrition in ALL-CAPS breadcrumbs so any intermediate count ties back to the raw cohort:

```
RAW PULL                   9,749   Delhi Dec-2025 installed, mobile-keyed
├─ drop bdo_lead=1         −5,840  (59.9% — ops-captured, different journey)
├─ drop null booking coords −    0
├─ drop null install coords −   54  (SSID never connected in 2mo lookahead)
└─ STAGE B CLEAN COHORT    3,855   (39.5% of raw)
    │
    │ Reference bands (NOT gate outcomes — gate never tests drift):
    ├─ A. ≤25m (within gate radius)                      : 1,987 (51.5%)
    ├─ B. 25-154.76m (within Stage A p95 jitter)         :   877 (22.7%)
    └─ C. >154.76m (structural booking-capture error)    :   991 (25.7%)
```

`investigations/drift_funnel.csv` stores the attrition table for `STORY.csv` to consume.

## Headline numbers (clean cohort, n = 3,855 installed non-BDO bookings)

### Drift distribution

| Quantile | `install_drift_m` |
|---:|---:|
| p50 | **22.5 m** |
| p75 | **162.7 m** |
| p90 | 478.6 m |
| p95 | 767.2 m |
| p99 | 2,870.8 m |
| max | 213,846 m (≈ 213 km — data hygiene tail, wrong-city booking) |

### Stage A vs Stage B — same quantile, different reference frame

| Quantile | Stage A per-ping jitter | Stage B booking→install drift | Stage B / Stage A |
|---:|---:|---:|---:|
| p50 | 7.66 m | 22.52 m | **2.9×** |
| p75 | 19.98 m | 162.65 m | **8.1×** |
| p95 | 154.76 m | 767.16 m | **5.0×** |
| p99 | 227.89 m | 2,870.83 m | **12.6×** |

Stage B is uniformly wider than Stage A at every quantile. The booking-capture process adds structural error on top of apparatus noise across the entire distribution, not just in the tail.

### Excess drift — what Stage A subtraction reveals

`excess_drift_m = max(install_drift_m − 154.76, 0)`

- **74.3% of installs (2,864)** have `excess_drift_m = 0` — drift is fully absorbed by Stage A apparatus noise.
- **25.7% of installs (991)** have `excess_drift_m > 0` — the booking coordinate was structurally wrong beyond anything GPS physics alone can produce. Median excess = 186 m, p95 excess = 612 m, p99 excess = 2,716 m.

### Data-hygiene tail

- **124 installs (3.2%)** have drift > 1 km
- **16 installs (0.4%)** have drift > 10 km
- Max drift = 213 km (almost certainly a wrong-city booking; worth isolating before any retrain that consumes `booking_lat/lng` as a feature)

## Verdict — the leak is upstream

- **Stage A**: apparatus is tight. Two fixes of the same home land within 5.9m (consec p50) or 7.7m (anchor p50). Hardware is not the bottleneck.
- **Stage B**: booking capture is not tight. p50 drift 22.5m, p75 162.7m — 3-8× wider than Stage A at corresponding quantiles.
- **Conclusion**: ~26% of bookings have booking coords that are wrong for reasons GPS cannot explain. Process/UI/user-behavior error at the moment of booking, not GPS physics. Fixable upstream via pincode cross-check, force re-capture on low `booking_accuracy`, map-pin confirmation with landmarks.

---

## Status

- [x] Folder scaffolded (2026-04-20)
- [x] `query_install_drift.txt` drafted — simpler than parent `Location capture funnel.sql`, installed-only, `bdo_lead` as column
- [x] `pull_install_drift.py` — 9,749 raw rows pulled; 98.6% install-coord coverage; clean
- [x] `build_drift.py` — clean cohort = 3,855 non-BDO installs; drift p50 = 22.5m, p75 = 162.7m, p95 = 767.2m; 25.7% have drift beyond Stage A apparatus noise
- [x] `write_story.py` — `STORY.csv` committed (Stage B narrative, 222 rows)
- [ ] `headline_drift.py` — slice by `time_bucket`, correlate with `booking_accuracy`, isolate the >10km tail (16 mobiles)
- [ ] Cross-link to `allocation_signal/` — merge on mobile; does Stage B drift explain the 448km D10 tail on `nearest_distance`?
