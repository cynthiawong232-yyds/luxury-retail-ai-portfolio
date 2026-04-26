"""Segment clients by beauty purchase behavior.

Builds per-client beauty profiles from transactions + RFM, then assigns each
client to one of four named segments the rest of the Maison Solène pipeline consumes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from tools.load_data_tool import load_data

SEGMENT_ORDER = [
    "Fragrance VIP",
    "Skincare Devotee",
    "Makeup Enthusiast",
    "Beauty Explorer",
]

VIP_RFM_LEVELS = {"VIP", "High Value"}


def _mode_or_nan(series: pd.Series):
    s = series.dropna()
    if s.empty:
        return np.nan
    counts = s.value_counts()
    top = counts.max()
    return sorted(counts[counts == top].index)[0]


def build_client_profiles(
    beauty_txn_df: pd.DataFrame, rfm_df: pd.DataFrame
) -> pd.DataFrame:
    """Return one row per client with beauty profile + assigned beauty_segment."""
    grp = beauty_txn_df.groupby("client_id", dropna=False)
    profiles = pd.DataFrame({
        "primary_beauty_category": grp["category"].agg(_mode_or_nan),
        "total_beauty_spend": grp["net_sales_amount"].sum(min_count=1),
        "beauty_purchase_count": grp.size(),
        "favorite_beauty_product": grp["product_name"].agg(_mode_or_nan),
        "distinct_category_count": grp["category"].nunique(),
    }).reset_index()

    rfm_slim = rfm_df[["client_id", "rfm_segment"]].drop_duplicates("client_id")
    clients = rfm_slim.merge(profiles, on="client_id", how="left")

    clients["beauty_purchase_count"] = (
        clients["beauty_purchase_count"].fillna(0).astype(int)
    )
    clients["distinct_category_count"] = (
        clients["distinct_category_count"].fillna(0).astype(int)
    )
    clients["total_beauty_spend"] = clients["total_beauty_spend"].fillna(0.0)

    clients["beauty_segment"] = clients.apply(_assign_segment, axis=1)
    return clients


def _assign_segment(row: pd.Series) -> str:
    if row["beauty_purchase_count"] == 0:
        return "Unsegmented"

    primary = row["primary_beauty_category"]
    rfm = row["rfm_segment"]

    if rfm in VIP_RFM_LEVELS and primary == "Fragrance":
        return "Fragrance VIP"
    if primary == "Skincare":
        return "Skincare Devotee"
    if primary == "Makeup":
        return "Makeup Enthusiast"
    return "Beauty Explorer"


def build_segment_summary(client_profiles_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the enriched client frame into the four-row dashboard summary."""
    rows = []
    for seg in SEGMENT_ORDER:
        members = client_profiles_df[client_profiles_df["beauty_segment"] == seg]
        if members.empty:
            rows.append({
                "segment": seg,
                "client_count": 0,
                "avg_spend": 0.0,
                "top_product": None,
            })
            continue
        rows.append({
            "segment": seg,
            "client_count": int(len(members)),
            "avg_spend": round(float(members["total_beauty_spend"].mean()), 2),
            "top_product": _mode_or_nan(members["favorite_beauty_product"]),
        })
    return pd.DataFrame(rows)


def segment_clients(beauty_txn_df: pd.DataFrame, rfm_df: pd.DataFrame):
    """Convenience wrapper: returns (client_profiles_df, segment_summary_df)."""
    profiles = build_client_profiles(beauty_txn_df, rfm_df)
    summary = build_segment_summary(profiles)
    return profiles, summary


def _print_summary(profiles: pd.DataFrame, summary: pd.DataFrame) -> None:
    print("=" * 60)
    print("SEGMENTATION SUMMARY")
    print("=" * 60)
    dist = profiles["beauty_segment"].value_counts()
    total = int(dist.sum())
    for seg, n in dist.items():
        print(f"  {seg:<18} {n:>4}")
    print(f"  {'TOTAL':<18} {total:>4}")

    print("\n  Segment summary (named segments):")
    print(summary.to_string(index=False))
    print("=" * 60)


if __name__ == "__main__":
    _, beauty_txn_df, _, rfm_df = load_data(verbose=False)
    profiles, summary = segment_clients(beauty_txn_df, rfm_df)
    _print_summary(profiles, summary)
