"""
Flag the address-resolution chain progression on transcripts.

Hypothesis: when partner and customer discuss an address, they follow a
canonical hierarchy:

  (1) LANDMARK  — which nearby spot (chowk/mandir/market/school) do we BOTH
                  recognize? May involve a to-and-fro across several landmarks
                  before mutual recognition is reached.
  (2) GALI      — once a landmark anchors the area, which gali / lane / street
                  off that landmark is the address on?
  (3) FLOOR     — inside that building, which floor (or ground / independent
                  house, so no floor step needed)?

A call may enter at any level (if landmark is already known both parties jump
to gali), jumble the order, or fail to progress. We tag WHICH STEPS WERE
REACHED and WHERE THE CHAIN GOT STUCK.

Adds FIVE columns to transcripts_classified.csv:
  - addr_landmark_step     : na / none / one_tried / multiple_tried / converged
  - addr_gali_step         : na / not_reached / attempted / converged
  - addr_floor_step        : na / not_reached / attempted / na_ground / converged
  - addr_chain_stuck_at    : na / landmark / gali / floor / none
  - addr_chain_evidence    : one-line snippet showing why (<=25 words)

"na" on all four means the call wasn't about address at all (price query,
payment, postponement with no location talk, etc.).

Run from: partner_customer_calls/
    python flag_address_chain.py
    python flag_address_chain.py --workers 10
    python flag_address_chain.py --limit 50   # smoke test

Cost: ~$2 at full 4,930 transcripts with Haiku 4.5.
"""

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd


HERE      = Path(__file__).resolve().parent
OUT_DIR   = HERE / "investigative"
IN_CSV    = OUT_DIR / "transcripts_classified.csv"
OUT_CSV   = OUT_DIR / "transcripts_classified.csv"
BACKUP    = OUT_DIR / "transcripts_classified_pre_addr_chain.csv"


LANDMARK_VALS = {"na", "none", "one_tried", "multiple_tried", "converged"}
GALI_VALS     = {"na", "not_reached", "attempted", "converged"}
FLOOR_VALS    = {"na", "not_reached", "attempted", "na_ground", "converged"}
STUCK_VALS    = {"na", "landmark", "gali", "floor", "none"}


SYSTEM_PROMPT = """You are rating the ADDRESS-RESOLUTION CHAIN on a phone call
between a Wiom installation partner and a booked customer in Delhi. The
transcript is in English, translated from Hindi by Whisper.

BACKGROUND — how people in Delhi converge on an address over the phone:
The canonical hierarchy is LANDMARK -> GALI -> FLOOR. The partner usually
has a pincode + block + rough locality; what's missing is the last 200m.
Both parties try to anchor on a nearby landmark (a chowk, mandir, market,
school, petrol pump, a well-known shop) that they BOTH recognize. They may
iterate across several landmarks before one lands. Once a landmark anchors
the area, they move to which gali/lane/street it is on. Finally they resolve
which floor (or confirm it's a ground-floor / independent house / kothi so
floor is not needed).

Calls may skip levels, enter mid-chain, jumble the order, or never get to
address at all. Rate each step independently; do NOT require strict ordering.

Dialect / vocabulary notes (Hindi-English mix in Delhi):
  Landmark words : landmark, "paas mein", "near", "ke samne", chowk, crossing,
                   mandir, masjid, gurudwara, market, bazaar, school, petrol
                   pump, metro station, park, well-known shop name.
  Gali words     : gali, lane, street, "gali number", "gali no", "3rd gali",
                   "last gali", "gali ke andar".
  Floor words    : manzil, floor, "pehli manzil", "first floor", "second
                   floor", "top floor", "chhat", "chhath".
  Ground floor   : "ground floor", "neeche", "independent house", "kothi",
                   "niji makaan", "apna ghar" when clearly single-storey.
  Product nouns  : "bom", "vyom", "router", "ruter", "box" = the Wiom Net
                   product. These are NOT landmarks.

Tag definitions — pick ONE value per field:

addr_landmark_step:
  na              : call is not about address at all (price query, payment,
                    pure reschedule without any location talk, etc.)
  none            : address IS being discussed but no landmark was even
                    proposed (went straight to gali or building name)
  one_tried       : exactly one landmark was proposed; mutual recognition
                    was NOT established (or call ended before confirming)
  multiple_tried  : two or more landmarks were proposed in back-and-forth;
                    may or may not have landed
  converged       : a landmark was proposed AND both parties recognized it
                    (explicit "haan, ha, yes, I know, theek hai, samajh gaya")

addr_gali_step:
  na              : call is not about address
  not_reached     : address discussed but gali was never named or asked
  attempted       : gali name / number was discussed but not confirmed by
                    the other side (or uncertainty remains)
  converged       : gali is confirmed by both parties

addr_floor_step:
  na              : call is not about address
  not_reached     : chain didn't progress this far; floor never came up
  attempted       : floor mentioned but not confirmed
  na_ground       : explicit that it's ground floor / independent house /
                    kothi, so a floor number isn't needed
  converged       : floor number confirmed by both parties

addr_chain_stuck_at:
  na              : call is not about address
  landmark        : got stuck at landmark step — no mutual recognition
  gali            : landmark OK but gali never converged
  floor           : gali OK but floor never converged
  none            : chain fully resolved, or ended for a non-address reason
                    (customer said "I'll call back", postponed, price talk
                    took over, etc.)

Return ONLY a JSON object, nothing else:
  {
    "addr_landmark_step":  "<value>",
    "addr_gali_step":      "<value>",
    "addr_floor_step":     "<value>",
    "addr_chain_stuck_at": "<value>",
    "evidence":            "<one-line snippet or reason, <=25 words>"
  }
"""


