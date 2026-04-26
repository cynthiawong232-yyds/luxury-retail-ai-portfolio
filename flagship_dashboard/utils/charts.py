import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

COLORS = {
    'US':   '#c8a96e',
    'EU':   '#8cb4c3',
    'Asia': '#c47b7b',
    'mid':  '#888880',
    'green':'#4a7c59',
    'red':  '#8b3a3a',
    'bg':   '#0a0a0a',
    'grid': '#1e1e1e',
    'text': '#f5f5f0',
}

LAYOUT_BASE = dict(
    paper_bgcolor=COLORS['bg'],
    plot_bgcolor=COLORS['bg'],
    font=dict(family='DM Mono, monospace', color=COLORS['text'], size=11),
    xaxis=dict(gridcolor=COLORS['grid'], linecolor=COLORS['grid'], tickfont_size=10),
    yaxis=dict(gridcolor=COLORS['grid'], linecolor=COLORS['grid'], tickfont_size=10),
    hoverlabel=dict(bgcolor='#1a1a1a', font_color=COLORS['text'], font_family='DM Mono'),
)

# Palette for multi-category donut/bar charts
MULTI_PALETTE = [
    '#c8a96e','#8cb4c3','#c47b7b','#7ab8a0','#b39bc8',
    '#d4a57a','#6b9fb8','#c47b7b','#88b888','#c8a9a9',
]

def _region_color(region: str) -> str:
    return COLORS.get(region, COLORS['mid'])


# ── Portfolio charts ──────────────────────────────────────────────────────────

