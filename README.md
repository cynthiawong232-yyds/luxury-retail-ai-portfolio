# Luxury Retail AI Portfolio

**Diagnostic AI tools for luxury retail decision-makers** — three Streamlit apps that answer the *"why?"* questions managers actually ask, with disciplined guardrails so the agents fail gracefully when they lack data instead of confabulating.

🌐 **Live demo:** <https://luxury-retail-ai-portfolio-ckevvwqdegeqlc7stc7ixr.streamlit.app/>

---

## Why this exists

Most retail dashboards stop at *what happened*. The decisions managers actually need help with are **diagnostic** (*"why is this category down?"*) and **prescriptive** (*"what should I do about this VIP?"*). That's where AI adds leverage — and where hallucinations cause the most damage. Every project here is built to answer "why?" questions, with explicit honesty about what it can and can't see.

| Project | Diagnostic question it answers | User |
|---|---|---|
| **[Flagship Dashboard](flagship_dashboard/)** — Maison Voss | *Why are these stores underperforming?* | Brand directors / store ops |
| **[Client Advisor Intelligence](client_advisor_intelligence_agent/)** — Maison Vega | *Why is this VIP slipping? Why is this segment churning?* | In-store advisors |
| **[Beauty Personalization Agent](beauty_client_personalization_agent/)** — Maison Solène | *Why did campaign B beat A for this segment?* | CRM / marketing managers |

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│         main.py (Streamlit router)              │
│  · single st.set_page_config                    │
│  · sidebar selectbox                            │
│  · landing page: 3 diagnostic value cards       │
└──────────────┬──────────────────────────────────┘
               │  importlib.import_module + run()
   ┌───────────┼───────────────┬──────────────────┐
   ▼           ▼               ▼
flagship_  client_advisor_  beauty_client_
dashboard/ intelligence_    personalization_
           agent/            agent/
   │           │               │
   └───────────┴───────────────┘
                       │
                       ▼
              shared/  (cross-cutting guardrails)
              · scope.py        — declarative ProjectScope per app
              · data_guards.py  — NoDataAvailable + require()
              · ui.py           — value cards, expanders, no-data render
