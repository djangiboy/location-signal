"""
Transcribe + Translate Partner->Customer Calls
================================================
Input : investigative/calls_manifest.csv (produced by pull_calls.py)
Output: investigative/transcripts.csv  (one row per call, resumable)

Hindi/Hinglish audio -> English transcript in one pass.

BACKEND:
  - Default: OpenAI Whisper API (audio.translations — Hindi -> English in one
    pass). Requires OPENAI_API_KEY in env. $0.006/min of audio.
  - Alternative: local Whisper (openai-whisper). Slower but free. Set
    TRANSCRIBE_BACKEND=local env var.

SAMPLING:
  --sample N      transcribe a random N calls (stratified by installed/declined).
                  Use 0 / -1 to transcribe ALL unique recordings.
  --status VAL    filter calls_manifest by call_status (default: CONNECTED)
  --min-duration  secs; skip calls shorter than this (default: 10)

RESUMABLE: skips call_ids already in transcripts.csv.

Run from: analyses/data/partner_customer_calls/
    python transcribe_calls.py --sample 100
"""

import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import requests


HERE        = Path(__file__).resolve().parent
OUT_DIR     = HERE / "investigative"
AUDIO_DIR   = HERE / "audio_cache"
AUDIO_DIR.mkdir(exist_ok=True)

MANIFEST    = OUT_DIR / "calls_manifest.csv"
TRANSCRIPTS = OUT_DIR / "transcripts.csv"


# ---------------------------------------------------------------------------
# AUDIO DOWNLOAD
# ---------------------------------------------------------------------------
def _exotel_auth():
    sid = os.environ.get("EXOTEL_SID")
    tok = os.environ.get("EXOTEL_TOKEN")
    if not sid or not tok:
        raise RuntimeError("EXOTEL_SID / EXOTEL_TOKEN env vars required")
    return (sid, tok)


