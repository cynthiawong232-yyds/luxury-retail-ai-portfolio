# ============================================================
# CONFIG — Your 3 flagship stores
# ============================================================

from datetime import date

# Store definitions
# Keys = site_number values in your CSV data and filenames
STORES = {
    "A800": {
        "label":    "SOHO",
        "region":   "US",
        "city":     "New York",
        "opened":   date(2025, 12, 7),   # Fiscal week 202544, week end 2025-12-07
        "currency": "USD",
        "flag":     "🇺🇸",
    },
    "J347": {
        "label":    "JAPAN",
        "region":   "Asia",
        "city":     "Japan",
        "opened":   date(2025, 8, 31),   # Fiscal week 202530, week end 2025-08-31
        "currency": "JPY",               # display only — data is already in USD
        "flag":     "🇯🇵",
    },
    "EU_F07M": {
        "label":    "EU",
        "region":   "EU",
        "city":     "Europe",
        "opened":   date(2025, 2, 9),    # Fiscal week 202501, week end 2025-02-09
        "currency": "EUR",               # display only — data is already in USD
        "flag":     "🇪🇺",
    },
}

# Channel labels (maps distribution_channel_code to readable name)
CHANNEL_LABELS = {
    "20": "Retail",
    "30": "Outlet",
    "40": "Off-Price",
    "50": "Wholesale",
    "70": "E-Commerce",
    "80": "Other",
}

# Groq API config for AI Advisor tab
# Get your free key at: https://console.groq.com
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# KPI thresholds for anomaly flagging
WOS_LOW_THRESHOLD  = 4.0    # below this = stockout risk
WOS_HIGH_THRESHOLD = 14.0   # above this = over-inventoried
COMP_WARNING_PCT   = -10.0  # below this = flag as underperforming
DISC_RATE_HIGH     = 0.35   # above 35% discount rate = flag
