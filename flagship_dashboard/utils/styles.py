import streamlit as st

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@300;400;600&family=DM+Mono:wght@300;400;500&display=swap');

    /* ── Root variables ── */
    :root {
        --black:     #0a0a0a;
        --white:     #f5f5f0;
        --ivory:     #f0ece3;
        --mid:       #aaaaaa;
        --border:    #2a2a2a;
        --us:        #c8a96e;
        --eu:        #8cb4c3;
        --asia:      #c47b7b;
        --green:     #4a7c59;
        --red:       #8b3a3a;
        --card-bg:   #111111;
        --hover:     #1a1a1a;
    }

    /* ── Global ── */
    html, body, [class*="css"] {
        font-family: 'DM Mono', monospace;
        background-color: var(--black);
        color: var(--white);
    }

    .stApp { background-color: var(--black); }

    /* ── Header ── */
    .ck-header {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 2rem 0 1.5rem;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1.5rem;
        letter-spacing: 0.3em;
    }
    .ck-logo {
        font-family: 'Cormorant Garamond', serif;
        font-size: 2.4rem;
        font-weight: 300;
        color: var(--white);
        letter-spacing: 0.5em;
    }
    .ck-subtitle {
        font-family: 'DM Mono', monospace;
        font-size: 0.6rem;
        color: var(--mid);
        letter-spacing: 0.4em;
        margin-top: 0.3rem;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #0d0d0d;
        border-right: 1px solid var(--border);
    }
    .sidebar-title {
        font-size: 0.55rem;
        letter-spacing: 0.4em;
        color: var(--mid);
        padding: 0.5rem 0 0.8rem;
    }
    .sidebar-section {
        font-size: 0.55rem;
        letter-spacing: 0.4em;
        color: var(--mid);
        padding: 0.3rem 0 0.5rem;
    }

    /* ── Store badges ── */
    .store-badge {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.4rem 0.6rem;
        margin: 0.2rem 0;
        border-left: 2px solid transparent;
        font-size: 0.7rem;
        letter-spacing: 0.15em;
    }
    .store-badge span {
        font-size: 0.55rem;
        color: var(--mid);
        letter-spacing: 0.2em;
    }
    .store-badge.us   { border-color: var(--us);   color: var(--us);   }
    .store-badge.eu   { border-color: var(--eu);   color: var(--eu);   }
    .store-badge.asia { border-color: var(--asia); color: var(--asia); }

    /* ── KPI cards ── */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    .kpi-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        padding: 1.2rem 1.4rem;
        position: relative;
        overflow: hidden;
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
    }
    .kpi-card.us::before   { background: var(--us);   }
    .kpi-card.eu::before   { background: var(--eu);   }
    .kpi-card.asia::before { background: var(--asia); }

    .kpi-label {
        font-size: 0.55rem;
        letter-spacing: 0.3em;
        color: var(--mid);
        margin-bottom: 0.5rem;
    }
    .kpi-value {
        font-family: 'Cormorant Garamond', serif;
        font-size: 2rem;
        font-weight: 300;
        color: var(--white);
        line-height: 1;
    }
    .kpi-sub {
        font-size: 0.6rem;
        color: var(--mid);
        margin-top: 0.3rem;
    }
    .kpi-var.pos { color: var(--green); }
    .kpi-var.neg { color: var(--red);   }
    .kpi-var.na  { color: var(--mid);   }

    /* ── Section headers ── */
    .section-header {
        font-size: 0.55rem;
        letter-spacing: 0.4em;
        color: var(--mid);
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.5rem;
        margin: 1.5rem 0 1rem;
    }

    /* ── Store pill ── */
    .store-pill {
        display: inline-block;
        padding: 0.2rem 0.7rem;
        font-size: 0.6rem;
        letter-spacing: 0.2em;
        border: 1px solid;
        margin-right: 0.5rem;
    }
    .store-pill.us   { border-color: var(--us);   color: var(--us);   }
    .store-pill.eu   { border-color: var(--eu);   color: var(--eu);   }
    .store-pill.asia { border-color: var(--asia); color: var(--asia); }

    /* ── Watch list / alert cards ── */
    .alert-card {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-left: 3px solid var(--red);
        padding: 0.8rem 1rem;
        margin: 0.4rem 0;
        font-size: 0.7rem;
        line-height: 1.6;
    }
    .alert-card.warning { border-left-color: var(--us); }
    .alert-card.info    { border-left-color: var(--eu); }

    /* ── Maturity badge ── */
    .maturity-badge {
        font-size: 0.55rem;
        letter-spacing: 0.2em;
        color: var(--mid);
        background: #1a1a1a;
        padding: 0.2rem 0.6rem;
        border: 1px solid var(--border);
        display: inline-block;
    }

    /* ── AI chat ── */
    .ai-message {
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-left: 2px solid var(--eu);
        padding: 1rem 1.2rem;
        margin: 0.6rem 0;
        font-size: 0.8rem;
        line-height: 1.8;
        white-space: pre-wrap;
        color: #e8e8e3;
    }
    .user-message {
        background: #151515;
        border: 1px solid var(--border);
        border-left: 2px solid var(--mid);
        padding: 0.8rem 1.2rem;
        margin: 0.6rem 0;
        font-size: 0.8rem;
        line-height: 1.6;
        color: #aaaaaa;
    }

    /* ── Empty state ── */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 5rem 2rem;
        text-align: center;
    }
    .empty-icon  { font-size: 3rem; margin-bottom: 1rem; }
    .empty-title { font-family: 'Cormorant Garamond', serif; font-size: 1.6rem; font-weight: 300; color: var(--white); }
    .empty-sub   { font-size: 0.7rem; color: var(--mid); margin-top: 0.5rem; letter-spacing: 0.1em; }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 1px solid var(--border);
        gap: 0;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.6rem;
        letter-spacing: 0.3em;
        color: var(--mid);
        padding: 0.6rem 1.5rem;
        background: transparent;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        color: var(--white) !important;
        border-bottom: 1px solid var(--white) !important;
        background: transparent !important;
    }

    /* ── Plotly chart backgrounds ── */
    .js-plotly-plot .plotly { background: transparent !important; }

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
    }

    /* ── Buttons ── */
    .stButton > button {
        background: transparent;
        border: 1px solid var(--white);
        color: var(--white);
        font-family: 'DM Mono', monospace;
        font-size: 0.65rem;
        letter-spacing: 0.2em;
        padding: 0.5rem 1.5rem;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: var(--white);
        color: var(--black);
    }

    /* ── Fix subtle text ── */
    [data-testid="stCaptionContainer"] p {
        color: #bbbbbb !important;
    }
    .gtitle, .xtitle, .ytitle {
        fill: #cccccc !important;
    }
    .section-header {
        color: #cccccc !important;
        border-bottom: 1px solid #444444 !important;
    }
    .alert-card {
        color: #cccccc !important;
    }
    .maturity-badge {
        color: #bbbbbb !important;
    }
    .kpi-label { color: #bbbbbb !important; }
    .kpi-sub   { color: #bbbbbb !important; }
    [data-testid="stMarkdownContainer"] p {
        color: #cccccc !important;
    }

    /* ── Radio / selectbox ── */
    .stRadio label, .stSelectbox label {
        font-size: 0.65rem;
        letter-spacing: 0.15em;
        color: var(--mid);
    }
    </style>
    """, unsafe_allow_html=True)
