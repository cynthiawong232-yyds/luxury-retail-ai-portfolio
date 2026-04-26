import streamlit as st
import requests
import json
import os
import pandas as pd
from datetime import date
from utils.data_loader import (
    store_totals, category_breakdown, top_styles,
    calc_wos, calc_disc_rate, calc_sell_through
)
from config import STORES, GROQ_MODEL, GROQ_API_URL, COMP_WARNING_PCT, DISC_RATE_HIGH

# Cross-project guardrails. `shared` lives at the repo root and is added to
# sys.path by main.py (router) or by the standalone __main__ block in app.py.
from shared.scope import FLAGSHIP_SCOPE


# Universal diagnostic-reasoning instructions appended to every LLM call from
# this tab. Tells the model to answer "why?" questions with ranked drivers +
# explicit acknowledgement of what data it doesn't have.
_DIAGNOSTIC_INSTRUCTIONS = """

=== DIAGNOSTIC REASONING ===
When answering questions about WHY a metric moved (e.g. "why is SOHO down?",
"what's dragging EU?"):
  1. List the 2-3 most likely drivers, ranked by strength of evidence in the
     data above.
  2. For each driver, cite the specific number(s) from the data that support it
     (e.g. "discount rate 22% vs. 14% prior period").
  3. Explicitly note what data you LACK that would strengthen or rule out each
     hypothesis (e.g. "I don't have foot traffic, so I cannot rule out a
     traffic decline").
  4. Do NOT invent numbers, weather events, marketing actions, or staffing
     changes that are not in the data above. If the data doesn't support a
     diagnosis, say so.
=== END DIAGNOSTIC REASONING ===
"""


# ── Build a data context string sent to the LLM ──────────────────────────────

def _build_context(data: dict, period: str) -> str:
    lines = [
        f"You are a senior retail analytics advisor for Maison Voss.",
        f"Today is {date.today().strftime('%B %d, %Y')}.",
        f"The user is analyzing {period} performance for 3 new flagship stores.",
        f"All sales figures are in USD.",
        "",
        "IMPORTANT CONTEXT:",
        "- These are newly opened flagship stores being closely monitored by leadership.",
        "- SOHO (US, A800): Opened December 7 2025. Very new — no prior year comparable at all.",
        "- JAPAN (Asia, J347): Opened August 31 2025. Partial LY data at best.",
        "- EU (EU, EU_F07M): Opened February 9 2025. Has the most history of the three.",
        "- All three stores opened within the same fiscal year (2025).",
        "- Do NOT rely on CY vs LY comp % as the primary success metric for these stores.",
        "  Instead focus on: absolute sales trajectory, ramp curve, category mix,",
        "  AUR health, discount rate, and WOS.",
        "- Leadership is likely asking: is the store concept working, how does the brand",
        "  translate across markets, when does each store reach maturity?",
        "- Be direct, specific, and actionable. No generic retail advice.",
        "",
    ]

    totals = store_totals(data)
    lines.append(f"=== {period} STORE SUMMARY ===")
    for _, row in totals.iterrows():
        code    = row['store_code']
        label   = row['store_label']
        region  = row['store_region']
        weeks   = row.get('weeks_open', '?')
        net_cy  = row['netslsamt_cy']
        net_ly  = row['netslsamt_ly']
        qty_cy  = row['netslsqty_cy']
        aur     = net_cy / qty_cy if qty_cy > 0 else 0
        disc    = calc_disc_rate(data[code]) * 100
        wos     = calc_wos(data[code])
        st_pct  = calc_sell_through(data[code]) * 100
        var_str = f"{(net_cy/net_ly-1)*100:+.1f}%" if net_ly > 0 else "N/A (new store)"

        lines += [
            f"\n{label} ({region}) — Week {weeks} since opening:",
            f"  Net Sales CY:  ${net_cy:,.0f}",
            f"  Net Sales LY:  ${net_ly:,.0f}  ({var_str})",
            f"  Units Sold:    {qty_cy:,.0f}",
            f"  AUR:           ${aur:.2f}",
            f"  Disc Rate:     {disc:.1f}%",
            f"  WOS:           {wos:.1f} weeks",
            f"  Sell-Through:  {st_pct:.1f}%",
        ]

        # Top 5 categories
        cat = category_breakdown(data[code]).head(5)
        lines.append(f"  Top Categories: " +
                     ", ".join(f"{r['gmh_category_text']} ${r['netslsamt_cy']:,.0f}"
                               for _, r in cat.iterrows()))

        # Top 5 styles
        styles = top_styles(data[code], n=5)
        lines.append(f"  Top Styles: " +
                     ", ".join(f"{r['plm_style_code']} ({r['gmh_category_text']}) ${r['netslsamt_cy']:,.0f}"
                               for _, r in styles.iterrows()))

    # Append the universal scope guardrails + diagnostic reasoning instructions
    # so every LLM call from this tab inherits both layers without per-call work.
    return "\n".join(lines) + FLAGSHIP_SCOPE.system_prompt_block() + _DIAGNOSTIC_INSTRUCTIONS


