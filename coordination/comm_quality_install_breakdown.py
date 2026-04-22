"""
Pair-level install rates across comm_quality_worst x address-family split.

Reads:  investigative/pairs_with_alloc.csv  (2,561 pair rows)
Writes: investigative/comm_quality_install_breakdown.csv

Two tables:
  A) comm_quality_worst x install rate (4 rows, sums to 2,561)
  B) comm_quality_worst x address-related split (8 rows, MECE, sums to 2,561)

Address family = primary_first in {address_not_clear, address_too_far,
address_wrong, building_access_issue, partner_reached_cant_find}.
"""

from pathlib import Path
import pandas as pd

HERE   = Path(__file__).resolve().parent
INV    = HERE / "investigative"
PAIRS  = INV / "pairs_with_alloc.csv"
OUT    = INV / "comm_quality_install_breakdown.csv"

ADDRESS_FAMILY = {
    "address_not_clear", "address_too_far", "address_wrong",
    "building_access_issue", "partner_reached_cant_find",
}
COMM_ORDER = ["mutual_failure", "one_sided_confusion", "clear", "not_applicable"]


def compute(pairs: pd.DataFrame):
    total = len(pairs)
    pairs = pairs.copy()
    pairs["is_address"] = pairs["primary_first"].isin(ADDRESS_FAMILY)

    # --- Table A: comm_quality_worst x install rate
    a = (pairs.groupby("comm_quality_worst")
              .agg(n=("installed", "size"),
                   installed=("installed", "sum"))
              .reset_index())
    a["share_%"]        = (a["n"]         / total * 100).round(1)
    a["install_rate_%"] = (a["installed"] / a["n"]  * 100).round(1)
    a = a.set_index("comm_quality_worst").reindex(COMM_ORDER).reset_index()

    # --- Table B: MECE split by address-family
    b = (pairs.groupby(["comm_quality_worst", "is_address"])
              .agg(n=("installed", "size"),
                   installed=("installed", "sum"))
              .reset_index())
    b["bucket"]         = b["is_address"].map({True: "address_related",
                                                False: "non_address_related"})
    b["share_%"]        = (b["n"]         / total * 100).round(1)
    b["install_rate_%"] = (b["installed"] / b["n"]  * 100).round(1)
    b["_ord"] = b["comm_quality_worst"].map({k:i for i,k in enumerate(COMM_ORDER)})
    b = (b.sort_values(["_ord", "is_address"], ascending=[True, False])
          .drop(columns=["_ord", "is_address"])
          [["comm_quality_worst", "bucket", "n", "share_%",
            "installed", "install_rate_%"]]
          .reset_index(drop=True))
    return a, b


def main():
    pairs = pd.read_csv(PAIRS)
    print(f"loaded {len(pairs):,} pairs from {PAIRS.name}")

    a, b = compute(pairs)

    print("\n=== Table A: comm_quality_worst x install rate ===")
    print(a.to_string(index=False))
    print(f"  TOTAL: n={a['n'].sum():,}, installed={a['installed'].sum():,}, "
          f"rate={a['installed'].sum()/a['n'].sum()*100:.1f}%")

    print("\n=== Table B: MECE split by address-family ===")
    print(b.to_string(index=False))
    print(f"  TOTAL: n={b['n'].sum():,}, installed={b['installed'].sum():,}")

    # Persist a single combined CSV for downstream consumers (write_story.py)
    a_out = a.assign(bucket="_all_")[
        ["comm_quality_worst", "bucket", "n", "share_%",
         "installed", "install_rate_%"]]
    combined = pd.concat([a_out, b], ignore_index=True)
    combined.to_csv(OUT, index=False)
    print(f"\nWROTE {OUT}")


if __name__ == "__main__":
    main()
