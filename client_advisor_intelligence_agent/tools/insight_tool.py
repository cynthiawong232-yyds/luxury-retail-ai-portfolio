"""Generate natural-language insights from structured client/segment data via Groq.

Uses LLaMA 3.3 70B. Falls back to a deterministic narrative if the Groq SDK
or GROQ_API_KEY is unavailable, so the rest of the agent still works in dev.
"""

from __future__ import annotations

import json
import os
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from groq import Groq
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False


GROQ_MODEL = "llama-3.3-70b-versatile"

VALID_USE_CASES = {
    "client_briefing", "segment_summary", "next_best_action",
    "product_summary", "product_ranking",
}

SYSTEM_PROMPT = (
    "You are a luxury client intelligence assistant for Maison Vega client advisors. "
    "Generate concise, warm, professional narratives (2-4 sentences). "
    "Tone: refined, polished, never clinical or robotic. "
    "Only describe facts present in the provided data — never invent details. "
    "Speak naturally to the client advisor as a trusted colleague."
)

USE_CASE_INSTRUCTIONS = {
    "client_briefing": (
        "Write a brief, advisor-ready briefing on this client. "
        "Cover their segment, recent visit cadence, top spend category, and one suggested next action. "
        "If pct_of_store_sales and pct_of_global_sales are provided, weave in their boutique-level "
        "contribution (primary) and global contribution (context) — e.g. 'contributes ~X% of "
        "boutique revenue and ~Y% of global Maison Vega sales'."
    ),
    "segment_summary": (
        "Summarize this client segment for the advisor. "
        "Highlight size, top spend behavior, and the most notable opportunity or risk."
    ),
    "next_best_action": (
        "Recommend a prioritized outreach plan based on this list of clients. "
        "The headline sentence MUST reference the Lapsing VIP count first, even if "
        "another bucket is larger. Priority order is: Lapsing VIP, Lapsing High Value, "
        "Win-back, Anniversary. Then briefly mention the other buckets in 2-4 sentences total."
    ),
    "product_summary": (
        "Summarize the client base for this product for the advisor. "
        "Mention the product name, how many distinct buyers it has, and name the top 1-2 "
        "buyers with their share of that product's total sales (pct_of_product_sales). "
        "If the top buyer represents a large share, flag them as a key brand ambassador for this SKU. "
        "Keep it to 2-4 sentences."
    ),
    "product_ranking": (
        "Summarize the top-selling products for the advisor. "
        "Lead with the #1 product — name it, state its total_sales and pct_of_scope_sales. "
        "Mention the scope (store or all stores). Briefly note the runner-up product if present. "
        "Keep it to 2-4 sentences."
    ),
}


