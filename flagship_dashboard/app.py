"""Flagship Dashboard — Maison Voss store intelligence (3 flagship stores).

Designed to be runnable in two ways:
  * Standalone:  streamlit run flagship_dashboard/app.py
  * Via router:  imported by main.py, which calls run().

Internal imports live INSIDE run() so they only resolve after _HERE is
on sys.path (matters when run via the router, where cwd is the repo root,
not this folder).
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

_HERE = Path(__file__).resolve().parent

# Top-level package names that exist in more than one sub-project (or could,
# in the future). When the user navigates between sub-apps in one Streamlit
# session, Python caches whichever project loaded these first — causing
# ModuleNotFoundError when the second project's bare imports try to use
# the cached (wrong) folder. _ensure_path() evicts foreign entries.
_SHADOWING_NAMES = {"agent", "tools", "utils", "config", "tabs"}


def _ensure_path() -> None:
    """Make this folder's bare imports (tabs, utils, config) resolve.

    Two layers:
    1. Force _HERE to sys.path[0] so PEP-420 / regular-package resolution
       finds THIS project's packages first, even after another sub-app
       added its own path on a prior turn.
    2. Evict sys.modules entries for shadowing package names that came
       from a different sub-project's folder, so re-imports start clean.
    """
    here_str = str(_HERE)
    while here_str in sys.path:
        sys.path.remove(here_str)
    sys.path.insert(0, here_str)
    for name in list(sys.modules):
        top = name.split(".", 1)[0]
        if top in _SHADOWING_NAMES:
            mod = sys.modules.get(name)
            mod_file = getattr(mod, "__file__", None) or ""
            if mod_file and not mod_file.startswith(here_str):
                sys.modules.pop(name, None)


def run() -> None:
    _ensure_path()

    # Internal imports (require _HERE on sys.path)
    from tabs import portfolio, store_deep_dive, inventory, ai_advisor
    from utils.data_loader import load_all_store_data
    from utils.styles import inject_css
    from config import STORES

    # Cross-project guardrails
    from shared.scope import FLAGSHIP_SCOPE
    from shared.ui import render_about_expander, render_scope_expander

    inject_css()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        """
    <div class="ck-header">
        <span class="ck-logo">MAISON VOSS</span>
        <span class="ck-subtitle">FLAGSHIP STORE INTELLIGENCE</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── Anti-hallucination guardrails (collapsed by default) ──────────────────
    render_about_expander(FLAGSHIP_SCOPE)
    render_scope_expander(FLAGSHIP_SCOPE)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown('<div class="sidebar-title">CONTROLS</div>', unsafe_allow_html=True)

        period = st.radio(
            "Reporting Period",
            ["WTD", "MTD", "QTD", "YTD"],
            horizontal=False,
            key="fd_period",
        )

        st.markdown("---")
        st.markdown('<div class="sidebar-section">DATA</div>', unsafe_allow_html=True)

        folder = st.text_input(
            "CSV folder path",
            value="flagship_dashboard/data",
            help=(
                "Folder containing your CSVs downloaded from Databricks. "
                "Path is resolved relative to where you ran `streamlit run`."
            ),
            key="fd_folder",
        )

        if st.button("Load Data", type="primary", key="fd_load"):
            with st.spinner("Loading..."):
                loaded = load_all_store_data(folder_path=folder, period=period)
            if loaded:
                st.session_state["fd_data_cache"] = loaded
                st.session_state["fd_loaded_period"] = period

        # Use cached data if period hasn't changed
        data: dict = {}
        if "fd_data_cache" in st.session_state:
            if st.session_state.get("fd_loaded_period") == period:
                data = st.session_state["fd_data_cache"]
            else:
                st.caption("⚠ Period changed — click Load Data to refresh.")

        if data:
            st.success(f"✓ {len(data)} store(s) loaded")
            for store_code, df in data.items():
                label = STORES.get(store_code, {}).get("label", store_code)
                st.caption(f"  {label}: {len(df):,} rows")

        st.markdown("---")
        st.markdown('<div class="sidebar-section">STORES</div>', unsafe_allow_html=True)
        for code, info in STORES.items():
            st.markdown(
                f'<div class="store-badge {info["region"].lower()}">'
                f'{info["flag"]} {info["label"]} <span>{info["region"]}</span></div>',
                unsafe_allow_html=True,
            )

    # ── Tabs ──────────────────────────────────────────────────────────────────
    if not data:
        st.markdown(
            """
        <div class="empty-state">
            <div class="empty-icon">📂</div>
            <div class="empty-title">No data loaded yet</div>
            <div class="empty-sub">Upload your CSVs or point to a local folder in the sidebar to get started.</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊  PORTFOLIO", "🏬  STORE DEEP DIVE", "📦  INVENTORY", "🤖  AI ADVISOR"]
        )
        with tab1:
            portfolio.render(data, period)
        with tab2:
            store_deep_dive.render(data, period)
        with tab3:
            inventory.render(data, period)
        with tab4:
            ai_advisor.render(data, period)


if __name__ == "__main__":
    # Standalone mode: streamlit run flagship_dashboard/app.py
    st.set_page_config(
        page_title="Maison Voss Flagship Stores",
        page_icon="🏬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    # Make 'shared' (sibling at repo root) resolvable in standalone mode.
    sys.path.insert(0, str(_HERE.parent))
    run()
