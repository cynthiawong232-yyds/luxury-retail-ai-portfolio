"""Luxury Retail AI Portfolio — Streamlit router.

Entry point for the unified portfolio app. Owns the single
`st.set_page_config` call (Streamlit allows only one per session) and
routes to each sub-project's `run()` function.

Run locally:
    streamlit run main.py

Run a single sub-app standalone (also supported):
    streamlit run flagship_dashboard/app.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# Load env vars from a root .env (if present). On Streamlit Cloud, the
# Secrets UI injects GROQ_API_KEY as an env var directly, so this is a no-op.
load_dotenv(_HERE / ".env")

st.set_page_config(
    page_title="Luxury Retail AI Portfolio",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

from shared.scope import ADVISOR_SCOPE, ALL_SCOPES, FLAGSHIP_SCOPE, PERSONALIZATION_SCOPE
from shared.ui import render_value_card

HOME = "— Home —"

PROJECT_ROUTES: dict[str, tuple[str, object]] = {
    HOME: ("", None),
    FLAGSHIP_SCOPE.name: ("flagship_dashboard.app", FLAGSHIP_SCOPE),
    ADVISOR_SCOPE.name: ("client_advisor_intelligence_agent.app", ADVISOR_SCOPE),
    PERSONALIZATION_SCOPE.name: ("beauty_client_personalization_agent.app", PERSONALIZATION_SCOPE),
}


def _render_landing() -> None:
    st.title("Luxury Retail AI Portfolio")
    st.markdown(
        "**Diagnostic AI tools for luxury retail decision-makers** — three Streamlit "
        "apps that answer the *“why?”* questions managers actually ask, with "
        "disciplined guardrails so the agents fail gracefully when they lack data "
        "instead of confabulating."
    )
    st.caption("← Use the sidebar selectbox to open any of the three projects.")
    st.divider()

    for scope in ALL_SCOPES:
        render_value_card(scope)
        st.markdown("")  # vertical breathing room


def _route_to(project_name: str) -> None:
    module_path, _scope = PROJECT_ROUTES[project_name]
    try:
        module = importlib.import_module(module_path)
    except Exception as exc:  # noqa: BLE001 — surface any import error to the UI
        st.error(
            f"Could not load **{project_name}** ({module_path}). "
            f"Underlying error: `{exc}`"
        )
        return

    run_fn = getattr(module, "run", None)
    if run_fn is None:
        st.error(
            f"**{project_name}** does not expose a `run()` function in `{module_path}`. "
            "This is a wiring bug — please report."
        )
        return

    run_fn()


def main() -> None:
    with st.sidebar:
        st.markdown("### Portfolio")
        project = st.selectbox(
            "Choose a project",
            options=list(PROJECT_ROUTES.keys()),
            index=0,
            key="portfolio_project_choice",
        )
        st.markdown("---")
        st.caption(
            "Each project ships with its own scope declaration. Open any "
            "project and expand “What I can / can't answer” to see how that "
            "project handles out-of-scope questions without hallucinating."
        )

    if project == HOME:
        _render_landing()
    else:
        _route_to(project)


if __name__ == "__main__":
    main()
else:
    # When Streamlit Cloud (or `streamlit run main.py`) executes the file,
    # __name__ is "__main__" — this branch only fires when imported, which
    # shouldn't happen for the entry script. Run anyway as a safety net.
    main()
