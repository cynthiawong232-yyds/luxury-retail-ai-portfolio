"""Query transaction history for a client, category, or segment."""

from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd

from tools.load_data_tool import load_data


def transaction_query(
    transactions_df: Optional[pd.DataFrame] = None,
    client_id: Optional[str] = None,
    client_ids: Optional[Iterable[str]] = None,
    category: Optional[str] = None,
    start_date: Optional[str | pd.Timestamp] = None,
    end_date: Optional[str | pd.Timestamp] = None,
) -> pd.DataFrame:
    """Filter transactions by client(s), category, and/or date range.

    All filters are AND-combined. Returns rows sorted newest-first.
    """
    if transactions_df is None:
        _, transactions_df, _ = load_data()

    df = transactions_df.copy()

    if client_id:
        df = df[df["client_id"] == client_id.upper()]

    if client_ids:
        ids = {c.upper() for c in client_ids}
        df = df[df["client_id"].isin(ids)]

    if category:
        df = df[df["category"].str.lower() == category.strip().lower()]

    if start_date is not None:
        df = df[df["transaction_date"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df["transaction_date"] <= pd.to_datetime(end_date)]

    df = df.sort_values("transaction_date", ascending=False).reset_index(drop=True)

    print(f"[transaction_query_tool] Returned {len(df)} transaction(s).")
    return df


def transaction_summary(transactions_df: pd.DataFrame) -> dict:
    """Compute key metrics from a transactions DataFrame.

    Returns: total_spend, num_transactions, num_visits, favorite_category,
    category_breakdown, last_purchase_date, first_purchase_date.
    """
    if transactions_df is None or len(transactions_df) == 0:
        return {
            "total_spend": 0.0,
            "num_transactions": 0,
            "num_visits": 0,
            "favorite_category": None,
            "category_breakdown": {},
            "last_purchase_date": None,
            "first_purchase_date": None,
        }

    category_spend = (
        transactions_df.groupby("category")["net_sales_amount"].sum().sort_values(ascending=False)
    )
    favorite_category = category_spend.index[0] if len(category_spend) > 0 else None

    return {
        "total_spend": float(transactions_df["net_sales_amount"].sum()),
        "num_transactions": int(len(transactions_df)),
        "num_visits": int(transactions_df["transaction_date"].dt.normalize().nunique()),
        "favorite_category": favorite_category,
        "category_breakdown": {k: float(v) for k, v in category_spend.items()},
        "last_purchase_date": transactions_df["transaction_date"].max(),
        "first_purchase_date": transactions_df["transaction_date"].min(),
    }


def category_breakdown_for_clients(
    transactions_df: pd.DataFrame, client_ids: Iterable[str]
) -> pd.DataFrame:
    """Aggregate spend per category across a list of client IDs (e.g. a segment)."""
    subset = transaction_query(transactions_df, client_ids=client_ids)
    if len(subset) == 0:
        return pd.DataFrame(columns=["category", "total_spend", "num_transactions"])

    grouped = (
        subset.groupby("category")
        .agg(total_spend=("net_sales_amount", "sum"), num_transactions=("transaction_id", "count"))
        .sort_values("total_spend", ascending=False)
        .reset_index()
    )
    return grouped


def _resolve_product_name(transactions_df: pd.DataFrame, query: str) -> Optional[str]:
    """Fuzzy-match a user phrase to a canonical product_name in the data.

    Strategy: exact (case-insensitive) -> substring -> token overlap.
    Returns the canonical product_name, or None if no confident match.
    """
    if not query:
        return None
    products = transactions_df["product_name"].dropna().unique().tolist()
    q = query.strip().lower()

    for p in products:
        if p.lower() == q:
            return p

    substring_hits = [p for p in products if q in p.lower()]
    if len(substring_hits) == 1:
        return substring_hits[0]
    if len(substring_hits) > 1:
        substring_hits.sort(key=len)
        return substring_hits[0]

    q_tokens = {t for t in q.replace("-", " ").split() if t and t != "mv"}
    if not q_tokens:
        return None
    best_p, best_score = None, 0
    for p in products:
        p_tokens = {t.lower() for t in p.replace("-", " ").split() if t.lower() != "mv"}
        score = len(q_tokens & p_tokens)
        if score > best_score:
            best_p, best_score = p, score
    if best_score >= 2:
        return best_p
    return None


def product_contribution(
    transactions_df: pd.DataFrame,
    product_name: str,
    rfm_df: Optional[pd.DataFrame] = None,
) -> tuple[pd.DataFrame, dict]:
    """Return per-client spend on a product and each client's % of that product's total sales.

    Returns (buyers_df, meta) where:
      buyers_df columns: client_id, name, nationality, store_name, client_spend,
                        units, pct_of_product_sales
      meta: resolved product_name, product_total_sales, num_buyers, num_units
    """
    resolved = _resolve_product_name(transactions_df, product_name)
    if resolved is None:
        return pd.DataFrame(), {
            "product_name": None,
            "query": product_name,
            "product_total_sales": 0.0,
            "num_buyers": 0,
            "num_units": 0,
        }

    subset = transactions_df[transactions_df["product_name"] == resolved]
    product_total = float(subset["net_sales_amount"].sum())
    num_units = int(subset["quantity"].sum())

    grouped = (
        subset.groupby("client_id")
        .agg(
            client_spend=("net_sales_amount", "sum"),
            units=("quantity", "sum"),
        )
        .reset_index()
    )
    grouped["pct_of_product_sales"] = (
        grouped["client_spend"] / product_total * 100 if product_total > 0 else 0.0
    )

    if rfm_df is not None and len(rfm_df) > 0:
        merged = grouped.merge(
            rfm_df[["client_id", "first_name", "last_name", "nationality", "store_name", "rfm_segment"]],
            on="client_id",
            how="left",
        )
        merged["name"] = (merged["first_name"].fillna("") + " " + merged["last_name"].fillna("")).str.strip()
        buyers = merged[
            ["client_id", "name", "nationality", "store_name", "rfm_segment",
             "client_spend", "units", "pct_of_product_sales"]
        ]
    else:
        buyers = grouped[["client_id", "client_spend", "units", "pct_of_product_sales"]]

    buyers = buyers.sort_values("client_spend", ascending=False).reset_index(drop=True)

    meta = {
        "product_name": resolved,
        "query": product_name,
        "product_total_sales": product_total,
        "num_buyers": int(len(buyers)),
        "num_units": num_units,
    }
    print(f"[transaction_query_tool] Product '{resolved}': {len(buyers)} buyer(s), ${product_total:,.0f} total.")
    return buyers, meta


def top_products(
    transactions_df: pd.DataFrame,
    store_code: Optional[str] = None,
    category: Optional[str] = None,
    top_n: int = 5,
) -> tuple[pd.DataFrame, dict]:
    """Rank products by net sales, optionally scoped to a store and/or category.

    Returns (ranked_df, meta) where:
      ranked_df columns: product_name, category, total_sales, units_sold,
                        num_buyers, pct_of_scope_sales
      meta: store_code, category, scope_total_sales, num_products
    """
    df = transactions_df.copy()
    if store_code:
        df = df[df["store_code"] == store_code]
    if category:
        df = df[df["category"].str.lower() == category.strip().lower()]

    if len(df) == 0:
        return pd.DataFrame(), {
            "store_code": store_code,
            "category": category,
            "scope_total_sales": 0.0,
            "num_products": 0,
        }

    scope_total = float(df["net_sales_amount"].sum())

    grouped = (
        df.groupby(["product_name", "category"])
        .agg(
            total_sales=("net_sales_amount", "sum"),
            units_sold=("quantity", "sum"),
            num_buyers=("client_id", "nunique"),
        )
        .reset_index()
    )
    grouped["pct_of_scope_sales"] = (
        grouped["total_sales"] / scope_total * 100 if scope_total > 0 else 0.0
    )
    grouped = grouped.sort_values("total_sales", ascending=False).reset_index(drop=True)

    num_products = int(len(grouped))
    if top_n and top_n > 0:
        grouped = grouped.head(top_n)

    meta = {
        "store_code": store_code,
        "category": category,
        "scope_total_sales": scope_total,
        "num_products": num_products,
    }
    scope_label = store_code or "all stores"
    print(f"[transaction_query_tool] Top {len(grouped)} products at {scope_label}: ${scope_total:,.0f} total.")
    return grouped, meta


def client_contribution(
    transactions_df: pd.DataFrame,
    client_id: str,
    preferred_store: Optional[str] = None,
) -> dict:
    """Compute a client's sales contribution at store and global level.

    Returns: client_spend, store_total_sales, global_total_sales,
             pct_of_store_sales, pct_of_global_sales, preferred_store.

    Store denominator uses the client's preferred_store if provided, else the
    store where the client has spent the most.
    """
    client_txns = transactions_df[transactions_df["client_id"] == client_id.upper()]
    client_spend = float(client_txns["net_sales_amount"].sum())

    if preferred_store is None and len(client_txns) > 0:
        preferred_store = (
            client_txns.groupby("store_code")["net_sales_amount"].sum().idxmax()
        )

    store_total = 0.0
    if preferred_store:
        store_total = float(
            transactions_df[transactions_df["store_code"] == preferred_store]["net_sales_amount"].sum()
        )

    global_total = float(transactions_df["net_sales_amount"].sum())

    pct_store = (client_spend / store_total * 100) if store_total > 0 else 0.0
    pct_global = (client_spend / global_total * 100) if global_total > 0 else 0.0

    return {
        "client_id": client_id.upper(),
        "client_spend": client_spend,
        "preferred_store": preferred_store,
        "store_total_sales": store_total,
        "global_total_sales": global_total,
        "pct_of_store_sales": pct_store,
        "pct_of_global_sales": pct_global,
    }


if __name__ == "__main__":
    _, transactions_df, _ = load_data()

    print("\n--- All transactions for MVC-00042 ---")
    txns = transaction_query(transactions_df, client_id="MVC-00042")
    print(txns.head(10))
    print("\nSummary:")
    summary = transaction_summary(txns)
    for k, v in summary.items():
        if k == "category_breakdown":
            print(f"  {k}:")
            for cat, amt in v.items():
                print(f"    {cat}: ${amt:,.2f}")
        else:
            print(f"  {k}: {v}")