```

**Common substrate**
- **`shared/scope.py`** — *single source of truth*. Each project declares what data it has and doesn't have. That declaration drives the system prompt, the "What I can/can't answer" UI expander, and the value cards on the landing page.
- **`shared/data_guards.py`** — `NoDataAvailable` exception + `require()` for deterministic refusals **before** any LLM call.
- **`shared/ui.py`** — `render_value_card`, `render_about_expander`, `render_scope_expander`, `render_no_data_response`.
- **WAT framework** (Workflows / Agents / Tools) — consistent agent structure across all three projects.
- **Groq + Llama 3.x** — sub-second LLM inference.
- **Streamlit** for UI, **Pandas** for data.
- **Synthetic data only** — fictional brands (Maison Voss, Maison Vega, Maison Solène). No real customer data.

---

## How hallucinations are handled

Three layers, cheapest first:

1. **Scope declaration in every system prompt.** The LLM receives an explicit block listing what data it has, what it doesn't, and the exact refusal template to use. See `shared/scope.py:ProjectScope.system_prompt_block`.
2. **Preflight data checks.** If a question references data that isn't available (a missing time period, an unsupported store, an unknown product), a deterministic refusal is rendered *without* calling the LLM. The Client Advisor's [`UNSUPPORTED_LOCATIONS`](client_advisor_intelligence_agent/agent/advisor_agent.py) is the canonical example — ask about London or Hong Kong and you get a clean "no data" response, not a hallucination.
3. **Visible "What I can / can't answer" UI** on every app — sets expectations upfront so users know what's in scope before they ask.

This **reduces** hallucination probability and makes failures graceful. It does not **eliminate** hallucinations — that's an unsolved problem. Layered defenses are the right shape of answer: deterministic where possible, prompt discipline where not, honest UI when both fail.

The Flagship Dashboard's **AI Advisor** tab pushes one layer further: when asked a *why?* question, the system prompt instructs it to return **the 2–3 most likely drivers ranked by evidence strength + the data it lacks** that would strengthen the diagnosis. So users see both what the data supports *and* what would refute it — diagnostic, not declarative.

---

## Run locally

```bash
git clone https://github.com/<your-username>/luxury-retail-ai-portfolio.git
cd luxury-retail-ai-portfolio
python -m venv .venv
source .venv/Scripts/activate          # Windows bash; PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                    # then paste your Groq key into .env
streamlit run main.py
```

Get a free Groq API key at <https://console.groq.com/keys>.

You can also run any sub-app standalone:
```bash
streamlit run flagship_dashboard/app.py
streamlit run client_advisor_intelligence_agent/app.py
streamlit run beauty_client_personalization_agent/app.py
```

---

## Project deep-dives

### Flagship Dashboard — *Maison Voss*

Store intelligence dashboard for three newly-opened flagship stores (SOHO New York, Tokyo, Paris). Tabs: **Portfolio**, **Store Deep Dive**, **Inventory** (WOS gauges, sell-through), **AI Advisor**.

The AI Advisor is the diagnostic centerpiece. It combines:
- Rule-based anomaly detection (no API call — pure pandas)
- Weekly narrative generation (Groq)
- Cross-market category insight (Groq)
- Period projection (Groq)
- Natural-language Q&A with diagnostic-reasoning prompt scaffolding

*Try asking:* *"Why is the worst-performing store underperforming this period?"* — the system prompt forces a "3 ranked drivers + data I lack" answer.

*What I'd do next:* add foot-traffic and weather as additional inputs so the AI Advisor can rule them out from the data, instead of just naming them as "data I lack."

### Client Advisor Intelligence — *Maison Vega*

Conversational chat UI for in-store luxury client advisors. Natural-language Q&A over synthetic client transactions: RFM segments, lapsing/winback alerts, product affinity, next-best-action.

Architectural detail worth talking through in interviews: explicit intent classification (4 intents — `SEGMENT`, `CLIENT`, `ALERT`, `PRODUCT`) routes each question to specific tools. The classifier is keyword-based by design, not LLM-inferred — it's deterministic, debuggable, and never hallucinates an intent.

The `UNSUPPORTED_LOCATIONS` set is the canonical Layer-2 guardrail demonstration: ask *"who are my top clients in London?"* and the agent returns *"I don't have data for London. Maison Vega data covers our SOHO New York, Tokyo, and Paris boutiques only."* — without invoking the LLM.

*What I'd do next:* add an LLM-powered *"why is this VIP slipping?"* tool that combines RFM + transaction history with the same ranked-drivers + data-I-lack pattern as the Flagship Advisor.

### Beauty Personalization Agent — *Maison Solène*

End-to-end agentic workflow for beauty brand marketing: load synthetic clients → segment by behavior → recommend products from the catalog → generate Variant A/B email copy via Groq → simulate A/B test → display results.

Each tool returns a typed result, composed into a single `result` dict consumed by the dashboard. The simulated A/B framework returns open / click / conversion rates with a recommended winner — clearly labelled as **simulation, not measurement**, both in the UI and in the project's scope declaration.

*What I'd do next:* swap the simulator for a real opt-in A/B framework, or wire up an actual ESP for a vertical slice that ships email and reads back engagement.

---

## Tech choices, briefly

- **Why Groq?** Sub-second inference is critical for chat UX. The free tier is sufficient for portfolio traffic. Llama 3.x is cheap, fast, and capable enough for ranked-driver reasoning.
- **Why Streamlit?** UI velocity. The portfolio's value is the AI / data layer, not bespoke React. A unified router across three apps is ~100 lines of Streamlit.
- **Why one repo with a router?** Coherent narrative; one deployment to maintain; the `shared/` module is the cross-cutting concern that turns "three apps" into one product.
- **Why a `shared/` module?** Scope-awareness is a cross-cutting concern. One source of truth keeps system prompts, UI affordances, and preflight checks consistent. Change a `ProjectScope` and three layers update at once.

---

## Repo layout

```
luxury-retail-ai-portfolio/
├── main.py                              # Streamlit router (entry point)
├── requirements.txt                     # union of sub-project deps
├── .env.example                         # local secrets template
├── .streamlit/
│   └── secrets.toml.example             # Streamlit Cloud secrets template
├── shared/                              # cross-cutting guardrail module
│   ├── scope.py
│   ├── data_guards.py
│   └── ui.py
├── flagship_dashboard/                  # Project 1 — Maison Voss
├── client_advisor_intelligence_agent/   # Project 2 — Maison Vega
└── beauty_client_personalization_agent/ # Project 3 — Maison Solène
```
