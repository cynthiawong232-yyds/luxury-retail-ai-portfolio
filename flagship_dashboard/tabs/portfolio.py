import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.data_loader import (
    store_totals, cross_store_dim, sector_breakdown,
    gender_breakdown, label_breakdown, subcategory_breakdown,
    calc_wos, calc_disc_rate, MERCH_DIMS
)
from utils.charts import (
    portfolio_bar, variance_bar, ramp_chart,
    dim_mix_chart, cross_store_dim_chart
)
from config import STORES

COLORS = {'US': '#c8a96e', 'EU': '#8cb4c3', 'Asia': '#c47b7b', 'mid': '#888880'}


def _kpi_card(label, value, sub, var_pct=None, region='', new_store=False):
    region_class = region.lower()
    if new_store or var_pct is None:
        var_html = '<span class="kpi-var na">NEW STORE</span>'
    elif var_pct >= 0:
        var_html = f'<span class="kpi-var pos">▲ {var_pct:+.1f}%</span>'
    else:
        var_html = f'<span class="kpi-var neg">▼ {var_pct:.1f}%</span>'

    return f"""
    <div class="kpi-card {region_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
        <div style="margin-top:0.4rem">{var_html}</div>
    </div>
    """


def render(data: dict, period: str):
    totals = store_totals(data)

    # ── Portfolio KPI cards ───────────────────────────────────────────────────
    st.markdown('<div class="section-header">PORTFOLIO OVERVIEW</div>',
                unsafe_allow_html=True)

    cols = st.columns(len(totals))
    for i, (_, row) in enumerate(totals.iterrows()):
        with cols[i]:
            net_cy  = row['netslsamt_cy']
            net_ly  = row['netslsamt_ly']
            var_pct = (net_cy / net_ly - 1) * 100 if net_ly > 0 else None
            weeks   = row.get('weeks_open')
            region  = row['store_region']
            flag    = row['store_flag']
            label   = row['store_label']
            is_new  = net_ly == 0

            wos  = calc_wos(data[row['store_code']])
            disc = calc_disc_rate(data[row['store_code']]) * 100

            st.markdown(
                f'<div class="store-pill {region.lower()}">'
                f'{flag} {label} · {region}</div>',
                unsafe_allow_html=True
            )
            if weeks:
                st.markdown(
                    f'<div class="maturity-badge">WEEK {int(weeks)} SINCE OPENING</div>',
                    unsafe_allow_html=True
                )
            st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
            st.markdown(_kpi_card(
                f"{period} NET SALES", f"${net_cy:,.0f}", f"LY ${net_ly:,.0f}",
                var_pct=var_pct, region=region, new_store=is_new,
            ), unsafe_allow_html=True)
            qty_cy  = row['netslsqty_cy']
            qty_ly  = row['netslsqty_ly']
            qty_var = (qty_cy / qty_ly - 1) * 100 if qty_ly > 0 else None
            st.markdown(_kpi_card(
                "UNITS SOLD", f"{qty_cy:,.0f}", f"LY {qty_ly:,.0f}",
                var_pct=qty_var, region=region, new_store=is_new,
            ), unsafe_allow_html=True)
            st.markdown(_kpi_card("WOS", f"{wos:.1f}", "weeks of supply",
                                  region=region), unsafe_allow_html=True)
            st.markdown(_kpi_card("DISC RATE", f"{disc:.1f}%", "net vs MSRP",
                                  region=region), unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<br>', unsafe_allow_html=True)

    # ── Ramp + variance charts ────────────────────────────────────────────────
    c1, c2 = st.columns([3, 2])
    with c1:
        st.plotly_chart(ramp_chart(totals, period), use_container_width=True)
    with c2:
        st.plotly_chart(variance_bar(totals), use_container_width=True)

    st.plotly_chart(portfolio_bar(totals), use_container_width=True)

    # ── Cross-store dimension breakdown ───────────────────────────────────────
    st.markdown('<div class="section-header">CROSS-MARKET MIX COMPARISON</div>',
                unsafe_allow_html=True)
    st.caption("Compare how each market's sales mix differs across dimensions.")

    # Dimension selector
    dim_choice = st.selectbox(
        "View by",
        options=list(MERCH_DIMS.keys()),
        key="portfolio_dim"
    )
    dim_col = MERCH_DIMS[dim_choice]

    combined = cross_store_dim(data, dim_col)
    if not combined.empty:
        st.plotly_chart(
            cross_store_dim_chart(combined, dim_col, dim_choice),
            use_container_width=True
        )

        # Mix % table per store side by side
        st.markdown(f'<div class="section-header">{dim_choice.upper()} MIX % BY STORE</div>',
                    unsafe_allow_html=True)
        pivot = combined.pivot_table(
            index=dim_col,
            columns='_store_label',
            values='mix_pct_cy',
            aggfunc='sum'
        ).fillna(0).reset_index()
        pivot.columns.name = None
        pivot = pivot.rename(columns={dim_col: dim_choice})
        pivot = pivot.sort_values(
            pivot.columns[1], ascending=False
        ) if len(pivot.columns) > 1 else pivot

        fmt = {col: '{:.1f}%' for col in pivot.columns if col != dim_choice}
        st.dataframe(
            pivot.style.format(fmt),
            hide_index=True,
            use_container_width=True
        )

    # ── Per-store dimension mix charts ────────────────────────────────────────
    st.markdown('<div class="section-header">STORE-LEVEL MIX BREAKDOWN</div>',
                unsafe_allow_html=True)

    for code, df in data.items():
        info   = STORES[code]
        region = info['region']
        label  = info['label']
        flag   = info['flag']

        st.markdown(
            f'<div class="store-pill {region.lower()}">{flag} {label}</div>',
            unsafe_allow_html=True
        )

        c1, c2, c3, c4 = st.columns(4)
        charts = [
            (c1, "SECTOR",       sector_breakdown(df),      'gmh_sector_text'),
            (c2, "GENDER",       gender_breakdown(df),      'gmh_gender_text'),
            (c3, "LABEL",        label_breakdown(df),       'gmh_sub_brand_text'),
            (c4, "SUB-CATEGORY", subcategory_breakdown(df), 'gmh_sub_category_text'),
        ]
        for col, title, breakdown_df, bcol in charts:
            with col:
                st.plotly_chart(
                    dim_mix_chart(breakdown_df, bcol, title, region),
                    use_container_width=True
                )
        st.markdown('<br>', unsafe_allow_html=True)

    # ── New store notes ───────────────────────────────────────────────────────
    new_stores = [
        (code, info) for code, info in STORES.items()
        if code in data and
        totals.loc[totals['store_code'] == code, 'netslsamt_ly'].values[0] == 0
    ]
    if new_stores:
        st.markdown('<div class="section-header">NEW STORE NOTES</div>',
                    unsafe_allow_html=True)
        for code, info in new_stores:
            row   = totals[totals['store_code'] == code].iloc[0]
            weeks = row.get('weeks_open', '?')
            st.markdown(f"""
            <div class="alert-card info">
                <strong>{info['flag']} {info['label']} ({info['region']})</strong>
                — No prior year comparable. Store is in week <strong>{weeks}</strong>
                since opening. Focus on absolute trajectory and mix rather than comp %.
            </div>
            """, unsafe_allow_html=True)
