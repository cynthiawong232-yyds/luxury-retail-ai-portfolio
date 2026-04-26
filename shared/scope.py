"""Per-project scope declarations.

Each ProjectScope answers, in one place: who is this for, what decision
moment does it serve, what data does it have, what does it NOT have, and
what diagnostic questions is it designed to answer.

That single declaration drives:
  * the system-prompt block injected into every LLM call
  * the "What I can/can't answer" UI expander on every sub-app
  * the value cards on the router landing page
  * the example "Try asking" prompts shown to interviewers

Change the data here and all three layers stay in sync.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class ProjectScope:
    name: str
    persona: str
    moment: str
    data_available: List[str]
    data_unavailable: List[str]
    example_questions: List[str]

    def system_prompt_block(self) -> str:
        avail = "\n".join(f"- {x}" for x in self.data_available)
        unavail = "\n".join(f"- {x}" for x in self.data_unavailable)
        return (
            "\n=== SCOPE GUARDRAILS ===\n"
            "DATA YOU HAVE:\n"
            f"{avail}\n\n"
            "DATA YOU DO NOT HAVE:\n"
            f"{unavail}\n\n"
            "WHEN A QUESTION REQUIRES DATA YOU DON'T HAVE:\n"
            "Respond with: \"I don't have [specific missing data] to answer that. "
            "To investigate, you'd want to check [where to look]. I can answer "
            "questions about: [list 2-3 things from DATA YOU HAVE].\"\n\n"
            "DO NOT speculate. DO NOT invent plausible-sounding reasons. "
            "DO NOT use general retail or beauty knowledge to fill gaps in the data. "
            "If unsure, say so explicitly.\n"
            "=== END SCOPE GUARDRAILS ===\n"
        )


FLAGSHIP_SCOPE = ProjectScope(
    name="Flagship Dashboard",
    persona="Brand directors and store-ops leaders at a luxury house",
    moment=(
        "The Sunday-night question: \"Why was last week down across our flagship "
        "stores — and what do I tell the exec team Monday?\""
    ),
    data_available=[
        "Maison Voss store sales, current and last year, by week and day",
        "3 flagship stores: SOHO New York (A800, opened Dec 7 2025), "
        "Tokyo (J347, opened Aug 31 2025), Paris/EU (EU_F07M, opened Feb 9 2025)",
        "Sales metrics: net sales, units, AUR, discount rate, sell-through, "
        "WOS (weeks of supply)",
        "Category and style breakdowns per store",
        "Inventory snapshots (on-hand units, sell-through, WOS)",
        "Reporting periods: WTD, MTD, QTD, YTD",
    ],
    data_unavailable=[
        "Foot traffic, weather, or external macro signals",
        "Marketing spend, campaigns, promotions, or paid media",
        "Competitor pricing, releases, or store openings",
        "Staffing levels, schedules, or staff performance",
        "Customer satisfaction, NPS, returns reasons, or qualitative feedback",
        "Pre-opening sales (these stores opened in 2025; LY data is partial or absent)",
    ],
    example_questions=[
        "Why is SOHO down 12% week-over-week?",
        "Which categories are dragging the EU portfolio this period?",
        "What inventory health changes should I notice this week?",
        "Where is the discount rate getting unhealthy?",
    ],
)


ADVISOR_SCOPE = ProjectScope(
    name="Client Advisor Intelligence",
    persona="In-store client advisors at Maison Vega luxury boutiques",
    moment=(
        "Before a client appointment or daily outreach plan: \"Who should I "
        "reach out to today, why, and what should I show them?\""
    ),
    data_available=[
        "Synthetic client roster + transaction history for Maison Vega",
        "3 boutiques: MV SOHO New York (A800), MV Flagship Tokyo (J347), "
        "MV Flagship Paris (EU_F07M)",
        "RFM features per client (recency, frequency, monetary value)",
        "RFM segments: VIP, High Value, Active, Dormant",
        "Lapsing flags + alert types: Lapsing VIP, Lapsing High Value, "
        "Win-back, Anniversary",
        "Product catalog by category (Handbags, Small Leather Goods, Footwear, "
        "Ready-to-Wear, Jewelry, Accessories, Fragrances) and tier "
        "(Heritage, Limited, Essential, Classic, Signature)",
        "Client-level contribution: % of store sales and % of global sales",
    ],
    data_unavailable=[
        "Live appointment notes or in-store interaction logs",
        "Returns reasons, complaints, or satisfaction scores",
        "External CRM, social media, or third-party data",
        "Boutiques outside SOHO / Tokyo / Paris (London, Milan, Hong Kong, "
        "Dubai, etc. are NOT in scope)",
        "Real-time inventory at the SKU/store level for purchase-readiness",
    ],
    example_questions=[
        "Which of my Tokyo VIPs is at risk of lapsing this quarter?",
        "Tell me about MVC-00042 — what should I show them next?",
        "Who bought MV Handbags Heritage in Paris?",
        "Which lapsing clients should I prioritize this week?",
    ],
)


PERSONALIZATION_SCOPE = ProjectScope(
    name="Beauty Personalization Agent",
    persona="Marketing and CRM managers at Maison Solène, a luxury beauty brand",
    moment=(
        "Campaign planning: \"Which segment gets which message, what should we "
        "recommend to each, and how do we know it works?\""
    ),
    data_available=[
        "Synthetic Maison Solène beauty client data: purchase behavior, "
        "channel, spend tier",
        "Behavioral beauty segments built from RFM + category affinity",
        "Per-segment product recommendations from the in-house catalog",
        "Variant A vs. Variant B marketing copy generated by Groq for each segment",
        "Simulated A/B test outcomes: open rate, click rate, conversion rate, "
        "recommended winner",
    ],
    data_unavailable=[
        "Real campaign performance from production marketing systems "
        "(the A/B numbers are SIMULATED, not measured)",
        "Customer satisfaction or qualitative feedback",
        "Competitor campaign or pricing data",
        "Channel-level cost or ROI inputs (CAC, LTV, etc.)",
        "Inventory or fulfillment readiness for the recommended SKUs",
    ],
    example_questions=[
        "Why did variant B beat variant A for the High Spender segment?",
        "What product would you recommend to a Lapsed VIP?",
        "Which segment is most responsive to exclusivity messaging "
        "vs. value framing?",
    ],
)


ALL_SCOPES = [FLAGSHIP_SCOPE, ADVISOR_SCOPE, PERSONALIZATION_SCOPE]