def _fallback_narrative(summary: dict[str, Any], use_case: str) -> str:
    """Deterministic narrative used when Groq is unavailable."""
    if use_case == "client_briefing":
        name = summary.get("name") or summary.get("client_id", "This client")
        seg = summary.get("rfm_segment", "valued")
        spend = summary.get("total_spend", 0.0)
        fav = summary.get("favorite_category", "—")
        days = summary.get("days_since_last_visit")
        days_str = f"{days} days ago" if days is not None else "recently"
        pct_store = summary.get("pct_of_store_sales")
        pct_global = summary.get("pct_of_global_sales")
        contrib_str = ""
        if pct_store is not None and pct_global is not None:
            contrib_str = (
                f" They represent ~{pct_store:.2f}% of their boutique's sales "
                f"and ~{pct_global:.2f}% of global Maison Vega sales."
            )
        return (
            f"{name} is a {seg} client with lifetime spend of ${spend:,.0f}, "
            f"favoring {fav}. Their last visit was {days_str}.{contrib_str} "
            "Consider a personalized outreach to acknowledge their loyalty."
        )

    if use_case == "segment_summary":
        seg = summary.get("segment", "This segment")
        n = summary.get("count", 0)
        avg = summary.get("avg_monetary_value", 0.0)
        top_cat = summary.get("top_category", "—")
        return (
            f"Your {seg} segment includes {n} clients with an average spend of "
            f"${avg:,.0f}. The strongest category is {top_cat}. "
            "Focus on retention and upsell within this group."
        )

    if use_case == "product_ranking":
        scope = summary.get("scope", "all stores")
        top = summary.get("top_products", [])
        total = summary.get("scope_total_sales", 0.0)
        if not top:
            return f"No product sales found for {scope}."
        t0 = top[0]
        lead = (
            f"At {scope}, {t0['product_name']} is the top-selling product with "
            f"${t0['total_sales']:,.0f} in sales (~{t0['pct_of_scope_sales']:.1f}% of scope)."
        )
        runner = ""
        if len(top) > 1:
            t1 = top[1]
            runner = (
                f" Runner-up: {t1['product_name']} at ${t1['total_sales']:,.0f} "
                f"(~{t1['pct_of_scope_sales']:.1f}%)."
            )
        return (
            f"{lead}{runner} Total scope sales: ${total:,.0f}. "
            "Consider aligning outreach and inventory focus around these SKUs."
        )

    if use_case == "product_summary":
        pname = summary.get("product_name", "this product")
        n_buyers = summary.get("num_buyers", 0)
        total = summary.get("product_total_sales", 0.0)
        top = summary.get("top_buyers", [])
        lead = ""
        if top:
            t0 = top[0]
            lead = (
                f" Top buyer: {t0.get('name') or t0.get('client_id')} "
                f"(~{t0.get('pct_of_product_sales', 0):.1f}% of this SKU's sales)."
            )
        return (
            f"{pname} has {n_buyers} distinct buyer(s) and ${total:,.0f} in total sales.{lead} "
            "Consider this client list for a personalized product-level outreach."
        )

    if use_case == "next_best_action":
        vip = summary.get("lapsing_vip_count", 0)
        hv = summary.get("lapsing_high_value_count", 0)
        wb = summary.get("winback_count", 0)
        anniv = summary.get("anniversary_count", 0)
        return (
            f"Prioritize your {vip} Lapsing VIP client(s) first this week — they are the "
            f"highest-impact outreach. After that: {hv} Lapsing High Value, {wb} Win-back "
            f"candidate(s), and {anniv} Anniversary touchpoint(s). "
            "Lead with the highest-spending Lapsing VIPs by longest absence."
        )

    return "No insight available."


def generate_insight(summary: dict[str, Any], use_case: str = "client_briefing") -> str:
    """Return a 2-4 sentence narrative for a structured summary.

    use_case: one of 'client_briefing', 'segment_summary', 'next_best_action'.
    """
    if use_case not in VALID_USE_CASES:
        raise ValueError(f"use_case must be one of {VALID_USE_CASES}, got {use_case!r}")

    api_key = os.getenv("GROQ_API_KEY")

    if not _GROQ_AVAILABLE or not api_key:
        reason = "groq SDK not installed" if not _GROQ_AVAILABLE else "GROQ_API_KEY not set"
        print(f"[insight_tool] Using fallback narrative ({reason}).")
        return _fallback_narrative(summary, use_case)

    instruction = USE_CASE_INSTRUCTIONS[use_case]
    user_message = (
        f"{instruction}\n\n"
        f"Structured data (JSON):\n{json.dumps(summary, default=str, indent=2)}"
    )

    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.6,
            max_tokens=220,
        )
        narrative = completion.choices[0].message.content.strip()
        print(f"[insight_tool] Generated {use_case} narrative ({len(narrative)} chars).")
        return narrative
    except Exception as e:
        print(f"[insight_tool] Groq call failed ({e}); using fallback.")
        return _fallback_narrative(summary, use_case)


if __name__ == "__main__":
    sample = {
        "client_id": "MVC-00042",
        "name": "William Kim",
        "rfm_segment": "VIP",
        "total_spend": 191348.48,
        "favorite_category": "Handbags",
        "days_since_last_visit": 54,
    }
    print("\n--- Client briefing ---")
    print(generate_insight(sample, "client_briefing"))
