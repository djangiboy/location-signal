"""
Flag mutual-communication-failure on transcripts.

Runs a focused Haiku pass on EVERY transcript and tags each with one of:
  - "mutual_failure"     : both parties repeatedly fail to establish what /
                           where / who they're talking about
  - "one_sided_confusion": only one party is confused (usually partner
                           parsing a clearly-given address, or customer not
                           recognizing the partner's company)
  - "clear"              : communication worked, info was exchanged
  - "not_applicable"     : transcript too short / noise / no meaningful
                           interaction to judge

Adds TWO columns to transcripts_classified.csv:
  - comm_quality         : one of the 4 tags above
  - comm_failure_evidence: one-line snippet showing WHY Haiku picked the tag

Run from: partner_customer_calls/
    python flag_comm_failure.py
    python flag_comm_failure.py --workers 10

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
BACKUP    = OUT_DIR / "transcripts_classified_pre_comm_flag.csv"


SYSTEM_PROMPT = """You are rating the COMMUNICATION QUALITY of a phone call
between a Wiom installation partner and a booked customer (transcript in
English, translated from Hindi by Whisper).

Pick ONE tag:

- mutual_failure     : BOTH parties repeatedly fail to establish what / where
                       / who they're talking about. Signs include repeated
                       "hello?" / "what?" / "where?" / "can't hear" /
                       "say again" / asking the same question 3+ times /
                       circling over same landmark without convergence.
                       The call ends without either side having understood
                       the other. Product mentions like "bom/vyom/router
                       box" do NOT count as mutual failure — they're just
                       the Wiom product name.

- one_sided_confusion: ONE party is confused while the other is clear.
                       Examples: partner repeatedly asks for a landmark
                       that the customer gave cleanly on turn 1; customer
                       doesn't recognize Wiom but partner is articulate.

- clear              : communication worked. Info was exchanged successfully
                       even if the call's content was postponement, price,
                       cancellation, etc. Tag CLEAR when the content flowed.

- not_applicable     : transcript is too short, noisy, empty, or contains
                       only greetings / recording notice. Nothing to judge.

Return ONLY a JSON object, nothing else:
  {"comm_quality": "<tag>", "evidence": "<one-line snippet or reason, <=20 words>"}
"""


def classify(client, text):
    if not isinstance(text, str) or len(text.strip()) < 5:
        return ("not_applicable", "empty transcript")
    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=[{"type":"text","text":SYSTEM_PROMPT,"cache_control":{"type":"ephemeral"}}],
            messages=[{"role":"user","content":text[:4000]}],
        )
        raw = msg.content[0].text.strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.M).strip()
        data = json.loads(raw)
        q = data.get("comm_quality", "not_applicable")
        if q not in ("mutual_failure","one_sided_confusion","clear","not_applicable"):
            q = "not_applicable"
        return (q, data.get("evidence", "")[:200])
    except Exception as e:
        return ("not_applicable", f"ERR:{str(e)[:100]}")


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

    # Only classify one row per unique call_id (classification is the same
    # regardless of which partner-candidate row we picked)
    unique_tx = df.drop_duplicates("call_id")
    if args.limit > 0:
        unique_tx = unique_tx.head(args.limit)
    print(f"Classifying {len(unique_tx):,} unique transcripts ...")

    from anthropic import Anthropic
    client = Anthropic()

    results = {}
    t0 = time.time()

    def work(cid, txt):
        q, ev = classify(client, txt)
        return cid, q, ev

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(work, r.call_id, r.transcript) for r in unique_tx.itertuples(index=False)]
        for f in futs:
            cid, q, ev = f.result()
            results[str(cid)] = (q, ev)
            done += 1
            if done % 200 == 0 or done == len(futs):
                rate = done / (time.time() - t0)
                eta = (len(futs) - done) / rate if rate > 0 else 0
                print(f"  {done}/{len(futs)} — {rate:.1f}/s — ETA {eta/60:.1f} min")

    # Broadcast back to all rows
    df["comm_quality"]          = df["call_id"].astype(str).map(lambda c: results.get(c, ("not_applicable",""))[0])
    df["comm_failure_evidence"] = df["call_id"].astype(str).map(lambda c: results.get(c, ("not_applicable",""))[1])

    df.to_csv(OUT_CSV, index=False)
    print(f"\nWROTE {OUT_CSV}")

    # Summary
    u = df.drop_duplicates("call_id")
    dist = u["comm_quality"].value_counts()
    print(f"\ncomm_quality distribution (n={len(u):,} unique calls):")
    for k, v in dist.items():
        print(f"  {k:<22s} {v:>5,}  {v/len(u)*100:5.1f}%")

    # Intersect with primary_reason = address_not_clear
    ac = u[u["primary_reason"] == "address_not_clear"]
    if len(ac):
        print(f"\namong address_not_clear calls (n={len(ac):,}):")
        for k, v in ac["comm_quality"].value_counts().items():
            print(f"  {k:<22s} {v:>5,}  {v/len(ac)*100:5.1f}%")


if __name__ == "__main__":
    main()
