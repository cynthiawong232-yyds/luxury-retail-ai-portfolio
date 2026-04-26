# PROJECT: Client Advisor Intelligence Agent
**An intelligent layer to superpower client advisors at fictional luxury maison "Maison Vega".**

---

## PROJECT OVERVIEW

A conversational agentic AI tool that allows a luxury client advisor to query client data in natural language and receive instant, intelligent responses — segment profiles, lapsing VIP alerts, favorite categories, visit history, and next-best-action recommendations.

This is a portfolio project demonstrating agentic AI applied to luxury retail clienteling. All data, brand names, store names, and product names are entirely synthetic and fictional. "Maison Vega" is a fabricated brand created for this demo and is not affiliated with any real company.

---

## THE PROBLEM THIS SOLVES

In luxury retail, the top 1% of clients drive a disproportionate share of revenue. Client advisors typically rely on memory and manual CRM lookups to prepare for client appointments. This tool gives them an AI-powered assistant that:
- Instantly surfaces who is lapsing, who is a VIP, and who hasn't visited recently
- Answers natural language questions about client segments
- Generates actionable narratives per segment for briefings and outreach planning

---

## WAT FRAMEWORK

### WORKFLOWS (`/workflows/`)
Step-by-step Markdown instructions that the agent follows.

### AGENTS (`/agent/`)
The orchestration layer — receives user questions, selects the right tool, calls it, and synthesizes the response.

### TOOLS (`/tools/`)
Python scripts that perform specific tasks. Each tool is standalone and testable independently.

---

## DATA FILES

All data files live in `/data/`. These are synthetic files — do NOT reference any other CSV files.

| File | Description | Key Columns |
|------|-------------|-------------|
| `client_master.csv` | 500 luxury clients | client_id, first_name, last_name, nationality, preferred_store, store_name, preferred_channel, join_date, last_visit_date, days_since_last_visit |
| `mv_transactions.csv` | 8,755 transaction rows | transaction_id, client_id, transaction_date, store_code, store_name, category, product_name, quantity, unit_price, net_sales_amount, channel |
| `rfm_summary.csv` | Pre-computed RFM scores for all 500 clients | client_id, first_name, last_name, nationality, preferred_store, store_name, preferred_channel, days_since_last_visit, frequency, monetary_value, avg_order_value, favorite_category, recency_score, frequency_score, monetary_score, rfm_total_score, rfm_segment, join_date, last_visit_date |

**RFM Segments in the data:**
- `VIP` — rfm_total_score >= 13, high frequency + high spend + recent
- `High Value` — rfm_total_score >= 10
- `Active` — rfm_total_score >= 7
- `Dormant` — recency_score <= 2, haven't visited in 365+ days

**Store codes:**
- `A800` = MV SOHO New York
- `J347` = MV Flagship Tokyo
- `EU_F07M` = MV Flagship Paris

---

## TOOLS TO BUILD

### `tools/load_data_tool.py`
Loads all three CSV files into memory and returns clean DataFrames.
- Input: none (reads from `/data/`)
- Output: clients_df, transactions_df, rfm_df
- Must validate that all required columns exist and handle missing values gracefully
- Print summary on load: number of clients, transactions, segments

### `tools/rfm_query_tool.py`
Queries the RFM summary to answer segment-level questions.
- Input: segment name (optional), store code (optional), top_n (optional)
- Output: filtered DataFrame of matching clients with key metrics
- Example queries it must handle:
  - Get all VIP clients
  - Get top N clients by monetary value
  - Get lapsing clients (Dormant or High Value with recency > 90 days)
  - Get clients by preferred store
  - Get clients by nationality

### `tools/transaction_query_tool.py`
Queries transaction history for a specific client or segment.
- Input: client_id (optional), category (optional), date_range (optional)
- Output: filtered transaction DataFrame
- Must compute: total spend, number of visits, favorite category, last purchase date
- Example queries:
  - Get all transactions for client MVC-00042
  - Get all Handbag purchases in last 6 months
  - Get category breakdown for VIP segment

### `tools/insight_tool.py`
Calls Groq API (LLaMA 3.3 70B) to generate natural language insights from structured data.
- Input: a JSON summary of client or segment data
- Output: a human-readable narrative (2-4 sentences)
- Use case 1: Generate a client briefing ("Client X is a VIP who last visited 12 days ago...")
- Use case 2: Generate a segment summary ("Your VIP segment consists of 174 clients...")
- Use case 3: Generate a next-best-action recommendation ("Consider reaching out to these 23 lapsing VIPs...")
- Keep tone warm, professional, luxury-appropriate — never clinical or robotic
- Groq model: `llama-3.3-70b-versatile`

