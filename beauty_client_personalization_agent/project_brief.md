# PROJECT: Beauty Client Personalization Agent
**Inspired by luxury beauty industry Digital Client Experience (DCX) practices — personalizing the boutique experience at scale**

> **Note:** Maison Solène is a fictional luxury beauty house created for this portfolio project. The architecture and pipeline are modeled on publicly-known DCX industry practices. No affiliation with any real brand. Synthetic data only.

---

## PROJECT OVERVIEW

A GenAI-powered agentic workflow that segments Maison Solène beauty clients by purchase behavior, generates personalized product recommendations per segment, writes AI-crafted outreach copy, runs a simulated A/B test comparing two messaging strategies, and presents results in a Streamlit dashboard designed for non-technical business users.

This project directly mirrors the DCX challenge facing modern luxury beauty houses: how to translate the magic of a boutique beauty advisor into a scalable digital personalization system — without losing the brand's warmth and exclusivity.

---

## THE PROBLEM THIS SOLVES

Like many luxury beauty houses, Maison Solène treats the boutique as sacred and limits the digital experience accordingly. But digital beauty clients expect personalized engagement. The DCX team needs to:
- Understand which clients prefer which beauty categories (Fragrance vs Skincare vs Makeup)
- Generate personalized outreach that feels like a boutique advisor wrote it, not an algorithm
- Test different messaging approaches before rolling out to the full client base
- Give non-technical marketing teams a simple interface to view and act on insights

This project is a GenAI pilot for exactly that challenge.

---

## WAT FRAMEWORK

### WORKFLOWS (`/workflows/`)
Step-by-step Markdown instructions the agent follows end-to-end.

### AGENTS (`/agent/`)
The orchestration layer — runs the full pipeline from segmentation through A/B results.

### TOOLS (`/tools/`)
Standalone Python scripts, each handling one specific task.

---

## DATA FILES

All data files live in `/data/`. These are synthetic files — do NOT reference any other CSV files.

| File | Description | Key Columns |
|------|-------------|-------------|
| `client_master.csv` | 500 clients | client_id, first_name, last_name, nationality, preferred_store, store_name, preferred_channel, join_date, last_visit_date, days_since_last_visit |
| `beauty_transactions.csv` | 1,626 beauty purchase rows | transaction_id, client_id, transaction_date, channel, category, product_name, quantity, unit_price, net_sales_amount, primary_category, secondary_category, favorite_product |
| `product_catalog.csv` | 26 Maison Solène beauty products | product_id, product_name, category, price_usd, description, target_segment, is_bestseller, launch_year |
| `rfm_summary.csv` | Pre-computed RFM scores | client_id, first_name, last_name, rfm_segment, monetary_value, frequency, days_since_last_visit, favorite_category, preferred_channel, preferred_store |

**Beauty Categories in the data:**
- `Fragrance` — highest spend, 45% of transactions
- `Skincare` — 25% of transactions
- `Makeup` — 18% of transactions
- `Hair Care` — 7% of transactions
- `Body Care` — 5% of transactions

**RFM Segments:**
- `VIP` — highest value clients
- `High Value` — strong repeat purchasers
- `Active` — regular clients
- `Dormant` — haven't purchased in 365+ days

**Key columns for personalization:**
- `primary_category` — client's main beauty interest
- `secondary_category` — secondary interest
- `favorite_product` — most purchased product

---

## TOOLS TO BUILD

### `tools/load_data_tool.py`
Loads all four CSV files and returns clean DataFrames.
- Input: none (reads from `/data/`)
- Output: clients_df, beauty_txn_df, catalog_df, rfm_df
- Validate columns, handle missing values
- Print summary on load

### `tools/segment_tool.py`
Segments clients by beauty purchase behavior.
- Input: beauty_txn_df, rfm_df
- Output: enriched client DataFrame with beauty profile per client
- Compute per client:
  - `primary_beauty_category` — most purchased category
  - `total_beauty_spend` — lifetime beauty spend
  - `beauty_purchase_count` — number of beauty transactions
  - `favorite_beauty_product` — most purchased product
  - `rfm_segment` — from rfm_summary
- Create 4 named client segments:
  - `Fragrance VIP` — VIP/High Value + primary_category = Fragrance
  - `Skincare Devotee` — any RFM segment + primary_category = Skincare
  - `Makeup Enthusiast` — any RFM segment + primary_category = Makeup
  - `Beauty Explorer` — clients with diverse purchases across 3+ categories
- Output a segment_summary DataFrame: segment name, client count, avg spend, top product

### `tools/recommend_tool.py`
Generates product recommendations per client segment.
- Input: segment name, catalog_df, segment_summary
- Output: top 3 recommended products for that segment with rationale
- Logic:
  - Match segment's primary category to catalog
  - Prioritize is_bestseller = True products
  - For VIP/High Value segments, prioritize higher price_usd
  - Return product_name, category, price_usd, and a one-line rationale
- This is a rule-based recommendation engine (no ML needed for portfolio project)

### `tools/copy_tool.py`
Calls Groq API to write personalized outreach copy for each segment.
- Input: segment name, top recommended products, segment stats (avg spend, favorite product)
- Output: two versions of outreach copy (Variant A and Variant B) for A/B testing
- Variant A: Warm, personal tone — feels like a boutique advisor writing to a client
- Variant B: Exclusive, aspirational tone — emphasizes luxury and discovery
- Keep copy to 3-4 sentences max — luxury brands are never verbose
- Always address the client's favorite product or category naturally
- Groq model: `llama-3.3-70b-versatile`
- System prompt must enforce: Maison Solène brand voice, no clichés, no exclamation marks, no emojis

