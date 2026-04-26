import streamlit as st
import pandas as pd
from utils.data_loader import (
    sector_breakdown, gender_breakdown, label_breakdown,
    subcategory_breakdown, style_table, program_breakdown,
    calc_wos, calc_disc_rate, calc_sell_through,
    load_program_names, apply_filters, MERCH_DIMS
)
from utils.charts import dim_bar_chart, dim_mix_chart, gender_donut
from config import STORES, CHANNEL_LABELS


def _mix_table(breakdown_df: pd.DataFrame, dim_col: str, dim_label: str,
               is_new: bool) -> None:
    """Render a styled breakdown table with mix% and YoY%."""
    display = breakdown_df[[
        dim_col, 'netslsamt_cy', 'mix_pct_cy',
        'netslsqty_cy', 'aur_cy',
        'netslsamt_ly', 'mix_pct_ly', 'var_pct'
    ]].rename(columns={
        dim_col:        dim_label,
        'netslsamt_cy': 'Net Sales CY',
        'mix_pct_cy':   'Mix % CY',
        'netslsqty_cy': 'Units CY',
        'aur_cy':       'AUR CY',
        'netslsamt_ly': 'Net Sales LY',
        'mix_pct_ly':   'Mix % LY',
        'var_pct':      'YoY %',
    })

    def color_yoy(val):
        if pd.isna(val): return 'color: #888880'
        return f'color: {"#4a7c59" if val >= 0 else "#8b3a3a"}'

    fmt = {
        'Net Sales CY': '${:,.0f}',
        'Mix % CY':     '{:.1f}%',
        'Units CY':     '{:,.0f}',
        'AUR CY':       '${:.2f}',
        'Net Sales LY': '${:,.0f}',
        'Mix % LY':     '{:.1f}%',
        'YoY %':        lambda v: f'{v:+.1f}%' if pd.notna(v) else 'NEW',
    }

    st.dataframe(
        display.style.format(fmt).map(color_yoy, subset=['YoY %']),
        hide_index=True,
        use_container_width=True
    )


