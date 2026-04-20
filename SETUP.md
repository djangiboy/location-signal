# Setup — running this repo locally

**Audience:** Rohan, Ryan, or anyone picking up the location-signal audit from `djangiboy`.

---

## 1. What this repo contains

A cross-engine audit of location signal fidelity across Wiom's matchmaking funnel. Structure (see `README.md` for the full orientation):

- `promise_maker_gps/` — pre-promise GPS signal quality (Stages A + B complete)
- `allocation_signal/` — partner-booking distance analysis vs GNN probability (complete)
- `coordination/` — partner-customer call transcripts (complete, 4,930 calls)
- `problem_statements/` — two Gate 0 thinking contracts filed with Satyam
- `solution_design.md` — agent-validated build spec (read this for what ships next)
- `solution_synthesis.md` — strategic critique + innovation layer
- `possible_solutioning_approaches/` — Maanas's own notes + the full Gate 0 HTML

## 2. What this repo does NOT contain (intentionally)

Per `.gitignore`:

- **`db_connectors.py`** — not shipped because the original contained hardcoded production credentials. Use the template (step 3).
- **`investigative/` directories** — intermediate CSVs (~200 MB). Regenerable via the `pull_*.py` and `build_*.py` scripts in each engine subfolder.
- **`coordination/audio_cache/`** — 323 MB of Exotel recordings. Regenerable via `transcribe_calls.py`.
- **`*.h5`** — binary hex / spatial caches. Regenerable from `partner_cluster_boundaries` build in `promise_maker/B/`.
- **`__pycache__/`**, **`.claude/`**, editor temps — standard.

## 3. Database credentials

In each engine subfolder where you'll run scripts, copy the template:

```bash
cp db_connectors.example.py allocation_signal/db_connectors.py
cp db_connectors.example.py coordination/db_connectors.py
cp db_connectors.example.py promise_maker_gps/gps_jitter/db_connectors.py
cp db_connectors.example.py promise_maker_gps/booking_install_distance/db_connectors.py
```

Then set environment variables (shell profile or a local `.env` you don't commit):

```bash
export SNOWFLAKE_USER=...
export SNOWFLAKE_ACCOUNT=...
export SNOWFLAKE_PRIVATE_KEY_PATH=$HOME/.snowflake/rsa_key.p8
export SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=...
# plus GENIE1_*, GENIE2_*, CLICKHOUSE_*, SQLSERVER_* as needed — see the template's docstring
```

Ask Maanas out-of-band (not over this repo) for the actual credential values + the private key file.

## 4. Regenerating the data

Each engine subfolder has a `README.md` with its own run-order. General pattern:

```bash
cd allocation_signal/
python unified_decile_analysis.py     # pulls cohort from Snowflake/MySQL, writes to investigative/
python investigate_tenure_gap.py       # follow-up slice
python write_story.py                  # rebuilds STORY.csv from all intermediate CSVs
```

```bash
cd coordination/
python pull_calls.py
python transcribe_calls.py --workers 10   # resumable, writes audio_cache/ + transcripts.csv
python classify_reasons.py --workers 10
python embedding_classify.py
python flag_comm_failure.py
python flag_address_chain.py
python aggregate_per_pair.py
python merge_with_allocation.py
python write_story.py
```

```bash
cd promise_maker_gps/gps_jitter/
python pull_wifi_pings.py
python build_jitter.py
python headline_jitter.py
python write_story.py
```

```bash
cd promise_maker_gps/booking_install_distance/
python pull_install_drift.py
python build_drift.py
python write_story.py
```

The `STORY.csv` in each engine folder is the handoff artifact — read those first.

## 5. Where to start reading

1. Parent `README.md` — orientation, customer flow, three-engine synthesis
2. `problem_statements/problem_1_*.md` + `problem_2_*.md` — Gate 0 thinking contracts
3. `solution_design.md` — agent-validated build spec, phasing, open questions
4. `solution_synthesis.md` — deeper critique + innovation reasoning
5. Individual engine `README.md` files for the analytical substrate

## 6. Questions, corrections, re-design

Maanas (djangiboy) owns this workstream. Cross-reference to the Promise Maker system work in `../../promise_maker/` for the ML destination this audit plugs into.
