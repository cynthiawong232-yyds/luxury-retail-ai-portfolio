"""Identify clients who need immediate advisor attention.

Alert types:
  - Lapsing VIP        : VIP, not seen in 60+ days
  - Lapsing High Value : High Value, not seen in 90+ days
  - Anniversary        : join_date anniversary within next 30 days
  - Win-back           : Dormant, monetary_value > $2,000
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from tools.load_data_tool import load_data

DEFAULT_VIP_LAPSE_DAYS = 60
DEFAULT_HV_LAPSE_DAYS = 90
DEFAULT_ANNIVERSARY_WINDOW_DAYS = 30
DEFAULT_WINBACK_MIN_VALUE = 2000.0

PRIORITY_RANK = {
    "Lapsing VIP": 1,
    "Lapsing High Value": 2,
    "Win-back": 3,
    "Anniversary": 4,
}

ALERT_RESULT_COLS = [
    "client_id", "first_name", "last_name", "rfm_segment",
    "preferred_store", "store_name", "nationality",
    "monetary_value", "days_since_last_visit", "last_visit_date",
    "join_date", "alert_type", "alert_reason", "priority",
]


def _days_until_anniversary(join_date: pd.Timestamp, today: pd.Timestamp) -> Optional[int]:
    if pd.isna(join_date):
        return None
    try:
        anniversary_this_year = join_date.replace(year=today.year)
    except ValueError:
        # Feb 29 join — treat as Feb 28
        anniversary_this_year = join_date.replace(year=today.year, day=28)
    if anniversary_this_year < today:
        try:
            anniversary_this_year = join_date.replace(year=today.year + 1)
        except ValueError:
            anniversary_this_year = join_date.replace(year=today.year + 1, day=28)
    return (anniversary_this_year - today).days


def get_alerts(
    rfm_df: Optional[pd.DataFrame] = None,
    days_since_visit: Optional[int] = None,
    segment: Optional[str] = None,
    min_monetary_value: Optional[float] = None,
    store: Optional[str] = None,
    today: Optional[pd.Timestamp] = None,
    anniversary_window: int = DEFAULT_ANNIVERSARY_WINDOW_DAYS,
) -> pd.DataFrame:
    """Return a prioritized DataFrame of clients flagged by any alert rule.

    Optional filters narrow the result post-flagging.
    """
    if rfm_df is None:
        _, _, rfm_df = load_data()

    today = pd.Timestamp(today) if today is not None else pd.Timestamp.today().normalize()

    rows: list[dict] = []

    vip_threshold = days_since_visit if days_since_visit is not None else DEFAULT_VIP_LAPSE_DAYS
    hv_threshold = days_since_visit if days_since_visit is not None else DEFAULT_HV_LAPSE_DAYS

    for _, r in rfm_df.iterrows():
        seg = r["rfm_segment"]
        days = r["days_since_last_visit"]
        monetary = r["monetary_value"]

        if seg == "VIP" and days >= vip_threshold:
            rows.append({
                **r.to_dict(),
                "alert_type": "Lapsing VIP",
                "alert_reason": f"VIP client not seen in {int(days)} days",
                "priority": PRIORITY_RANK["Lapsing VIP"],
            })

        if seg == "High Value" and days >= hv_threshold:
            rows.append({
                **r.to_dict(),
                "alert_type": "Lapsing High Value",
                "alert_reason": f"High Value client not seen in {int(days)} days",
                "priority": PRIORITY_RANK["Lapsing High Value"],
            })

        if seg == "Dormant" and monetary > DEFAULT_WINBACK_MIN_VALUE:
            rows.append({
                **r.to_dict(),
                "alert_type": "Win-back",
                "alert_reason": f"Dormant client with ${monetary:,.0f} lifetime spend",
                "priority": PRIORITY_RANK["Win-back"],
            })

        days_to_anniv = _days_until_anniversary(r["join_date"], today)
        if days_to_anniv is not None and 0 <= days_to_anniv <= anniversary_window:
            rows.append({
                **r.to_dict(),
                "alert_type": "Anniversary",
                "alert_reason": f"Join anniversary in {days_to_anniv} days",
                "priority": PRIORITY_RANK["Anniversary"],
            })

    if not rows:
        print("[alert_tool] No alerts generated.")
        return pd.DataFrame(columns=ALERT_RESULT_COLS)

    alerts = pd.DataFrame(rows)

    if segment:
        alerts = alerts[alerts["rfm_segment"].str.lower() == segment.strip().lower()]
    if min_monetary_value is not None:
        alerts = alerts[alerts["monetary_value"] >= min_monetary_value]
    if store:
        alerts = alerts[
            (alerts["preferred_store"].str.upper() == store.upper())
            | (alerts["store_name"].str.lower() == store.lower())
        ]

    alerts = alerts.sort_values(
        by=["priority", "monetary_value"], ascending=[True, False]
    ).reset_index(drop=True)

    cols = [c for c in ALERT_RESULT_COLS if c in alerts.columns]
    result = alerts[cols]

    print(f"[alert_tool] Generated {len(result)} alert(s) across {alerts['alert_type'].nunique()} type(s).")
    return result


if __name__ == "__main__":
    _, _, rfm_df = load_data()
    alerts = get_alerts(rfm_df, today=pd.Timestamp("2026-04-16"))
    print("\n--- Alert breakdown ---")
    print(alerts["alert_type"].value_counts())
    print("\n--- Top 10 priority alerts ---")
    print(alerts.head(10)[["client_id", "rfm_segment", "alert_type", "alert_reason"]])
