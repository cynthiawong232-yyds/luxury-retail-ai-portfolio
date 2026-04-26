"""Client Advisor Intelligence Agent — routes natural language questions to tools.

Intent classification is explicit keyword matching (not AI inference) per spec.
Four intents:
  1. SEGMENT  — broad questions about groups of clients     -> rfm_query_tool
  2. CLIENT   — questions about an individual client        -> transaction_query_tool + rfm_query_tool
  3. ALERT    — prioritization / outreach / at-risk         -> alert_tool
  4. PRODUCT  — questions about a specific product          -> transaction_query_tool
Fallback: SEGMENT.
"""

from __future__ import annotations

import re
from typing import Optional

import pandas as pd

# Tool imports — uncommented as each tool is built.
from tools.load_data_tool import load_data
from tools.rfm_query_tool import rfm_query
from tools.transaction_query_tool import (
    transaction_query,
    transaction_summary,
    product_contribution,
    client_contribution,
    top_products,
    _resolve_product_name,
)
from tools.insight_tool import generate_insight
from tools.alert_tool import get_alerts


CLIENT_ID_PATTERN = re.compile(r"\bMVC-\d{5}\b", re.IGNORECASE)

SEGMENT_KEYWORDS = [
    "who are my", "which clients", "show me all", "how many", "top",
    "lapsing", "vip", "high value", "segment", "nationality",
]

# Phrases that indicate a ranking/group question — checked BEFORE name matching
# to prevent "who is the top 1 client in paris" from routing to CLIENT.
# Keep this narrow: only patterns that unambiguously ask for ranked client lists.
SEGMENT_RANKING_PHRASES = [
    "top 1 client", "top 1 clients",
    "who are my top", "who are the top",
]

CLIENT_KEYWORDS = [
    "tell me about", "briefing on", "history of", "profile of",
    "contribution", "% of sales", "percent of sales", "percentage of sales",
    "how much did", "how much does", "how much has",
]

ALERT_KEYWORDS = [
    "prioritize", "this week", "should i reach out", "alerts",
    "haven't visited", "havent visited", "at risk", "win-back", "win back",
]

PRODUCT_KEYWORDS = [
    "product", "sold", "bought", "buyers of", "who bought", "who purchased",
    "best selling", "best-selling", "bestseller", "top seller", "top-selling",
]

RANKING_PHRASES = [
    "top sale", "top sales", "top seller", "top-selling", "top selling",
    "best seller", "best selling", "best-selling", "bestseller",
    "most popular", "most sold", "highest selling", "highest-selling",
    "top product", "top products", "which product", "what product",
]

PRODUCT_TIERS = ["heritage", "limited", "essential", "classic", "signature"]
PRODUCT_CATEGORIES_LOWER = [
    "handbags", "footwear", "accessories", "ready-to-wear", "ready to wear",
    "small leather goods", "jewelry",
]


_NAME_NOISE = {
    "a", "an", "the", "is", "are", "my", "me", "at", "in", "to", "of", "for",
    "who", "what", "how", "many", "much", "top", "all", "about", "do", "does",
    "tell", "show", "clients", "client", "sales", "buy", "bought", "this",
    "contribution", "percentage", "percent", "store", "product", "products",
    "and", "or", "with", "from", "by", "on", "not", "no", "yes", "please",
    "briefing", "history", "profile", "vip", "high", "value", "lapsing",
    "segment", "paris", "tokyo", "soho", "york", "new", "which", "that",
}


