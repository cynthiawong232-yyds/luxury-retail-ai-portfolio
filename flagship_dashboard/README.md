# CK Flagship Store Intelligence Dashboard

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
streamlit run app.py
```

## Your Stores

| Store Code | Label  | Region | Opened      |
|------------|--------|--------|-------------|
| A800       | SOHO   | US     | 2025-12-07  |
| J347       | JAPAN  | Asia   | 2025-08-31  |
| EU_F07M    | EU     | EU     | 2025-02-09  |

These are already configured in `config.py`. If anything changes (opening date,
store code) just edit that file — nothing else needs to change.

## File Naming Convention

The loader detects store + period from the filename automatically.
The site code must appear somewhere in the filename before the period token.

**Recommended format:**
```
SOHO_A800_WTD_2025-03-16.csv
JAPAN_J347_WTD_2025-03-16.csv
EU_EU_F07M_WTD_2025-03-16.csv
```

The loader handles `EU_F07M` correctly even though it contains an underscore —
it matches against known store codes using longest-match logic.

**Minimal format also works:**
```
A800_WTD_2025-03-16.csv
J347_MTD_2025-03-16.csv
EU_F07M_QTD_2025-03-16.csv
```

## Loading Data

1. Download your CSVs from Databricks (WTD, MTD, QTD, or YTD for each store)
2. Save them all into one folder, e.g. `./data`
3. Open the dashboard, enter the folder path in the sidebar, select period, click **Load Data**

You only need to load the files for the period you want to view.
Switch periods in the sidebar and click Load Data again to refresh.

## AI Advisor

Get a free Groq API key at [console.groq.com](https://console.groq.com).
Enter it in the AI Advisor tab, or set as an environment variable so it auto-fills:

```bash
export GROQ_API_KEY=your_key_here
streamlit run app.py
```

The **Anomaly Watch List** (Tab 4, section ①) works without any API key.
Sections ②–⑤ require the key.

## Project Structure

```
flagship_dashboard/
├── app.py                  ← entry point, sidebar, tab routing
├── config.py               ← store codes, opening dates, thresholds (edit here)
├── requirements.txt
├── README.md
├── data/                   ← put your CSVs here (create this folder)
├── tabs/
│   ├── portfolio.py        ← Tab 1: all 3 stores side by side + ramp view
│   ├── store_deep_dive.py  ← Tab 2: single store drill-down
│   ├── inventory.py        ← Tab 3: WOS gauges + inventory health
│   └── ai_advisor.py       ← Tab 4: anomaly flags + 4 AI functions
└── utils/
    ├── data_loader.py      ← CSV loading, aggregation, derived metrics
    ├── charts.py           ← all Plotly charts (dark CK theme)
    └── styles.py           ← CSS (Cormorant Garamond + DM Mono)
```
