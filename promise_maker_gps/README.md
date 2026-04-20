# Promise Maker GPS — Booking-Location Signal Validation

**Engine:** Promise Maker (pre-promise)
**Parent:** `../` (`location_signal_audit/`) — one of three engine-scoped audits of location signal fidelity across Wiom's matchmaking funnel.

**Analysis periods:**
- **Stage A (GPS jitter baseline)** — **2025-09-01 → 2026-01-26** · pan-India mobiles emitting `wifi_connected_location_captured` (see `gps_jitter/`). **Complete.**
- **Stage B (booking-vs-install drift)** — **Delhi · Dec 2025 installed bookings** · booking events 2025-12-01 → 2026-01-01, install pings 2025-12-01 → 2026-02-28 (2-mo lookahead) (see `booking_install_distance/`). **First cut complete** (installed-only, non-BDO). Declined cohort comparison pending.

**Cohort (planned / in progress):** Delhi · Dec 2025 fee-captured bookings · installed + declined (Stage B), plus a wider Sep 2025 – Jan 2026 window of repeat `wifi_connected_location_captured` events for jitter-baseline estimation (Stage A, done).
**Status:** Scaffolded 2026-04-20. Stage A re-pulled and validated against Rohan's prior run (bit-exact match on 8,317 final mobiles / 20,231 subseq pings). `gps_jitter/STORY.csv` committed. `location_genie_analysis.ipynb` has **31 cells of prior work** loading a previously-exported CSV from Rohan's local machine and exploring time-bucket × area-decline, hourly GPS-accuracy vs area-decline, and the night-indoor-GPS hypothesis. That logic will inform Stage B — the referenced CSV was not portable, so Stage B's cohort will be pulled fresh via `db_connectors.py`.

---

## Where this sits in the funnel

Location signals travel through three engines. Each can corrupt or preserve the signal independently. This folder is stage 1 — the earliest stage, and the one that everything downstream inherits from:

| Stage | Sibling folder | Question |
|---|---|---|
| **1 — pre-promise** | **this folder** | **Is the booking GPS reliable at capture?** |
| 2 — post-promise, pre-acceptance | `../allocation_signal/` | Does the partner↔booking distance predict installs? |
| 3 — post-acceptance | `../coordination/` | Once the partner has accepted, where does address resolution break on the ground? |

---

## The question

**Is the booking GPS reliable at capture — before we commit to a promise?**

Promise Maker gates each lead on a **25m serviceability test**: if an installed connection or splitter point exists within 25m of the booking's lat/lng, make the promise. That test consumes a lat/lng captured at booking-fee time (`lead_state_changed` event with `lead_state = 'serviceable'`).

If the captured lat/lng has significant GPS jitter vs where the customer actually lives, every downstream decision — the 25m gate itself, the GNN's `nearest_distance` in Allocation, the partner's notification geometry in Coordination — propagates from a corrupted origin. You can't fix noise downstream that was baked in upstream.

### The methodology — two stages

You can't interpret booking-vs-install drift without first knowing the intrinsic noise floor of the measurement apparatus itself. So the analysis runs in two stages:

#### Stage A — GPS jitter baseline (intrinsic noise floor)

`wifi_connected_location_captured` is emitted every time the customer's Wiom app connects to their home's **unique SSID** — once at first install, and again whenever the customer uninstalls the app and reinstalls it (then reconnects). Same physical home, multiple GPS fixes, spread across time. That is a natural repeat-measurement experiment.

Per mobile, compute the spread of subsequent pings vs the first ping (Haversine meters). Across the population, this gives the **intrinsic GPS jitter distribution** — how much a single "ground-truth" location varies just because GPS itself is noisy.

Two cleaning rules apply before the baseline is computed:

1. **De-dup pings within 15 minutes of each other** — these are either GPS-cache hits on the device (phone returns the same cached fix) OR a known app bug that re-emits the event. They are not independent samples and would artificially tighten the baseline.
2. **Exclude pings > 250m from the first-ping location** — these almost certainly represent the customer moving homes (rent turnover is common in the Delhi cohort). That is a real location change, not jitter, and including it would artificially fatten the baseline.

The output of Stage A is a jitter distribution (p50, p95, p99). That is the floor.

#### Stage B — Booking vs install drift, net of Stage A

For each installed booking: `install_drift_meters` = Haversine(booking_lat/lng, first `wifi_connected_location_captured` ping).

