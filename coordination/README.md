# Coordination — Partner ↔ Customer Call Transcription Analysis

**Engine:** Coordination (post-acceptance, pre-install)
**Parent:** `../` (`location_signal_audit/`) — one of three engine-scoped audits of location signal fidelity across Wiom's matchmaking funnel.
**Cohort:** Delhi · **Jan–Mar 2026** · non-BDO (the Dec 2025 scope used in `../allocation_signal/` could not be matched because `USER_CONNECTION_CALL_LOGS` only started populating on **2025-12-30**; see "UCCL date probe" below).
**Scale:** 4,930 unique call recordings · 2,561 (mobile, partner) pairs · 20,367 allocation cohort.
**Created:** 2026-04-19 · **Updated:** 2026-04-20
**Status:** Full end-to-end run complete (2026-04-19). V2 classifier deployed after pilot review. Address-chain classifier + findings added 2026-04-20. README / STORY updates (incl. polygon cross-cut) committed 2026-04-20 afternoon.
**Feeds into:** `../master_story.md` Part C (narrative — C.A flow, C.B primary reason + monotonicity collapse, C.C comm_quality, C.G install-time non-discrimination, C.missing data gaps) and `../master_story.csv` (tables C.B primary_reason, C.B ANC transcript rate by distance/prob decile, C.B monotonicity summary, C.C pair-level + within-ANC comm_quality, C.missing monthly no-call, D.B install-time by bucket). Parent synthesis; this folder is source of truth for Coordination.

---

## Where this sits in the funnel

Location signals travel through three engines. Each can corrupt or preserve the signal independently. This folder is stage 3:

| Stage | Sibling folder | Question |
|---|---|---|
| 1 — pre-promise | `../promise_maker_gps/` | Is the booking GPS reliable at capture? |
| 2 — post-promise, pre-acceptance | `../allocation_signal/` | Does the partner↔booking distance predict installs? |
| **3 — post-acceptance** | **this folder** | **Once the partner has accepted, where does address resolution break on the ground?** |

## Why this exists

`../allocation_signal/` found that dropdown `decision_reason` = "address_not_clear" separates **48% → 2.5% across GNN prob deciles** and 9.8% → 28.5% across distance deciles. The dropdown is what partners *click* when they decline. A click is a low-fidelity signal: two partners declining for completely different real reasons can click the same option.

> **When the partner actually spoke to the customer, what did they say?**

Transcripts are the ground truth. The question this subfolder answers: does the dropdown's decile pattern survive when we replace "partner clicked this" with "partner actually said this on the call"?

---

## End-to-end journey map

```
                                 Snowflake
                                     │
                                     ▼
    ┌──────────────────────────────────────────────────────────────┐
    │ query_pcalls.txt                query_allocation.txt         │
    │   (call manifest SQL)           (full Jan-Mar alloc cohort)  │
    └──────────────────┬──────────────────┬───────────────────────┘
                       │                  │
                       ▼                  │
            ┌───────────────────┐         │
            │  pull_calls.py    │         │
            └─────────┬─────────┘         │
                      │                   │
                      ▼                   │
           investigative/calls_manifest.csv  (6,199 rows; 4,930 unique call_ids)
                      │                   │
                      ▼                   │
            ┌───────────────────┐         │
            │ transcribe_calls  │  Exotel download (Basic auth)
            │     .py           │  → OpenAI Whisper `audio.translations`
            │  (10 workers)     │  (Hindi → English, one pass)
            └─────────┬─────────┘
                      │
                      ▼
           investigative/transcripts.csv  (4,930 unique call_ids)
                      │
                      ▼
            ┌───────────────────┐             ┌──────────────────────┐
            │ classify_reasons  │    and      │ embedding_classify   │
            │     .py           │   parallel  │     .py              │
            │ (Haiku 4.5 +      │             │ (text-embedding-3-   │
            │  regex, 10 wk)    │             │  small, 20 protos)   │
            └─────────┬─────────┘             └──────────┬───────────┘
                      │                                  │
                      ▼                                  ▼
     investigative/transcripts_classified.csv   investigative/embedding_reason_scores.csv
           (primary_reason,                    (sim_<label> × 20, emb_top1/2/3)
            secondary_reason,                   investigative/embedding_vs_haiku.csv
            llm_summary,                        (disagreement audit)
            rx_<label> × 14)
                      │
                      ▼
            ┌───────────────────┐
            │ aggregate_per_pair│
            │     .py           │  time-proximity resolution +
            │                   │  pair-level union of reasons +
            │                   │  decision_to_install_hours
            └─────────┬─────────┘
                      │
                      ▼
     investigative/calls_resolved.csv        (4,930 rows — 1 per call, correct partner)
     investigative/pair_aggregated.csv       (2,561 rows — 1 per mobile×partner pair)
                      │                                  │
                      └──────────────┬───────────────────┘
                                     ▼                                ▲
                           ┌───────────────────┐         allocation_cohort.csv
                           │ merge_with_       │        (20,367 Jan-Mar pairs, for deciles)
                           │  allocation.py    │◄───────┘
                           │                   │
                           │ deciles computed  │
                           │ over FULL 20K     │
                           │ cohort (apples    │
                           │ to location_      │
                           │ accuracy/)        │
                           └─────────┬─────────┘
                                     │
                                     ▼
     investigative/calls_with_alloc.csv       (call-level, distance+prob+nearest_type)
     investigative/pairs_with_alloc.csv       (pair-level, same + reasons_union,
                                                decision_to_install_hours)
     investigative/callLevel_reason_by_{distance,prob}_decile.csv
     investigative/pairLevel_reason_by_{distance,prob}_decile.csv
     investigative/callLevel_reason_by_nearest_type.csv
```