### `tools/alert_tool.py`
Identifies clients that need immediate attention.
- Input: threshold parameters (days_since_visit, segment, min_monetary_value)
- Output: prioritized list of clients with alert reason
- Alert types:
  - Lapsing VIP: VIP client not seen in 60+ days
  - Lapsing High Value: High Value client not seen in 90+ days
  - Anniversary alert: client join_date anniversary within 30 days
  - Win-back candidate: Dormant client with monetary_value > $2,000

---

## AGENT ORCHESTRATION

### `agent/advisor_agent.py`
The main agent that:
1. Receives a natural language question from the user
2. Determines which tool(s) to call
3. Calls the tool(s) with appropriate parameters
4. Passes results to insight_tool.py for narrative generation
5. Returns a final, clear, actionable response

**Example questions the agent must handle:**
- "Who are my top 10 VIP clients at SOHO?"
- "Which clients haven't visited in over 90 days but have spent more than $5,000?"
- "Give me a briefing on client MVC-00042"
- "Which lapsing clients should I prioritize for outreach this week?"
- "What is the favorite category of my High Value segment?"
- "Show me all Japanese clients who prefer Handbags"
- "Who are my top clients in Tokyo?"

---

## STREAMLIT FRONT END

### `app.py`
A clean, professional Streamlit chat interface.

**Layout:**
- Header: "Client Advisor Intelligence" with a subtle luxury aesthetic
- Sidebar: Store selector (filter by SOHO / Tokyo / Paris / All stores)
- Main area: Chat interface — user types question, agent responds
- Below chat: Key metrics row showing total clients, VIP count, lapsing alerts count
- Color scheme: Dark navy / gold / white — luxury feel

**Chat behavior:**
- User types a question in natural language
- Agent processes and responds with text + optional data table
- If the response includes a list of clients, show it as a formatted st.dataframe()
- Maintain chat history in st.session_state

---

## WORKFLOW FILE

### `workflows/client_intelligence_workflow.md`
Step-by-step instructions for the agent:

1. Load data using load_data_tool
2. Parse the user question to identify intent:
   - Segment query → rfm_query_tool
   - Individual client query → transaction_query_tool + rfm_query_tool
   - Alert/priority query → alert_tool
   - General question → rfm_query_tool with broad parameters
3. Call appropriate tool(s)
4. Pass structured results to insight_tool for narrative
5. Return response to user

---

## PROJECT STRUCTURE

```
MV_ClientAdvisor/
├── claude.md               ← this file
├── app.py                  ← Streamlit front end
├── .env                    ← GROQ_API_KEY (never commit this)
├── requirements.txt        ← dependencies
├── data/
│   ├── client_master.csv
│   ├── mv_transactions.csv
│   └── rfm_summary.csv
├── tools/
│   ├── load_data_tool.py
│   ├── rfm_query_tool.py
│   ├── transaction_query_tool.py
│   ├── insight_tool.py
│   └── alert_tool.py
├── agent/
│   └── advisor_agent.py
├── workflows/
│   └── client_intelligence_workflow.md
└── temporary/              ← scratch files, not committed
```

---

## TECH STACK

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Front end | Streamlit |
| Data processing | pandas, numpy |
| AI / GenAI | Groq API, LLaMA 3.3 70B |
| Version control | Git / GitHub |
| Environment | .env for API keys |

---

## DEPENDENCIES (requirements.txt)

```
streamlit
pandas
numpy
groq
python-dotenv
```

---

## ENVIRONMENT VARIABLES (.env)

```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free Groq API key at: https://console.groq.com

---

## WAT FRAMEWORK RULES

1. **Workflows** define WHAT to do — written in Markdown, human-readable
2. **Agent** decides HOW to do it — orchestrates tool selection and sequencing
3. **Tools** are the execution layer — each is a standalone Python function
4. Every tool must: handle errors gracefully, return a consistent data structure, print a status message on completion
5. The agent must never hallucinate client data — it only reports what the tools return
6. If a tool returns no results, the agent must say so clearly rather than making something up

---

## DEMO STORY FOR INTERVIEWS

*"I built a prototype of an agentic AI layer for luxury clienteling — an intelligent assistant that superpowers client advisors. A client advisor can type 'Which lapsing VIP clients should I prioritize this week?' and immediately get a prioritized list with AI-generated outreach recommendations. The tool uses RFM segmentation, synthetic transaction history for a fictional maison, and Groq's LLaMA model to generate briefings — demonstrating the kind of agentic client intelligence system that's increasingly relevant across luxury retail."*

---

## INITIALIZATION PROMPT

When starting Claude Code, say:
> "Initialize this project based on the claude.md file. Create the folder structure, then start with tools/load_data_tool.py."
