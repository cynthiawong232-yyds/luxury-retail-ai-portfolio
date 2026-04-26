"""Simulate an A/B test comparing Variant A (warm) vs Variant B (aspirational).

The simulation is rule-based with base rates from the spec and +/- 5pp noise.
Content of the variant text is accepted for downstream display but is not
used by the simulation itself. Results are flagged as simulated in both the
module constant and the printed summary.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from tools.segment_tool import SEGMENT_ORDER

SIMULATION_DISCLAIMER = "This is a simulated A/B test for demonstration purposes"

BASE_RATES = {
    "Variant A": {"open": 0.42, "click": 0.22},
    "Variant B": {"open": 0.38, "click": 0.28},
}
NOISE_PP = 0.05

RESULT_COLUMNS = [
    "segment", "variant", "n_assigned", "opens", "clicks",
    "open_rate", "click_rate", "conversion_rate", "recommended_winner",
]


def simulate_ab_test(
    variant_a_text: str,
    variant_b_text: str,
    segment_name: str,
    n_clients: int,
    seed: int | None = None,
) -> pd.DataFrame:
    """Return a 2-row DataFrame (one per variant) with simulated metrics."""
    _ = (variant_a_text, variant_b_text)  # accepted for API consistency

    if n_clients < 2:
        raise ValueError(
            f"Need at least 2 clients for A/B split; got {n_clients} for '{segment_name}'."
        )

    rng = np.random.default_rng(seed)
    n_a = n_clients // 2
    n_b = n_clients - n_a

    stats_a = _simulate_variant(rng, n_a, "Variant A")
    stats_b = _simulate_variant(rng, n_b, "Variant B")

    winner = (
        "Variant A"
        if stats_a["conversion_rate"] >= stats_b["conversion_rate"]
        else "Variant B"
    )

    rows = [
        _row(segment_name, "Variant A", n_a, stats_a, winner),
        _row(segment_name, "Variant B", n_b, stats_b, winner),
    ]
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def _simulate_variant(rng: np.random.Generator, n: int, variant: str) -> dict:
    base = BASE_RATES[variant]
    open_rate_true = float(np.clip(base["open"] + rng.uniform(-NOISE_PP, NOISE_PP), 0.0, 1.0))
    click_rate_true = float(np.clip(base["click"] + rng.uniform(-NOISE_PP, NOISE_PP), 0.0, 1.0))

    # Hierarchical model: a client must open before they can click.
    # Interpret base click_rate as clicks/sent, so click-to-open rate (CTOR)
    # is the ratio click_rate / open_rate, capped at 1.
    ctor = min(1.0, click_rate_true / open_rate_true) if open_rate_true > 0 else 0.0

    opens = int(rng.binomial(n, open_rate_true)) if n > 0 else 0
    clicks = int(rng.binomial(opens, ctor)) if opens > 0 else 0

    obs_open = opens / n if n else 0.0
    obs_click = clicks / n if n else 0.0
    conv = clicks / opens if opens else 0.0

    return {
        "opens": opens,
        "clicks": clicks,
        "open_rate": round(obs_open, 4),
        "click_rate": round(obs_click, 4),
        "conversion_rate": round(conv, 4),
    }


def _row(segment: str, variant: str, n_assigned: int, stats: dict, winner: str) -> dict:
    return {
        "segment": segment,
        "variant": variant,
        "n_assigned": n_assigned,
        "opens": stats["opens"],
        "clicks": stats["clicks"],
        "open_rate": stats["open_rate"],
        "click_rate": stats["click_rate"],
        "conversion_rate": stats["conversion_rate"],
        "recommended_winner": winner,
    }


def simulate_for_all_segments(
    copy_by_segment: dict[str, dict[str, str]],
    segment_summary: pd.DataFrame,
    seed: int | None = None,
) -> pd.DataFrame:
    """Run the simulation for every named segment and stack the results.

    copy_by_segment: {segment_name: {'variant_a': str, 'variant_b': str}}
    segment_summary: output of segment_tool.build_segment_summary
    """
    frames = []
    for seg in SEGMENT_ORDER:
        if seg not in copy_by_segment:
            continue
        match = segment_summary[segment_summary["segment"] == seg]
        if match.empty or int(match.iloc[0]["client_count"]) < 2:
            continue
        n_clients = int(match.iloc[0]["client_count"])
        frames.append(
            simulate_ab_test(
                copy_by_segment[seg]["variant_a"],
                copy_by_segment[seg]["variant_b"],
                seg,
                n_clients,
                seed=seed,
            )
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=RESULT_COLUMNS)


def _print_summary(results_df: pd.DataFrame) -> None:
    print("=" * 78)
    print("A/B TEST SIMULATION")
    print("=" * 78)
    for seg in results_df["segment"].unique():
        sub = results_df[results_df["segment"] == seg]
        winner = sub["recommended_winner"].iloc[0]
        print(f"\n  Segment: {seg}    Winner: {winner}")
        for _, r in sub.iterrows():
            print(
                f"    {r['variant']:<10}  "
                f"n={r['n_assigned']:>3}  "
                f"open={r['open_rate']:.1%}  "
                f"click={r['click_rate']:.1%}  "
                f"conv={r['conversion_rate']:.1%}"
            )
    print(f"\n  Note: {SIMULATION_DISCLAIMER}")
    print("=" * 78)


if __name__ == "__main__":
    from tools.load_data_tool import load_data
    from tools.segment_tool import segment_clients

    _, beauty_txn_df, _, rfm_df = load_data(verbose=False)
    _, summary = segment_clients(beauty_txn_df, rfm_df)

    dummy_copy = {
        seg: {
            "variant_a": "[warm copy placeholder]",
            "variant_b": "[aspirational copy placeholder]",
        }
        for seg in SEGMENT_ORDER
    }
    results = simulate_for_all_segments(dummy_copy, summary, seed=42)
    _print_summary(results)