# ── Groq API call ─────────────────────────────────────────────────────────────

def _call_groq(system_prompt: str, user_message: str, api_key: str,
               history: list = None) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    resp = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 1024,
        },
        timeout=30
    )
    if resp.status_code != 200:
        raise Exception(f"Groq API error {resp.status_code}: {resp.text}")
    return resp.json()["choices"][0]["message"]["content"]


# ── Anomaly detection (no API needed) ────────────────────────────────────────

def _detect_anomalies(data: dict, period: str) -> list:
    alerts = []
    totals = store_totals(data)

    for _, row in totals.iterrows():
        code    = row['store_code']
        label   = row['store_label']
        region  = row['store_region']
        net_cy  = row['netslsamt_cy']
        net_ly  = row['netslsamt_ly']
        wos     = calc_wos(data[code])
        disc    = calc_disc_rate(data[code]) * 100

        # Comp warning
        if net_ly > 0:
            var = (net_cy / net_ly - 1) * 100
            if var < COMP_WARNING_PCT:
                alerts.append(("🔴", f"{label} ({region})",
                               f"{period} comp is {var:+.1f}% — significantly below LY. "
                               f"Investigate category or channel drivers."))

        # Discount rate
        if disc > DISC_RATE_HIGH * 100:
            alerts.append(("🟡", f"{label} ({region})",
                           f"Discount rate is {disc:.1f}% — above {DISC_RATE_HIGH*100:.0f}% threshold. "
                           f"Sales may be relying on promotions."))

        # WOS
        if 0 < wos < 4:
            alerts.append(("🔴", f"{label} ({region})",
                           f"WOS is {wos:.1f} — critically low. Stockout risk this period."))
        elif wos > 14:
            alerts.append(("🟡", f"{label} ({region})",
                           f"WOS is {wos:.1f} — over-inventoried. Consider markdowns or transfers."))

        # New store with zero sales
        if net_cy == 0:
            alerts.append(("⚪", f"{label} ({region})",
                           f"No sales data for {period}. Check if data loaded correctly."))

    # Cross-store category gap
    cat_ranks = {}
    for code, df in data.items():
        cat = category_breakdown(df)
        for rank, (_, r) in enumerate(cat.iterrows()):
            key = r['gmh_category_text']
            if key not in cat_ranks:
                cat_ranks[key] = {}
            cat_ranks[key][code] = (rank + 1, r['netslsamt_cy'])

    for cat, stores in cat_ranks.items():
        if len(stores) < 2:
            continue
        vals = [(code, rank, sales) for code, (rank, sales) in stores.items()]
        vals.sort(key=lambda x: x[1])
        best_code, best_rank, best_sales = vals[0]
        for other_code, other_rank, other_sales in vals[1:]:
            if best_rank == 1 and other_rank >= 4 and best_sales > 0:
                best_label  = STORES[best_code]['label']
                other_label = STORES[other_code]['label']
                alerts.append(("🔵", "CROSS-MARKET",
                               f"'{cat}' is #{best_rank} at {best_label} (${best_sales:,.0f}) "
                               f"but #{other_rank} at {other_label}. "
                               f"Possible assortment or allocation opportunity."))
                break

    return alerts


# ── Render ────────────────────────────────────────────────────────────────────

