# Personalization Workflow

Human-readable definition of the Maison Solène Beauty Client Personalization pipeline. The agent in [../agent/personalization_agent.py](../agent/personalization_agent.py) orchestrates the tools in [../tools/](../tools/) to execute the steps below.

> Maison Solène is a fictional luxury beauty house used for this demonstration. The pipeline architecture is modeled on publicly-known Digital Client Experience (DCX) industry practices and is not affiliated with any real brand.

---

## Purpose

Translate raw Maison Solène beauty transaction and client data into segment-level personalization outputs — product recommendations, A/B-tested outreach copy, and simulated performance results — and present them in a dashboard usable by a non-technical marketing manager.

---

## Prerequisites

Before the pipeline runs, the following must be in place:

- **Data files** in [../data/](../data/):
  - `client_master.csv`
  - `beauty_transactions.csv`
  - `product_catalog.csv`
  - `rfm_summary.csv`
- **`.env` file** at project root with a valid `GROQ_API_KEY`.
- **Python dependencies** from [../requirements.txt](../requirements.txt) installed.
- **`curl`** available on the system PATH (used by the copy tool to reach the Groq API without relying on Python's SSL module).

---

## Pipeline Steps

### Step 1 — Load Data

**Tool:** [../tools/load_data_tool.py](../tools/load_data_tool.py) (`load_data()`)

Reads the four CSVs, validates columns, parses dates, coerces numerics, and returns four DataFrames: `clients_df`, `beauty_txn_df`, `catalog_df`, `rfm_df`.

**Output:** clean DataFrames, plus a printed load summary (row counts, category mix, RFM distribution).

---

### Step 2 — Build Beauty Segments

**Tool:** [../tools/segment_tool.py](../tools/segment_tool.py) (`segment_clients()`)

For every client in `rfm_df`, compute a beauty profile from their transactions and merge with the RFM tier:

- `primary_beauty_category` — most purchased category
- `total_beauty_spend` — lifetime beauty spend
- `beauty_purchase_count` — number of beauty transactions
- `favorite_beauty_product` — most purchased product
- `distinct_category_count` — how many categories they have purchased in
- `rfm_segment` — from `rfm_summary.csv`

Then assign each client to exactly one of the four named segments, in **priority order** (first match wins):

1. **Fragrance VIP** — RFM tier is `VIP` or `High Value` AND primary beauty category is `Fragrance`
2. **Skincare Devotee** — primary beauty category is `Skincare`
3. **Makeup Enthusiast** — primary beauty category is `Makeup`
4. **Beauty Explorer** — catch-all for everyone else (Hair Care, Body Care, or Fragrance non-VIP primaries). Interpreted as clients whose beauty behavior is broader than any single-category loyalty.

Clients with zero beauty transactions are labeled `Unsegmented` and excluded from the segment summary.

**Output:**
- `client_profiles_df` — one row per client with profile and assigned `beauty_segment`
- `segment_summary` — one row per named segment: client count, average spend, top product

---

### Step 3 — Per-Segment Personalization

For each of the 4 named segments, run the following three tools in sequence:

#### 3a. Generate Product Recommendations

**Tool:** [../tools/recommend_tool.py](../tools/recommend_tool.py) (`recommend_products()`)

Rule-based recommender — no ML. Returns the top 3 products per segment with a rationale:

- **Fragrance VIP** — Fragrance catalog products, ranked by bestseller first, then highest price (VIP pricing rule).
- **Skincare Devotee / Makeup Enthusiast** — catalog products in the segment's category, ranked by bestseller first, then lowest price (accessible entry points).
- **Beauty Explorer** — one pick from each of Fragrance, Skincare, and Hair Care, each ranked by bestseller and highest price — emphasizes range.

Rationale text is varied per product using `is_bestseller` and `launch_year` (e.g., "Bestseller · House icon since 2018", "Bestseller · introduced 2023") so cards look distinct, not templated.

#### 3b. Generate A/B Outreach Copy

**Tool:** [../tools/copy_tool.py](../tools/copy_tool.py) (`generate_copy()`)

Two calls to the Groq LLaMA 3.3 70B model, one per variant:

- **Variant A — Warm Boutique Advisor** — conversational, refined, as if a beauty advisor is writing personally.
- **Variant B — Exclusive Aspirational** — evocative, emphasizes craft and House heritage.

Both variants are bound by the Maison Solène brand voice rules enforced in the system prompt:

- 3 to 4 sentences maximum
- No exclamation marks, no emojis, no clichés ("treat yourself", "must-have", "unlock")
- No hyperbole, no all-caps, no hard sell
- Address the favorite product or primary category naturally
- Close with "Maison Solène" on its own line

If the Groq API is unreachable or the key is missing, the agent raises a clear error — no silent fallback.

#### 3c. Simulate A/B Test

**Tool:** [../tools/ab_test_tool.py](../tools/ab_test_tool.py) (`simulate_ab_test()`)

Rule-based simulation (no real users). For each segment's client count:

1. Split 50/50 between Variant A and Variant B.
2. Apply base rates plus ±5pp noise:
   - Variant A base: 42% open, 22% click
   - Variant B base: 38% open, 28% click
3. Sample opens from `Binomial(n, open_rate)`.
4. Sample clicks from `Binomial(opens, click_rate / open_rate)` — clicks require an open (hierarchical funnel).
5. Compute `open_rate`, `click_rate`, `conversion_rate` (clicks ÷ opens), and pick the winner by conversion.

The output DataFrame carries the explicit disclaimer: **"This is a simulated A/B test for demonstration purposes."**

---

### Step 4 — Compile Results

**Orchestrator:** [../agent/personalization_agent.py](../agent/personalization_agent.py) (`run_pipeline()`)

The agent packages everything into a single result dictionary:

```
{
  "client_profiles_df":  DataFrame,
  "segment_summary":     DataFrame,
  "per_segment": {
      "Fragrance VIP":     { recommendations, copy (A/B), ab_results, n_clients, ... },
      "Skincare Devotee":  { ... },
      "Makeup Enthusiast": { ... },
      "Beauty Explorer":   { ... },
  },
  "ab_results_all":      DataFrame (concatenated),
  "disclaimer":          simulation note,
}
```

**Modes:**
- Default — runs the pipeline for all 4 segments (8 Groq calls).
- `single_segment="Fragrance VIP"` — runs the pipeline for one segment only (2 Groq calls). Useful for demos.
- `skip_copy=True` — bypasses Groq entirely, inserts placeholder copy. Useful for UI iteration.

---

### Step 5 — Display in Dashboard

**Entry:** [../app.py](../app.py) (Streamlit)
**Helpers:** [../tools/dashboard_tool.py](../tools/dashboard_tool.py)

The dashboard has three sections, each rendered from the agent's result dict:

1. **Segment Overview** — metric cards (total clients, named segments, avg spend), bar chart of clients per segment, and the segment summary table. Respects the store filter (SOHO / Paris / Tokyo / All).
2. **Personalization Output** (per selected segment) — three product cards plus a side-by-side A / B copy comparison.
3. **A/B Test Results** (per selected segment) — per-variant metric cards, a grouped bar chart, the recommended winner in a black callout, and the simulation disclaimer.

Users drill in by selecting a segment from the sidebar. Changing the segment does **not** re-run the pipeline; all segment outputs are precomputed on the Run click and cached in session state.

---

## Running the Pipeline

- **Command line (all segments, live Groq):**
  `python agent/personalization_agent.py`
- **Command line (one segment):**
  `python agent/personalization_agent.py --segment "Skincare Devotee"`
- **Command line (skip Groq for fast iteration):**
  `python agent/personalization_agent.py --skip-copy`
- **Dashboard:**
  `streamlit run app.py` — then click **Generate Personalization Report** in the sidebar.

---

## Guarantees and Invariants

- Every named segment is always represented in `segment_summary` — zero-client segments appear with zeros rather than being dropped, so the dashboard bar chart remains stable.
- Every client lands in exactly one segment (one of the four named segments, or `Unsegmented` if they have no beauty transactions). No "Other" bucket.
- The A/B test output always carries the simulation disclaimer.
- The copy tool never invents products, prices, or claims — it uses only the recommendations and segment stats passed in.

---

## What This Workflow Replaces in a Production DCX Setup

This project is a pilot. In a live Digital Client Experience rollout at any luxury beauty house, each step would plug into an existing system rather than run on synthetic data:

| Pilot step | Production equivalent |
|---|---|
| Load CSVs from `/data/` | Query the client / transaction warehouse (Snowflake or similar). |
| Segment via local pandas logic | The same rules, run on the warehouse or in a feature store. |
| Recommend from a 26-product catalog | The live catalog API. |
| Generate copy via Groq | Same tool, optionally with a review step for brand-compliance before send. |
| Simulate A/B results | Salesforce Marketing Cloud (or the ESP of choice) handles randomization, delivery, and event tracking; a warehouse job lands opens/clicks; real rates replace the simulated ones. |
| Streamlit dashboard | Tableau / Looker / an internal DCX tool, fed by the same result schema. |

The agent boundary stays the same — creative generation and per-segment recommendations sit inside the agent; delivery and measurement are handed off to existing platforms.
