"""Load the four beauty CSVs from /data/ and return clean DataFrames."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

FILES = {
    "clients": "client_master.csv",
    "beauty_txn": "beauty_transactions.csv",
    "catalog": "product_catalog.csv",
    "rfm": "rfm_summary.csv",
}

REQUIRED_COLUMNS = {
    "clients": [
        "client_id", "first_name", "last_name", "nationality",
        "preferred_store", "store_name", "preferred_channel",
        "join_date", "last_visit_date", "days_since_last_visit",
    ],
    "beauty_txn": [
        "transaction_id", "client_id", "transaction_date", "channel",
        "category", "product_name", "quantity", "unit_price",
        "net_sales_amount", "primary_category", "secondary_category",
        "favorite_product",
    ],
    "catalog": [
        "product_id", "product_name", "category", "price_usd",
        "description", "target_segment", "is_bestseller", "launch_year",
    ],
    "rfm": [
        "client_id", "first_name", "last_name", "rfm_segment",
        "monetary_value", "frequency", "days_since_last_visit",
        "favorite_category", "preferred_channel", "preferred_store",
    ],
}

DATE_COLUMNS = {
    "clients": ["join_date", "last_visit_date"],
    "beauty_txn": ["transaction_date"],
    "catalog": [],
    "rfm": ["join_date", "last_visit_date"],
}


def _read_csv(key: str) -> pd.DataFrame:
    path = DATA_DIR / FILES[key]
    if not path.exists():
        raise FileNotFoundError(f"Expected data file not found: {path}")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS[key] if c not in df.columns]
    if missing:
        raise ValueError(
            f"{FILES[key]} is missing required columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    for col in DATE_COLUMNS[key]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()

    return df


def _print_summary(
    clients_df: pd.DataFrame,
    beauty_txn_df: pd.DataFrame,
    catalog_df: pd.DataFrame,
    rfm_df: pd.DataFrame,
) -> None:
    print("=" * 60)
    print("DATA LOAD SUMMARY")
    print("=" * 60)
    print(f"  clients:       {len(clients_df):>6,} rows  |  {clients_df.shape[1]} cols")
    print(f"  transactions:  {len(beauty_txn_df):>6,} rows  |  {beauty_txn_df.shape[1]} cols")
    print(f"  catalog:       {len(catalog_df):>6,} rows  |  {catalog_df.shape[1]} cols")
    print(f"  rfm_summary:   {len(rfm_df):>6,} rows  |  {rfm_df.shape[1]} cols")

    if "category" in beauty_txn_df.columns:
        top_cats = (
            beauty_txn_df["category"].value_counts(normalize=True).mul(100).round(1)
        )
        print("\n  Beauty category mix (% of transactions):")
        for cat, pct in top_cats.items():
            print(f"    - {cat:<12} {pct:>5}%")

    if "rfm_segment" in rfm_df.columns:
        seg_counts = rfm_df["rfm_segment"].value_counts()
        print("\n  RFM segment distribution:")
        for seg, n in seg_counts.items():
            print(f"    - {seg:<12} {n:>4}")
    print("=" * 60)


def load_data(verbose: bool = True):
    """Load all four CSVs and return (clients_df, beauty_txn_df, catalog_df, rfm_df)."""
    clients_df = _read_csv("clients")
    beauty_txn_df = _read_csv("beauty_txn")
    catalog_df = _read_csv("catalog")
    rfm_df = _read_csv("rfm")

    if "is_bestseller" in catalog_df.columns:
        catalog_df["is_bestseller"] = (
            catalog_df["is_bestseller"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False})
            .fillna(False)
        )

    for df, cols in [
        (beauty_txn_df, ["quantity", "unit_price", "net_sales_amount"]),
        (catalog_df, ["price_usd", "launch_year"]),
        (rfm_df, ["monetary_value", "frequency", "days_since_last_visit"]),
        (clients_df, ["days_since_last_visit"]),
    ]:
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    if verbose:
        _print_summary(clients_df, beauty_txn_df, catalog_df, rfm_df)

    return clients_df, beauty_txn_df, catalog_df, rfm_df


if __name__ == "__main__":
    load_data()