def render(data: dict, period: str):
    # ── Store selector ────────────────────────────────────────────────────────
    store_options = {
        code: f"{STORES[code]['flag']} {STORES[code]['label']} ({STORES[code]['region']})"
        for code in data
    }
    selected_code = st.selectbox(
        "Select Store",
        options=list(store_options.keys()),
        format_func=lambda c: store_options[c],
        key="deep_dive_store"
    )

    df     = data[selected_code]
    info   = STORES[selected_code]
    region = info['region']
    flag   = info['flag']
    label  = info['label']
    weeks  = df['_weeks_open'].iloc[0]
    is_new = df['netslsamt_ly'].sum() == 0

    # ── Store header ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex; align-items:baseline; gap:1rem; margin:1rem 0 0.5rem;">
        <span class="ck-logo" style="font-size:1.4rem;">{flag} {label}</span>
        <span class="store-pill {region.lower()}">{region}</span>
        <span class="maturity-badge">WEEK {int(weeks) if weeks else '?'} SINCE OPENING</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">FILTERS</div>', unsafe_allow_html=True)

    fc1, fc2, fc3, fc4 = st.columns(4)
    filters = {}

    with fc1:
        opts = sorted(df['gmh_sector_text'].dropna().unique().tolist())
        sel  = st.multiselect("Sector", opts, key=f"filter_sector_{selected_code}")
        filters['gmh_sector_text'] = sel

    with fc2:
        opts = sorted(df['gmh_gender_text'].dropna().unique().tolist())
        sel  = st.multiselect("Gender", opts, key=f"filter_gender_{selected_code}")
        filters['gmh_gender_text'] = sel

    with fc3:
        opts = sorted(df['gmh_sub_brand_text'].dropna().unique().tolist())
        sel  = st.multiselect("Label", opts, key=f"filter_label_{selected_code}")
        filters['gmh_sub_brand_text'] = sel

    with fc4:
        opts = sorted(df['gmh_sub_category_text'].dropna().unique().tolist())
        sel  = st.multiselect("Sub-Category", opts,
                              key=f"filter_subcat_{selected_code}")
        filters['gmh_sub_category_text'] = sel

    # Apply filters
    filtered_df = apply_filters(df.copy(), filters)
    active = sum(1 for v in filters.values() if v)
    if active:
        st.caption(f"Showing filtered view — {active} filter(s) active · "
                   f"{len(filtered_df):,} rows of {len(df):,}")
    else:
        st.caption("No filters active — showing all data")

    # ── Top KPIs (filtered) ───────────────────────────────────────────────────
    net_cy  = filtered_df['netslsamt_cy'].sum()
    net_ly  = filtered_df['netslsamt_ly'].sum()
    qty_cy  = filtered_df['netslsqty_cy'].sum()
    qty_ly  = filtered_df['netslsqty_ly'].sum()
    aur_cy  = net_cy / qty_cy if qty_cy > 0 else 0
    aur_ly  = net_ly / qty_ly if qty_ly > 0 else 0
    disc    = calc_disc_rate(filtered_df) * 100
    wos     = calc_wos(filtered_df)
    st_pct  = calc_sell_through(filtered_df) * 100

    def delta(cy, ly):
        if ly == 0 or is_new:
            return "NEW", "na"
        v = (cy / ly - 1) * 100
        return f"{v:+.1f}%", "pos" if v >= 0 else "neg"

    k1, k2, k3, k4, k5 = st.columns(5)
    metrics = [
        (k1, f"{period} NET SALES", f"${net_cy:,.0f}",  f"LY ${net_ly:,.0f}", *delta(net_cy, net_ly)),
        (k2, "UNITS SOLD",          f"{qty_cy:,.0f}",   f"LY {qty_ly:,.0f}", *delta(qty_cy, qty_ly)),
        (k3, "AUR",                 f"${aur_cy:.2f}",   f"LY ${aur_ly:.2f}", *delta(aur_cy, aur_ly)),
        (k4, "DISC RATE",           f"{disc:.1f}%",     "net vs MSRP",        "—", "na"),
        (k5, "WOS",                 f"{wos:.1f} wks",   f"sell-thru {st_pct:.0f}%", "—", "na"),
    ]
    for col, title, val, sub, var, cls in metrics:
        with col:
            var_html = (f'<span class="kpi-var {cls}">{var}</span>'
                        if var != "—" else f'<span class="kpi-var na">{sub}</span>')
            st.markdown(f"""
            <div class="kpi-card {region.lower()}">
                <div class="kpi-label">{title}</div>
                <div class="kpi-value" style="font-size:1.4rem;">{val}</div>
                <div class="kpi-sub">{sub if var != "—" else ""}</div>
                <div style="margin-top:0.3rem">{var_html}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Merchant dimension breakdowns ─────────────────────────────────────────
    st.markdown('<div class="section-header">SALES MIX BREAKDOWN</div>',
                unsafe_allow_html=True)

    dim_tab1, dim_tab2, dim_tab3, dim_tab4 = st.tabs(
        ["SECTOR", "GENDER", "LABEL", "SUB-CATEGORY"]
    )

    breakdown_map = [
        (dim_tab1, sector_breakdown(filtered_df),      'gmh_sector_text',      'Sector'),
        (dim_tab2, gender_breakdown(filtered_df),      'gmh_gender_text',      'Gender'),
        (dim_tab3, label_breakdown(filtered_df),       'gmh_sub_brand_text',   'Label'),
        (dim_tab4, subcategory_breakdown(filtered_df), 'gmh_sub_category_text','Sub-Category'),
    ]

    for tab, bdf, bcol, blabel in breakdown_map:
        with tab:
            c1, c2 = st.columns([2, 3])
            with c1:
                st.plotly_chart(
                    dim_mix_chart(bdf, bcol, blabel, region),
                    use_container_width=True
                )
            with c2:
                st.plotly_chart(
                    dim_bar_chart(bdf, bcol, blabel, region),
                    use_container_width=True
                )
            _mix_table(bdf, bcol, blabel, is_new)

    # ── Top & Bottom Styles ───────────────────────────────────────────────────
    st.markdown('<div class="section-header">STYLE PERFORMANCE</div>',
                unsafe_allow_html=True)

    # Load program names (cached)
    program_df = load_program_names('./data/program_names.xlsx')

    top_tab, bot_tab = st.tabs(["TOP 20 STYLES", "BOTTOM 20 STYLES"])

    for tab, is_bottom, title in [
        (top_tab, False, "TOP 20"),
        (bot_tab, True,  "BOTTOM 20")
    ]:
        with tab:
            styles_df = style_table(
                filtered_df, n=20,
                bottom=is_bottom,
                program_df=program_df if not program_df.empty else None
            )

            has_programs = 'program_name' in styles_df.columns

            base_cols = {
                'plm_style_code':             'Style',
                'style_description':          'Description',
                'gmh_sector_text':            'Sector',
                'gmh_gender_text':            'Gender',
                'gmh_sub_brand_text':         'Label',
                'gmh_sub_category_text':      'Sub-Cat',
                'netslsamt_cy':               'Net Sales CY',
                'mix_pct_cy':                 'Mix %',
                'netslsqty_cy':               'Units CY',
                'aur_cy':                     'AUR',
                'netslsamt_ly':               'Net Sales LY',
                'var_pct':                    'YoY %',
            }
            if has_programs:
                base_cols['program_name'] = 'Program'

            display_df = styles_df[list(base_cols.keys())].rename(columns=base_cols)

            def color_yoy(val):
                if pd.isna(val): return 'color: #888880'
                return f'color: {"#4a7c59" if val >= 0 else "#8b3a3a"}'

            fmt = {
                'Net Sales CY': '${:,.0f}',
                'Mix %':        '{:.1f}%',
                'Units CY':     '{:,.0f}',
                'AUR':          '${:.2f}',
                'Net Sales LY': '${:,.0f}',
                'YoY %':        lambda v: f'{v:+.1f}%' if pd.notna(v) else 'NEW',
            }

            st.dataframe(
                display_df.style.format(fmt).map(color_yoy, subset=['YoY %']),
                hide_index=True,
                use_container_width=True,
                height=500
            )

    # ── Underwear program breakdown ───────────────────────────────────────────
    underwear_df = filtered_df[
        filtered_df['gmh_sub_category_text'].str.contains(
            'underwear|underwear|brief|trunk|bra|bralette|boxer',
            case=False, na=False
        )
    ]

    if not underwear_df.empty and not program_df.empty:
        st.markdown('<div class="section-header">UNDERWEAR — PROGRAM BREAKDOWN</div>',
                    unsafe_allow_html=True)
        prog_df = program_breakdown(underwear_df, program_df)
        if not prog_df.empty:
            st.dataframe(
                prog_df.rename(columns={
                    'program_name':  'Program',
                    'netslsamt_cy':  'Net Sales CY',
                    'mix_pct_cy':    'Mix %',
                    'netslsqty_cy':  'Units CY',
                    'netslsamt_ly':  'Net Sales LY',
                    'var_pct':       'YoY %',
                }).style.format({
                    'Net Sales CY': '${:,.0f}',
                    'Mix %':        '{:.1f}%',
                    'Units CY':     '{:,.0f}',
                    'Net Sales LY': '${:,.0f}',
                    'YoY %':        lambda v: f'{v:+.1f}%' if pd.notna(v) else 'NEW',
                }),
                hide_index=True,
                use_container_width=True
            )
        elif program_df.empty:
            st.caption("Add program_names.xlsx to your data/ folder to enable this section.")

    # ── Channel mix ───────────────────────────────────────────────────────────
    if 'distribution_channel_code' in filtered_df.columns:
        st.markdown('<div class="section-header">CHANNEL MIX</div>',
                    unsafe_allow_html=True)
        ch = filtered_df.groupby('distribution_channel_code', as_index=False).agg(
            netslsamt_cy=('netslsamt_cy', 'sum'),
            netslsqty_cy=('netslsqty_cy', 'sum'),
        )
        ch['Channel'] = ch['distribution_channel_code'].map(CHANNEL_LABELS).fillna(
            ch['distribution_channel_code']
        )
        ch['Mix %'] = (ch['netslsamt_cy'] / ch['netslsamt_cy'].sum() * 100).round(1)
        ch = ch.sort_values('netslsamt_cy', ascending=False)
        st.dataframe(
            ch[['Channel', 'netslsamt_cy', 'netslsqty_cy', 'Mix %']].rename(columns={
                'netslsamt_cy': 'Net Sales CY',
                'netslsqty_cy': 'Units CY',
            }).style.format({
                'Net Sales CY': '${:,.0f}',
                'Units CY':     '{:,.0f}',
                'Mix %':        '{:.1f}%',
            }),
            hide_index=True,
            use_container_width=True
        )