def _default():
    return ("na", "na", "na", "na", "empty transcript")


def classify(client, text):
    if not isinstance(text, str) or len(text.strip()) < 5:
        return _default()
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=[{"type":"text","text":SYSTEM_PROMPT,"cache_control":{"type":"ephemeral"}}],
            messages=[{"role":"user","content":text[:4000]}],
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.M).strip()
        data = json.loads(raw)
        lm = data.get("addr_landmark_step", "na")
        gl = data.get("addr_gali_step",     "na")
        fl = data.get("addr_floor_step",    "na")
        st = data.get("addr_chain_stuck_at","na")
        if lm not in LANDMARK_VALS: lm = "na"
        if gl not in GALI_VALS:     gl = "na"
        if fl not in FLOOR_VALS:    fl = "na"
        if st not in STUCK_VALS:    st = "na"
        ev = str(data.get("evidence", ""))[:250]
        return (lm, gl, fl, st, ev)
    except Exception as e:
        return ("na", "na", "na", "na", f"ERR:{str(e)[:100]}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--limit", type=int, default=0, help="0 = all; else first N")
    args = p.parse_args()

    df = pd.read_csv(IN_CSV)
    # Backup before overwrite
    if not BACKUP.exists():
        df.to_csv(BACKUP, index=False)
        print(f"BACKUP written: {BACKUP}")

    # Classification is content-only; dedup to unique call_id before hitting Haiku
    unique_tx = df.drop_duplicates("call_id")
    if args.limit > 0:
        unique_tx = unique_tx.head(args.limit)
    print(f"CLASSIFYING {len(unique_tx):,} unique transcripts ...")

    from anthropic import Anthropic
    client = Anthropic()

    results = {}
    t0 = time.time()

    def work(cid, txt):
        lm, gl, fl, st, ev = classify(client, txt)
        return cid, lm, gl, fl, st, ev

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(work, r.call_id, r.transcript) for r in unique_tx.itertuples(index=False)]
        for f in futs:
            cid, lm, gl, fl, st, ev = f.result()
            results[str(cid)] = (lm, gl, fl, st, ev)
            done += 1
            if done % 200 == 0 or done == len(futs):
                rate = done / (time.time() - t0)
                eta = (len(futs) - done) / rate if rate > 0 else 0
                print(f"  {done}/{len(futs)} — {rate:.1f}/s — ETA {eta/60:.1f} min")

    # Broadcast back to all rows (one call_id -> many manifest rows due to SQL join)
    df["addr_landmark_step"]   = df["call_id"].astype(str).map(lambda c: results.get(c, _default())[0])
    df["addr_gali_step"]       = df["call_id"].astype(str).map(lambda c: results.get(c, _default())[1])
    df["addr_floor_step"]      = df["call_id"].astype(str).map(lambda c: results.get(c, _default())[2])
    df["addr_chain_stuck_at"]  = df["call_id"].astype(str).map(lambda c: results.get(c, _default())[3])
    df["addr_chain_evidence"]  = df["call_id"].astype(str).map(lambda c: results.get(c, _default())[4])

    df.to_csv(OUT_CSV, index=False)
    print(f"\nWROTE {OUT_CSV}")

    # -------- Summary breakdown --------
    u = df.drop_duplicates("call_id")
    n = len(u)
    print(f"\n== SUMMARY over {n:,} unique calls ==")

    for col in ["addr_landmark_step", "addr_gali_step", "addr_floor_step", "addr_chain_stuck_at"]:
        print(f"\n{col} distribution:")
        for k, v in u[col].value_counts().items():
            print(f"  {k:<18s} {v:>5,}  {v/n*100:5.1f}%")

    # Intersect with primary_reason = address_not_clear — the high-signal slice
    if "primary_reason" in u.columns:
        ac = u[u["primary_reason"] == "address_not_clear"]
        if len(ac):
            print(f"\n== AMONG address_not_clear (n={len(ac):,}) ==")
            for col in ["addr_landmark_step", "addr_gali_step", "addr_floor_step", "addr_chain_stuck_at"]:
                print(f"\n{col}:")
                for k, v in ac[col].value_counts().items():
                    print(f"  {k:<18s} {v:>5,}  {v/len(ac)*100:5.1f}%")


if __name__ == "__main__":
    main()
