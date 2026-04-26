"""Orchestrator: runs the full Maison Solène personalization pipeline end-to-end.

Pipeline:
  1. Load data (load_data_tool)
  2. Build beauty segments (segment_tool)
  3. For each target segment:
       a. Generate product recommendations (recommend_tool)
       b. Generate Variant A / B outreach copy via Groq (copy_tool)
       c. Simulate A/B test (ab_test_tool)
  4. Compile everything into a result dict consumable by the Streamlit dashboard.

Also supports single-segment mode for fast demos.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from tools.ab_test_tool import SIMULATION_DISCLAIMER, simulate_ab_test
from tools.copy_tool import generate_copy
from tools.load_data_tool import load_data
from tools.recommend_tool import recommend_products
from tools.segment_tool import SEGMENT_ORDER, segment_clients

PLACEHOLDER_COPY = {
    "variant_a": "[Variant A copy skipped — run without skip_copy=True to generate.]",
    "variant_b": "[Variant B copy skipped — run without skip_copy=True to generate.]",
}


def run_pipeline(
    single_segment: str | None = None,
    seed: int | None = None,
    skip_copy: bool = False,
    top_n_recommendations: int = 3,
    verbose: bool = True,
) -> dict:
    """Run the full pipeline and return a result dict.

    Args:
        single_segment: if given, only run the pipeline for that one segment.
        seed: seed for the A/B simulation (copy generation stays stochastic).
        skip_copy: skip the Groq API calls (placeholder copy is used instead).
        top_n_recommendations: how many products to recommend per segment.
        verbose: print progress to stdout.
    """
    segments = _resolve_segments(single_segment)

    _log(verbose, f"Step 1/4  Loading data...")
    clients_df, beauty_txn_df, catalog_df, rfm_df = load_data(verbose=False)

    _log(verbose, f"Step 2/4  Building segments...")
    profiles_df, segment_summary = segment_clients(beauty_txn_df, rfm_df)

    _log(verbose, f"Step 3/4  Running per-segment pipeline on: {segments}")
    per_segment: dict[str, dict] = {}
    ab_frames: list[pd.DataFrame] = []

    for seg in segments:
        row_match = segment_summary[segment_summary["segment"] == seg]
        if row_match.empty or int(row_match.iloc[0]["client_count"]) == 0:
            _log(verbose, f"  - {seg}: 0 clients, skipping")
            continue

        seg_row = row_match.iloc[0]
        n_clients = int(seg_row["client_count"])
        avg_spend = float(seg_row["avg_spend"])
        favorite_product = seg_row["top_product"]
        top_category = _top_category_for_segment(profiles_df, seg)

        _log(verbose, f"  - {seg}: recommending products...")
        recs = recommend_products(seg, catalog_df, segment_summary, top_n=top_n_recommendations)

        if skip_copy:
            copy = dict(PLACEHOLDER_COPY)
            _log(verbose, f"    copy skipped (skip_copy=True)")
        else:
            _log(verbose, f"    generating copy via Groq...")
            t0 = time.time()
            copy = generate_copy(
                segment_name=seg,
                recommendations_df=recs,
                avg_spend=avg_spend,
                favorite_product=favorite_product,
                top_category=top_category,
            )
            _log(verbose, f"    copy generated in {time.time() - t0:.1f}s")

        _log(verbose, f"    simulating A/B test ({n_clients} clients)...")
        ab_df = simulate_ab_test(
            variant_a_text=copy["variant_a"],
            variant_b_text=copy["variant_b"],
            segment_name=seg,
            n_clients=n_clients,
            seed=seed,
        )

        per_segment[seg] = {
            "recommendations": recs,
            "copy": copy,
            "ab_results": ab_df,
            "n_clients": n_clients,
            "avg_spend": avg_spend,
            "favorite_product": favorite_product,
            "top_category": top_category,
        }
        ab_frames.append(ab_df)

    _log(verbose, "Step 4/4  Compiling results...")
    ab_results_all = (
        pd.concat(ab_frames, ignore_index=True) if ab_frames else pd.DataFrame()
    )

    return {
        "clients_df": clients_df,
        "beauty_txn_df": beauty_txn_df,
        "catalog_df": catalog_df,
        "rfm_df": rfm_df,
        "client_profiles_df": profiles_df,
        "segment_summary": segment_summary,
        "segments_run": list(per_segment.keys()),
        "per_segment": per_segment,
        "ab_results_all": ab_results_all,
        "disclaimer": SIMULATION_DISCLAIMER,
    }


def _resolve_segments(single_segment: str | None) -> list[str]:
    if single_segment is None:
        return list(SEGMENT_ORDER)
    if single_segment not in SEGMENT_ORDER:
        raise ValueError(
            f"Unknown segment '{single_segment}'. Expected one of {SEGMENT_ORDER}."
        )
    return [single_segment]


def _top_category_for_segment(profiles_df: pd.DataFrame, segment_name: str):
    sub = profiles_df[profiles_df["beauty_segment"] == segment_name]
    if sub.empty:
        return None
    modes = sub["primary_beauty_category"].mode()
    return modes.iloc[0] if not modes.empty else None


def _log(verbose: bool, msg: str) -> None:
    if verbose:
        print(msg)


def _print_digest(result: dict) -> None:
    print("\n" + "=" * 78)
    print("PIPELINE RESULT DIGEST")
    print("=" * 78)
    print(f"  Segments run: {result['segments_run']}")
    print(f"  Total clients profiled: {len(result['client_profiles_df'])}")
    print("\n  Segment summary:")
    print(result["segment_summary"].to_string(index=False))
    if not result["ab_results_all"].empty:
        print("\n  A/B test results (all segments):")
        cols = ["segment", "variant", "n_assigned", "open_rate", "click_rate",
                "conversion_rate", "recommended_winner"]
        print(result["ab_results_all"][cols].to_string(index=False))
    print(f"\n  Note: {result['disclaimer']}")
    print("=" * 78)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Maison Solène personalization pipeline.")
    parser.add_argument("--segment", help="Run for a single segment only.")
    parser.add_argument("--skip-copy", action="store_true",
                        help="Skip Groq API calls (use placeholder copy).")
    parser.add_argument("--seed", type=int, help="Seed for A/B simulation.")
    args = parser.parse_args()

    result = run_pipeline(
        single_segment=args.segment,
        seed=args.seed,
        skip_copy=args.skip_copy,
    )
    _print_digest(result)