def _name_to_client_id(question: str, rfm_df: pd.DataFrame) -> Optional[str] | list[str]:
    """Try to match a first+last name in the question to a client.

    Case-insensitive. Tries consecutive word pairs first (first+last), then
    single-word last-name or first-name lookup (skipping noise words).
    Returns a single client_id on unique match, a list of IDs on ambiguity,
    or None if no match.
    """
    words = re.findall(r"[a-zA-Z]{2,}", question)
    if not words:
        return None

    # 1. Try consecutive pairs as first_name + last_name
    for i in range(len(words) - 1):
        first, last = words[i].lower(), words[i + 1].lower()
        if first in _NAME_NOISE and last in _NAME_NOISE:
            continue
        hits = rfm_df[
            (rfm_df["first_name"].str.lower() == first)
            & (rfm_df["last_name"].str.lower() == last)
        ]
        if len(hits) == 1:
            return str(hits.iloc[0]["client_id"])
        if len(hits) > 1:
            return hits["client_id"].astype(str).tolist()

    # 2. Try reversed pairs (last_name first_name) for "Sharma Ling"-style input
    for i in range(len(words) - 1):
        last, first = words[i].lower(), words[i + 1].lower()
        if first in _NAME_NOISE and last in _NAME_NOISE:
            continue
        hits = rfm_df[
            (rfm_df["first_name"].str.lower() == first)
            & (rfm_df["last_name"].str.lower() == last)
        ]
        if len(hits) == 1:
            return str(hits.iloc[0]["client_id"])
        if len(hits) > 1:
            return hits["client_id"].astype(str).tolist()

    # 3. Try single words as last_name (skip noise), unique match only
    for w in words:
        wl = w.lower()
        if wl in _NAME_NOISE or len(wl) < 3:
            continue
        hits = rfm_df[rfm_df["last_name"].str.lower() == wl]
        if len(hits) == 1:
            return str(hits.iloc[0]["client_id"])
        # Don't return ambiguous single-name matches — too risky

    # 4. Try single words as first_name, unique match only
    for w in words:
        wl = w.lower()
        if wl in _NAME_NOISE or len(wl) < 3:
            continue
        hits = rfm_df[rfm_df["first_name"].str.lower() == wl]
        if len(hits) == 1:
            return str(hits.iloc[0]["client_id"])

    return None


def _looks_like_product_question(question: str) -> bool:
    q = question.lower()
    if any(k in q for k in PRODUCT_KEYWORDS):
        return True
    if any(p in q for p in RANKING_PHRASES):
        return True
    if "mv " in q and any(t in q for t in PRODUCT_TIERS):
        return True
    if any(c in q for c in PRODUCT_CATEGORIES_LOWER) and any(t in q for t in PRODUCT_TIERS):
        return True
    return False


def _is_product_ranking_question(question: str) -> bool:
    q = question.lower()
    if any(p in q for p in RANKING_PHRASES):
        return True
    if re.search(r"\btop\s+\d+\s+products?\b", q):
        return True
    return False


STORE_PHRASE_TO_CODE = {
    # SOHO / New York / USA
    "soho": "A800", "new york": "A800", "nyc": "A800", "a800": "A800",
    "united states": "A800", "america": "A800", "usa": "A800",
    # Tokyo / Japan
    "tokyo": "J347", "j347": "J347", "japan": "J347",
    # Paris / France / Europe
    "paris": "EU_F07M", "eu_f07m": "EU_F07M",
    "france": "EU_F07M", "europe": "EU_F07M",
}

# Cities and countries we DON'T have store data for. If a question names one of
# these (and no supported location), the agent returns a "no data" response
# instead of silently falling back to all stores.
UNSUPPORTED_LOCATIONS = {
    # Europe
    "london", "uk", "u.k.", "britain", "england", "great britain",
    "milan", "rome", "florence", "italy",
    "madrid", "barcelona", "spain",
    "berlin", "munich", "frankfurt", "germany",
    "amsterdam", "netherlands", "holland",
    "vienna", "austria",
    "geneva", "zurich", "switzerland",
    "brussels", "belgium",
    "stockholm", "sweden", "copenhagen", "denmark", "oslo", "norway",
    "moscow", "russia",
    # Asia / Middle East
    "hong kong", "shanghai", "beijing", "china", "macau",
    "seoul", "korea", "south korea",
    "singapore", "bangkok", "thailand",
    "mumbai", "delhi", "india",
    "taipei", "taiwan",
    "dubai", "uae", "abu dhabi",
    "riyadh", "saudi arabia",
    "doha", "qatar", "kuwait",
    "tel aviv", "israel",
    # Americas (other than NYC)
    "los angeles", "miami", "chicago", "san francisco",
    "las vegas", "boston", "houston", "dallas",
    "toronto", "vancouver", "montreal", "canada",
    "mexico", "mexico city",
    "sao paulo", "rio", "brazil",
    "buenos aires", "argentina",
    # Oceania / Africa
    "sydney", "melbourne", "australia",
    "johannesburg", "cape town", "south africa",
}


