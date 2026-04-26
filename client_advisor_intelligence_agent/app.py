"""Client Advisor Intelligence — Maison Vega chat UI.

Runnable two ways:
  * Standalone:  streamlit run client_advisor_intelligence_agent/app.py
  * Via router:  imported by main.py, which calls run().

Helper functions (cached_load_data, render_*) live at module level — they
contain no Streamlit *calls* until invoked. CSS markdown and the actual UI
rendering happen inside run() so importing the module is side-effect-free.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_HERE = Path(__file__).resolve().parent

# Both this project AND beauty_client_personalization_agent have folders
# called `agent/` and `tools/`. When the user switches between them in one
# Streamlit session, Python caches whichever project loaded first — causing
# ModuleNotFoundError when the second project's bare imports try to use
# the cached (wrong) folder. _ensure_path() evicts foreign entries.
_SHADOWING_NAMES = {"agent", "tools", "utils", "config", "tabs"}

STORE_OPTIONS = {
    "All stores": "All",
    "MV SOHO New York": "A800",
    "MV Flagship Tokyo": "J347",
    "MV Flagship Paris": "EU_F07M",
}

_THEME_CSS = """
<style>
    .stApp { background-color: #0B1A2E; color: #F5F5F0; }
    section[data-testid="stSidebar"] { background-color: #07111F; }
    h1, h2, h3 { color: #F5F5F0; letter-spacing: 0.5px; }
    .mv-accent { color: #C9A961; }
    .mv-subtitle { color: #B8B8AE; font-size: 0.95rem; margin-top: -0.5rem; }

    div[data-testid="stMetric"] {
        background-color: #102339;
        border: 1px solid #2A4A6E;
        border-radius: 6px;
        padding: 1.1rem 1.25rem;
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *,
    div[data-testid="stMetricLabel"] p {
        color: #E5C97A !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.4px;
        text-transform: uppercase;
        opacity: 1 !important;
    }
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] * {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }

    .stChatMessage { background-color: #102339; border-radius: 8px; }
    .stChatMessage p { color: #F5F5F0 !important; }

    section[data-testid="stSidebar"] * { color: #F5F5F0 !important; }
    section[data-testid="stSidebar"] h3 { color: #C9A961 !important; }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
        color: #D8D4C2 !important;
        opacity: 1 !important;
    }

    .stButton > button,
    section[data-testid="stSidebar"] .stButton > button {
        background-color: #102339 !important;
        color: #C9A961 !important;
        border: 1px solid #C9A961 !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover,
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #C9A961 !important;
        color: #0B1A2E !important;
        border-color: #C9A961 !important;
    }
    .stButton > button p,
    section[data-testid="stSidebar"] .stButton > button p {
        color: inherit !important;
    }

    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] * {
        color: #0B1A2E !important;
    }
</style>
"""


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


@st.cache_data(show_spinner="Loading client data…")
def _cached_load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    _ensure_path()
    from tools.load_data_tool import load_data
    return load_data()


@st.cache_data(show_spinner=False)
def _cached_metrics(store_code: str) -> dict:
    _ensure_path()
    from tools.alert_tool import get_alerts

    clients_df, _, rfm_df = _cached_load_data()

    if store_code != "All":
        clients_view = clients_df[clients_df["preferred_store"] == store_code]
        rfm_view = rfm_df[rfm_df["preferred_store"] == store_code]
    else:
        clients_view = clients_df
        rfm_view = rfm_df

    alerts = get_alerts(rfm_view)
    if len(alerts) > 0:
        lapsing_count = int(
            alerts["alert_type"].isin(["Lapsing VIP", "Lapsing High Value"]).sum()
        )
    else:
        lapsing_count = 0

    return {
        "total_clients": int(len(clients_view)),
        "vip_count": int((rfm_view["rfm_segment"] == "VIP").sum()),
        "lapsing_alerts": lapsing_count,
    }


def _render_header() -> None:
    st.markdown(
        "<h1>Client Advisor <span class='mv-accent'>Intelligence</span></h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p class='mv-subtitle'>An intelligent layer to superpower client advisors.</p>",
        unsafe_allow_html=True,
    )
    st.divider()


def _render_sidebar() -> str:
    with st.sidebar:
        st.markdown("### Store")
        store_label = st.selectbox(
            "Filter by boutique",
            options=list(STORE_OPTIONS.keys()),
            index=0,
            label_visibility="collapsed",
            key="cai_store_filter",
        )
        st.markdown("---")
        st.markdown("### Try asking")
        st.caption("• Who are my top 10 VIP clients at Tokyo?")
        st.caption("• Tell me about MVC-00042")
        st.caption("• Tell me about Elena Bernard")
        st.caption("• Who bought MV Handbags Heritage?")
        st.caption("• What is the top-selling product in Paris?")
        st.caption("• Which lapsing clients should I prioritize this week?")
        st.caption("• Show me all Japanese clients who prefer Handbags")
        st.markdown("---")
        if st.button("Clear conversation", use_container_width=True, key="cai_clear"):
            st.session_state["cai_messages"] = []
            st.rerun()
    return STORE_OPTIONS[store_label]


def _render_metrics(store_code: str) -> None:
    metrics = _cached_metrics(store_code)
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Clients", f"{metrics['total_clients']:,}")
    c2.metric("VIP Clients", f"{metrics['vip_count']:,}")
    c3.metric("Lapsing Alerts", f"{metrics['lapsing_alerts']:,}")


def _render_chat(store_code: str) -> None:
    _ensure_path()
    from agent.advisor_agent import run_agent

    if "cai_messages" not in st.session_state:
        st.session_state["cai_messages"] = []

    for msg in st.session_state["cai_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(
                f"<p style='color: #F5F5F0; font-size: 15px; line-height: 1.6;'>{msg['content']}</p>",
                unsafe_allow_html=True,
            )
            if msg.get("table") is not None:
                st.dataframe(msg["table"], use_container_width=True, hide_index=True)

    prompt = st.chat_input("Ask about your clients…")
    if not prompt:
        return

    st.session_state["cai_messages"].append(
        {"role": "user", "content": prompt, "table": None}
    )
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                result = run_agent(prompt, store_filter=store_code)
            except Exception as e:
                err = f"Something went wrong: {e}"
                st.error(err)
                st.session_state["cai_messages"].append(
                    {"role": "assistant", "content": err, "table": None}
                )
                return

        st.caption(f"Intent: {result['intent']}  ·  Tool: {result['tool_called']}")
        st.markdown(
            f"<p style='color: #F5F5F0; font-size: 15px; line-height: 1.6;'>{result['response_text']}</p>",
            unsafe_allow_html=True,
        )

        table = result["data_table"]
        if table is not None and len(table) > 0:
            st.dataframe(table, use_container_width=True, hide_index=True)

        st.session_state["cai_messages"].append(
            {"role": "assistant", "content": result["response_text"], "table": table}
        )


def run() -> None:
    _ensure_path()

    # Theme CSS — must be inside run(), not at module top, otherwise it would
    # fire on import (i.e. while a different sub-app is selected).
    st.markdown(_THEME_CSS, unsafe_allow_html=True)

    # Anti-hallucination guardrails
    from shared.scope import ADVISOR_SCOPE
    from shared.ui import render_about_expander, render_scope_expander
    render_about_expander(ADVISOR_SCOPE)
    render_scope_expander(ADVISOR_SCOPE)

    _render_header()
    store_code = _render_sidebar()
    _render_chat(store_code)
    _render_metrics(store_code)


if __name__ == "__main__":
    st.set_page_config(
        page_title="Client Advisor Intelligence",
        page_icon="◆",
        layout="wide",
    )
    sys.path.insert(0, str(_HERE.parent))  # so 'shared' resolves
    run()