Run via the chain script once transcription is done:
```bash
./run_downstream.sh   # classify → embed → aggregate → merge
```

Or manually:
```bash
python pull_calls.py                  # step 1
python transcribe_calls.py --workers 10   # step 2  (resumable)
python classify_reasons.py --workers 10   # step 3
python embedding_classify.py          # step 4
python aggregate_per_pair.py          # step 5
python merge_with_allocation.py       # step 6
python show_samples_by_reason.py --n 3  # optional: eyeball check
```

---

## Files

### SQL queries

| File | Purpose | Parity with `../` |
|---|---|---|
| `query_pcalls.txt` | Call manifest: Delhi + Jan-Mar 2026 + non-BDO + `t_serviceability_logs.serviceable=TRUE` (10-day lookback) + `calls.call_time ∈ [assigned_time, +14d]` + `recording_url IS NOT NULL` | Same CTE skeleton as `../query_unified_correl.txt` (delhi_mobiles / bdo_mobiles / booking_location), adds `calls` + `scoped` |
| `query_allocation.txt` | Full Jan-Mar allocation for decile computation (~20K pairs) | Same JSON flatten of `notification_schedule` as `../query_unified_correl.txt` |

### Python pipeline

| Order | File | Core logic | Lines to validate |
|---|---|---|---|
| 1 | `pull_calls.py` | Executes `query_pcalls.txt`, writes `calls_manifest.csv` + prints cohort descriptives | — trivial — |
| 2 | `transcribe_calls.py` | Exotel download with `requests.get(..., auth=(EXOTEL_SID, EXOTEL_TOKEN))`, OpenAI Whisper `audio.translations` (Hindi→English in one pass). `ThreadPoolExecutor(--workers)`. Resumable via `call_id` dedupe. | `_exotel_auth`, `transcribe_openai`, `process_one`, `main` |
| 3 | `classify_reasons.py` | Claude Haiku 4.5 with cached system prompt (20 labels + disambiguation + few-shot). Per-call output: `primary_reason`, `secondary_reason`, `llm_summary`. Regex pre-pass (14 flags, `rx_<label>` columns). | `LABELS`, `REGEX_BY_LABEL`, `SYSTEM_PROMPT` (lines ~170-270), `_classify_one` |
| 4 | `embedding_classify.py` | OpenAI `text-embedding-3-small`. One prototype text per label. Cosine similarity matrix → top-3 reasons per transcript. Cross-check vs Haiku, output disagreement audit. | `REASON_PROTOTYPES` dict (lines 55-155), `cosine_matrix`, `main` |
| 5 | `aggregate_per_pair.py` | **(a)** `resolve_call_to_partner` picks the partner with most-recent `assigned_time` before `call_time` (fixes SQL join duplication). **(b)** `groupby(mobile, partner).apply(agg)` — union of reasons, raw transcripts (concat `" ||| "`), Haiku summaries (`"|"`), timestamps, `decision_to_install_hours = (installed_time - decision_time)/3600`. | `resolve_call_to_partner`, `agg` closure |
| 6 | `merge_with_allocation.py` | Pulls `query_allocation.txt` → 20K pairs. Computes distance + prob deciles over **full** cohort via `pd.qcut`. Merges both call-level and pair-level. For pair-level, explodes `reasons_union` so counts = "pairs that TOUCHED reason X". | `pct_crosstab`, `touch_rate`, decile computation |
| 7 | `show_samples_by_reason.py` | Utility: N transcript samples per `primary_reason` bucket | Pure display |
| — | `run_downstream.sh` | Chain: classify → embed → aggregate → merge | Orchestration only |

### One-off utilities

| File | Why it exists |
|---|---|
| `probe_call_log_dates.py` | Established UCCL go-live = 2025-12-30 (drove the Dec→Jan cohort pivot) |
| `smoke_test_one.py` | Confirmed Exotel auth + Whisper API + Haiku all work end-to-end on one call before burning $40 |

### Outputs in `investigative/`