def _find_location(question: str, locations) -> Optional[str]:
    """Return the first location keyword in the question (word-boundary match).

    Tries longest phrases first so 'new york' wins over 'york' if both were in
    the location set. Returns None if no location matches.
    """
    q = question.lower()
    for phrase in sorted(locations, key=len, reverse=True):
        if re.search(r"\b" + re.escape(phrase) + r"\b", q):
            return phrase
    return None


def _extract_store_code(question: str, store_filter: str = "All") -> Optional[str]:
    matched = _find_location(question, STORE_PHRASE_TO_CODE.keys())
    if matched:
        return STORE_PHRASE_TO_CODE[matched]
    if store_filter and store_filter.lower() != "all":
        return store_filter
    return None


def _is_segment_ranking(question: str) -> bool:
    """Return True if the question asks for top/ranked clients (SEGMENT), not a specific person."""
    q = question.lower()
    if any(p in q for p in SEGMENT_RANKING_PHRASES):
        return True
    if re.search(r"\btop\s+\d+\s+clients?\b", q):
        return True
    return False


def classify_intent(question: str, rfm_df: Optional[pd.DataFrame] = None) -> str:
    """Return one of: 'CLIENT', 'PRODUCT', 'ALERT', 'SEGMENT'. Most specific first."""
    q = question.lower().strip()

    # 1. Explicit client ID is always CLIENT
    if CLIENT_ID_PATTERN.search(question):
        return "CLIENT"

    # 2. Segment-level ranking phrases (top N clients) beat everything except ID
    if _is_segment_ranking(question):
        return "SEGMENT"

    # 3. Product ranking (top-selling product)
    if _is_product_ranking_question(question):
        return "PRODUCT"

    # 4. Product-specific (who bought X)
    if _looks_like_product_question(question):
        return "PRODUCT"

    # 5. Explicit CLIENT keywords (tell me about, contribution, etc.)
    if any(k in q for k in CLIENT_KEYWORDS):
        return "CLIENT"

    # 6. Alert keywords
    if any(k in q for k in ALERT_KEYWORDS):
        return "ALERT"

    # 7. Name match in data → CLIENT (unless segment keywords dominate)
    if rfm_df is not None:
        name_match = _name_to_client_id(question, rfm_df)
        if name_match is not None:
            return "CLIENT"

    # 8. Segment keywords → SEGMENT
    if any(k in q for k in SEGMENT_KEYWORDS) or "store" in q:
        return "SEGMENT"

    return "SEGMENT"


def _extract_client_id(question: str, rfm_df: Optional[pd.DataFrame] = None) -> Optional[str] | list[str]:
    match = CLIENT_ID_PATTERN.search(question)
    if match:
        return match.group(0).upper()
    if rfm_df is not None:
        return _name_to_client_id(question, rfm_df)
    return None


SEGMENT_PHRASE_TO_NAME = {
    "vip": "VIP",
    "high value": "High Value",
    "active": "Active",
    "dormant": "Dormant",
}

STORE_PHRASES = list(STORE_PHRASE_TO_CODE.keys())
NATIONALITIES = [
    "japanese", "chinese", "korean", "american", "french", "italian",
    "british", "german", "spanish", "russian",
]
CATEGORY_PHRASES = [
    "handbags", "small leather goods", "footwear", "ready-to-wear",
    "jewelry", "accessories", "fragrances",
]


