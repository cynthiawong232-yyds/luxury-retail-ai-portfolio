"""Cross-project guardrail module.

Single source of truth for what each project's AI agent can and cannot answer.
Used by every system prompt, every "What I can/can't answer" UI affordance,
and every preflight data check across the three sub-apps.
"""

from shared.scope import (
    ProjectScope,
    FLAGSHIP_SCOPE,
    ADVISOR_SCOPE,
    PERSONALIZATION_SCOPE,
    ALL_SCOPES,
)
from shared.data_guards import NoDataAvailable, require
from shared.ui import (
    render_value_card,
    render_about_expander,
    render_scope_expander,
    render_no_data_response,
)

__all__ = [
    "ProjectScope",
    "FLAGSHIP_SCOPE",
    "ADVISOR_SCOPE",
    "PERSONALIZATION_SCOPE",
    "ALL_SCOPES",
    "NoDataAvailable",
    "require",
    "render_value_card",
    "render_about_expander",
    "render_scope_expander",
    "render_no_data_response",
]
