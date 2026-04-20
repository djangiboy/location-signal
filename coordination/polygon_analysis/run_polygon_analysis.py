"""
Polygon-based analysis of the 2,561 pair cohort
================================================
Questions:
  (a) Of 2,561 pairs, how many have an eligible partner polygon?
  (b) For pairs with a polygon: is the booking point INSIDE or OUTSIDE it?
      Does that split change the address_not_clear rate and install rate?
  (c) For pairs INSIDE the polygon: does distance-to-edge or distance-to-center
      differentiate the reason distribution and install rate?

Polygon source: promise_maker/B/training/partner_cluster_boundaries.h5
  One row per (partner, cluster). A partner may have multiple clusters. Each
  cluster has a shapely Polygon, a center (center_lat, center_lon), and an
  area_km2.

Booking coordinates: allocation_cohort.csv (same `booking_location` CTE as
query_pcalls.txt — serviceable lat/lng from t_serviceability_logs).

Uses geopandas for spatial join with predicate='within'. Uses UTM zone 43N
(EPSG:32643) for meter-accurate distance computation.

Partner polygons vary in shape → we compute:
  - distance_to_edge_m        (raw meters, signed: + inside / − outside)
  - distance_to_center_m      (raw meters, from polygon centroid/center)
  - equivalent_radius_m       (sqrt(area_km2 * 1e6 / pi), a size normalizer)
  - norm_distance_to_edge     (dist / equivalent_radius, scale-invariant)
  - norm_distance_to_center   (dist / equivalent_radius)

If a partner has multiple polygons:
  - If the booking point is inside ANY of them → "inside", use the deepest one
  - Otherwise → "outside", use the one with closest edge

Outputs to investigative/:
  pairs_with_polygon.csv              — full per-pair result
  polygon_eligibility.csv             — how many pairs have polygon
  inside_vs_outside_by_reason.csv     — (a) reason mix, (b) install rate
  inside_distance_deciles.csv         — distance-based decile cuts for INSIDE pairs

Run from: partner_customer_calls/polygon_analysis/
    python run_polygon_analysis.py
"""

from pathlib import Path
import math
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import nearest_points


HERE   = Path(__file__).resolve().parent
PARENT = HERE.parent
INV    = HERE / "investigative"
INV.mkdir(exist_ok=True)

POLY_H5      = HERE / "partner_cluster_boundaries.h5"
PAIR_AGG     = PARENT / "investigative" / "pair_aggregated.csv"
ALLOC_COHORT = PARENT / "investigative" / "allocation_cohort.csv"

OUT_PAIRS     = INV / "pairs_with_polygon.csv"
OUT_ELIG      = INV / "polygon_eligibility.csv"
OUT_IO_REASON = INV / "inside_vs_outside_by_reason.csv"
OUT_IO_INSTALL= INV / "inside_vs_outside_install_rate.csv"
OUT_DIST_DEC  = INV / "inside_distance_deciles.csv"

WGS = "EPSG:4326"
UTM = "EPSG:32643"  # UTM zone 43N — covers Delhi


