"""
Time-to-install percentiles (installed pairs only), split by whether the
pair's primary_first reason sits in the address family.

Reads:  investigative/pairs_with_alloc.csv  (2,561 pair rows)
Writes: investigative/time_to_install_by_address.csv

Decision_to_install_hours = hours from decision_time (OTP_VERIFIED) to
installed_time. Meaningful only for installed pairs.

Address family = primary_first in {address_not_clear, address_too_far,
address_wrong, building_access_issue, partner_reached_cant_find}.

Output columns: bucket, n, installed, min, p10, p25, median, mean, p75,
p90, p95, p99, max.
"""

from pathlib import Path
import pandas as pd
import numpy as np

HERE  = Path(__file__).resolve().parent
INV   = HERE / "investigative"
PAIRS = INV / "pairs_with_alloc.csv"
OUT   = INV / "time_to_install_by_address.csv"

ADDRESS_FAMILY = {
    "address_not_clear", "address_too_far", "address_wrong",
    "building_access_issue", "partner_reached_cant_find",
}


def quantiles(series: pd.Series) -> dict:
    s = series.dropna()
    if len(s) == 0:
        return {"n":0}
    return {
        "n":       int(len(s)),
        "min":     float(s.min()),
        "p10":     float(np.percentile(s, 10)),
        "p25":     float(np.percentile(s, 25)),
        "median":  float(np.percentile(s, 50)),
        "mean":    float(s.mean()),
        "p75":     float(np.percentile(s, 75)),
        "p90":     float(np.percentile(s, 90)),
        "p95":     float(np.percentile(s, 95)),
        "p99":     float(np.percentile(s, 99)),
        "max":     float(s.max()),
    }


def main():
    pairs = pd.read_csv(PAIRS)
    print(f"loaded {len(pairs):,} pairs")

    inst = pairs[pairs["installed"] == 1].copy()
    print(f"installed pairs: {len(inst):,}")

    inst["is_address"] = inst["primary_first"].isin(ADDRESS_FAMILY)
    inst["bucket"] = inst["is_address"].map(
        {True: "address_related", False: "non_address_related"})

    rows = []
    for label, sub in [
        ("ALL_INSTALLED",        inst),
        ("address_related",      inst[inst["is_address"]]),
        ("non_address_related",  inst[~inst["is_address"]]),
    ]:
        q = quantiles(sub["decision_to_install_hours"])
        q["bucket"] = label
        rows.append(q)
    out = pd.DataFrame(rows)[
        ["bucket","n","min","p10","p25","median","mean","p75","p90","p95","p99","max"]]

    for c in out.columns[2:]:
        out[c] = out[c].round(2)

    print("\n=== Time-to-install (hours) — installed pairs only ===")
    print(out.to_string(index=False))

    # Sanity: address + non_address totals should equal ALL_INSTALLED
    addr_n = int(out.loc[out["bucket"]=="address_related","n"].iat[0])
    non_n  = int(out.loc[out["bucket"]=="non_address_related","n"].iat[0])
    all_n  = int(out.loc[out["bucket"]=="ALL_INSTALLED","n"].iat[0])
    print(f"\nSANITY: address_related ({addr_n}) + non_address_related ({non_n}) "
          f"= {addr_n+non_n}  vs  ALL_INSTALLED={all_n}  "
          f"{'OK' if addr_n+non_n==all_n else 'MISMATCH'}")

    out.to_csv(OUT, index=False)
    print(f"\nWROTE {OUT}")


if __name__ == "__main__":
    main()