def download_audio(url, call_id):
    """OBJECTIVE: Fetch the recording once, cache under audio_cache/<call_id>.*.
    Exotel requires HTTP Basic auth (SID, Token). Returns local path or None."""
    ext = ".mp3"
    lower = url.lower().split("?")[0]
    for candidate in (".wav", ".mp3", ".m4a", ".ogg"):
        if lower.endswith(candidate):
            ext = candidate
            break
    local = AUDIO_DIR / f"{call_id}{ext}"
    if local.exists() and local.stat().st_size > 0:
        return local
    try:
        r = requests.get(url, timeout=60, stream=True, auth=_exotel_auth())
        r.raise_for_status()
        with open(local, "wb") as f:
            for chunk in r.iter_content(1 << 15):
                f.write(chunk)
        return local
    except Exception as e:
        print(f"  [DOWNLOAD FAIL] {call_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# BACKEND: LOCAL WHISPER
# ---------------------------------------------------------------------------
def load_local_whisper(size="small"):
    import whisper
    print(f"LOADING LOCAL WHISPER model={size}")
    return whisper.load_model(size)


def transcribe_local(model, audio_path):
    """task='translate' -> English regardless of source language."""
    result = model.transcribe(str(audio_path), task="translate", fp16=False)
    return result.get("text", "").strip(), result.get("language", "")


# ---------------------------------------------------------------------------
# BACKEND: OPENAI WHISPER API
# Translate endpoint returns English directly regardless of source language.
# Whisper API has a 25MB file-size limit. All Exotel recordings (few min, 64kbps)
# are well under. No chunking needed.
# ---------------------------------------------------------------------------
_OPENAI_CLIENT = None


def _get_openai_client():
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        from openai import OpenAI
        _OPENAI_CLIENT = OpenAI()
    return _OPENAI_CLIENT


def transcribe_openai(audio_path):
    client = _get_openai_client()
    with open(audio_path, "rb") as f:
        resp = client.audio.translations.create(
            model="whisper-1",
            file=f,
            response_format="text",
        )
    # response_format='text' returns a plain string; older libs return obj.text
    text = resp if isinstance(resp, str) else getattr(resp, "text", str(resp))
    return text.strip(), "translated"


# ---------------------------------------------------------------------------
# SAMPLING
# ---------------------------------------------------------------------------
def stratified_sample(df, n):
    """Roughly 50/50 split between installed and not-installed calls."""
    inst = df[df["installed"] == 1]
    noinst = df[df["installed"] == 0]
    n_each = n // 2
    picks = []
    if len(inst) > 0:
        picks.append(inst.sample(min(n_each, len(inst)), random_state=42))
    if len(noinst) > 0:
        picks.append(noinst.sample(min(n - (picks[0].shape[0] if picks else 0),
                                       len(noinst)),
                                   random_state=42))
    return pd.concat(picks).reset_index(drop=True) if picks else df.head(0)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
_FLUSH_LOCK = threading.Lock()


def process_one(row, backend, local_model=None):
    """Worker function: download + transcribe one call. Returns dict or error row."""
    cid = str(row.call_id)
    audio = download_audio(row.recording_url, cid)
    if audio is None:
        return {"call_id": cid, "transcript": "", "lang": "", "error": "download_fail"}
    try:
        if backend == "local":
            text, lang = transcribe_local(local_model, audio)
        else:
            text, lang = transcribe_openai(audio)
        return {"call_id": cid, "transcript": text, "lang": lang, "error": ""}
    except Exception as e:
        return {"call_id": cid, "transcript": "", "lang": "", "error": str(e)[:200]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sample", type=int, default=0,
                   help="0 or -1 = transcribe ALL unique recordings")
    p.add_argument("--status", default="CONNECTED")
    p.add_argument("--min-duration", type=int, default=10)
    p.add_argument("--model-size", default="small",
                   help="local whisper model: tiny|base|small|medium|large")
    p.add_argument("--workers", type=int, default=10,
                   help="number of parallel download+transcribe workers")
    args = p.parse_args()

    backend = os.environ.get("TRANSCRIBE_BACKEND", "openai").lower()
    print(f"BACKEND: {backend}  WORKERS: {args.workers}")
    assert MANIFEST.exists(), f"Run pull_calls.py first — {MANIFEST} missing"

    df = pd.read_csv(MANIFEST)
    print(f"MANIFEST ROWS: {len(df):,}")

    df = df[df["call_status"] == args.status]
    df = df[df["call_duration"].fillna(0) >= args.min_duration]
    df = df[df["recording_url"].notna()]
    print(f"AFTER FILTERS (status={args.status}, dur>={args.min_duration}s): {len(df):,}")

    # Invariant check before dedup: call metadata (duration/status/url/time)
    # should be stable per call_id across duplicate manifest rows. The SQL
    # join duplicates calls ONLY on partner-side fields (partner_id,
    # assigned_time, decision_time, installed). If a call-side column varies,
    # `keep="first"` would silently pick one — halt instead of dedup blind.
    INVARIANT_COLS = ["call_duration", "call_status", "recording_url", "call_time"]
    HALT_THRESHOLD = 0.005   # >0.5% of call_ids breaking invariant -> halt
    total_ids = df["call_id"].nunique()
    any_halt = False
    for col in INVARIANT_COLS:
        n_bad = (df.groupby("call_id")[col].nunique() > 1).sum()
        if n_bad > 0:
            frac = n_bad / total_ids
            tag = "HALT" if frac > HALT_THRESHOLD else "warn"
            print(f"  [{tag}] {n_bad:,} call_ids vary on '{col}' "
                  f"({frac*100:.2f}% of {total_ids:,})")
            any_halt = any_halt or (frac > HALT_THRESHOLD)
    if any_halt:
        raise AssertionError(
            "Call metadata invariant violated above 0.5% threshold. "
            "keep='first' would pick arbitrarily — resolve at source "
            "(re-check the SQL join or UCCL ingestion) before proceeding."
        )

    df = df.drop_duplicates("call_id", keep="first").reset_index(drop=True)
    print(f"AFTER DEDUP (unique call_id): {len(df):,}")

    if args.sample > 0 and args.sample < len(df):
        df = stratified_sample(df, args.sample)
        print(f"SAMPLED: {len(df):,}")
    else:
        print(f"TRANSCRIBING ALL: {len(df):,}")

    # Resume: skip already-done call_ids
    done = set()
    if TRANSCRIPTS.exists():
        done = set(pd.read_csv(TRANSCRIPTS)["call_id"].astype(str))
        print(f"RESUMING — {len(done):,} already transcribed, skipping")

    todo = df[~df["call_id"].astype(str).isin(done)].reset_index(drop=True)
    print(f"TO TRANSCRIBE: {len(todo):,}")

    model = load_local_whisper(args.model_size) if backend == "local" else None

    rows = []
    t0 = time.time()
    total = len(todo)
    completed = 0

    def flush(rows):
        with _FLUSH_LOCK:
            out_df = pd.DataFrame(rows)
            if TRANSCRIPTS.exists():
                out_df = pd.concat([pd.read_csv(TRANSCRIPTS), out_df],
                                   ignore_index=True).drop_duplicates("call_id",
                                                                       keep="last")
            out_df.to_csv(TRANSCRIPTS, index=False)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_one, r, backend, model): r
                   for r in todo.itertuples(index=False)}
        for fut in as_completed(futures):
            result = fut.result()
            rows.append(result)
            completed += 1
            if result["error"]:
                print(f"[{completed}/{total}] {result['call_id']} ERR: {result['error']}")
            else:
                snippet = result["transcript"][:80].replace("\n", " ")
                print(f"[{completed}/{total}] {result['call_id']} OK {snippet}...")
            if completed % 50 == 0 or completed == total:
                flush(rows)
                rate = completed / (time.time() - t0)
                eta = (total - completed) / rate if rate > 0 else 0
                print(f"  CHECKPOINT {completed}/{total} — {rate:.1f}/s — ETA {eta/60:.1f} min")

    flush(rows)
    dt = time.time() - t0
    print(f"\nDONE in {dt:.1f}s ({dt / max(total, 1):.2f}s/call avg, "
          f"{total/dt*60:.1f} calls/min)")


if __name__ == "__main__":
    main()
