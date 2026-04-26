"""Deterministic preflight checks: refuse before calling the LLM.

This is the cheapest, most reliable hallucination defense. If a question
references data the project doesn't have (a missing time period, an
unsupported store, an unknown product), we raise NoDataAvailable BEFORE
any LLM call and let the UI render a graceful refusal.

No LLM call = no hallucination. That is the entire idea.
"""

from __future__ import annotations

from typing import Iterable, Optional


class NoDataAvailable(Exception):
    """Raised when a question requires data this project does not have.

    The exception message should be user-facing: it is rendered directly
    by render_no_data_response() in shared.ui.
    """


def require(condition: bool, message: str) -> None:
    """Refuse with a user-facing message if `condition` is False.

    Pattern at every LLM call site:

        try:
            require(df["period"].eq(period).any(),
                    f"I don't have data for {period}. Most recent: {df['period'].max()}.")
            answer = call_llm(...)
            render(answer)
        except NoDataAvailable as e:
            render_no_data_response(str(e))
    """
    if not condition:
        raise NoDataAvailable(message)


def find_unsupported_term(text: str, unsupported: Iterable[str]) -> Optional[str]:
    """Return the first unsupported term mentioned in `text`, else None.

    Used to detect questions that name out-of-scope locations, products, or
    time periods. Case-insensitive substring match — callers should pass
    a curated set, not a free-form list (false positives are worse than false
    negatives here, since a false positive blocks an answerable question).
    """
    if not text:
        return None
    lowered = text.lower()
    for term in unsupported:
        if term.lower() in lowered:
            return term
    return None
