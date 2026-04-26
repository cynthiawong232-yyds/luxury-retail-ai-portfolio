import streamlit as st
import pandas as pd
from utils.data_loader import (
    inv_by_dim, calc_wos, calc_sell_through,
    store_totals, apply_filters, MERCH_DIMS
)
from utils.charts import inv_dim_bar, wos_gauge
from config import STORES, WOS_LOW_THRESHOLD, WOS_HIGH_THRESHOLD


def render(data: dict, period: str):
    st.markdown('<div class="section-header">INVENTORY HEALTH  —  ALL STORES</div>',
                unsafe_allow_html=True)
    st.caption("Point-in-time weekly snapshot. WOS = EOH units ÷ period net sales qty.")

    # ── WOS gauges ────────────────────────────────────────────────────────────
    cols = st.columns(len(data))
    for i, (code, df) in enumerate(data.items()):
        info   = STORES[code]
        region = info['region']
        label  = info['label']
        flag   = info['flag']
        wos    = calc_wos(df)

        with cols[i]:
            st.plotly_chart(
                wos_gauge(wos, f"{flag} {label}", region),
                use_container_width=True
            )
            if 0 < wos < WOS_LOW_THRESHOLD:
                st.markdown(f"""
                <div class="alert-card">
                    ⚠️ <strong>{label}</strong> — WOS {wos:.1f} is critically low.
                    Stockout risk. Review replenishment.
                </div>""", unsafe_allow_html=True)
            elif wos > WOS_HIGH_THRESHOLD:
                st.markdown(f"""
                <div class="alert-card warning">
                    📦 <strong>{label}</strong> — WOS {wos:.1f} exceeds
                    {WOS_HIGH_THRESHOLD:.0f} weeks. Over-inventoried.
                    Review markdowns or transfers.
                </div>""", unsafe_allow_html=True)

    # ── Summary table ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">INVENTORY SUMMARY</div>',
                unsafe_allow_html=True)

    rows = []
    for code, df in data.items():
        info = STORES[code]
        rows.append({
            'Store':          f"{info['flag']} {info['label']}",
            'Region':         info['region'],
            'EOH Units CY':   df['eohttlqty_cy'].sum(),
            'EOH Units LY':   df['eohttlqty_ly'].sum(),
            'EOH Var %':      (df['eohttlqty_cy'].sum() / df['eohttlqty_ly'].sum() - 1) * 100
                              if df['eohttlqty_ly'].sum() > 0 else None,
            'Store Units CY': df['eohstrqty_cy'].sum(),
            'In-Transit CY':  df['intranqty_cy'].sum(),
            'WOS':            calc_wos(df),
            'Sell-Thru %':    calc_sell_through(df) * 100,
        })

    inv_df = pd.DataFrame(rows)

    def color_wos(val):
        if val < WOS_LOW_THRESHOLD:  return 'color: #8b3a3a'
        elif val > WOS_HIGH_THRESHOLD: return 'color: #c8a96e'
        return 'color: #4a7c59'

    def color_var(val):
        if pd.isna(val): return 'color: #888880'
        return f'color: {"#4a7c59" if val >= 0 else "#8b3a3a"}'

    st.dataframe(
        inv_df.style
        .format({
            'EOH Units CY':   '{:,.0f}',
            'EOH Units LY':   '{:,.0f}',
            'EOH Var %':      lambda v: f'{v:+.1f}%' if pd.notna(v) else 'NEW',
            'Store Units CY': '{:,.0f}',
            'In-Transit CY':  '{:,.0f}',
            'WOS':            '{:.1f}',
            'Sell-Thru %':    '{:.1f}%',
        })
        .map(color_wos, subset=['WOS'])
        .map(color_var, subset=['EOH Var %']),
        hide_index=True,
        use_container_width=True
    )

    # ── Per-store inventory drill-down ────────────────────────────────────────
    st.markdown('<div class="section-header">INVENTORY DETAIL BY STORE</div>',
                unsafe_allow_html=True)

    # Dimension selector — applies to all store expanders below
    dim_choice = st.selectbox(
        "Break down inventory by",
        options=list(MERCH_DIMS.keys()),
        key="inv_dim_select"
    )
    dim_col = MERCH_DIMS[dim_choice]

    for code, df in data.items():
        info   = STORES[code]
        region = info['region']
        flag   = info['flag']
        label  = info['label']

        with st.expander(f"{flag} {label} — {region}", expanded=True):

            # Filters inside each store expander
            fc1, fc2, fc3, fc4 = st.columns(4)
            filters = {}
            with fc1:
                opts = sorted(df['gmh_sector_text'].dropna().unique().tolist())
                sel  = st.multiselect("Sector", opts, key=f"inv_sector_{code}")
                filters['gmh_sector_text'] = sel
            with fc2:
                opts = sorted(df['gmh_gender_text'].dropna().unique().tolist())
                sel  = st.multiselect("Gender", opts, key=f"inv_gender_{code}")
                filters['gmh_gender_text'] = sel
            with fc3:
                opts = sorted(df['gmh_sub_brand_text'].dropna().unique().tolist())
                sel  = st.multiselect("Label", opts, key=f"inv_label_{code}")
                filters['gmh_sub_brand_text'] = sel
            with fc4:
                opts = sorted(df['gmh_sub_category_text'].dropna().unique().tolist())
                sel  = st.multiselect("Sub-Cat", opts, key=f"inv_subcat_{code}")
                filters['gmh_sub_category_text'] = sel

            filtered = apply_filters(df.copy(), filters)
            inv_dim  = inv_by_dim(filtered, dim_col)

            c1, c2 = st.columns([3, 2])
            with c1:
                st.plotly_chart(
                    inv_dim_bar(inv_dim, dim_col, dim_choice, region),
                    use_container_width=True
                )
            with c2:
                # Inventory table
                display = inv_dim[[
                    dim_col, 'eohttlqty_cy', 'mix_pct_cy',
                    'eohttlqty_ly', 'eoh_var_pct',
                    'intranqty_cy', 'transit_pct', 'wos'
                ]].rename(columns={
                    dim_col:        dim_choice,
                    'eohttlqty_cy': 'EOH CY',
                    'mix_pct_cy':   'Mix %',
                    'eohttlqty_ly': 'EOH LY',
                    'eoh_var_pct':  'EOH Var %',
                    'intranqty_cy': 'In-Transit',
                    'transit_pct':  'Transit %',
                    'wos':          'WOS',
                })

                def color_wos_cell(val):
                    if val < WOS_LOW_THRESHOLD:   return 'color: #8b3a3a'
                    elif val > WOS_HIGH_THRESHOLD: return 'color: #c8a96e'
                    return 'color: #4a7c59'

                def color_var_cell(val):
                    if pd.isna(val): return 'color: #888880'
                    return f'color: {"#4a7c59" if val >= 0 else "#8b3a3a"}'

                st.dataframe(
                    display.style
                    .format({
                        'EOH CY':    '{:,.0f}',
                        'Mix %':     '{:.1f}%',
                        'EOH LY':    '{:,.0f}',
                        'EOH Var %': lambda v: f'{v:+.1f}%' if pd.notna(v) else 'NEW',
                        'In-Transit':'{:,.0f}',
                        'Transit %': '{:.1f}%',
                        'WOS':       '{:.1f}',
                    })
                    .map(color_wos_cell,  subset=['WOS'])
                    .map(color_var_cell,  subset=['EOH Var %']),
                    hide_index=True,
                    use_container_width=True,
                    height=320
                )