| File | Grain | Key columns |
|---|---|---|
| `calls_manifest.csv` | 1 row per (call × partner-assignment candidate) | mobile, partner_id, call_id, recording_url, assigned_time, decision_event, decision_reason, decision_time, installed, installed_time, call_duration |
| `transcripts.csv` | 1 row per unique call_id | call_id, transcript, lang, error |
| `transcripts_classified.csv` | 1 row per (call_id × partner-candidate) | + primary_reason, secondary_reason, llm_summary, rx_* flags |
| `embedding_reason_scores.csv` | 1 row per unique call_id | sim_<label> × 20 + emb_top1/2/3 reason + score |
| `embedding_vs_haiku.csv` | Disagreement audit rows (emb_top1 ≠ haiku_primary, score ≥ 0.35) | For manual QA |
| `calls_resolved.csv` | 1 row per unique call_id, resolved to correct (mobile, partner) | Classified + correct partner via time-proximity |
| **`pair_aggregated.csv`** | **1 row per (mobile, partner_id)** | n_calls, total_duration_s, primary_reasons, secondary_reasons, **reasons_union** (comma-list), reasons_count, **transcripts** (concatenated), summaries, installed, decision_event, decision_reason, assigned_time, decision_time, installed_time, **decision_to_install_hours** |
| `allocation_cohort.csv` | Full Jan-Mar Delhi non-BDO allocation (~20K rows) | mobile, partner_id, nearest_distance, nearest_type, probability, allocated_at |
| `calls_with_alloc.csv` | `calls_resolved` ⋈ allocation | + distance_decile, prob_decile, nearest_type |
| **`pairs_with_alloc.csv`** | **`pair_aggregated` ⋈ allocation** (one per pair) | Final deliverable — 18 columns, 2,561 rows |
| `callLevel_reason_by_distance_decile.csv` | Decile × reason % (call level) | Includes `_total` column |
| `callLevel_reason_by_prob_decile.csv` | | |
| `callLevel_reason_by_nearest_type.csv` | active_base vs splitter | |
| `pairLevel_reason_by_distance_decile.csv` | Decile × reason touch-rate (pair level) | |
| `pairLevel_reason_by_prob_decile.csv` | | |
| `transcripts_classified_v1.csv`, `reason_distribution_v1.csv`, `embedding_reason_scores_v1.csv` | Archived V1 outputs (before prompt tightening) — for before/after audit | |
| `uccl_monthly.csv`, `uccl_first_month_daily.csv`, `pcl_monthly.csv` | Date probe results | |
| `samples_by_reason.txt` | Human-readable sample transcripts per bucket | |

---

## UCCL date probe (why cohort is Jan-Mar, not Dec)

Probed 2026-04-19 via `probe_call_log_dates.py`:

| Dimension | Value |
|---|---|
| Earliest `created_at` | **2025-12-30 21:37** — effective go-live 2025-12-31 |
| Latest | 2026-04-19 |
| Total rows | 31,967 |
| Recording fill-rate | ~27% stable across months (≈ `CONNECTED` status calls) |

Dec 2025 bookings whose ASSIGNED→install calls happened before 2025-12-30 are unrecoverable. Jan-Mar 2026 is the first month of full UCCL coverage, so the cohort was shifted there.

`partner_call_log` (PTL) goes back to 2025-07-15 but is partners-to-Wiom-support — not our source.

---

## Match-level funnel (pair cohort)

Starts from the MASTER cohort — first-ASSIGNED per (mobile, partner) in Jan-Mar 2026 Delhi, post-serviceability, non-BDO — and traces the drop-off as we filter to pairs that have a recorded call AND win ownership:

| Stage | Unique mobiles | Unique (mobile, partner) pairs |
|---|---:|---:|
| All assigned (Jan-Mar Delhi) | 6,523 | 8,584 |
| + passed serviceability gate | 6,405 | 8,444 |
| + non-BDO filter | 5,225 | **6,951** ← MASTER |
| INNER JOIN with UCCL calls (≥1 call in `[assigned, +14d]`) | 2,336 | 2,991 |
| After `resolve_call_to_partner` (ownership via time-proximity) | — | **2,561** |

**Master → calls-inner-join drop: 57% of pairs (3,960 of 6,951)** — pairs with no recorded call in UCCL.
**Calls-inner-join → resolve drop: 430 pairs** — orphan pairs where every candidate call was won by a later-assigned partner.

### Install rate by call-status bucket (master 6,951)

| Bucket | n | Installed | Install rate |
|---|---:|---:|---:|
| All master pairs | 6,951 | 3,147 | **45.3%** |
| (A) No call in UCCL at all | 3,960 | 1,827 | 46.1% |
| (B) Orphan — in manifest, lost ownership via resolve | **430** | **3** | **0.7%** |
| (C) Won a resolved call (in `pair_aggregated`) | 2,561 | 1,317 | **51.4%** |

**What the install-rate split tells us:**