def main():
    print("=" * 75)
    print("POLYGON ANALYSIS — 2,561 pair cohort")
    print("=" * 75)

    # ---- Load pairs + booking coords ----
    pa = pd.read_csv(PAIR_AGG)
    print(f"\nPAIR_AGGREGATED: {len(pa):,} rows")

    alloc = pd.read_csv(ALLOC_COHORT)
    alloc.columns = [c.lower() for c in alloc.columns]
    print(f"ALLOCATION_COHORT: {len(alloc):,} rows — "
          f"with booking_lat/lng: {alloc[['booking_lat','booking_lng']].notna().all(axis=1).sum():,}")

    for c in ["mobile", "partner_id"]:
        pa[c]    = pa[c].astype(str)
        alloc[c] = alloc[c].astype(str)

    # Merge booking coords into pair_aggregated (LEFT JOIN, keep all 2,561 pairs)
    bk = alloc[["mobile","partner_id","booking_lat","booking_lng"]].drop_duplicates(
        ["mobile","partner_id"], keep="last")
    pairs = pa.merge(bk, on=["mobile","partner_id"], how="left")

    n_coords = pairs[["booking_lat","booking_lng"]].notna().all(axis=1).sum()
    print(f"\nPairs with booking coords: {n_coords:,} / {len(pairs):,}")

    # ---- Load polygons ----
    polys = pd.read_hdf(POLY_H5)
    print(f"\nPOLYGON TABLE: {len(polys):,} cluster rows, "
          f"{polys['partner_id'].nunique():,} unique partners")
    polys["partner_id"] = polys["partner_id"].astype(str)

    # Polygon metadata we need: poly geometry, area_km2, partner_id, cluster_id, centers
    polys_gdf = gpd.GeoDataFrame(
        polys[["partner_id","cluster_id","cluster_type","center_lat",
                "center_lon","area_km2","boundary_poly"]].rename(
            columns={"boundary_poly":"geometry"}),
        geometry="geometry", crs=WGS)
    polys_utm = polys_gdf.to_crs(UTM).copy()
    polys_utm["center_geom_wgs"] = gpd.points_from_xy(polys_utm["center_lon"], polys_utm["center_lat"])
    polys_utm["center_geom_utm"] = (
        gpd.GeoSeries(polys_utm["center_geom_wgs"], crs=WGS).to_crs(UTM).values)
    polys_utm["equivalent_radius_m"] = (polys_utm["area_km2"] * 1e6 / math.pi) ** 0.5

    # ---- Build pairs GeoDataFrame ----
    valid = pairs[pairs[["booking_lat","booking_lng"]].notna().all(axis=1)].copy()
    pair_geom = gpd.points_from_xy(valid["booking_lng"], valid["booking_lat"])
    pairs_gdf = gpd.GeoDataFrame(valid, geometry=pair_geom, crs=WGS).to_crs(UTM)

    # Join pairs × polygons on partner_id (many-to-many per partner, then reduce)
    joined = pairs_gdf.merge(polys_utm, on="partner_id", how="left",
                              suffixes=("_pair", "_poly"))
    print(f"\nJOIN pairs × partner polygons: {len(joined):,} rows")
    n_pairs_with_poly = joined[joined["geometry_poly"].notna()]["mobile"].groupby(
        joined.loc[joined["geometry_poly"].notna(), ["mobile","partner_id"]].apply(tuple, axis=1)
    ).size().shape[0]
    # simpler: count unique pairs with any polygon row
    pairs_with_poly_set = joined.loc[joined["geometry_poly"].notna(),
                                      ["mobile","partner_id"]].drop_duplicates()
    print(f"Pairs with at least 1 polygon: {len(pairs_with_poly_set):,}")

    # ---- For each pair × polygon row: compute geometry metrics ----
    jn = joined[joined["geometry_poly"].notna()].reset_index(drop=True).copy()
    pair_points = gpd.GeoSeries(jn["geometry_pair"].values, crs=UTM)
    pair_polys  = gpd.GeoSeries(jn["geometry_poly"].values, crs=UTM)
    pair_centers_utm = gpd.GeoSeries(jn["center_geom_utm"].values, crs=UTM)

    jn["is_inside"] = pair_polys.contains(pair_points).values
    # distance from point to polygon boundary (exterior) — always >= 0 in shapely
    jn["dist_edge_m_raw"] = pair_polys.boundary.distance(pair_points, align=False).values
    # signed: inside = positive (depth), outside = negative
    jn["dist_edge_m"]   = np.where(jn["is_inside"], jn["dist_edge_m_raw"],
                                    -jn["dist_edge_m_raw"])
    jn["dist_center_m"] = pair_centers_utm.distance(pair_points, align=False).values

    # Normalize by equivalent radius
    jn["norm_dist_edge"]   = jn["dist_edge_m"]   / jn["equivalent_radius_m"]
    jn["norm_dist_center"] = jn["dist_center_m"] / jn["equivalent_radius_m"]

    # ---- Reduce to 1 row per pair using the tie-break rule ----
    # If any polygon contains the point → pick deepest inside (max dist_edge_m > 0)
    # Else → pick nearest edge (max dist_edge_m, which is least negative)
    jn["_any_inside"] = jn.groupby(["mobile","partner_id"])["is_inside"].transform("any")
    mask_consider = (jn["_any_inside"] & jn["is_inside"]) | (~jn["_any_inside"])
    jn2 = jn[mask_consider].copy()
    # Among eligible rows per pair, pick the one with max dist_edge_m
    jn2 = jn2.sort_values(["mobile","partner_id","dist_edge_m"], ascending=[True,True,False])
    picked = jn2.drop_duplicates(["mobile","partner_id"], keep="first")
    print(f"Picked best polygon per pair: {len(picked):,}")

    # ---- Merge back to full pairs list (including those with no polygon) ----
    metric_cols = ["cluster_id","cluster_type","area_km2","equivalent_radius_m",
                   "is_inside","dist_edge_m","dist_center_m",
                   "norm_dist_edge","norm_dist_center"]
    keep = picked[["mobile","partner_id"] + metric_cols].copy()

    out = pairs.merge(keep, on=["mobile","partner_id"], how="left")
    out["has_polygon"] = out["cluster_id"].notna()
    # Coarse label for inside/outside/none
    out["polygon_side"] = np.where(out["has_polygon"],
                                    np.where(out["is_inside"]==True, "inside", "outside"),
                                    "no_polygon")
    out.to_csv(OUT_PAIRS, index=False)
    print(f"\nWROTE {OUT_PAIRS}  ({len(out):,} rows)")

    # ====================================================================
    # (a) ELIGIBILITY
    # ====================================================================
    print("\n" + "=" * 75)
    print("(a) POLYGON ELIGIBILITY")
    print("=" * 75)
    elig = pd.DataFrame({
        "bucket": ["total pairs", "with booking coords", "with polygon",
                    "no polygon", "inside polygon", "outside polygon"],
        "n": [
            len(out),
            out[["booking_lat","booking_lng"]].notna().all(axis=1).sum(),
            out["has_polygon"].sum(),
            (~out["has_polygon"]).sum(),
            (out["polygon_side"]=="inside").sum(),
            (out["polygon_side"]=="outside").sum(),
        ],
    })
    elig["pct_of_total"] = (elig["n"] / len(out) * 100).round(1)
    elig.to_csv(OUT_ELIG, index=False)
    print(elig.to_string(index=False))

    # ====================================================================
    # (b) INSIDE vs OUTSIDE — reason + install rate
    # ====================================================================
    print("\n" + "=" * 75)
    print("(b) INSIDE vs OUTSIDE — reason mix + install rate")
    print("=" * 75)
    buckets = out[out["has_polygon"]].copy()  # exclude no_polygon for this cut

    print("\n--- Install rate by polygon_side ---")
    ir = (buckets.groupby("polygon_side")
                 .agg(pairs=("installed","count"),
                      installed=("installed","sum"))
                 .reset_index())
    ir["install_rate_%"] = (ir["installed"]/ir["pairs"]*100).round(1)
    print(ir.to_string(index=False))
    ir.to_csv(OUT_IO_INSTALL, index=False)

    print("\n--- primary_first distribution by polygon_side (n and %) ---")
    counts = pd.crosstab(buckets["primary_first"], buckets["polygon_side"])
    pct    = pd.crosstab(buckets["primary_first"], buckets["polygon_side"],
                          normalize="columns") * 100
    pct = pct.round(1)
    combined = counts.add_suffix("_n").join(pct.add_suffix("_%")).fillna(0)
    combined.to_csv(OUT_IO_REASON)
    print(combined.to_string())

    # Install rate for address_not_clear pairs specifically, by side
    anc = buckets[buckets["primary_first"]=="address_not_clear"]
    print("\n--- address_not_clear pairs: install rate by polygon_side ---")
    print(anc.groupby("polygon_side")
             .agg(pairs=("installed","count"),
                  installed=("installed","sum"),
                  install_rate=("installed","mean"))
             .assign(install_rate_pct=lambda d: (d["install_rate"]*100).round(1))
             .drop(columns="install_rate").to_string())

    # ====================================================================
    # (c) INSIDE pairs — distance deciles
    # ====================================================================
    print("\n" + "=" * 75)
    print("(c) INSIDE pairs — does distance-to-edge / distance-to-center differentiate?")
    print("=" * 75)
    inside = out[out["polygon_side"]=="inside"].copy()
    print(f"INSIDE pairs: {len(inside):,}")
    if len(inside) < 50:
        print("  Too few — skipping decile cuts.")
        return

    # Distance deciles — higher decile = deeper inside (further from edge)
    for metric in ["dist_edge_m", "dist_center_m", "norm_dist_edge", "norm_dist_center"]:
        inside[f"{metric}_decile"] = pd.qcut(
            inside[metric].rank(method="first"),
            10, labels=False, duplicates="drop") + 1

    # For each decile of dist_edge_m, report install rate and address_not_clear rate
    def decile_cut(df, dec_col):
        g = df.groupby(dec_col).agg(
            n_pairs=("installed","count"),
            installed=("installed","sum"),
            edge_median=("dist_edge_m","median"),
            center_median=("dist_center_m","median"),
        ).reset_index()
        g["install_rate_%"] = (g["installed"]/g["n_pairs"]*100).round(1)
        # address_not_clear (primary_first) share
        anc_counts = df[df["primary_first"]=="address_not_clear"].groupby(dec_col).size()
        g["anc_pairs"] = g[dec_col].map(anc_counts).fillna(0).astype(int)
        g["anc_rate_%"] = (g["anc_pairs"]/g["n_pairs"]*100).round(1)
        return g

    summaries = {}
    for metric in ["dist_edge_m","dist_center_m","norm_dist_edge","norm_dist_center"]:
        summaries[metric] = decile_cut(inside, f"{metric}_decile")

    # Write combined CSV
    all_dec = pd.concat([s.assign(metric=m) for m, s in summaries.items()],
                        ignore_index=True)
    all_dec.to_csv(OUT_DIST_DEC, index=False)

    for m, s in summaries.items():
        print(f"\n--- decile by {m} ---")
        print(s.to_string(index=False))

    print(f"\nWROTE {OUT_DIST_DEC}")


if __name__ == "__main__":
    main()
