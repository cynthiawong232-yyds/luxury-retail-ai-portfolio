import pandas as pd
import os
import io
from datetime import date
import streamlit as st
from config import STORES

# ── Column name maps ──────────────────────────────────────────────────────────
METRIC_COLS = [
    'netslsamt_cy', 'netslscstmerch_cy', 'netslsqty_cy', 'netmsrpamt_cy',
    'netslsamt_ly', 'netslscstmerch_ly', 'netslsqty_ly', 'netmsrpamt_ly',
    'eohttlqty_cy', 'eohstrqty_cy', 'intranqty_cy',
    'eohttlqty_ly', 'eohstrqty_ly', 'intranqty_ly',
]

# Merchant dimensions — used for filters and breakdowns across all tabs
MERCH_DIMS = {
    'Sector':       'gmh_sector_text',
    'Gender':       'gmh_gender_text',
    'Label':        'gmh_sub_brand_text',
    'Sub-Category': 'gmh_sub_category_text',
}

DIM_COLS = [
    'plm_style_code', 'style_description', 'color_code',
    'colorway_short_description', 'gmh_sector_text', 'gmh_gender_text',
    'gmh_category_text', 'gmh_sub_category_text', 'gmh_sub_brand_code',
    'gmh_sub_brand_text', 'company_code', 'distribution_channel_code',
    'site_number', 'site_text',
]


# ── Program names loader ──────────────────────────────────────────────────────

@st.cache_data
def load_program_names(filepath: str = './data/program_names.xlsx') -> pd.DataFrame:
    """
    Load program names Excel file and return as DataFrame.
    Expected columns: style code column + program name column.
    Tries to auto-detect column names.
    """
    if not os.path.exists(filepath):
        return pd.DataFrame()
    try:
        df = pd.read_excel(filepath)
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

        # Auto-detect style code and program name columns
        style_col   = next((c for c in df.columns if 'style' in c or 'plm' in c), None)
        program_col = next((c for c in df.columns if 'program' in c or 'name' in c), None)

        if not style_col or not program_col:
            st.warning(f"Program names file found but couldn't detect columns. "
                      f"Columns found: {df.columns.tolist()}")
            return pd.DataFrame()

        result = df[[style_col, program_col]].copy()
        result.columns = ['plm_style_code', 'program_name']
        result['plm_style_code'] = result['plm_style_code'].astype(str).str.strip()
        result['program_name']   = result['program_name'].astype(str).str.strip()
        return result.drop_duplicates('plm_style_code')

    except Exception as e:
        st.warning(f"Could not load program names: {e}")
        return pd.DataFrame()


# ── Filename parser ───────────────────────────────────────────────────────────

def _parse_filename(name: str):
    """
    Extract (store_code, period) from filename.
    Handles store codes with underscores (e.g. EU_F07M).
    Longest match wins.
    """
    PERIODS = ('WTD', 'MTD', 'QTD', 'YTD')
    stem  = os.path.basename(name).replace('.csv', '')
    parts = stem.split('_')

    period_idx = None
    period     = None
    for i, p in enumerate(parts):
        if p in PERIODS:
            period_idx = i
            period = p
            break

    if period_idx is None:
        return None, None

    known_codes = set(STORES.keys())
    site_code   = None
    best_len    = 0

    for start in range(period_idx):
        for end in range(start + 1, period_idx + 1):
            candidate = '_'.join(parts[start:end])
            if candidate in known_codes and (end - start) > best_len:
                site_code = candidate
                best_len  = end - start

    return site_code, period


# ── Enrichment ────────────────────────────────────────────────────────────────