- **(B) orphan pairs are ghost assignments** — 0.7% install (3/430) is essentially noise. These partners were ASSIGNED to the mobile in task_logs but never actually engaged the customer; a later-assigned partner took over. `resolve_call_to_partner` correctly separates them from active pairs.
- **(A) no-call pairs install at the master average (46.1%)** — the absence of a recorded call does NOT mean the install didn't happen. UCCL only records ~27% of its rows (CONNECTED calls); the rest is off-platform coordination or unrecorded.

**BUT — the no-call rate is NOT uniform in time. It's heavily concentrated in Jan-early-Feb (UCCL bed-in period):**

| Month | Master pairs | With call | No call | % no-call |
|---|---:|---:|---:|---:|
| Jan 2026 | 2,666 | 725 | 1,941 | **72.8%** |
| Feb 2026 | 2,319 | 999 | 1,320 | 56.9% |
| Mar 2026 | 1,867 | 1,216 | 651 | **34.9%** |
| Apr 2026 (partial) | 99 | 51 | 48 | 48.5% |

Weekly view shows the decline is monotonic: Dec-29/Jan-04 = 77% no-call → Mar-02/08 = 29% no-call. UCCL logging matured over the first two months. **Feb 7-9 had >92% no-call for 3 consecutive days** — likely an acute ingestion outage worth flagging operationally.

**Implication:** the Jan data is polluted by UCCL gaps, not by genuine no-call behavior. For cleanest-data analysis, see `./mar_only/` subfolder — re-runs the pair-level decile analysis on the March-only slice where UCCL is mature.
- **(C) call-having pairs install at 51.4%**, only 5pp above master. Our analysis is NOT heavily selection-biased — the cohort we transcribe and classify is representative.
- The logic in `resolve_call_to_partner` is validated by the 0.7% vs 46% gap. A buggy resolver would leave orphans near 46%, not at noise level.

---

## Observation funnel — SQL pull to final deliverable

Row counts at each stage, with drop-off reasons:

