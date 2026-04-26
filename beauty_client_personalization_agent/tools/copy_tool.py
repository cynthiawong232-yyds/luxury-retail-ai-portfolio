"""Generate A/B outreach copy per segment via Groq LLaMA 3.3 70B.

Variant A: warm boutique-advisor tone.
Variant B: exclusive, aspirational luxury tone.
Both enforce the Maison Solène brand voice: no exclamation marks, no emojis,
no cliches, 3-4 sentences max.

Uses `curl` via subprocess to reach the Groq HTTPS API. This works around
environments where Python's `ssl` module is unavailable, and keeps the
dependency surface to the Python stdlib + python-dotenv + pandas.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parent.parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
REQUEST_TIMEOUT_SEC = 60

BRAND_RULES = """You write outreach copy on behalf of Maison Solène's Digital Client Experience team for beauty clients.
Enforce these brand-voice rules, without exception:
- 3 to 4 sentences maximum. Luxury brands are never verbose.
- No exclamation marks. No emojis. No cliches such as "treat yourself", "must-have", "game-changer", "unlock", "elevate".
- No hyperbole, no all-caps, no hard sell.
- Address the segment's favorite product or primary beauty category naturally, as if continuing a conversation.
- Do not invent products, prices, or claims. Use only what is provided.
- Do not address the reader as "dear customer" or "dear client". Write as a boutique advisor addressing one person.
- Close with "Maison Solène" on its own final line."""

VARIANT_A_SYSTEM = BRAND_RULES + """

TONE: Warm, personal, advisory. Reads as if a trusted boutique beauty advisor is writing directly to one client. Conversational but refined."""

VARIANT_B_SYSTEM = BRAND_RULES + """

TONE: Exclusive, aspirational. Emphasizes discovery, craft, and Maison Solène's heritage. Evocative and understated, never pushy."""


def generate_copy(
    segment_name: str,
    recommendations_df: pd.DataFrame,
    avg_spend: float,
    favorite_product: str | None,
    top_category: str | None = None,
    api_key: str | None = None,
) -> dict[str, str]:
    """Return {'variant_a': str, 'variant_b': str} for the segment."""
    key = api_key or _get_api_key()
    user_prompt = _build_user_prompt(
        segment_name, recommendations_df, avg_spend, favorite_product, top_category
    )
    variant_a = _call_groq(key, VARIANT_A_SYSTEM, user_prompt)
    variant_b = _call_groq(key, VARIANT_B_SYSTEM, user_prompt)
    return {"variant_a": variant_a, "variant_b": variant_b}


def _build_user_prompt(
    segment_name: str,
    recommendations_df: pd.DataFrame,
    avg_spend: float,
    favorite_product: str | None,
    top_category: str | None,
) -> str:
    products_block = "\n".join(
        f"- {r['product_name']} ({r['category']}) at ${r['price_usd']:.2f}"
        for _, r in recommendations_df.iterrows()
    )
    lines = [
        f"Segment: {segment_name}",
        f"Average lifetime beauty spend in this segment: ${avg_spend:,.2f}",
    ]
    if favorite_product and str(favorite_product).lower() != "nan":
        lines.append(f"Segment's favorite product: {favorite_product}")
    if top_category:
        lines.append(f"Segment's primary beauty category: {top_category}")
    lines += [
        "",
        "Products to recommend in this outreach:",
        products_block,
        "",
        "Write the outreach copy now. 3 to 4 sentences. Follow every brand rule.",
    ]
    return "\n".join(lines)


def _call_groq(api_key: str, system_prompt: str, user_prompt: str) -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 300,
    })

    result = subprocess.run(
        [
            "curl", "-sS", "-X", "POST", GROQ_URL,
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {api_key}",
            "--data-binary", "@-",
        ],
        input=payload,
        text=True,
        capture_output=True,
        timeout=REQUEST_TIMEOUT_SEC,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed (exit {result.returncode}): {result.stderr.strip()}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Non-JSON response from Groq: {result.stdout[:200]}") from e

    if "error" in data:
        raise RuntimeError(f"Groq API error: {data['error']}")
    return data["choices"][0]["message"]["content"].strip()


def _get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key or key.startswith("PASTE_") or key == "your_groq_api_key_here":
        raise RuntimeError(
            "GROQ_API_KEY is missing or still a placeholder. "
            "Paste your real key into .env at the project root."
        )
    return key


if __name__ == "__main__":
    from tools.load_data_tool import load_data
    from tools.recommend_tool import recommend_products
    from tools.segment_tool import segment_clients

    _, beauty_txn_df, catalog_df, rfm_df = load_data(verbose=False)
    _, summary = segment_clients(beauty_txn_df, rfm_df)

    target_segment = "Fragrance VIP"
    row = summary[summary["segment"] == target_segment].iloc[0]
    recs = recommend_products(target_segment, catalog_df, summary, top_n=3)

    result = generate_copy(
        segment_name=target_segment,
        recommendations_df=recs,
        avg_spend=float(row["avg_spend"]),
        favorite_product=row["top_product"],
        top_category="Fragrance",
    )

    print("=" * 70)
    print(f"OUTREACH COPY - {target_segment}")
    print("=" * 70)
    print("\n--- VARIANT A (Warm boutique advisor) ---\n")
    print(result["variant_a"])
    print("\n--- VARIANT B (Exclusive aspirational) ---\n")
    print(result["variant_b"])
    print("\n" + "=" * 70)
