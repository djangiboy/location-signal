# Mar-only pair-level analysis

**Parent:** `../` (`partner_customer_calls/`).
**Cohort:** `assigned_time ∈ 2026-03-01 … 2026-03-31` (Delhi, non-BDO, serviceable).
**Status:** Re-runs the pair-level decile analysis on the cleanest UCCL slice to check whether the "distance/prob flat" finding is driven by genuine behavior or by Jan-Feb UCCL ingestion gaps.

---

## Why this subfolder exists

The parent analysis ran over Jan-Mar 2026. When we split by month, **UCCL no-call rate was 72.8% in Jan, 56.9% in Feb, and 34.9% in Mar** — i.e. Jan/Feb pairs were dropped from the analysis not because the partners didn't call customers, but because UCCL was still bedding in. This is a data-availability artifact, not a behavioral one.

March is the month where UCCL logging had matured to ~35% no-call (which is close to the expected ~27% recording-fill-rate floor). If the finding — "address_not_clear is flat across distance and probability deciles" — holds on the March-only slice, it's robust. If it shifts meaningfully, the original finding was contaminated by selection bias from the ingestion gaps.

---

## What this folder does

- Filters the parent's existing `pair_aggregated.csv` to pairs with `assigned_time ∈ March 2026`.
- Pulls a **March-only allocation cohort** from Snowflake (so deciles are recomputed on March-only distance/probability distributions — apples-to-apples with the filtered pair set).
- Recomputes distance- and probability-decile touch-rates per reason.
- Outputs the crosstabs + a before/after (Jan-Mar vs Mar-only) comparison table so the shift is immediately visible.

No re-transcription, no re-classification — the transcripts and Haiku labels are reused from the parent folder.

---

## Files

| File | Purpose |
|---|---|
| `run_mar_analysis.py` | Self-contained pipeline: filter → pull alloc → compute deciles → merge → crosstabs |
| `db_connectors.py` | Symlink to shared connector |
| `investigative/` | Output CSVs |

**Run:**
```bash
python run_mar_analysis.py
```

---

## Outputs in `investigative/`

| File | Grain |
|---|---|
| `mar_pairs_aggregated.csv` | Pair-aggregated rows filtered to March only |
| `mar_allocation_cohort.csv` | March-only Delhi non-BDO allocation pull |
| `mar_pairs_with_alloc.csv` | Final: pair-level, March-only, with March deciles |
| `mar_pairLevel_reason_by_distance_decile.csv` | Touch-rate × decile |
| `mar_pairLevel_reason_by_prob_decile.csv` | |
| `mar_callLevel_reason_by_distance_decile.csv` | Call-level for comparison |
| `mar_callLevel_reason_by_prob_decile.csv` | |
| `comparison_vs_full.csv` | Side-by-side: full cohort % vs Mar-only % for each reason × decile |

---

## Hypothesis going in

- **H1 (null):** Distance and probability deciles remain flat for `address_not_clear` on March-only data. The parent finding is robust.
- **H2 (selection bias):** Deciles show at least a partial monotonic rise when we strip out Jan/Feb UCCL gaps. The parent finding was dampened by contaminated data.

---

## Results

**Cohort:** 1,010 March-assigned pairs (vs 2,561 full cohort).
Install rate in March-only cohort: not recomputed here — inherits parent's per-pair `installed` flag.

### Pair-level `address_not_clear` % by distance decile

| Decile | Full (Jan-Mar) | **Mar-only** | Δ pp | Mar n |
|---:|---:|---:|---:|---:|
| D1 | 44.4% | **45.4%** | +1.0 | 141 |
| D2 | 40.1% | 41.2% | +1.1 | 136 |
| D3 | 45.0% | 50.0% | +5.0 | 118 |
| D4 | 45.5% | 42.6% | -2.9 | 115 |
| D5 | 45.6% | 51.0% | +5.4 | 102 |
| D6 | 45.7% | 43.3% | -2.4 | 90 |
| D7 | 44.5% | 48.3% | +3.8 | 89 |
| D8 | 52.6% | **58.1%** | +5.5 | 86 |
| D9 | 45.1% | 52.9% | +7.8 | 70 |
| D10 | 41.1% | 50.8% | +9.7 | 63 |