def portfolio_bar(totals_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for _, row in totals_df.iterrows():
        c     = _region_color(row['store_region'])
        label = f"{row['store_flag']} {row['store_label']}"
        fig.add_trace(go.Bar(
            name=f"{label} CY", x=[label], y=[row['netslsamt_cy']],
            marker_color=c,
            text=[f"${row['netslsamt_cy']:,.0f}"], textposition='outside', textfont_size=9,
        ))
        fig.add_trace(go.Bar(
            name=f"{label} LY", x=[label], y=[row['netslsamt_ly']],
            marker_color=c, marker_pattern_shape='/', opacity=0.4, showlegend=False,
        ))
    fig.update_layout(
        **LAYOUT_BASE,
        barmode='group',
        title=dict(text='NET SALES  CY vs LY', font_size=11, x=0),
        showlegend=False, height=320,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def variance_bar(totals_df: pd.DataFrame) -> go.Figure:
    df = totals_df.copy()
    df['var_pct'] = df.apply(
        lambda r: (r['netslsamt_cy'] / r['netslsamt_ly'] - 1) * 100
        if r['netslsamt_ly'] > 0 else None, axis=1
    )
    df     = df.sort_values('var_pct', ascending=True)
    colors = [COLORS['green'] if (v or 0) >= 0 else COLORS['red'] for v in df['var_pct']]
    labels = [f"{r['store_flag']} {r['store_label']}" for _, r in df.iterrows()]
    fig = go.Figure(go.Bar(
        x=df['var_pct'], y=labels, orientation='h', marker_color=colors,
        text=[f"{v:+.1f}%" if v is not None else "NEW" for v in df['var_pct']],
        textposition='outside', textfont_size=10,
    ))
    fig.add_vline(x=0, line_color=COLORS['mid'], line_width=1)
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text='COMP VARIANCE %  vs LY', font_size=11, x=0),
        height=200, xaxis_ticksuffix='%',
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def ramp_chart(totals_df: pd.DataFrame, period: str) -> go.Figure:
    fig = go.Figure()
    for _, row in totals_df.iterrows():
        c    = _region_color(row['store_region'])
        wk   = row.get('weeks_open')
        label = f"{row['store_flag']} {row['store_label']}"
        ann  = f"Wk {int(wk)}" if wk else "?"
        fig.add_trace(go.Bar(
            name=label, x=[label], y=[row['netslsamt_cy']], marker_color=c,
            text=[f"${row['netslsamt_cy']:,.0f}<br><span style='font-size:9px'>{ann} since open</span>"],
            textposition='inside', textfont_size=10,
        ))
    fig.update_layout(
        **LAYOUT_BASE,
        barmode='group',
        title=dict(text=f'{period} NET SALES  BY STORE  (WEEKS SINCE OPENING)', font_size=11, x=0),
        showlegend=False, height=300,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


# ── Merchant dimension mix charts ─────────────────────────────────────────────

def dim_mix_chart(dim_df: pd.DataFrame, dim_col: str,
                  title: str, region: str) -> go.Figure:
    """
    Donut chart showing mix % by any merchant dimension (sector/gender/label/subcat).
    Used on Portfolio store-level mix section and Store Deep Dive tabs.
    """
    fig = go.Figure(go.Pie(
        labels=dim_df[dim_col],
        values=dim_df['netslsamt_cy'],
        hole=0.55,
        marker_colors=MULTI_PALETTE[:len(dim_df)],
        textfont_size=9,
        textinfo='label+percent',
        hovertemplate='%{label}<br>$%{value:,.0f}<br>%{percent}<extra></extra>',
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text=f'{title} MIX  CY', font_size=11, x=0),
        height=260,
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def dim_bar_chart(dim_df: pd.DataFrame, dim_col: str,
                  title: str, region: str) -> go.Figure:
    """
    Grouped bar chart CY vs LY for any merchant dimension.
    Used in Store Deep Dive breakdown tabs.
    """
    c = _region_color(region)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='CY', x=dim_df[dim_col], y=dim_df['netslsamt_cy'],
        marker_color=c,
        text=dim_df['netslsamt_cy'].apply(lambda v: f"${v:,.0f}"),
        textposition='outside', textfont_size=9,
    ))
    fig.add_trace(go.Bar(
        name='LY', x=dim_df[dim_col], y=dim_df['netslsamt_ly'],
        marker_color=c, opacity=0.35, marker_pattern_shape='/',
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        barmode='group',
        title=dict(text=f'{title.upper()} — NET SALES CY vs LY', font_size=11, x=0),
        height=280,
        xaxis_tickangle=-30,
        legend=dict(bgcolor='rgba(0,0,0,0)', font_size=10),
        margin=dict(l=20, r=20, t=40, b=40),
    )
    return fig


def cross_store_dim_chart(combined_df: pd.DataFrame,
                           dim_col: str, dim_label: str) -> go.Figure:
    """
    Grouped bar: same dimension across all stores side by side.
    Replaced the old cross_store_category chart.
    """
    fig = go.Figure()
    for store_label, grp in combined_df.groupby('_store_label'):
        region = grp['_store_region'].iloc[0]
        flag   = grp['_store_flag'].iloc[0]
        fig.add_trace(go.Bar(
            name=f"{flag} {store_label}",
            x=grp[dim_col],
            y=grp['netslsamt_cy'],
            marker_color=_region_color(region),
            hovertemplate='%{x}<br>$%{y:,.0f}<extra>' + store_label + '</extra>',
        ))
    fig.update_layout(
        **LAYOUT_BASE,
        barmode='group',
        title=dict(text=f'{dim_label.upper()} MIX  CROSS-STORE COMPARISON', font_size=11, x=0),
        height=340,
        xaxis_tickangle=-30,
        legend=dict(bgcolor='rgba(0,0,0,0)', font_size=10),
        margin=dict(l=20, r=20, t=40, b=60),
    )
    return fig


# ── Inventory charts ──────────────────────────────────────────────────────────

def inv_dim_bar(inv_df: pd.DataFrame, dim_col: str,
                dim_label: str, region: str) -> go.Figure:
    """
    Inventory bar chart by any merchant dimension — CY vs LY EOH units.
    Replaces the old inv_category_bar.
    """
    c = _region_color(region)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='EOH CY', x=inv_df[dim_col], y=inv_df['eohttlqty_cy'],
        marker_color=c,
        text=inv_df['eohttlqty_cy'].apply(lambda v: f"{v:,.0f}"),
        textposition='outside', textfont_size=9,
    ))
    fig.add_trace(go.Bar(
        name='EOH LY', x=inv_df[dim_col], y=inv_df['eohttlqty_ly'],
        marker_color=c, opacity=0.35, marker_pattern_shape='/',
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        barmode='group',
        title=dict(text=f'EOH UNITS BY {dim_label.upper()}  CY vs LY', font_size=11, x=0),
        height=300,
        xaxis_tickangle=-30,
        legend=dict(bgcolor='rgba(0,0,0,0)', font_size=10),
        margin=dict(l=20, r=20, t=40, b=60),
    )
    return fig


def wos_gauge(wos: float, store_label: str, region: str) -> go.Figure:
    c = _region_color(region)
    fig = go.Figure(go.Indicator(
        mode='gauge+number',
        value=wos,
        number=dict(suffix=' wks', font_color=COLORS['text'], font_size=28),
        gauge=dict(
            axis=dict(range=[0, 20], tickcolor=COLORS['mid'], tickfont_size=9),
            bar=dict(color=c),
            bgcolor=COLORS['bg'],
            bordercolor=COLORS['grid'],
            steps=[
                dict(range=[0, 4],   color='#2a1a1a'),
                dict(range=[4, 14],  color='#0d0d0d'),
                dict(range=[14, 20], color='#1a2a1a'),
            ],
            threshold=dict(
                line=dict(color=COLORS['mid'], width=2),
                thickness=0.75, value=wos,
            ),
        ),
        title=dict(text=f'WOS · {store_label}',
                   font_color=COLORS['mid'], font_size=10),
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        height=220,
        margin=dict(l=20, r=20, t=30, b=10),
    )
    return fig


# ── Legacy aliases ────────────────────────────────────────────────────────────
# Kept so any old references don't break

def category_bar(cat_df, region):
    return dim_bar_chart(cat_df, 'gmh_category_text', 'Category', region)

def category_variance_bar(cat_df):
    df = cat_df.dropna(subset=['var_pct']).sort_values('var_pct', ascending=True)
    colors = [COLORS['green'] if v >= 0 else COLORS['red'] for v in df['var_pct']]
    fig = go.Figure(go.Bar(
        x=df['var_pct'], y=df['gmh_category_text'],
        orientation='h', marker_color=colors,
        text=[f"{v:+.1f}%" for v in df['var_pct']],
        textposition='outside', textfont_size=9,
    ))
    fig.add_vline(x=0, line_color=COLORS['mid'], line_width=1)
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text='CATEGORY COMP %', font_size=11, x=0),
        height=300, xaxis_ticksuffix='%',
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig

def gender_donut(gender_df, region):
    return dim_mix_chart(gender_df, 'gmh_gender_text', 'GENDER', region)

def cross_store_category(data):
    from utils.data_loader import cross_store_dim
    combined = cross_store_dim(data, 'gmh_sector_text')
    return cross_store_dim_chart(combined, 'gmh_sector_text', 'Sector')

def inv_category_bar(inv_df, region):
    return inv_dim_bar(inv_df, 'gmh_category_text', 'Category', region)