Then interpret it **against the Stage A baseline**:
- Drift within Stage A's p95 jitter bound → indistinguishable from pure apparatus noise. The signal is as clean as it can physically be.
- Drift systematically wider than Stage A's bound → there is real booking-time capture error, on top of the GPS jitter. This is the Promise Maker input quality loss we care about.
- Reporting lens: `excess_drift_meters = max(install_drift_meters − p95_jitter, 0)` lets us separate "how much is the apparatus" from "how much is the process."

**Headline reads:**
- **If Stage B ≈ Stage A**: booking GPS is trustworthy given current hardware; the 25m gate is operating on the cleanest input physics allows. Promise Maker is not the leak.
- **If Stage B ≫ Stage A**: the booking-time capture itself has structural error (time-of-day effects, indoor fixes, stale caches, user-input contamination). The gate is admitting/rejecting on a corrupted coordinate regardless of how good the apparatus is, and the downstream engines inherit that corruption.

---

## Why this sibling exists now

Two upstream findings converged to make this the next workstream:

1. `../allocation_signal/` found a **448 km D10 tail** on `nearest_distance` and flagged it as likely data hygiene (Round-1 Monday action #9). That tail could be real outliers OR booking-lat/lng noise. This folder tells us which.
2. `../coordination/` found that **transcript-level address friction is flat across distance deciles** (~20% everywhere), while the dropdown signal was monotonic. If booking-GPS jitter is the dominant noise source at Promise Maker, that decile-wise flatness is mechanically expected — the capture-time error washes out the ranking.

Both findings point at the same hypothesis: the coordinate we're feeding into the ranker may not be real. That hypothesis is what this folder tests.

---

## Artifacts

| File | Role | Stage |
|---|---|---|
| `gps_jitter/` | **Stage A subfolder** — GPS jitter baseline analysis. Contains `query_getlatlong.txt` (repeat `wifi_connected_location_captured` events), pull/build/headline scripts, intermediate CSVs, and its own README. See `gps_jitter/README.md`. | A |
| `booking_install_distance/` | **Stage B subfolder** — booking-vs-install drift analysis. Installed-only, non-BDO, Delhi Dec-2025. Simpler query (`query_install_drift.txt`) than the parent's `Location capture funnel.sql`. Full funnel + deciles + excess-drift analysis, own README and `STORY.csv`. | B |
| `Location capture funnel.sql` | Parent-level Stage B reference query (installed + declined, more CTEs than Stage B currently needs). Kept for declined-cohort comparison in a later pass. `booking_install_distance/query_install_drift.txt` is the simpler installed-only derivative currently in use. | B |
| `location_genie_analysis.ipynb` | Notebook — contains 31 cells of prior work by Rohan exploring time-bucket × area-decline, hourly GPS-accuracy vs area-decline, and the night-indoor-GPS hypothesis. Loads a locally-exported CSV not portable to this machine. The cohort needs to be **re-pulled** via `db_connectors.py`; prior logic can be reused once the dataframe is rebuilt. | A+B |
| `db_connectors.py` | Shared Snowflake connector (same as sibling folders). Also copied into `gps_jitter/` for self-contained Stage A runs. | — |

---

## Source events — mapping to what each lat/lng represents

| Event | What the lat/lng here represents |
|---|---|
| `lead_state_changed` · `lead_state = 'serviceable'` | Booking-time GPS — the lat/lng Promise Maker actually sees and gates on |
| `location_accuracy_captured` | Device-reported GPS accuracy in meters — the phone's own confidence in the fix it returned |
| `wifi_connected_location_captured` | Customer's phone GPS at the moment the Wiom app connects to the home's **unique SSID** (unique per household, broadcast by the Wiom router). Emitted on *every* such connection — first install AND every subsequent reinstall/reconnect. This is the repeat-measurement that makes jitter estimation possible. |

### Why `wifi_connected_location_captured` fires multiple times per mobile

- **First fire**: when the customer's Wiom app connects to the home SSID for the first time after installation. This is the Stage B ground-truth proxy.
- **Subsequent fires**: customer uninstalls the Wiom app (phone replacement, troubleshooting, app storage cleanup, etc.) and later reinstalls it. When the app reconnects to the same home SSID, the event fires again — with a fresh GPS fix from wherever the phone happens to be at reconnection time. These are Stage A's repeat samples.

### Cleaning rules before Stage A treats pings as independent samples

1. **15-minute dedup.** Within any 15-minute window for the same mobile, collapse pings to one. These can come from (a) the phone returning a cached GPS fix rather than acquiring a fresh one, or (b) a known app-side bug where the event re-emits on the same connection. Either way, they're not independent draws and must be dedup'd before jitter is computed.
2. **250m home-move filter.** If a subsequent ping is >250m from the first ping, the customer has likely changed homes (rental turnover is common in the Delhi cohort — people move, take the Wiom service with them via relocation, and the app re-emits the event from the new home). Exclude these pings from the jitter distribution; keep them aside as their own (small, interesting) cohort for measuring relocation rate.

Only `installed` leads have a non-null `install_drift_meters` (no install event → no first ping → no ground truth). Declined leads are useful for distributional comparison on the input side (booking_accuracy, time_bucket), even without ground truth — see Open questions below.

---

## Headline metrics

Two distributions, compared against each other:

**Stage A — `jitter_meters` (per ping beyond the first, per mobile):**
Haversine(first ping, subsequent ping) across all `wifi_connected_location_captured` events for that mobile, after the 15-min dedup and 250m home-move filter. Aggregated across population → noise-floor distribution with p50, p95, p99.

**Stage B — `install_drift_meters` (per installed booking):**
Haversine(booking_lat/lng at `lead_state = 'serviceable'`, first-ping install_lat/lng). Interpret against Stage A.

**Derived — `excess_drift_meters`:**
`max(install_drift_meters − p95_jitter, 0)`. This isolates the booking-time capture error from the apparatus noise — it's the part of the drift that Promise Maker could, in principle, address via upstream fixes.

Slices planned on Stage B + excess_drift:
- **Drift decile** (D1 tightest → D10 noisiest) — how fat is the tail? What fraction exceeds 25m? What fraction exceeds 25m *after* subtracting jitter?
- **Time-of-day bucket** — `time_bucket` column in the SQL (night `22-04_at_home`, early `04-06`, morning `06-09`, workday AM `09-13`, afternoon `13-16`, evening `16-19`, night `19-22`). Hypothesis: late-night indoor captures are noisier. The notebook has prior exploration of this — worth validating against the rebuilt dataframe.
- **Booking accuracy decile** — does the phone's self-reported `booking_accuracy` predict actual `install_drift_meters`? If yes → cheap feature Promise Maker could consume at gate time. If no → the self-report is noise; need a stronger validator.
- **Installed vs declined** — compare `booking_accuracy` distribution across cohorts (declined leads lack install ground truth, but their booking-side inputs are still observable).

---

## Open questions (pre-analysis)

1. **Direct gate test**: what fraction of installed bookings have `install_drift_meters > 25m`? Every one of these is a lead where the 25m gate, applied at booking time, was operating on a lat/lng that was itself >25m from where the customer actually lives. That's a structural falsification of the gate's precondition.
2. **Time-of-day effect**: does the `time_bucket` segmentation reveal the indoor-GPS hypothesis? If late-night captures are systematically worse, the fix is upstream (force re-capture, prompt to step outside, reverse-geocode against pincode).
3. **Self-report calibration**: is `booking_accuracy` (device meters-of-accuracy self-report) correlated with `install_drift_meters`? If yes → gate on it. If the correlation is weak or absent, the self-report is noise and we need a stronger validation signal (e.g., pincode reverse-geocode cross-check, Donna's neighborhood-memory artifact from `../coordination/`).
4. **Cohort drift asymmetry**: are declined bookings more concentrated in high-drift regions than installed ones? Would suggest Promise Maker is admitting GPS-noisy leads that then fail Allocation or Coordination downstream — a systematic leak between engines.

---

## How this connects back upstream

If the drift distribution is wide, the implications cascade:

- **Allocation signal** (`../allocation_signal/`) — the D10 tail is partially / wholly a GPS-jitter artifact. Current recommendation there (distance-based refusal primitive at ~50km, Monday action #2) may be cutting on a noisy coordinate, not a true partner-reach problem. Gate tightness should be tuned *after* drift is bounded, not before.
- **Coordination** (`../coordination/`) — the flat transcript-level address-friction signal across deciles is consistent with upstream GPS noise washing out decile ordering. Gali-level address capture interventions (the headline intervention proposed there) may be under-leveraged if the root cause is that the partner arrives at the wrong block entirely.
- **GNN retrain label contamination** — if drift correlates with splitter-share (the `../allocation_signal/` tenure-gap H2 finding), the gamer population may also be submitting booking lat/lngs with systematic offsets. That's a second label-contamination channel the GNN cannot defend against on its own.

---

## Status

- [x] Stage A query drafted (`gps_jitter/query_getlatlong.txt` — repeat `wifi_connected_location_captured` events, **2025-09-01 → 2026-01-26**)
- [x] Stage B cohort SQL drafted (`Location capture funnel.sql`, **Delhi · Dec 2025 fee-captured bookings**)
- [x] Prior exploratory work exists in `location_genie_analysis.ipynb` (31 cells by Rohan, local CSV path — not portable; to be reused as logic, not as data)
- [x] Stage A scaffolded into `gps_jitter/` subfolder (2026-04-20) — own README, pull script, investigations/
- [x] Stage A — data re-pulled and pipeline run. v4 cohort = **8,317 mobiles / 20,231 subseq pings**. Bit-exact match with Rohan's prior notebook. Per-ping p50 = 7.7m, p95 = 154.8m. 70% of mobiles have max_dist ≤ 25m. See `gps_jitter/STORY.csv`.
- [x] Stage B (installed-only first cut) — Delhi Dec-2025, non-BDO. Clean cohort = **3,855 installed bookings**. Drift p50 = 22.5m, p75 = 162.7m, p95 = 767.2m. **25.7% of installs have drift beyond Stage A p95** (structural capture error). See `booking_install_distance/STORY.csv`.
- [ ] Stage B (declined comparison) — pull declined cohort, compare booking-side distributions (`booking_accuracy`, `time_bucket`) against installed. Confirm whether Promise Maker admits noisier GPS more than it declines.
- [ ] Stage B slices — drift × `time_bucket` (night-indoor hypothesis), drift × `booking_accuracy` (self-report correlation). Isolate >10km tail.
- [ ] Stage B — compute `install_drift_meters`, then `excess_drift_meters` net of Stage A p95
- [ ] Slice both (drift decile, time-of-day, booking_accuracy decile, installed-vs-declined)
- [ ] Findings written to `STORY.csv` (matching sibling convention)
- [ ] Results cross-linked back into sibling READMEs
- [ ] Joint story across all three engines (this folder + `allocation_signal/` + `coordination/`) — **to be assembled by `story_teller_part1` session once Stage A + B findings land**

---

## Timeline

| Date | Event |
|---|---|
| 2026-04-20 | Subfolder scaffolded as part of `location_signal_audit/` restructure. Previously `input_validations/`; renamed by engine. Parent renamed from `location_accuracy/` to reflect the three-engine funnel scope. |
| 2026-04-20 | README updated with two-stage methodology (Stage A jitter baseline via repeat `wifi_connected_location_captured` events, Stage B booking-vs-install drift net of jitter), cleaning rules (15-min dedup + 250m home-move filter), event semantics, and corrected role of `query_getlatlong.txt` as the Stage A query. Notebook flagged as containing prior exploratory work on non-portable CSV. |
| 2026-04-20 | Stage A work isolated into `gps_jitter/` subfolder (own README, `query_getlatlong.txt` moved there, `db_connectors.py` copied, `investigations/` created, `pull_wifi_pings.py` scaffolded). Keeps Stage A self-contained for a future session to pick up without re-deriving context. |
| 2026-04-20 | Stage A pipeline run end-to-end — 8,317 mobiles / 20,231 subseq pings in v4 cohort, bit-exact match with Rohan's prior notebook. Per-ping p95 jitter = 154.76m locked in as Stage B subtraction floor. `gps_jitter/STORY.csv` committed (Stage A narrative, 389 rows). |
| 2026-04-20 | Stage B scaffolded into `booking_install_distance/` subfolder. Simpler query (`query_install_drift.txt`) — installed-only, non-BDO, Delhi Dec-2025. Pulled 9,749 rows; clean cohort = 3,855 after BDO drop + null-coord drop. **Drift p50 = 22.5m, p75 = 162.7m; 25.7% of installs have drift beyond Stage A p95 (structural capture error).** `booking_install_distance/STORY.csv` committed. Reference bands relabeled to make clear they are NOT gate outcomes (the 25m gate never tests drift). |
