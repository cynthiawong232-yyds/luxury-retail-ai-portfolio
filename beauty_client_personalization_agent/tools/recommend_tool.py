"""Rule-based product recommender for each Maison Solène beauty segment.

Given a segment name and the catalog, returns the top N recommended products
with a one-line rationale. No ML — just luxury-retail heuristics.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from tools.load_data_tool import load_data
from tools.segment_tool import SEGMENT_ORDER, segment_clients

CATEGORY_BY_SEGMENT = {
    "Fragrance VIP": "Fragrance",
    "Skincare Devotee": "Skincare",
    "Makeup Enthusiast": "Makeup",
}

VIP_SEGMENTS = {"Fragrance VIP"}

EXPLORER_CATEGORIES = ["Fragrance", "Skincare", "Hair Care", "Body Care", "Makeup"]

REC_COLUMNS = ["product_name", "category", "price_usd", "rationale"]


def recommend_products(
    segment_name: str,
    catalog_df: pd.DataFrame,
    segment_summary: pd.DataFrame | None = None,
    top_n: int = 3,
) -> pd.DataFrame:
    """Return top-N recommendations for a segment as a DataFrame."""
    if segment_name not in SEGMENT_ORDER:
        raise ValueError(
            f"Unknown segment '{segment_name}'. Expected one of {SEGMENT_ORDER}."
        )

    if segment_name == "Beauty Explorer":
        rows = _explorer_picks(catalog_df, top_n=top_n)
    else:
        category = CATEGORY_BY_SEGMENT[segment_name]
        pool = catalog_df[catalog_df["category"] == category]
        if pool.empty:
            raise ValueError(f"No catalog products in category '{category}'.")
        ranked = _rank_pool(pool, is_vip=segment_name in VIP_SEGMENTS)
        rows = [ranked.iloc[i] for i in range(min(top_n, len(ranked)))]

    recs = [_to_rec(row, segment_name) for row in rows]
    df = pd.DataFrame(recs, columns=REC_COLUMNS)
    if segment_summary is not None:
        _ = segment_summary  # reserved for future personalization
    return df


def recommend_for_all_segments(
    catalog_df: pd.DataFrame,
    segment_summary: pd.DataFrame | None = None,
    top_n: int = 3,
) -> dict[str, pd.DataFrame]:
    """Return {segment_name: recs_df} for every named segment."""
    return {
        seg: recommend_products(seg, catalog_df, segment_summary, top_n=top_n)
        for seg in SEGMENT_ORDER
    }


def _rank_pool(pool: pd.DataFrame, is_vip: bool) -> pd.DataFrame:
    price_ascending = not is_vip
    return pool.sort_values(
        by=["is_bestseller", "price_usd"],
        ascending=[False, price_ascending],
    ).reset_index(drop=True)


def _explorer_picks(catalog_df: pd.DataFrame, top_n: int) -> list[pd.Series]:
    """One pick per category across EXPLORER_CATEGORIES until we hit top_n."""
    picks = []
    for cat in EXPLORER_CATEGORIES:
        if len(picks) >= top_n:
            break
        pool = catalog_df[catalog_df["category"] == cat]
        if pool.empty:
            continue
        ranked = pool.sort_values(
            by=["is_bestseller", "price_usd"], ascending=[False, False]
        ).reset_index(drop=True)
        picks.append(ranked.iloc[0])
    return picks


def _to_rec(row: pd.Series, segment_name: str) -> dict:
    return {
        "product_name": row["product_name"],
        "category": row["category"],
        "price_usd": float(row["price_usd"]),
        "rationale": _rationale(row, segment_name),
    }


_SEGMENT_ANGLES = {
    "Fragrance VIP": "an anchor for our top-value Fragrance clients.",
    "Skincare Devotee": "aligned with the segment's primary category.",
    "Makeup Enthusiast": "a refined complement for Makeup-led clients.",
    "Beauty Explorer": "broadens the segment's beauty repertoire.",
}


def _rationale(row: pd.Series, segment_name: str) -> str:
    bestseller = bool(row.get("is_bestseller", False))
    category = row["category"]
    try:
        year = int(row.get("launch_year")) if pd.notna(row.get("launch_year")) else 0
    except (TypeError, ValueError):
        year = 0

    if bestseller and year and year <= 2020:
        lead = f"Bestseller · House icon since {year}"
    elif bestseller and year and year >= 2023:
        lead = f"Bestseller · introduced {year}"
    elif bestseller:
        lead = f"Bestseller in {category}"
    elif year and year <= 2020:
        lead = f"House icon since {year}"
    elif year and year >= 2023:
        lead = f"Newly introduced in {year}"
    else:
        lead = f"Signature {category}"

    angle = _SEGMENT_ANGLES.get(
        segment_name, f"broadens the segment's beauty repertoire in {category}."
    )
    return f"{lead} — {angle}"


def _print_summary(recs_by_segment: dict[str, pd.DataFrame]) -> None:
    print("=" * 70)
    print("RECOMMENDATIONS PER SEGMENT")
    print("=" * 70)
    for seg, df in recs_by_segment.items():
        print(f"\n  {seg}")
        print("  " + "-" * (len(seg)))
        for _, r in df.iterrows():
            print(
                f"    - {r['product_name']:<28} "
                f"{r['category']:<10} "
                f"${r['price_usd']:>6.2f}"
            )
            print(f"        {r['rationale']}")
    print("=" * 70)


if __name__ == "__main__":
    _, beauty_txn_df, catalog_df, rfm_df = load_data(verbose=False)
    _, segment_summary = segment_clients(beauty_txn_df, rfm_df)
    recs = recommend_for_all_segments(catalog_df, segment_summary, top_n=3)
    _print_summary(recs)
