# Client Intelligence Workflow

Step-by-step instructions the `advisor_agent` follows when handling a user question.

## Step 1 — Load Data

Call `tools/load_data_tool.py::load_data()` to obtain three DataFrames:
- `clients_df` — 500 client master records
- `transactions_df` — 8,755 transaction rows
- `rfm_df` — pre-computed RFM scores and segments per client

The loader validates that all required columns exist, parses date fields, and prints a summary on completion.

## Step 2 — Classify Intent

Use explicit keyword matching (NOT AI inference) to classify the question into exactly one intent. Order matters — check most specific first:

1. **CLIENT** — question contains a client ID matching `MVC-\d{5}`, or explicit client keywords (`tell me about`, `briefing on`, `history of`, `profile of`, `contribution`, `% of sales`), or a first+last name that matches a client in the data (case-insensitive, supports reversed order like "Sharma Ling")
2. **PRODUCT (ranking)** — question asks for top-selling / best-selling / most-popular products (e.g. "top sale in paris", "best selling product at Tokyo")
3. **PRODUCT (specific)** — question references a specific product name, category + tier, or asks "who bought X"
4. **ALERT** — question contains any of: `prioritize`, `this week`, `should I reach out`, `alerts`, `haven't visited`, `at risk`, `win-back`
5. **SEGMENT** — question contains any of: `who are my`, `which clients`, `show me all`, `how many`, `top`, `lapsing`, `VIP`, `High Value`, `segment`, `nationality`, `store`

**Priority guard:** "top N client(s)" patterns (e.g. "who is the top 1 client in paris") always route to SEGMENT, not CLIENT, even though they may superficially resemble a name lookup.

**Fallback:** if no keywords match and no name is found, default to SEGMENT.

## Step 3 — Route to Tool(s)

| Intent | Tools called | Purpose |
|--------|--------------|---------|
| SEGMENT | `rfm_query_tool` | Filter the RFM summary by segment / store / nationality / category / lapsing / top_n |
| CLIENT  | `transaction_query_tool` + RFM lookup + `client_contribution` | Fetch full transaction history, the client's RFM row, and their % of store + global sales |
| PRODUCT (ranking) | `top_products` | Rank products by net_sales_amount, scoped by store / category, with pct_of_scope_sales |
| PRODUCT (specific) | `product_contribution` | List buyers of a product with each buyer's pct_of_product_sales |
| ALERT   | `alert_tool` | Generate prioritized list of clients flagged by alert rules |

For SEGMENT and CLIENT, `_parse_segment_params()` extracts filter values from the question (segment name, store, nationality, favorite category, top N).

### Name Resolution (CLIENT)

Clients can be looked up by:
- Explicit ID: `MVC-XXXXX`
- First + last name (case-insensitive): "Elena Bernard", "elena bernard"
- Reversed order: "Sharma Ling"
- Single name (only if unique match in data)

When multiple clients share the same name, the agent returns a disambiguation table with IDs and asks the advisor to re-ask with a specific MVC-XXXXX.

## Step 4 — Generate Narrative

Pass the structured tool output to `tools/insight_tool.py::generate_insight()` with one of five use cases:
- `client_briefing` — for CLIENT intent (includes boutique + global contribution %)
- `segment_summary` — for SEGMENT intent
- `next_best_action` — for ALERT intent
- `product_ranking` — for PRODUCT ranking intent
- `product_summary` — for PRODUCT specific-product intent

The insight tool calls Groq (`llama-3.3-70b-versatile`) when the SDK and `GROQ_API_KEY` are available, and falls back to a deterministic template otherwise.

**ALERT priority rule:** the headline sentence MUST reference the Lapsing VIP count first, even if another bucket is larger. Priority order: Lapsing VIP → Lapsing High Value → Win-back → Anniversary.

**CLIENT contribution metrics:** each client briefing includes two sales-contribution percentages:
- `pct_of_store_sales` — the client's spend as a % of their preferred boutique's total sales (primary metric for client advisors)
- `pct_of_global_sales` — the client's spend as a % of all-store sales (context for VIP tiering)

## Step 5 — Return Response

`run_agent(user_question, store_filter='All')` returns a dict with:
- `response_text` (str) — the narrative shown to the advisor
- `data_table` (DataFrame | None) — the underlying client/transaction/product rows for display
- `intent` (str) — `CLIENT`, `SEGMENT`, `PRODUCT`, or `ALERT`
- `tool_called` (str) — which tool(s) ran

## Guardrails

1. The agent never hallucinates client data — it only reports what the tools return.
2. If a tool returns zero results, the agent says so explicitly (e.g. "No client found with ID X.", "No matching clients were found.").
3. Every tool prints a status message and returns a consistent data structure.
4. Date filters and aggregations always use the RFM row as the canonical visit/segment source.
5. Ambiguous name matches return a disambiguation table — the agent never guesses.
