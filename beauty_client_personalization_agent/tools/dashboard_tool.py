"""Streamlit view helpers for the Maison Solène DCX dashboard.

This module contains the reusable render functions. `app.py` at the project
root is the Streamlit entry and composes these helpers.

Color palette: black / cream / gold (luxury-beauty aesthetic).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))
from tools.segment_tool import SEGMENT_ORDER

BRAND_BLACK = "#0A0A0A"
BRAND_CREAM = "#F5EFE6"
BRAND_GOLD = "#B9985A"
BRAND_INK = "#2B2B2B"


def apply_brand_theme() -> None:
    st.markdown(
        f"""
        <style>
        html, body, [class*="css"] {{
            font-family: 'Didot', 'Bodoni 72', 'Times New Roman', serif;
        }}
        .stApp {{
            background-color: {BRAND_CREAM};
            color: {BRAND_INK};
        }}
        [data-testid="stSidebar"], [data-testid="stSidebar"] > div {{
            background-color: {BRAND_CREAM} !important;
            border-right: 1px solid {BRAND_GOLD};
        }}
        .stDeployButton, [data-testid="stDeployButton"] {{
            display: none !important;
        }}
        #MainMenu {{ visibility: hidden; }}
        .stButton > button, .stButton > button[kind="primary"] {{
            background-color: {BRAND_BLACK} !important;
            color: {BRAND_CREAM} !important;
            border: 1px solid {BRAND_GOLD} !important;
            border-radius: 2px !important;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-size: 0.85rem;
        }}
        .stButton > button:hover, .stButton > button[kind="primary"]:hover {{
            background-color: {BRAND_GOLD} !important;
            color: {BRAND_BLACK} !important;
            border: 1px solid {BRAND_BLACK} !important;
        }}
        h1, h2, h3, h4 {{
            color: {BRAND_BLACK};
            font-family: 'Didot', 'Bodoni 72', 'Times New Roman', serif;
            letter-spacing: 0.04em;
        }}
        .brand-card {{
            background: #ffffff;
            padding: 1.2rem 1.25rem;
            border: 1px solid {BRAND_GOLD};
            border-radius: 2px;
            height: 100%;
        }}
        .brand-product-name {{
            font-size: 1.1rem;
            font-weight: 600;
            color: {BRAND_BLACK};
        }}
        .brand-product-meta {{
            color: {BRAND_GOLD};
            font-size: 0.85rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin: 0.3rem 0 0.6rem 0;
        }}
        .brand-product-rationale {{
            color: {BRAND_INK};
            font-size: 0.9rem;
            font-style: italic;
        }}
        .brand-copy-box {{
            background: #ffffff;
            padding: 1.4rem;
            border: 1px solid {BRAND_GOLD};
            border-radius: 2px;
            min-height: 180px;
            white-space: pre-wrap;
            line-height: 1.55;
        }}
        .brand-winner {{
            background: {BRAND_BLACK};
            color: {BRAND_CREAM};
            padding: 1rem 1.4rem;
            border-radius: 2px;
            font-size: 1.1rem;
            letter-spacing: 0.08em;
            text-align: center;
        }}
        .brand-disclaimer {{
            color: #7a7a7a;
            font-size: 0.8rem;
            font-style: italic;
            margin-top: 0.75rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown("# Beauty Client Personalization Agent")
    st.markdown("##### DCX Intelligence — Powered by GenAI")
    st.markdown("---")


def render_overview(result: dict, store_filter: str = "All stores") -> None:
    st.markdown("## Segment Overview")

    profiles = result["client_profiles_df"]
    clients = result["clients_df"][["client_id", "store_name"]]
    merged = profiles.merge(clients, on="client_id", how="left")

    if store_filter != "All stores":
        merged = merged[
            merged["store_name"].fillna("").str.contains(store_filter, case=False)
        ]

    named = merged[merged["beauty_segment"].isin(SEGMENT_ORDER)]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total clients", f"{len(merged):,}")
    c2.metric("Named segments", int(named["beauty_segment"].nunique()))
    avg_spend = named["total_beauty_spend"].mean() if len(named) else 0.0
    c3.metric("Avg spend per named client", f"${avg_spend:,.0f}")

    counts = (
        named.groupby("beauty_segment").size().reindex(SEGMENT_ORDER, fill_value=0)
    )
    fig = go.Figure(
        go.Bar(
            x=list(counts.index),
            y=list(counts.values),
            marker=dict(color=BRAND_GOLD, line=dict(color=BRAND_BLACK, width=1)),
            text=[str(v) for v in counts.values],
            textposition="outside",
        )
    )
    fig.update_layout(
        title=dict(text="Clients per Beauty Segment", font=dict(color=BRAND_BLACK, size=18)),
        paper_bgcolor=BRAND_CREAM,
        plot_bgcolor=BRAND_CREAM,
        font=dict(family="Didot, Times New Roman, serif", color=BRAND_INK),
        margin=dict(t=60, b=40, l=40, r=40),
        showlegend=False,
    )
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

    summary = (
        _rebuild_summary(named)
        if store_filter != "All stores"
        else result["segment_summary"].copy()
    )
    summary = summary.rename(
        columns={
            "segment": "Segment",
            "client_count": "Clients",
            "avg_spend": "Avg Spend",
            "top_product": "Top Product",
        }
    )
    summary["Avg Spend"] = summary["Avg Spend"].apply(
        lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
    )
    summary["Clients"] = summary["Clients"].apply(lambda x: f"{int(x):,}")
    st.dataframe(summary, use_container_width=True, hide_index=True)


def render_personalization(result: dict, segment: str) -> None:
    st.markdown(f"## Personalization Output — {segment}")

    seg_data = result["per_segment"].get(segment)
    if seg_data is None:
        st.warning(f"No pipeline output available for segment '{segment}'.")
        return

    st.markdown("### Recommended Products")
    recs = seg_data["recommendations"]
    cols = st.columns(len(recs))
    for col, (_, r) in zip(cols, recs.iterrows()):
        with col:
            st.markdown(
                f"""
                <div class="brand-card">
                    <div class="brand-product-name">{r['product_name']}</div>
                    <div class="brand-product-meta">{r['category']} · ${r['price_usd']:,.2f}</div>
                    <div class="brand-product-rationale">{r['rationale']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("### Outreach Copy — A / B Comparison")
    left, right = st.columns(2)
    copy = seg_data["copy"]
    with left:
        st.markdown("**Variant A — Warm Boutique Advisor**")
        st.markdown(
            f"<div class='brand-copy-box'>{_escape(copy['variant_a'])}</div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown("**Variant B — Exclusive Aspirational**")
        st.markdown(
            f"<div class='brand-copy-box'>{_escape(copy['variant_b'])}</div>",
            unsafe_allow_html=True,
        )


def render_ab_results(result: dict, segment: str) -> None:
    st.markdown(f"## A/B Test Results — {segment}")

    seg_data = result["per_segment"].get(segment)
    if seg_data is None or seg_data["ab_results"].empty:
        st.warning(f"No A/B test results available for segment '{segment}'.")
        return

    ab = seg_data["ab_results"]
    a = ab[ab["variant"] == "Variant A"].iloc[0]
    b = ab[ab["variant"] == "Variant B"].iloc[0]

    st.markdown("#### Variant A")
    c1, c2, c3 = st.columns(3)
    c1.metric("Open rate", f"{a['open_rate']:.1%}")
    c2.metric("Click rate", f"{a['click_rate']:.1%}")
    c3.metric("Conversion rate", f"{a['conversion_rate']:.1%}")

    st.markdown("#### Variant B")
    c1, c2, c3 = st.columns(3)
    c1.metric("Open rate", f"{b['open_rate']:.1%}")
    c2.metric("Click rate", f"{b['click_rate']:.1%}")
    c3.metric("Conversion rate", f"{b['conversion_rate']:.1%}")

    metrics = ["open_rate", "click_rate", "conversion_rate"]
    labels = ["Open Rate", "Click Rate", "Conversion Rate"]
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Variant A",
            x=labels,
            y=[a[m] for m in metrics],
            marker_color=BRAND_INK,
        )
    )
    fig.add_trace(
        go.Bar(
            name="Variant B",
            x=labels,
            y=[b[m] for m in metrics],
            marker_color=BRAND_GOLD,
        )
    )
    fig.update_layout(
        barmode="group",
        title=dict(text="Variant A vs Variant B", font=dict(color=BRAND_BLACK, size=18)),
        paper_bgcolor=BRAND_CREAM,
        plot_bgcolor=BRAND_CREAM,
        font=dict(family="Didot, Times New Roman, serif", color=BRAND_INK),
        margin=dict(t=60, b=40, l=40, r=40),
        yaxis=dict(tickformat=".0%"),
    )
    st.plotly_chart(fig, use_container_width=True)

    winner = a["recommended_winner"]
    st.markdown(
        f"<div class='brand-winner'>Recommended: {winner} — higher conversion rate</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='brand-disclaimer'>{result['disclaimer']}.</div>",
        unsafe_allow_html=True,
    )


def _rebuild_summary(named_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for seg in SEGMENT_ORDER:
        sub = named_df[named_df["beauty_segment"] == seg]
        if sub.empty:
            rows.append({"segment": seg, "client_count": 0, "avg_spend": 0.0, "top_product": None})
            continue
        rows.append({
            "segment": seg,
            "client_count": int(len(sub)),
            "avg_spend": round(float(sub["total_beauty_spend"].mean()), 2),
            "top_product": sub["favorite_beauty_product"].mode().iloc[0]
            if not sub["favorite_beauty_product"].mode().empty else None,
        })
    return pd.DataFrame(rows)


def _escape(text: str) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
