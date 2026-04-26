"""Query the RFM summary for segment-level questions."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from tools.load_data_tool import load_data

VALID_SEGMENTS = {"VIP", "High Value", "Active", "Dormant"}

STORE_ALIASES = {
    # SOHO / New York / USA
    "A800": "A800",
    "SOHO": "A800",
    "MV SOHO NEW YORK": "A800",
    "NEW YORK": "A800",
    "NYC": "A800",
    "USA": "A800",
    "UNITED STATES": "A800",
    "AMERICA": "A800",
    # Tokyo / Japan
    "J347": "J347",
    "TOKYO": "J347",
    "MV FLAGSHIP TOKYO": "J347",
    "JAPAN": "J347",
    # Paris / France / Europe
    "EU_F07M": "EU_F07M",
    "PARIS": "EU_F07M",
    "MV FLAGSHIP PARIS": "EU_F07M",
    "FRANCE": "EU_F07M",
    "EUROPE": "EU_F07M",
}

DEFAULT_RESULT_COLS = [
    "client_id", "first_name", "last_name", "nationality",
    "preferred_store", "store_name", "rfm_segment",
    "monetary_value", "frequency", "days_since_last_visit",
    "favorite_category", "rfm_total_score", "last_visit_date",
]


def _resolve_store(store: Optional[str]) -> Optional[str]:
    """Map an aliased store string to a canonical store code, or None for All/empty."""
    if not store:
        return None
    s = store.strip().upper()
    if s in {"ALL", "ANY", ""}:
        return None
    return STORE_ALIASES.get(s, store)


def _normalize_segment(segment: Optional[str]) -> Optional[str]:
    if not segment:
        return None
    s = segment.strip().lower()
    for valid in VALID_SEGMENTS:
        if s == valid.lower():
            return valid
    return None


def rfm_query(
    rfm_df: Optional[pd.DataFrame] = None,
    segment: Optional[str] = None,
    store: Optional[str] = None,
    nationality: Optional[str] = None,
    favorite_category: Optional[str] = None,
    lapsing: bool = False,
    min_monetary_value: Optional[float] = None,
    top_n: Optional[int] = None,
    sort_by: str = "monetary_value",
    ascending: bool = False,
) -> pd.DataFrame:
    """Filter the RFM summary by the given criteria and return a DataFrame.

    All filters are AND-combined. Returns DEFAULT_RESULT_COLS columns by default.
    If no rows match, returns an empty DataFrame with those columns.
    """
    if rfm_df is None:
        _, _, rfm_df = load_data()

    df = rfm_df.copy()

    seg = _normalize_segment(segment)
    if seg:
        df = df[df["rfm_segment"] == seg]

    store_code = _resolve_store(store)
    if store_code:
        df = df[df["preferred_store"] == store_code]

    if nationality:
        df = df[df["nationality"].str.lower() == nationality.strip().lower()]

    if favorite_category:
        df = df[df["favorite_category"].str.lower() == favorite_category.strip().lower()]

    if lapsing:
        # Lapsing = Dormant OR (High Value with recency > 90 days)
        mask = (df["rfm_segment"] == "Dormant") | (
            (df["rfm_segment"] == "High Value") & (df["days_since_last_visit"] > 90)
        )
        df = df[mask]

    if min_monetary_value is not None:
        df = df[df["monetary_value"] >= min_monetary_value]

    if sort_by in df.columns:
        df = df.sort_values(by=sort_by, ascending=ascending)

    if top_n is not None and top_n > 0:
        df = df.head(top_n)

    cols = [c for c in DEFAULT_RESULT_COLS if c in df.columns]
    result = df[cols].reset_index(drop=True)

    print(f"[rfm_query_tool] Returned {len(result)} client(s).")
    return result


if __name__ == "__main__":
    _, _, rfm_df = load_data()

    print("\n--- All VIP clients ---")
    print(rfm_query(rfm_df, segment="VIP").head())

    print("\n--- Top 5 by monetary value ---")
    print(rfm_query(rfm_df, top_n=5))

    print("\n--- Lapsing clients ---")
    print(rfm_query(rfm_df, lapsing=True).head())

    print("\n--- Tokyo clients ---")
    print(rfm_query(rfm_df, store="Tokyo").head())

    print("\n--- Japanese clients who prefer Handbags ---")
    print(rfm_query(rfm_df, nationality="Japanese", favorite_category="Handbags"))
