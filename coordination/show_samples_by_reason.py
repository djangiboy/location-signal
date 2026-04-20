"""
Pretty-print N sample transcripts per primary_reason for eyeball QA.

Input:  investigative/transcripts_classified.csv
Output: prints to stdout + writes investigative/samples_by_reason.txt

Run from: analyses/data/partner_customer_calls/
    python show_samples_by_reason.py --n 5
"""

import argparse
from pathlib import Path
import pandas as pd


HERE = Path(__file__).resolve().parent
OUT  = HERE / "investigative" / "samples_by_reason.txt"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=5, help="samples per reason")
    p.add_argument("--max-chars", type=int, default=500, help="truncate transcripts")
    args = p.parse_args()

    df = pd.read_csv(HERE / "investigative" / "transcripts_classified.csv")
    df = df[df["transcript"].notna() & (df["transcript"].astype(str).str.len() > 0)]

    lines = []
    def add(s=""):
        print(s); lines.append(s)

    add(f"# Samples by reason  (n per bucket = {args.n})\n")
    counts = df["primary_reason"].value_counts()
    add("## Reason distribution")
    for r, c in counts.items():
        add(f"  {r:<40s} {c:>5,} ({c/len(df)*100:.1f}%)")
    add(f"  {'TOTAL':<40s} {len(df):>5,}")
    add("")

    for reason in counts.index:
        sub = df[df["primary_reason"] == reason]
        samples = sub.sample(min(args.n, len(sub)), random_state=42)
        add(f"\n{'=' * 78}")
        add(f"{reason}  (n={len(sub)})")
        add("=" * 78)
        for i, row in enumerate(samples.itertuples(), 1):
            txt = str(row.transcript)[:args.max_chars].replace("\n", " ")
            summary = getattr(row, "llm_summary", "") or ""
            secondary = getattr(row, "secondary_reason", "") or ""
            installed = getattr(row, "installed", "")
            decision  = getattr(row, "decision_event", "")
            dec_reason = getattr(row, "decision_reason", "")
            add(f"\n[{i}] call_id={row.call_id}  installed={installed}  decision={decision}")
            add(f"    decision_reason: {dec_reason}")
            if secondary:
                add(f"    secondary: {secondary}")
            add(f"    summary  : {summary}")
            add(f"    transcript: {txt}")

    OUT.write_text("\n".join(lines))
    print(f"\nWROTE: {OUT}")


if __name__ == "__main__":
    main()
