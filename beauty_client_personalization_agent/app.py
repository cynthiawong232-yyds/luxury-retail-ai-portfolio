"""Streamlit front end for the Maison Solène Beauty Client Personalization Agent.

Runnable two ways:
  * Standalone:  streamlit run beauty_client_personalization_agent/app.py
  * Via router:  imported by main.py, which calls run().
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_HERE = Path(__file__).resolve().parent

# Both this project AND client_advisor_intelligence_agent have folders
# called `agent/` and `tools/`. When the user switches between them in one
# Streamlit session, Python caches whichever project loaded first — causing
# ModuleNotFoundError when the second project's bare imports try to use
# the cached (wrong) folder. _ensure_path() evicts foreign entries.
_SHADOWING_NAMES = {"agent", "tools", "utils", "config", "tabs"}


def _ensure_path() -> None:
    """Force _HERE to sys.path[0] AND evict cached sibling-project modules.

    sys.path[0] dominance matters: when two sub-projects both have a regular
    package called `agent/`, whichever folder is earliest in sys.path wins
    (PEP 420). Just inserting `_HERE` doesn't help if it's already further
    back in sys.path from a previous switch.
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

    # Internal imports
    from agent.personalization_agent import run_pipeline
    from tools.dashboard_tool import (
        apply_brand_theme,
        render_ab_results,
        render_header,
        render_overview,
        render_personalization,
    )
    from tools.segment_tool import SEGMENT_ORDER

    # Cross-project guardrails
    from shared.scope import PERSONALIZATION_SCOPE
    from shared.ui import render_about_expander, render_scope_expander

    apply_brand_theme()
    render_header()

    render_about_expander(PERSONALIZATION_SCOPE)
    render_scope_expander(PERSONALIZATION_SCOPE)

    with st.sidebar:
        st.markdown("### Control Panel")
        st.caption(
            "Runs the full WAT pipeline: load → segment → recommend → "
            "generate copy → A/B test."
        )

        run_clicked = st.button(
            "Generate Personalization Report",
            use_container_width=True,
            type="primary",
            key="bca_run",
        )

        skip_copy = st.checkbox(
            "Fast mode (skip Groq copy)",
            value=False,
            help="Skip the GenAI copy generation for faster iteration while developing.",
            key="bca_skip_copy",
        )

        st.markdown("---")
        segment = st.selectbox(
            "Segment",
            SEGMENT_ORDER,
            index=0,
            help="Choose a segment to view personalization output and A/B results.",
            key="bca_segment",
        )

        store = st.selectbox(
            "Store filter (affects Overview only)",
            ["All stores", "SOHO", "Paris", "Tokyo"],
            index=0,
            key="bca_store",
        )

    if run_clicked:
        with st.spinner(
            "Running pipeline — loading data, segmenting, recommending, "
            "generating copy, simulating A/B test..."
        ):
            st.session_state["bca_result"] = run_pipeline(
                seed=42,
                skip_copy=skip_copy,
                verbose=False,
            )

    result = st.session_state.get("bca_result")

    if result is None:
        st.info(
            "Click **Generate Personalization Report** in the sidebar to run "
            "the pipeline. Fast mode skips the Groq call (useful for previewing "
            "the UI without waiting for copy)."
        )
    else:
        render_overview(result, store_filter=store)
        st.markdown("---")
        render_personalization(result, segment)
        st.markdown("---")
        render_ab_results(result, segment)


if __name__ == "__main__":
    st.set_page_config(
        page_title="Maison Solène — Beauty Personalization Agent",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    sys.path.insert(0, str(_HERE.parent))  # so 'shared' resolves
    run()