def render(data: dict, period: str):
    st.markdown('<div class="section-header">AI ADVISOR</div>', unsafe_allow_html=True)

    api_key = os.environ.get("GROQ_API_KEY", "")

    context = _build_context(data, period)

    # ── Function 1: Anomaly Watch List (no API) ───────────────────────────────
    st.markdown('<div class="section-header">① ANOMALY WATCH LIST</div>',
                unsafe_allow_html=True)
    st.caption("Rule-based flags — no API key needed.")

    alerts = _detect_anomalies(data, period)
    if alerts:
        for icon, store, msg in alerts:
            severity = "warning" if icon == "🟡" else ("info" if icon in ("🔵","⚪") else "")
            st.markdown(f"""
            <div class="alert-card {severity}">
                {icon} <strong>{store}</strong> — {msg}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-card info">
            ✓ No anomalies detected for this period.
        </div>
        """, unsafe_allow_html=True)

    if not api_key:
        st.info("Groq API key not found. Add GROQ_API_KEY to your .env file to unlock AI features.")
        return

    # ── Function 2: Weekly Narrative ─────────────────────────────────────────
    st.markdown('<div class="section-header">② WEEKLY NARRATIVE SUMMARY</div>',
                unsafe_allow_html=True)

    if st.button("Generate Weekly Narrative", key="btn_narrative"):
        with st.spinner("Drafting narrative..."):
            try:
                prompt = (
                    f"Write a concise 4–6 sentence executive narrative summary of this week's "
                    f"{period} performance across the 3 flagship stores. "
                    f"Lead with the most important finding. "
                    f"Call out any stores with no LY comparable and reframe those in terms of "
                    f"absolute trajectory instead. "
                    f"End with one forward-looking sentence. "
                    f"Write in plain business English — no bullet points, no headers."
                )
                narrative = _call_groq(context, prompt, api_key)
                st.session_state["narrative"] = narrative
            except Exception as e:
                st.error(f"API error: {e}")

    if "narrative" in st.session_state:
        st.markdown(
            f'<div class="ai-message">{st.session_state["narrative"]}</div>',
            unsafe_allow_html=True
        )

    # ── Function 3: Market Insight ────────────────────────────────────────────
    st.markdown('<div class="section-header">③ CROSS-MARKET CATEGORY INSIGHT</div>',
                unsafe_allow_html=True)

    if st.button("Analyse Cross-Market Patterns", key="btn_market"):
        with st.spinner("Analysing..."):
            try:
                prompt = (
                    "Compare category and gender performance across the 3 stores. "
                    "Identify the top 2–3 meaningful differences in what's selling across markets. "
                    "Suggest one possible business reason for each difference "
                    "(e.g. local consumer preference, climate, assortment depth). "
                    "Be specific about category names and store names. "
                    "Keep it to 150 words."
                )
                insight = _call_groq(context, prompt, api_key)
                st.session_state["market_insight"] = insight
            except Exception as e:
                st.error(f"API error: {e}")

    if "market_insight" in st.session_state:
        st.markdown(
            f'<div class="ai-message">{st.session_state["market_insight"]}</div>',
            unsafe_allow_html=True
        )

    # ── Function 4: Period Projection ─────────────────────────────────────────
    st.markdown('<div class="section-header">④ PERIOD PROJECTION</div>',
                unsafe_allow_html=True)
    st.caption("Directional pace projection based on current period run rate.")

    if st.button("Project Period-End Performance", key="btn_proj"):
        with st.spinner("Projecting..."):
            try:
                prompt = (
                    f"Based on the {period} data provided, project where each store is likely "
                    f"to land by end of period if the current pace continues. "
                    f"For stores with LY data, express this as a comp % range. "
                    f"For the US store (no LY), express as an absolute sales trajectory. "
                    f"Flag any store where the current pace suggests a meaningful risk or opportunity. "
                    f"Keep it under 120 words. Be direct."
                )
                proj = _call_groq(context, prompt, api_key)
                st.session_state["projection"] = proj
            except Exception as e:
                st.error(f"API error: {e}")

    if "projection" in st.session_state:
        st.markdown(
            f'<div class="ai-message">{st.session_state["projection"]}</div>',
            unsafe_allow_html=True
        )

    # ── Function 5: Natural Language Q&A ─────────────────────────────────────
    st.markdown('<div class="section-header">⑤ ASK YOUR DATA</div>',
                unsafe_allow_html=True)
    st.caption("Ask anything about the loaded store data in plain English.")

    # Quick prompts — first two are diagnostic ("why?") to demo the
    # ranked-drivers + data-I-lack reasoning pattern.
    quick = st.pills(
        "Quick questions",
        options=[
            "Why is the worst-performing store underperforming this period?",
            "What are the most likely drivers of the EU portfolio's results?",
            "Which store has the best momentum?",
            "Where is inventory risk highest?",
            "Which categories should we prioritize?",
            "Draft a 3-line email update for my manager",
        ],
        key="quick_pills"
    )

    # Maintain chat history
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    user_input = st.chat_input("Ask a question about your store data...")
    if quick and quick != st.session_state.get("_last_quick"):
        user_input = quick
        st.session_state["_last_quick"] = quick

    if user_input:
        st.session_state["chat_history"].append({"role": "user", "content": user_input})
        with st.spinner("Thinking..."):
            try:
                # Keep last 6 turns for context
                history = st.session_state["chat_history"][-6:]
                answer = _call_groq(context, user_input, api_key, history=history[:-1])
                st.session_state["chat_history"].append({"role": "assistant", "content": answer})
            except Exception as e:
                st.session_state["chat_history"].append(
                    {"role": "assistant", "content": f"Error: {e}"}
                )

    # Display chat
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="user-message">YOU: {msg["content"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="ai-message">{msg["content"]}</div>',
                unsafe_allow_html=True
            )

    if st.session_state.get("chat_history"):
        if st.button("Clear Chat", key="clear_chat"):
            st.session_state["chat_history"] = []
            st.rerun()
