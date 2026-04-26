"""Shared Streamlit components.

Four pieces:
  * render_value_card    — per-project card on the router landing page
  * render_about_expander — collapsed "About this project" inside each app
  * render_scope_expander — collapsed "What I can / can't answer" inside each app
  * render_no_data_response — graceful render when NoDataAvailable is caught

All four pull their content from a single ProjectScope instance, so changes
to scope.py propagate automatically.
"""

from __future__ import annotations

from typing import Callable, Optional

import streamlit as st

from shared.scope import ProjectScope


def render_value_card(scope: ProjectScope, on_open: Optional[Callable[[], None]] = None) -> None:
    """Single landing-page card for one project. Call once per ProjectScope."""
    with st.container(border=True):
        st.markdown(f"### {scope.name}")
        st.markdown(f"**For:** *{scope.persona}*")
        st.markdown(f"**Decision moment:** {scope.moment}")
        st.markdown("**Try asking:**")
        for q in scope.example_questions:
            st.markdown(f"- *{q}*")
        if on_open is not None:
            st.button(
                f"→ Open {scope.name}",
                on_click=on_open,
                key=f"open_{scope.name}",
                use_container_width=True,
            )


def render_about_expander(scope: ProjectScope) -> None:
    """Collapsed-by-default. Sits at the top of each sub-app's run()."""
    with st.expander(f"ℹ️  About — {scope.name}", expanded=False):
        st.markdown(f"**Built for:** {scope.persona}")
        st.markdown(f"**The decision moment:** {scope.moment}")
        st.markdown("**Diagnostic questions this project is designed to answer:**")
        for q in scope.example_questions:
            st.markdown(f"- *{q}*")


def render_scope_expander(scope: ProjectScope) -> None:
    """Collapsed-by-default. Sets honest expectations about what's in/out of scope."""
    with st.expander("\U0001f50d  What I can / can't answer", expanded=False):
        col_yes, col_no = st.columns(2)
        with col_yes:
            st.markdown("**✅ I can answer about:**")
            for item in scope.data_available:
                st.markdown(f"- {item}")
        with col_no:
            st.markdown("**❌ I cannot answer about:**")
            for item in scope.data_unavailable:
                st.markdown(f"- {item}")
        st.caption(
            "When asked something outside scope, this assistant will say so "
            "explicitly rather than guess. That's by design — see "
            "`shared/scope.py`."
        )


def render_no_data_response(message: str) -> None:
    """Render when a NoDataAvailable is caught at an LLM call site."""
    st.warning(message, icon="\U0001f937")