### `tools/ab_test_tool.py`
Simulates an A/B test comparing Variant A and Variant B outreach copy.
- Input: variant_a text, variant_b text, segment name, n_clients in segment
- Output: simulated test results DataFrame
- Simulation logic:
  - Randomly assign clients 50/50 to Variant A or B
  - Simulate open rate: Variant A base 42%, Variant B base 38% (warm tone wins on open rate)
  - Simulate click rate: Variant B base 28%, Variant A base 22% (aspirational tone wins on clicks)
  - Add random noise: +/- 5% per simulation run
  - Compute: open_rate, click_rate, conversion_rate (click/open), winner by conversion
- Output includes: variant, open_rate, click_rate, conversion_rate, recommended_winner
- Note in output: "This is a simulated A/B test for demonstration purposes"

### `tools/dashboard_tool.py`
Builds the Streamlit dashboard — this IS the front end, not a separate app.py.
- See Streamlit Front End section below for full spec.

---

## AGENT ORCHESTRATION

### `agent/personalization_agent.py`
Runs the full pipeline end-to-end:
1. Call load_data_tool — load all data
2. Call segment_tool — build beauty segments
3. For each segment:
   a. Call recommend_tool — get product recommendations
   b. Call copy_tool — generate Variant A and Variant B copy
   c. Call ab_test_tool — simulate test results
4. Compile all results into a structured output dictionary
5. Pass to dashboard for display

The agent should also support single-segment mode: run the pipeline for one segment only (useful for demo).

---

## STREAMLIT FRONT END

### `app.py`
A clean Streamlit dashboard designed for non-technical Maison Solène business users.

**Layout:**

**Header:**
- Title: "Beauty Client Personalization Agent"
- Subtitle: "DCX Intelligence — Powered by GenAI"

**Sidebar:**
- Run button: "Generate Personalization Report"
- Segment selector: dropdown to view one segment at a time
- Store filter: All stores / SOHO / Tokyo / Paris

**Main dashboard — 3 sections:**

Section 1: Segment Overview
- Metric cards: total clients, segments identified, avg spend per segment
- Bar chart: client count per beauty segment
- Table: segment summary (name, count, avg spend, top product)

Section 2: Personalization Output (per selected segment)
- Recommended products: 3 product cards with name, category, price, rationale
- Outreach copy comparison:
  - Left column: Variant A (warm advisor tone) with full copy text
  - Right column: Variant B (aspirational luxury tone) with full copy text

Section 3: A/B Test Results
- Metric cards: open rate, click rate, conversion rate for each variant
- Bar chart: Variant A vs B comparison
- Winner callout: "Recommended: Variant [X] — higher conversion rate"
- Disclaimer: "Simulated results for demonstration purposes"

**Color scheme:** Black / cream / gold — luxury aesthetic. Clean, minimal, no clutter.

---

## WORKFLOW FILE

### `workflows/personalization_workflow.md`
Full pipeline instructions:

1. Load all data files from /data/
2. Run segmentation — build beauty client profiles
3. For each of the 4 segments:
   - Generate product recommendations from catalog
   - Generate Variant A copy (warm tone) via Groq API
   - Generate Variant B copy (aspirational tone) via Groq API
   - Run A/B simulation
   - Store results
4. Display all results in Streamlit dashboard
5. Allow user to drill into any segment for detail

---

## PROJECT STRUCTURE

```
MaisonSolene_PersonalizationAgent/
├── claude.md                    ← this file
├── app.py                       ← Streamlit front end
├── .env                         ← GROQ_API_KEY (never commit this)
├── requirements.txt             ← dependencies
├── data/
│   ├── client_master.csv
│   ├── beauty_transactions.csv
│   ├── product_catalog.csv
│   └── rfm_summary.csv
├── tools/
│   ├── load_data_tool.py
│   ├── segment_tool.py
│   ├── recommend_tool.py
│   ├── copy_tool.py
│   ├── ab_test_tool.py
│   └── dashboard_tool.py
├── agent/
│   └── personalization_agent.py
├── workflows/
│   └── personalization_workflow.md
└── temporary/                   ← scratch files, not committed
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
plotly
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
3. **Tools** are the execution layer — each is standalone and independently testable
4. Every tool must: handle errors gracefully, return consistent data structures, print status on completion
5. The copy_tool must never break Maison Solène's brand voice — no exclamation marks, no emojis, no clichés
6. The ab_test_tool must always include a disclaimer that results are simulated
7. The dashboard must be usable by a non-technical marketing manager with zero data science background

---

## DEMO STORY FOR INTERVIEWS

*"I built a GenAI pilot for a luxury beauty house's Digital Client Experience team — the exact challenge they're trying to solve: how do you translate boutique clienteling into digital personalization without losing the brand's soul? The agent segments beauty clients by purchase behavior, generates personalized product recommendations, writes two variants of outreach copy in a Maison Solène-style luxury brand voice using LLaMA 3.3 70B, and simulates an A/B test to identify which messaging strategy drives higher conversion. The whole pipeline runs in one click and displays in a Streamlit dashboard designed for non-technical marketing users — including the change management dimension luxury beauty employers specifically call out (e.g., Maison Solène's DCX team)."*

---

## INITIALIZATION PROMPT

When starting Claude Code, say:
> "Initialize this project based on the project_brief.md file. Create the folder structure, then start with tools/load_data_tool.py."
