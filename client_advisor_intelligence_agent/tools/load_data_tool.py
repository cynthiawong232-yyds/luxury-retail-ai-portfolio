"""Load Maison Vega client, transaction, and RFM data from /data into pandas DataFrames."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CLIENT_FILE = "client_master.csv"
TRANSACTION_FILE = "mv_transactions.csv"
RFM_FILE = "rfm_summary.csv"

REQUIRED_CLIENT_COLS = [
    "client_id", "first_name", "last_name", "nationality",
    "preferred_store", "store_name", "preferred_channel",
    "join_date", "last_visit_date", "days_since_last_visit",
]

REQUIRED_TRANSACTION_COLS = [
    "transaction_id", "client_id", "transaction_date", "store_code",
    "store_name", "category", "product_name", "quantity", "unit_price",
    "net_sales_amount", "channel",
]

REQUIRED_RFM_COLS = [
    "client_id", "first_name", "last_name", "nationality",
    "preferred_store", "store_name", "preferred_channel",
    "days_since_last_visit", "frequency", "monetary_value", "avg_order_value",
    "favorite_category", "recency_score", "frequency_score", "monetary_score",
    "rfm_total_score", "rfm_segment", "join_date", "last_visit_date",
]

DATE_COLS = {
    CLIENT_FILE: ["join_date", "last_visit_date"],
    TRANSACTION_FILE: ["transaction_date"],
    RFM_FILE: ["join_date", "last_visit_date"],
}


def _read_csv(filename: str, required_cols: list[str]) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Required data file not found: {path}")

    df = pd.read_csv(path)

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"{filename} is missing required columns: {missing}")

    for col in DATE_COLS.get(filename, []):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all three data files and return (clients_df, transactions_df, rfm_df)."""
    clients_df = _read_csv(CLIENT_FILE, REQUIRED_CLIENT_COLS)
    transactions_df = _read_csv(TRANSACTION_FILE, REQUIRED_TRANSACTION_COLS)
    rfm_df = _read_csv(RFM_FILE, REQUIRED_RFM_COLS)

    numeric_fills = {
        "days_since_last_visit": clients_df["days_since_last_visit"].median(),
    }
    clients_df = clients_df.fillna(value=numeric_fills)

    transactions_df["quantity"] = transactions_df["quantity"].fillna(0)
    transactions_df["net_sales_amount"] = transactions_df["net_sales_amount"].fillna(0.0)

    n_clients = len(clients_df)
    n_transactions = len(transactions_df)
    segments = rfm_df["rfm_segment"].value_counts().to_dict()

    print("[load_data_tool] Data loaded successfully.")
    print(f"  Clients:      {n_clients}")
    print(f"  Transactions: {n_transactions}")
    print(f"  Segments:     {segments}")

    return clients_df, transactions_df, rfm_df


if __name__ == "__main__":
    load_data()