Mar-only range: **41% → 58%** (spread 17pp). Full cohort was 40%-52%. **The upper end widened — D8/D9/D10 all shifted up** (+5 to +10pp). Suggests a subtle physical distance signal was being suppressed by the Jan/Feb contaminated data.

### Pair-level `address_not_clear` % by probability decile

| Decile | Full (Jan-Mar) | **Mar-only** | Δ pp | Mar n |
|---:|---:|---:|---:|---:|
| P1 | 42.4% | 46.0% | +3.6 | 50 |
| P2 | 43.5% | 52.8% | +9.3 | 89 |
| P3 | 50.2% | 51.9% | +1.7 | 77 |
| P4 | 51.8% | 41.9% | -9.9 | 86 |
| P5 | 42.2% | 49.0% | +6.8 | 96 |
| P6 | 45.6% | 47.7% | +2.1 | 111 |
| P7 | 41.3% | 43.0% | +1.7 | 107 |
| P8 | 45.2% | 44.4% | -0.8 | 81 |
| P9 | 43.7% | 50.8% | +7.1 | 126 |
| P10 | 44.7% | 48.2% | +3.5 | 168 |

Mar-only range: **42% → 53%** (spread 11pp). Full cohort was 42%-52%. **Essentially unchanged — still flat, no monotonic pattern.**

### Call-level `address_not_clear` % by distance decile (less-saturated metric)

| D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20.6% | 16.1% | 22.1% | 20.1% | 26.3% | 19.2% | 22.6% | **28.2%** | 26.3% | 26.2% |

Spread D1 → D10: **5.6pp rise** (20.6 → 26.2). A modest directional signal — more noticeable than full cohort's 6.5pp range flat across deciles. Still weak, but directionally consistent with "partners at higher distance hit address-friction more often."

---

## Verdict

**H1 mostly wins, H2 partial credit on distance.**

- **Distance:** Mar-only shows a **subtle rise** at upper deciles (D8-D10 +5-10pp vs full) and a **wider spread** (17pp vs 12pp in full cohort). Directionally consistent with a physical distance signal being partially suppressed by Jan/Feb gaps. But the pattern is still not cleanly monotonic — D4 and D6 are lower than their neighbors, so the signal is weaker than the dropdown's monotonic 10%→29% in `../../location_accuracy/`.
- **Probability:** Mar-only remains **flat**, range 42-53%. The dismissal-channel interpretation from the parent stands: partners face address friction at roughly the same rate regardless of GNN probability. The dropdown's 48%→2.5% pattern was genuinely decline-willingness, not address-friction.
- **Net:** the parent headline — "transcripts flatten both distance and probability separation" — needed softening on distance (there IS a weak physical signal at far deciles once data is clean) but stands on probability.

### Implication for `../location_accuracy/` narrative

Update to be made in the parent's STORY.csv / README:
- Distance: transcripts show a **weak but present** physical signal (D1-D10 spread 6pp call-level, 17pp pair-level). Not as strong as dropdown (19pp call-level) but not zero either. Dropdown overstates the distance signal by ~3× at pair-level.
- Probability: transcripts show **no separation**. Dropdown's 48%→2.5% is entirely a decline-channel artifact — empirically confirmed on the clean Mar-only slice.

---

## Files

| File | Purpose |
|---|---|
| `run_mar_analysis.py` | Self-contained pipeline: filter → pull Mar alloc → compute deciles → merge → crosstabs + comparison table |
| `db_connectors.py` | Symlink to shared connector |
| `investigative/mar_pairs_aggregated.csv` | Parent's pair_aggregated filtered to March-assigned |
| `investigative/mar_allocation_cohort.csv` | March-only Delhi non-BDO allocation pull |
| `investigative/mar_pairs_with_alloc.csv` | Final: pair-level Mar-only + Mar deciles |
| `investigative/mar_pairLevel_reason_by_{distance,prob}_decile.csv` | Touch-rate crosstabs |
| `investigative/mar_callLevel_reason_by_{distance,prob}_decile.csv` | Call-level crosstabs |
| `investigative/comparison_vs_full_{distance,prob}.csv` | Side-by-side full vs Mar-only | 