def _enrich(df: pd.DataFrame, site_code: str) -> pd.DataFrame:
    """Add computed columns used across all tabs."""
    store_info = STORES.get(site_code, {})

    for col in METRIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    df['_store_code']   = site_code
    df['_store_label']  = store_info.get('label', site_code)
    df['_store_region'] = store_info.get('region', '')
    df['_store_flag']   = store_info.get('flag', '')

    opened = store_info.get('opened')
    if opened:
        weeks_open = max(1, (date.today() - opened).days // 7)
        df['_weeks_open'] = weeks_open
    else:
        df['_weeks_open'] = None

    if 'netslsamt_cy' in df.columns and 'netslsqty_cy' in df.columns:
        df['_aur_cy'] = df.apply(
            lambda r: r['netslsamt_cy'] / r['netslsqty_cy'] if r['netslsqty_cy'] > 0 else 0,
            axis=1
        )
    if 'netslsamt_ly' in df.columns and 'netslsqty_ly' in df.columns:
        df['_aur_ly'] = df.apply(
            lambda r: r['netslsamt_ly'] / r['netslsqty_ly'] if r['netslsqty_ly'] > 0 else 0,
            axis=1
        )
    return df


def _read_csv(source) -> pd.DataFrame:
    return pd.read_csv(source, low_memory=False)


# ── Main loader ───────────────────────────────────────────────────────────────

def load_all_store_data(
    uploaded_files=None,
    folder_path: str = None,
    period: str = "WTD"
) -> dict:
    sources = []

    if uploaded_files:
        for f in uploaded_files:
            sources.append((f.name, f))
    elif folder_path:
        if not os.path.isdir(folder_path):
            st.error(f"Folder not found: {folder_path}")
            return {}
        for fn in os.listdir(folder_path):
            if fn.endswith('.csv'):
                sources.append((fn, os.path.join(folder_path, fn)))

    data   = {}
    errors = []

    for name, source in sources:
        site_code, file_period = _parse_filename(name)

        if file_period != period:
            continue

        if site_code not in STORES:
            matched = None
            for code, info in STORES.items():
                if info['label'].upper() in name.upper():
                    matched = code
                    break
            if matched:
                site_code = matched
            else:
                errors.append(f"Unrecognised store in filename: {name}")
                continue

        try:
            df = _read_csv(source)
            df = _enrich(df, site_code)
            data[site_code] = df
        except Exception as e:
            errors.append(f"Error reading {name}: {e}")

    for err in errors:
        st.warning(err)

    return data


# ── Core aggregation helper ───────────────────────────────────────────────────

def _dim_breakdown(df: pd.DataFrame, dim_col: str) -> pd.DataFrame:
    """
    Generic breakdown by any merchant dimension.
    Returns sales, units, mix%, YoY%, AUR for CY and LY.
    This is the core function behind all sector/gender/label/subcategory cuts.
    """
    total_cy = df['netslsamt_cy'].sum()
    total_ly = df['netslsamt_ly'].sum()

    grp = df.groupby(dim_col, as_index=False).agg(
        netslsamt_cy  =('netslsamt_cy',   'sum'),
        netslsamt_ly  =('netslsamt_ly',   'sum'),
        netslsqty_cy  =('netslsqty_cy',   'sum'),
        netslsqty_ly  =('netslsqty_ly',   'sum'),
        netmsrpamt_cy =('netmsrpamt_cy',  'sum'),
        eohttlqty_cy  =('eohttlqty_cy',   'sum'),
        eohttlqty_ly  =('eohttlqty_ly',   'sum'),
        intranqty_cy  =('intranqty_cy',   'sum'),
    ).sort_values('netslsamt_cy', ascending=False)

    # Mix %
    grp['mix_pct_cy'] = grp['netslsamt_cy'].apply(
        lambda v: round(v / total_cy * 100, 1) if total_cy > 0 else 0
    )
    grp['mix_pct_ly'] = grp['netslsamt_ly'].apply(
        lambda v: round(v / total_ly * 100, 1) if total_ly > 0 else 0
    )

    # YoY %
    grp['var_pct'] = grp.apply(
        lambda r: round((r['netslsamt_cy'] / r['netslsamt_ly'] - 1) * 100, 1)
        if r['netslsamt_ly'] > 0 else None, axis=1
    )

    # AUR
    grp['aur_cy'] = grp.apply(
        lambda r: round(r['netslsamt_cy'] / r['netslsqty_cy'], 2)
        if r['netslsqty_cy'] > 0 else 0, axis=1
    )
    grp['aur_ly'] = grp.apply(
        lambda r: round(r['netslsamt_ly'] / r['netslsqty_ly'], 2)
        if r['netslsqty_ly'] > 0 else 0, axis=1
    )

    return grp


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """
    Apply merchant dimension filters to a DataFrame.
    filters = {'gmh_sector_text': ['Apparel'], 'gmh_gender_text': ['Men'], ...}
    Empty list = no filter applied for that dimension.
    """
    for col, values in filters.items():
        if values and col in df.columns:
            df = df[df[col].isin(values)]
    return df


# ── Store-level totals ────────────────────────────────────────────────────────

def store_totals(data: dict) -> pd.DataFrame:
    rows = []
    for code, df in data.items():
        row = {
            'store_code':   code,
            'store_label':  df['_store_label'].iloc[0],
            'store_region': df['_store_region'].iloc[0],
            'store_flag':   df['_store_flag'].iloc[0],
            'weeks_open':   df['_weeks_open'].iloc[0],
        }
        for col in METRIC_COLS:
            row[col] = df[col].sum() if col in df.columns else 0
        rows.append(row)
    return pd.DataFrame(rows)


# ── Merchant dimension breakdowns ─────────────────────────────────────────────

def sector_breakdown(df: pd.DataFrame)       -> pd.DataFrame:
    return _dim_breakdown(df, 'gmh_sector_text')

def gender_breakdown(df: pd.DataFrame)       -> pd.DataFrame:
    return _dim_breakdown(df, 'gmh_gender_text')

def label_breakdown(df: pd.DataFrame)        -> pd.DataFrame:
    return _dim_breakdown(df, 'gmh_sub_brand_text')

def subcategory_breakdown(df: pd.DataFrame)  -> pd.DataFrame:
    return _dim_breakdown(df, 'gmh_sub_category_text')

def category_breakdown(df: pd.DataFrame)     -> pd.DataFrame:
    return _dim_breakdown(df, 'gmh_category_text')


# ── Cross-store dimension breakdown (for Portfolio tab) ───────────────────────

def cross_store_dim(data: dict, dim_col: str) -> pd.DataFrame:
    """
    Returns combined DataFrame with store label column added.
    Used for cross-store sector/gender/label charts on Portfolio tab.
    """
    frames = []
    for code, df in data.items():
        grp = _dim_breakdown(df, dim_col)
        grp['_store_label']  = df['_store_label'].iloc[0]
        grp['_store_region'] = df['_store_region'].iloc[0]
        grp['_store_flag']   = df['_store_flag'].iloc[0]
        frames.append(grp)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ── Styles ────────────────────────────────────────────────────────────────────

def style_table(df: pd.DataFrame, n: int = 20,
                bottom: bool = False,
                program_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Top or bottom N styles by net sales CY.
    Optionally joins program names for underwear visibility.
    """
    grp = df.groupby(
        ['plm_style_code', 'style_description', 'color_code',
         'colorway_short_description', 'gmh_sector_text',
         'gmh_gender_text', 'gmh_sub_brand_text',
         'gmh_category_text', 'gmh_sub_category_text'],
        as_index=False
    ).agg(
        netslsamt_cy  =('netslsamt_cy',  'sum'),
        netslsamt_ly  =('netslsamt_ly',  'sum'),
        netslsqty_cy  =('netslsqty_cy',  'sum'),
        netslsqty_ly  =('netslsqty_ly',  'sum'),
        netmsrpamt_cy =('netmsrpamt_cy', 'sum'),
    )

    total_cy = grp['netslsamt_cy'].sum()

    grp['aur_cy']    = grp.apply(
        lambda r: round(r['netslsamt_cy'] / r['netslsqty_cy'], 2)
        if r['netslsqty_cy'] > 0 else 0, axis=1
    )
    grp['mix_pct_cy'] = grp['netslsamt_cy'].apply(
        lambda v: round(v / total_cy * 100, 1) if total_cy > 0 else 0
    )
    grp['var_pct'] = grp.apply(
        lambda r: round((r['netslsamt_cy'] / r['netslsamt_ly'] - 1) * 100, 1)
        if r['netslsamt_ly'] > 0 else None, axis=1
    )

    # Join program names if provided
    if program_df is not None and not program_df.empty:
        grp = grp.merge(program_df, on='plm_style_code', how='left')
        grp['program_name'] = grp['program_name'].fillna('—')

    grp = grp.sort_values('netslsamt_cy', ascending=bottom)
    return grp.head(n)


# ── Program breakdown (Underwear) ─────────────────────────────────────────────

def program_breakdown(df: pd.DataFrame,
                      program_df: pd.DataFrame) -> pd.DataFrame:
    """
    Sales breakdown by program name for underwear styles.
    Joins program names onto the filtered underwear DataFrame.
    """
    if program_df is None or program_df.empty:
        return pd.DataFrame()

    merged = df.merge(program_df, on='plm_style_code', how='left')
    merged['program_name'] = merged['program_name'].fillna('Unknown / No Program')

    total_cy = merged['netslsamt_cy'].sum()

    grp = merged.groupby('program_name', as_index=False).agg(
        netslsamt_cy =('netslsamt_cy', 'sum'),
        netslsamt_ly =('netslsamt_ly', 'sum'),
        netslsqty_cy =('netslsqty_cy', 'sum'),
        netslsqty_ly =('netslsqty_ly', 'sum'),
    ).sort_values('netslsamt_cy', ascending=False)

    grp['mix_pct_cy'] = grp['netslsamt_cy'].apply(
        lambda v: round(v / total_cy * 100, 1) if total_cy > 0 else 0
    )
    grp['var_pct'] = grp.apply(
        lambda r: round((r['netslsamt_cy'] / r['netslsamt_ly'] - 1) * 100, 1)
        if r['netslsamt_ly'] > 0 else None, axis=1
    )
    return grp


# ── Inventory by dimension ────────────────────────────────────────────────────

def inv_by_dim(df: pd.DataFrame, dim_col: str) -> pd.DataFrame:
    """Inventory breakdown by any merchant dimension."""
    total_cy = df['eohttlqty_cy'].sum()
    total_ly = df['eohttlqty_ly'].sum()

    grp = df.groupby(dim_col, as_index=False).agg(
        eohttlqty_cy =('eohttlqty_cy', 'sum'),
        eohttlqty_ly =('eohttlqty_ly', 'sum'),
        eohstrqty_cy =('eohstrqty_cy', 'sum'),
        intranqty_cy =('intranqty_cy', 'sum'),
        netslsqty_cy =('netslsqty_cy', 'sum'),
    ).sort_values('eohttlqty_cy', ascending=False)

    grp['mix_pct_cy'] = grp['eohttlqty_cy'].apply(
        lambda v: round(v / total_cy * 100, 1) if total_cy > 0 else 0
    )
    grp['eoh_var_pct'] = grp.apply(
        lambda r: round((r['eohttlqty_cy'] / r['eohttlqty_ly'] - 1) * 100, 1)
        if r['eohttlqty_ly'] > 0 else None, axis=1
    )
    grp['wos'] = grp.apply(
        lambda r: round(r['eohttlqty_cy'] / r['netslsqty_cy'], 1)
        if r['netslsqty_cy'] > 0 else 0, axis=1
    )
    grp['transit_pct'] = grp.apply(
        lambda r: round(r['intranqty_cy'] / r['eohttlqty_cy'] * 100, 1)
        if r['eohttlqty_cy'] > 0 else 0, axis=1
    )
    return grp


# ── Legacy helpers (kept for backward compat) ─────────────────────────────────

def top_styles(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    return style_table(df, n=n, bottom=False)

def inv_by_category(df: pd.DataFrame) -> pd.DataFrame:
    return inv_by_dim(df, 'gmh_category_text')

def calc_wos(df: pd.DataFrame) -> float:
    eoh  = df['eohttlqty_cy'].sum()
    wkly = df['netslsqty_cy'].sum()
    return round(eoh / wkly, 1) if wkly > 0 else 0.0

def calc_disc_rate(df: pd.DataFrame) -> float:
    msrp = df['netmsrpamt_cy'].sum()
    net  = df['netslsamt_cy'].sum()
    return round(1 - (net / msrp), 3) if msrp > 0 else 0.0

def calc_sell_through(df: pd.DataFrame) -> float:
    sold = df['netslsqty_cy'].sum()
    eoh  = df['eohttlqty_cy'].sum()
    return round(sold / (sold + eoh), 3) if (sold + eoh) > 0 else 0.0


# ── Excel export ──────────────────────────────────────────────────────────────

def to_excel_download(data: dict, period: str) -> bytes:
    """One sheet per store, filtered export columns only."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        for store_code, df in data.items():
            label      = STORES.get(store_code, {}).get('label', store_code)
            sheet_name = f"{label}_{period}"[:31]
            export_df  = df[[c for c in df.columns if not c.startswith('_')]]
            export_df.to_excel(writer, sheet_name=sheet_name, index=False)
    return buffer.getvalue()