def _parse_segment_params(question: str, store_filter: str) -> dict:
    q = question.lower()
    params: dict = {}

    for phrase, name in SEGMENT_PHRASE_TO_NAME.items():
        if phrase in q:
            params["segment"] = name
            break

    if "lapsing" in q:
        params["lapsing"] = True
        params.pop("segment", None)

    matched_store = _find_location(question, STORE_PHRASE_TO_CODE.keys())
    if matched_store:
        params["store"] = STORE_PHRASE_TO_CODE[matched_store]
    elif store_filter and store_filter.lower() != "all":
        params["store"] = store_filter

    for nat in NATIONALITIES:
        if nat in q:
            params["nationality"] = nat.capitalize()
            break

    for cat in CATEGORY_PHRASES:
        if cat in q:
            params["favorite_category"] = cat.title() if cat != "ready-to-wear" else "Ready-to-Wear"
            break

    top_match = re.search(r"top\s+(\d+)", q)
    if top_match:
        params["top_n"] = int(top_match.group(1))

    return params


def _extract_product_phrase(question: str) -> Optional[str]:
    """Pull a product-like phrase from a question for fuzzy matching downstream.

    Prefers quoted text, then an 'MV ...' span, else joins any tier/category hits.
    """
    q = question.strip()

    quoted = re.search(r'["\']([^"\']+)["\']', q)
    if quoted:
        return quoted.group(1)

    mv_match = re.search(r"\bMV\s+[A-Za-z][\w\-\s]*", q, re.IGNORECASE)
    if mv_match:
        phrase = mv_match.group(0).strip()
        phrase = re.split(r"\bfor\b|\bat\b|\?|,", phrase, maxsplit=1)[0].strip()
        return phrase

    ql = q.lower()
    parts: list[str] = []
    for cat in PRODUCT_CATEGORIES_LOWER:
        if cat in ql:
            parts.append(cat)
            break
    for tier in PRODUCT_TIERS:
        if tier in ql:
            parts.append(tier)
            break
    if parts:
        return " ".join(parts)
    return None