| Step | Stage | Rows | Unique call_ids | Unique pairs |
|---|---|---:|---:|---:|
| 1 | `pull_calls.py` → manifest | **6,199** | 4,944 | 2,991 |
| 2a | filter: `CONNECTED` + dur ≥ 10s + `recording_url` not null | 6,182 | 4,930 | — |
| 2b | `drop_duplicates(call_id)` (invariant-checked for call metadata stability) | 4,930 | 4,930 | — |
| 2c | transcribe → `transcripts.csv` | 4,929 (1 decode fail) | 4,929 | — |
| 3 | `classify_reasons.py` (tx × manifest merge re-adds dup) | 6,182 | 4,930 | — |
| 4 | `embedding_classify.py` (dedup'd to call_id) | 4,930 | 4,930 | — |
| 5a | `resolve_call_to_partner` (time-proximity) | 6,182 | 4,930 | **2,561** |
| 5b | `pair_aggregated` (groupby mobile, partner_id) | **2,561** | — | 2,561 |
| 6a | full Jan-Mar allocation cohort (baseline for deciles) | 20,367 | — | 20,367 |
| 6b | `calls_with_alloc` (call ⋈ alloc, LEFT) | 6,182 | 4,930 | — |
| 6c | `pairs_with_alloc` (pair ⋈ alloc, LEFT — FINAL) | **2,561** | — | 2,561 |
| | &nbsp;&nbsp;with `distance_decile` non-null | 2,559 | | |
| | &nbsp;&nbsp;with `prob_decile` non-null | 2,508 | | |

**Key drop-offs:**

| Transition | Rows lost | % | Why |
|---|---:|---:|---|
| Manifest → filters | 17 | 0.3% | Non-CONNECTED / duration <10s / null recording_url |
| Filters → `call_id` dedup | **1,252** | **20.3%** | SQL join duplicates one call across multiple candidate partners |
| Transcription | 1 | 0.02% | Whisper decode failure on one file |
| Manifest pairs → pair_aggregated | **430** | 14.4% | Orphan pairs: partner was ASSIGNED to the mobile but never attributed a call by `resolve_call_to_partner` (time-proximity awarded the calls to a more-recently-assigned partner) |
| Allocation merge (pairs) | **0 row loss (LEFT JOIN)** | | 2 pairs get null distance_decile (missing from alloc cohort); 53 pairs have null prob_decile (alloc row present but probability field null) |

**Note on classify-step waste:** the tx × manifest merge re-introduces the 20.3% duplication before Haiku is called, so Haiku classifies ~6,182 rows instead of ~4,930 unique transcripts. Correctness is unaffected (same transcript → same label), but ~$1.50 of Haiku cost is wasted per full run. Not worth fixing unless we run the pipeline many more times.

---

## Reason taxonomy — 20 first-principles labels

Decomposed from: the call sits between ASSIGNED and OTP_VERIFIED; JTBD = resolve everything needed for a physical install to happen.

```
Location resolution       Scheduling               Post-visit recovery
  address_not_clear         customer_postpone        partner_reached_cant_find
  address_too_far           partner_postpone         partner_no_show
  address_wrong             slot_confirmation
  building_access_issue                            Technical / site
                          Customer decision         install_site_technical
Commercial                  customer_cancelling     router_or_stock_issue
  price_or_plan_query       competitor_or_consent   duplicate_or_existing_connection
  payment_issue
                          Fallback / noise
                            wrong_customer          customer_unreachable
                            noise_or_empty          other
```

Full definitions + disambiguation rules + few-shot examples: `classify_reasons.py :: SYSTEM_PROMPT` (after V2 tightening).

---

## Key findings (full cohort, 2,561 pairs / 4,930 calls)

### 1. Dropdown under-counts address friction by ~2×

| Metric | Dropdown (`../`) | Transcript (here) |
|---|---|---|
| `address_not_clear` base rate | ~13% | **~20% of calls, ~36% of pairs (primary)** |

### 2. Distance and probability DO NOT separate transcript-level address friction

**Call-level `address_not_clear %` by distance decile** (D1 → D10):
19.5 · 18.3 · 19.7 · 21.4 · 21.2 · 21.3 · 21.6 · 24.8 · 21.4 · 20.1 — **range 6.5pp, flat**

**Call-level by probability decile:**
16.2 · 18.3 · 23.3 · 22.8 · 20.1 · 21.9 · 19.9 · 21.5 · 18.4 · 21.7 — **range 7.1pp, flat**

Contrast with dropdown: distance spread 19pp, prob spread 45pp (monotonic ↓).

### 3. The dropdown's 48%→2.5% prob pattern is a decline-channel artifact

Low-prob partners face address friction at roughly the same per-call rate as high-prob partners (16% vs 22%). But in the dropdown, low-prob partners disproportionately **choose** "address not clear" as their exit-click when declining. Transcripts invalidate the dropdown as a GNN calibration signal. Geoff's "dismissal channel" framing is now empirically confirmed.

### 4. Splitters face real excess address friction (+4pp)

| nearest_type | address_not_clear % of calls | partner_reached_cant_find % |
|---|---:|---:|
| active_base | 19.9% | 9.8% |
| splitter | 23.8% | 11.1% |

Consistent with `../location_accuracy/` splitter-gaming finding.

### 5. Multi-call pairs are the norm

- **70% of pairs have >1 distinct reason across calls** — a snapshot of one call misses most of the story.
- n_calls distribution: 38% have 1 call, 32% have 2, 11% have 3, rest have 4-24. One pair had 24 calls.

### 6. Chain engagement is protective (counter-intuitive)

Pairs that engage the Delhi address chain (landmark → gali → floor) at any point install BETTER than pairs that never engage it:

| cohort | pairs | install rate |
|---|---:|---:|
| Never engaged chain | 1,627 | 47.8% |
| Engaged chain (any call) | 934 | **57.7%** (+10pp) |

Effect disappears within 927 ANC pairs (+0.5pp) — the chain signal adds predictive power OUTSIDE the primary-reason = address_not_clear bucket. Mode breakdown: na 49.5% → landmark 56.9% → gali 53.4% → resolved 58.1% → floor **73.9%**. Full tables in STORY.csv § 12d and the "Address-chain findings" subsection below.

**Crossed with polygon_side** (see `polygon_analysis/`): the chain-engagement protective effect is almost entirely inside-polygon (+11.2pp). Outside polygon, chain engagement barely helps (+2.7pp). The most dangerous cell anywhere in the analysis: **gali-stuck × outside-polygon = 25.4% install** (+37pp below inside-polygon). See `polygon_analysis/STORY.csv` § 7b.

### 7. Decision → install time gap (1,317 installed pairs)

| p10 | p25 | **p50** | p75 | p90 | p95 | p99 | max |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2.8h | 5.6h | **20.8h** | 28.4h | 49.6h | 70.5h | 182h | 58 days |

Median ~21h. 90% install within 50h. Long tail.

Median by primary reason (installed only):
- `partner_reached_cant_find`: **8.0h** ⚡ (call-at-door → install same day)
- `address_not_clear`: 21.4h
- `slot_confirmation`: 23.5h
- `customer_postpone`: 24.5h
- `partner_postpone`: 33.2h 🐢

### 8. The 927 ANC pairs split by how far they got

16% converged on a landmark, 19% got the gali confirmed, 6% resolved the floor. 41% never engaged the gali step at all — likely customer disengagement or partner never asking. See address-chain findings block below for the full `addr_*_best` breakdown.

---

## Comm-quality tagging — where it lives in the code

Added as a second classification pass to answer "among `address_not_clear` calls, is it mutual breakdown or partner-side parsing?"

| File | What it does | Lines to read |
|---|---|---|
| `flag_comm_failure.py` | Runs Haiku on every unique transcript with a 4-way prompt: `mutual_failure / one_sided_confusion / clear / not_applicable`. Writes `comm_quality` + `comm_failure_evidence` into `transcripts_classified.csv`. Parallel (10 workers), ~11 min on 4,930 calls. | `SYSTEM_PROMPT` block ~lines 28-58; `classify()` function |
| `transcripts_classified.csv` | One row per (call_id × manifest-partner-row). Columns added: `comm_quality`, `comm_failure_evidence`. | |
| `aggregate_per_pair.py` | Rolls up per-pair: `comm_quality_list` (comma-joined), `comm_quality_worst` (pessimistic: mutual > one_sided > clear > NA), `comm_quality_mode` (most common). | `agg()` function with `COMM_RANK` dict |
| `pair_aggregated.csv` / `pairs_with_alloc.csv` | Final pair-level outputs carry the 3 comm_quality columns. | |

**Key result:** among 1,023 `address_not_clear` calls, **46% are one-sided (partner confused, customer clear)**, 32% genuinely mutual, 20% resolved-eventually. This refutes the "mutual breakdown" framing for the dominant address-friction pattern.

**Pair-level worst-case rollup** (across 2,561 pairs): 40.1% had at least one mutual-failure call; 33.0% one-sided; 16.2% all-clear; 10.7% not-applicable.

---

## Address-resolution chain tagging — where it lives in the code

Added as a third classification pass to answer: "when partner & customer discuss an address, do they follow the canonical Delhi hierarchy **LANDMARK → GALI → FLOOR**, and where does the chain break?"

The canonical chain: both parties first try to anchor on a mutually-recognized landmark (chowk / mandir / market / school / metro station), possibly after multiple to-and-fro attempts; then converge on which `gali` / lane the address is on; then resolve which floor inside the building (or confirm ground / independent house / kothi — so no floor step is needed). Calls may skip levels, enter mid-chain, jumble the order, or never get to address at all.

| File | What it does | Lines to read |
|---|---|---|
| `flag_address_chain.py` | Runs Haiku on every unique transcript with a 4-field prompt covering each step of the chain. Writes 5 columns into `transcripts_classified.csv`. Parallel (10 workers), ~11 min on 4,930 calls, ~$2. | `SYSTEM_PROMPT` block ~lines 56-140; `classify()` function |
| `transcripts_classified.csv` | One row per (call_id × manifest-partner-row). Columns added: `addr_landmark_step`, `addr_gali_step`, `addr_floor_step`, `addr_chain_stuck_at`, `addr_chain_evidence`. | |
| `aggregate_per_pair.py` | Rolls up per-pair: `addr_landmark_best`, `addr_gali_best`, `addr_floor_best` (furthest-along outcome across calls — optimistic, symmetric-but-inverted to `comm_quality_worst`), plus `addr_chain_stuck_at_list` and `addr_chain_stuck_at_mode`. | `agg()` with `LANDMARK_RANK` / `GALI_RANK` / `FLOOR_RANK` dicts |
| `pair_aggregated.csv` / `pairs_with_alloc.csv` | Final pair-level outputs carry the 5 address-chain columns. | |

**Tag values (call-level):**

| Column | Possible values |
|---|---|
| `addr_landmark_step` | `na` · `none` · `one_tried` · `multiple_tried` · `converged` |
| `addr_gali_step` | `na` · `not_reached` · `attempted` · `converged` |
| `addr_floor_step` | `na` · `not_reached` · `attempted` · `na_ground` · `converged` |
| `addr_chain_stuck_at` | `na` · `landmark` · `gali` · `floor` · `none` |
| `addr_chain_evidence` | one-line snippet (≤25 words) |

`na` on all four means the call wasn't about address (price query, payment, pure reschedule, etc.). `none` on `addr_chain_stuck_at` means chain fully resolved OR ended for a non-address reason.

**Pair-level rollup rationale:** `comm_quality_worst` is pessimistic (worst-case severity across calls); `addr_*_best` is optimistic (furthest-along outcome reached). The questions are inverted: for comm-quality we ask "did this pair ever fail?", for the address chain we ask "did this pair ever get there?"

Run order (assuming transcription + base classification + comm-quality have already run):
```bash
python flag_address_chain.py --workers 10   # ~11 min, ~$2
python aggregate_per_pair.py                # re-roll with new columns
python merge_with_allocation.py             # deciles unchanged, new cols pass through LEFT join
```

### Address-chain findings (see STORY.csv § 12d for full tables)

**Call-level stuck_at distribution** (n = 4,930 unique calls):

| stuck_at | n | % |
|---|---:|---:|
| na (not an address call) | 3,727 | 75.6% |
| landmark | 430 | 8.7% |
| gali | 364 | 7.4% |
| none (resolved / non-address end) | 350 | 7.1% |
| floor | 59 | 1.2% |

**Pair-level mode × install rate** (n = 2,561):

| stuck_at_mode | pairs | share | install rate |
|---|---:|---:|---:|
| na | 1,915 | 74.8% | 49.5% |
| **landmark** | **239** | **9.3%** | **56.9%** ← +7pp vs na |
| **gali** | **232** | **9.1%** | **53.4%** ← +4pp |
| none | 129 | 5.0% | 58.1% ← +9pp |
| **floor** | **46** | **1.8%** | **73.9%** ← +24pp |

**Counter-intuitive result:** every chain-engaged bucket installs BETTER than `na` (49.5%). Engaging the chain at all is protective; floor-stuck pairs install at 74% because by then the partner is at the door. Full cohort comparison: chain-engaged pairs 57.7% install vs 47.8% for non-engaged (+10pp). Within 927 ANC pairs the difference collapses (+0.5pp) — the chain signal adds predictive power OUTSIDE the ANC bucket.

**Within 927 ANC — furthest step reached across the pair's calls:**
- 145 (16%) converged on a landmark
- 173 (19%) got the gali confirmed
- 55 (6%) resolved the floor
- ~383 (41%) never engaged the gali step (chain broke at/before landmark)

**Two operational reads:**
1. **Gali is the call-level bottleneck.** Pre-dispatch address capture that gives the partner the gali directly = highest-leverage intervention.
2. **40% of ANC pairs never engage the gali step** — different failure mode than those that did (likely customer disengagement or partner never asking). Worth splitting as a distinct pattern.

**Mode vs any_chain_engaged — when to use which:**
- `addr_chain_stuck_at_mode` is pessimistic-to-noise (ANC pair with 1 address + 2 noise calls → mode = `na`). Use for dominant-theme framing.
- `addr_chain_stuck_at_list` + list-based "any chain engaged" is the cleaner "did this pair engage the chain at all" signal. Use for predictive cuts.

---

## V1 → V2 classifier evolution (audit trail)

V1 SYSTEM_PROMPT was too permissive on `noise_or_empty` (30% of calls, mostly genuine but ~34% rescuable into real buckets per embeddings). V2 tightened with:
- Explicit rule: any intelligible content → classify by content, NOT noise_or_empty.
- Dialect note: `bom`, `vyom`, `router`, `ruter` = Wiom Net box, not location.
- Few-shot examples drawn from real pilot transcripts.

V1 embedding `competitor_or_consent` prototype drifted to ~18% of calls (too broad — matched "my husband" / "my wife" language that should be `customer_postpone`). V2 narrowed to require explicit purchase-decision pending or explicit ISP comparison.

Result: Haiku ↔ embedding agreement jumped **29% → 47%** (+18pp). V1 outputs archived as `*_v1.csv`.

---

## What to validate (for manual screening)

1. **SQL join logic** in `query_pcalls.txt`: `scoped` CTE joins `calls` to `assigned` on mobile + time window, not on partner_id (phone numbers are Exotel-proxied so we can't match partner). `aggregate_per_pair.py::resolve_call_to_partner` is what actually assigns a call to the correct partner.
2. **Non-BDO filter**: `bdo_mobiles` CTE selects `event_name='prospect_identified'`; `WHERE bdo_lead = 0` at end of `scoped`.
3. **Serviceability lookback**: `booking_location` uses `created_at >= '2025-12-22'` (10 days before Jan 1, per Wiom convention).
4. **Haiku prompt** in `classify_reasons.py` — SYSTEM_PROMPT block ~170-270. Disambiguation rules and few-shot examples.
5. **Embedding prototypes** in `embedding_classify.py` — REASON_PROTOTYPES dict ~55-155. Specifically `customer_postpone` vs `competitor_or_consent`.
6. **Decile computation** in `merge_with_allocation.py` — `pd.qcut(alloc["nearest_distance"], 10)` runs over full ~20K cohort, not the ~2,500 with-calls subset.
7. **`decision_to_install_hours` sign**: for INTERESTED events, `decision_time` often **precedes** `assigned_time` (partner marked interest before being assigned). Gap = `installed_time - decision_time` represents the full "partner committed" → "install done" funnel.
8. **Address-chain prompt** in `flag_address_chain.py` — `SYSTEM_PROMPT` block. Specifically the dialect/vocabulary notes (landmark / gali / floor keywords including `manzil`, `chhat`, `kothi`) and the explicit rule that `bom/vyom/router/box` mean the Wiom product, NOT a landmark. Also sanity-check that `addr_chain_stuck_at = none` is being used for "chain resolved OR ended for non-address reason" — it's dual-purpose by design.

Spot-check `samples_by_reason.txt` for any label that looks off.

---

## Credentials (not in repo)

Transcription needs these env vars:
```bash
export EXOTEL_SID='<from Wiom Exotel dashboard>'
export EXOTEL_TOKEN='<...>'
export OPENAI_API_KEY='<...>'     # for Whisper + embeddings
export ANTHROPIC_API_KEY='<...>'  # for Haiku classification
```

---

## Possible next steps (from Geoff + Donna validation round — 2026-04-20)

Four concrete follow-up tests flagged by the agents. Full critiques captured in `agent_critiques.md`.

| # | Source | Ask | What it proves / disproves | Est. effort |
|---|---|---|---|---:|
| **G1** | Geoff | **Re-label 200 `address_not_clear` transcripts** — 100 by a second Haiku run with a reworded prompt, 100 by a human local to Delhi. Measure inter-rater agreement on the one_sided-vs-mutual split, specifically on "partner is the confused party" | If human agreement ≥70% on "partner is confused" → bank the 46% headline. If <70% → kill it. | 1-2 hrs + 2 hrs human |
| **G2** | Geoff | Among splitter-area calls, does install rate vary by **partner tenure in that specific splitter**? | Separates "territorial encoding is bad" (fix = upstream address infrastructure / Promise Maker gating) from "partner unfamiliar" (fix = partner training / matching) | 1 hr |
| **D1** | Donna | Re-run `comm_quality` install rates **conditional on call number** (1st call vs 2nd vs 3+). Test: does mutual_failure install rate drop for multi-call pairs? | Tests saturation bias — is mutual_failure a root cause or a symptom of distressed pairs? | 1 hr |
| **D2** | Donna | Does install rate within `address_not_clear` correlate with the partner's **n-th task of the day**? | Tests fatigue hypothesis — is the 59% surmountable-install rate driven by partner persistence (scarce resource) vs address-complexity? | 1-2 hr (partner task ordering needed) |

### Framing shifts the agents requested

- **Headline on the 46% partner-side parsing finding**: direction is defensible, magnitude ±10pp due to Haiku label noise. Should not land as "46%" until G1 validates it.
- **Splitter +4pp attribution**: currently reads as "partner territorial unfamiliarity." Could equally be "splitter areas have under-encoded addresses" — a territory-infrastructure problem, not a partner problem. G2 separates these.
- **On-site mutual failure (41% in `partner_reached_cant_find`) was under-played**. Breakdown peaks at the moment of partner arrival, not at pre-dispatch scheduling. Any intervention targeting only pre-dispatch address capture misses this. Worth a separate write-up.
- **Intervention lever update**: pre-dispatch pin-drop + reverse-geocode is ONE lever. Donna's **neighborhood-memory artifact store** (first partner to crack a cluster writes a 2-line note, surfaced to next partner) is likely higher-leverage — converts leaky partner-memory stock into durable system-memory stock. Risk = stale-note decay; track note-age vs install-rate.
- **Pin-drop as a hard gate is risky** — creates gaming loop (customers drop any pin to pass). Soft nudge + reverse-geocode sanity check against pincode is safer.

---

## Timeline

| Date | Event |
|---|---|
| 2026-04-19 | Subfolder scaffolded; UCCL probe → Dec 2025 cohort thin (234 recordings); switched to Jan-Mar 2026 |
| 2026-04-19 | Exotel Basic auth sorted; smoke test passed end-to-end |
| 2026-04-19 | Pilot: 600 stratified calls → V1 classifier → 30% noise, 18% address_not_clear |
| 2026-04-19 | Embeddings added; Haiku ↔ emb agreement 29% |
| 2026-04-19 | V2: tightened SYSTEM_PROMPT + fixed embedding drift → agreement jumped to 47% |
| 2026-04-19 | Added `decision_to_install_hours`; added raw transcripts concatenated per pair |
| 2026-04-19 | Full run: 4,330 new calls transcribed in 88 min; 2,561 pairs aggregated |
| 2026-04-19 | Subfolder moved inside `location_accuracy/` per scope convention |
| 2026-04-19 | **Finding: transcript distance/prob separation is flat (~20%). Dropdown's 48%→2.5% was decline-channel artifact. Confirmed empirically.** |
| 2026-04-20 | Added `flag_comm_failure.py` — 4-way comm-quality tagging. 46% of ANC calls are one-sided (partner confused), only 32% mutual. |
| 2026-04-20 | Added `flag_address_chain.py` — LANDMARK → GALI → FLOOR hierarchy. Ran full pass on 4,930 transcripts; 5 addr_* columns propagated to pair level. |
| 2026-04-20 | **Finding: chain engagement is protective.** Chain-engaged pairs install 57.7% vs 47.8% for non-engaged (+10pp). Effect disappears within ANC (+0.5pp) — chain signal adds predictive power OUTSIDE primary_first=address_not_clear. Floor-stuck pairs install at 74% (partner at door). |
| 2026-04-20 | Gali identified as single biggest call-level bottleneck (7.4% of calls stuck there). 41% of ANC pairs never engaged the gali step — distinct failure mode. |
| 2026-04-20 | STORY.csv section 12d added covering address-chain drill-down (call-level, pair-level, primary_first × stuck_at crosstab, furthest-step-reached within ANC). |