def run_agent(user_question: str, store_filter: str = "All") -> dict:
    """Route a user question to the right tool(s) and return a structured response.

    Returns a dict with keys:
      - response_text (str)
      - data_table (pd.DataFrame | None)
      - intent (str)
      - tool_called (str)
    """
    _, transactions_df, rfm_df = load_data()

    # Early guard: if the question names a place we don't have store data for
    # (and doesn't ALSO name a supported store), bail out with a clear message
    # rather than silently falling back to all stores.
    unsupported = _find_location(user_question, UNSUPPORTED_LOCATIONS)
    supported = _find_location(user_question, STORE_PHRASE_TO_CODE.keys())
    if unsupported and not supported:
        return {
            "response_text": (
                f"I don't have data for {unsupported.title()}. "
                "Maison Vega data covers our SOHO New York, Tokyo, and Paris boutiques only."
            ),
            "data_table": None,
            "intent": "NO_DATA",
            "tool_called": "none",
        }

    intent = classify_intent(user_question, rfm_df=rfm_df)

    response_text: str = ""
    data_table: Optional[pd.DataFrame] = None
    tool_called: str = ""

    if intent == "SEGMENT":
        tool_called = "rfm_query_tool"
        params = _parse_segment_params(user_question, store_filter)
        data_table = rfm_query(rfm_df, **params)

        if len(data_table) == 0:
            response_text = "No clients matched that query."
            data_table = None
        else:
            top_cat_counts = data_table["favorite_category"].value_counts()
            seg_summary = {
                "segment": params.get("segment") or ("lapsing" if params.get("lapsing") else "filtered"),
                "count": int(len(data_table)),
                "avg_monetary_value": float(data_table["monetary_value"].mean()),
                "top_category": top_cat_counts.index[0] if len(top_cat_counts) else None,
                "filters": {k: v for k, v in params.items() if v not in (None, False)},
            }
            response_text = generate_insight(seg_summary, use_case="segment_summary")

    elif intent == "CLIENT":
        tool_called = "transaction_query_tool + rfm_query_tool"
        resolved = _extract_client_id(user_question, rfm_df=rfm_df)

        if resolved is None:
            response_text = (
                "I couldn't find that client. Include a client ID (MVC-XXXXX) "
                "or a first + last name I can match."
            )
        elif isinstance(resolved, list):
            matches = rfm_df[rfm_df["client_id"].isin(resolved)][
                ["client_id", "first_name", "last_name", "store_name", "rfm_segment", "monetary_value"]
            ].reset_index(drop=True)
            response_text = (
                f"Multiple clients share that name ({len(resolved)} matches). "
                "Please re-ask with the specific MVC-XXXXX ID."
            )
            data_table = matches
        else:
            client_id = resolved
            txns = transaction_query(transactions_df, client_id=client_id)
            summary = transaction_summary(txns)
            rfm_row = rfm_df[rfm_df["client_id"] == client_id]

            if len(txns) == 0 and len(rfm_row) == 0:
                response_text = f"No client found with ID {client_id}."
            else:
                preferred_store = None
                if len(rfm_row) > 0:
                    preferred_store = str(rfm_row.iloc[0]["preferred_store"])
                contrib = client_contribution(
                    transactions_df, client_id, preferred_store=preferred_store
                )

                briefing_input: dict = {
                    "client_id": client_id,
                    "total_spend": summary["total_spend"],
                    "num_transactions": summary["num_transactions"],
                    "num_visits": summary["num_visits"],
                    "favorite_category": summary["favorite_category"],
                    "pct_of_store_sales": round(contrib["pct_of_store_sales"], 3),
                    "pct_of_global_sales": round(contrib["pct_of_global_sales"], 3),
                }
                if len(rfm_row) > 0:
                    r = rfm_row.iloc[0]
                    briefing_input.update({
                        "name": f"{r['first_name']} {r['last_name']}",
                        "nationality": r["nationality"],
                        "store_name": r["store_name"],
                        "rfm_segment": r["rfm_segment"],
                        "days_since_last_visit": int(r["days_since_last_visit"]),
                        "monetary_value": float(r["monetary_value"]),
                    })
                response_text = generate_insight(briefing_input, use_case="client_briefing")
                data_table = txns

    elif intent == "PRODUCT" and _is_product_ranking_question(user_question):
        tool_called = "transaction_query_tool (top_products)"
        store_code = _extract_store_code(user_question, store_filter)

        category = None
        ql = user_question.lower()
        for cat in PRODUCT_CATEGORIES_LOWER:
            if cat in ql:
                category = "Ready-to-Wear" if cat in ("ready-to-wear", "ready to wear") else cat.title()
                break

        top_n = 5
        top_match = re.search(r"top\s+(\d+)", ql)
        if top_match:
            top_n = int(top_match.group(1))
        elif "top product" in ql and "top products" not in ql:
            top_n = 1

        ranked, meta = top_products(
            transactions_df, store_code=store_code, category=category, top_n=top_n
        )
        if len(ranked) == 0:
            response_text = "No product sales found for that scope."
        else:
            display = ranked.copy()
            display["total_sales"] = display["total_sales"].round(2)
            display["pct_of_scope_sales"] = display["pct_of_scope_sales"].round(2)
            data_table = display

            store_label = {
                "A800": "MV SOHO New York",
                "J347": "MV Flagship Tokyo",
                "EU_F07M": "MV Flagship Paris",
            }.get(store_code, "all stores")

            ranking_summary = {
                "scope": store_label,
                "store_code": store_code,
                "category_filter": category,
                "scope_total_sales": round(meta["scope_total_sales"], 2),
                "num_products_in_scope": meta["num_products"],
                "top_products": [
                    {
                        "product_name": r["product_name"],
                        "category": r["category"],
                        "total_sales": round(float(r["total_sales"]), 2),
                        "units_sold": int(r["units_sold"]),
                        "num_buyers": int(r["num_buyers"]),
                        "pct_of_scope_sales": round(float(r["pct_of_scope_sales"]), 2),
                    }
                    for _, r in ranked.iterrows()
                ],
            }
            response_text = generate_insight(ranking_summary, use_case="product_ranking")

    elif intent == "PRODUCT":
        tool_called = "transaction_query_tool (product_contribution)"
        product_query = _extract_product_phrase(user_question)
        if not product_query:
            response_text = (
                "I couldn't identify a product in your question. Try naming the "
                "category and tier, e.g. 'Handbags Heritage' or 'MV Footwear Classic'."
            )
        else:
            buyers, meta = product_contribution(
                transactions_df, product_query, rfm_df=rfm_df
            )
            if meta["product_name"] is None or len(buyers) == 0:
                response_text = (
                    f"No product matched '{product_query}'. Check the product name "
                    "and try again."
                )
            else:
                display = buyers.copy()
                display["client_spend"] = display["client_spend"].round(2)
                display["pct_of_product_sales"] = display["pct_of_product_sales"].round(2)
                data_table = display

                top = buyers.head(3).to_dict(orient="records")
                product_summary = {
                    "product_name": meta["product_name"],
                    "product_total_sales": round(meta["product_total_sales"], 2),
                    "num_buyers": meta["num_buyers"],
                    "num_units": meta["num_units"],
                    "top_buyers": [
                        {
                            "client_id": b["client_id"],
                            "name": b.get("name"),
                            "client_spend": round(float(b["client_spend"]), 2),
                            "pct_of_product_sales": round(float(b["pct_of_product_sales"]), 2),
                        }
                        for b in top
                    ],
                }
                response_text = generate_insight(product_summary, use_case="product_summary")

    elif intent == "ALERT":
        tool_called = "alert_tool"

        store_param = None if not store_filter or store_filter.lower() == "all" else store_filter
        data_table = get_alerts(rfm_df, store=store_param)

        if len(data_table) == 0:
            response_text = "No clients are currently flagged for outreach."
            data_table = None
        else:
            # Priority order is fixed by spec, NOT by bucket size.
            priority_order = ["Lapsing VIP", "Lapsing High Value", "Win-back", "Anniversary"]
            counts = data_table["alert_type"].value_counts().to_dict()
            ordered_counts = {b: int(counts.get(b, 0)) for b in priority_order}

            action_input = {
                "total_count": int(len(data_table)),
                "lapsing_vip_count": ordered_counts["Lapsing VIP"],
                "lapsing_high_value_count": ordered_counts["Lapsing High Value"],
                "winback_count": ordered_counts["Win-back"],
                "anniversary_count": ordered_counts["Anniversary"],
                "priority_breakdown": ordered_counts,
                "top_clients": data_table.head(5)[
                    ["client_id", "alert_type", "alert_reason", "monetary_value"]
                ].to_dict(orient="records"),
            }
            response_text = generate_insight(action_input, use_case="next_best_action")

    if data_table is not None and len(data_table) == 0:
        response_text = "No matching clients were found for that query."
        data_table = None

    return {
        "response_text": response_text,
        "data_table": data_table,
        "intent": intent,
        "tool_called": tool_called,
    }


if __name__ == "__main__":
    samples = [
        "Who are my top 10 VIP clients at SOHO?",
        "Tell me about MVC-00042",
        "Which lapsing clients should I prioritize this week?",
        "What is the favorite category of my High Value segment?",
        "Show me all Japanese clients who prefer Handbags",
    ]
    for q in samples:
        result = run_agent(q)
        print(f"Q: {q}\n  -> intent={result['intent']}, tool={result['tool_called']}\n")
