from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from .strategy_replay import (
    ROUND_DATA_DIRS,
    TraderProtocol,
    load_trader_factory,
    run_day,
)

DEFAULT_HELD_OUT_ROUNDS = (2,)
DEFAULT_HELD_OUT_DAYS = (0, 1)


@dataclass(slots=True)
class CandidateStrategy:
    """Specification of a candidate trading strategy to evaluate."""

    name: str
    factory: Callable[[], TraderProtocol]
    position_limits: dict[str, int] = field(default_factory=dict)


def resolve_candidate(candidate: CandidateStrategy | int | str | Path) -> CandidateStrategy:
    """Resolve a candidate strategy representation into a CandidateStrategy instance."""
    if isinstance(candidate, CandidateStrategy):
        return candidate
    if isinstance(candidate, int):
        factory, limits = load_trader_factory(candidate)
        return CandidateStrategy(name=f"round_{candidate}", factory=factory, position_limits=limits)
    if isinstance(candidate, (str, Path)):
        str_val = str(candidate).strip()
        if str_val in {"1", "2", "round_1", "round_2"}:
            r_num = int(str_val.replace("round_", ""))
            factory, limits = load_trader_factory(r_num)
            return CandidateStrategy(name=f"round_{r_num}", factory=factory, position_limits=limits)
        path = Path(candidate).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Candidate strategy file not found: {candidate}")
        factory, limits = load_trader_factory(path)
        return CandidateStrategy(name=path.stem, factory=factory, position_limits=limits)
    raise TypeError(f"Unsupported candidate strategy type: {type(candidate)}")


def _aggregate_segment(days: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Calculate summary metrics for a segment of day replay results."""
    if not days:
        return {
            "day_count": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "mean_daily_pnl": 0.0,
            "return_to_drawdown": None,
            "fills": 0,
            "traded_volume": 0,
            "position_limit_rejections": 0,
        }

    total_pnl = round(sum(cast(float, d["total_pnl"]) for d in days), 2)
    max_drawdown = round(max(cast(float, d["max_drawdown"]) for d in days), 2)
    fills = sum(cast(int, d["fills"]) for d in days)
    traded_volume = sum(cast(int, d["traded_volume"]) for d in days)
    rejections = sum(cast(int, d["position_limit_rejections"]) for d in days)
    mean_daily_pnl = round(total_pnl / len(days), 2)
    return_to_drawdown = round(total_pnl / max_drawdown, 2) if max_drawdown > 0 else None

    return {
        "day_count": len(days),
        "total_pnl": total_pnl,
        "max_drawdown": max_drawdown,
        "mean_daily_pnl": mean_daily_pnl,
        "return_to_drawdown": return_to_drawdown,
        "fills": fills,
        "traded_volume": traded_volume,
        "position_limit_rejections": rejections,
    }


def compare_candidate_strategies(
    candidates: Sequence[CandidateStrategy | int | str | Path] | None = None,
    rounds: Sequence[int] = (1, 2),
    held_out_rounds: Sequence[int] | None = DEFAULT_HELD_OUT_ROUNDS,
    held_out_days: Sequence[int] | None = DEFAULT_HELD_OUT_DAYS,
    match_trades: str = "worse",
    data_dirs: dict[int, Path] | None = None,
) -> dict[str, Any]:
    """Compare multiple candidate strategies across rounds and held-out days."""
    if match_trades not in {"all", "worse", "none"}:
        raise ValueError(f"Unsupported trade matching mode: {match_trades}")

    if candidates is None:
        raw_candidates: list[CandidateStrategy | int | str | Path] = ["round_1", "round_2"]
    else:
        raw_candidates = list(candidates)

    if not raw_candidates:
        raise ValueError("At least one candidate strategy must be specified for comparison")

    resolved_candidates = [resolve_candidate(c) for c in raw_candidates]

    if not rounds:
        raise ValueError("At least one round must be specified for evaluation")

    held_out_rounds_set = set(held_out_rounds) if held_out_rounds is not None else set()
    held_out_days_set = set(held_out_days) if held_out_days is not None else set()

    active_data_dirs = data_dirs if data_dirs is not None else ROUND_DATA_DIRS

    round_price_files: dict[int, list[tuple[int, Path, Path]]] = {}
    for round_num in rounds:
        data_dir = active_data_dirs.get(round_num)
        if data_dir is None or not data_dir.is_dir():
            raise ValueError(
                f"Historical replay data is available for rounds 1 and 2, not {round_num}"
            )

        found_price_files = sorted(
            data_dir.glob(f"prices_round_{round_num}_day_*.csv"),
            key=lambda path: int(
                re.search(r"_day_(-?\d+)\.csv(?:\.gz)?$", path.name).group(1)  # type: ignore[union-attr]
            ),
        )
        if not found_price_files:
            # Check for gzipped price files
            found_price_files = sorted(
                data_dir.glob(f"prices_round_{round_num}_day_*.csv.gz"),
                key=lambda path: int(
                    re.search(r"_day_(-?\d+)\.csv(?:\.gz)?$", path.name).group(1)  # type: ignore[union-attr]
                ),
            )
        if not found_price_files:
            raise FileNotFoundError(f"No price data found for round {round_num} in {data_dir}")

        day_entries: list[tuple[int, Path, Path]] = []
        for prices_path in found_price_files:
            day_match = re.search(r"_day_(-?\d+)\.csv(?:\.gz)?$", prices_path.name)
            if day_match is None:
                raise ValueError(f"Could not read day number from {prices_path.name}")
            day_num = int(day_match.group(1))

            trades_path = data_dir / f"trades_round_{round_num}_day_{day_num}.csv"
            if not trades_path.is_file():
                gz_trades = trades_path.with_name(trades_path.name + ".gz")
                if gz_trades.is_file():
                    trades_path = gz_trades
                else:
                    raise FileNotFoundError(
                        f"No trade data found for round {round_num} day {day_num}"
                    )
            day_entries.append((day_num, prices_path, trades_path))

        round_price_files[round_num] = day_entries

    candidate_results: dict[str, Any] = {}
    candidate_summaries: list[dict[str, Any]] = []

    for candidate in resolved_candidates:
        candidate_days: list[dict[str, Any]] = []
        for round_num in rounds:
            for day_num, prices_path, trades_path in round_price_files[round_num]:
                is_held_out_round = round_num in held_out_rounds_set
                is_held_out_day = day_num in held_out_days_set
                is_held_out = is_held_out_round or is_held_out_day
                split = "held_out" if is_held_out else "in_sample"

                trader = candidate.factory()
                day_res = run_day(
                    round_num,
                    prices_path,
                    trades_path,
                    trader,
                    candidate.position_limits,
                    match_trades,
                )
                day_record: dict[str, Any] = {
                    "strategy": candidate.name,
                    "round": round_num,
                    "day": day_num,
                    "is_held_out_round": is_held_out_round,
                    "is_held_out_day": is_held_out_day,
                    "split": split,
                    "total_pnl": day_res["total_pnl"],
                    "product_pnl": day_res["product_pnl"],
                    "max_drawdown": day_res["max_drawdown"],
                    "max_abs_position": day_res["max_abs_position"],
                    "ending_position": day_res["ending_position"],
                    "position_limit_rejections": day_res["position_limit_rejections"],
                    "submitted_orders": day_res["submitted_orders"],
                    "fills": day_res["fills"],
                    "traded_volume": day_res["traded_volume"],
                }
                candidate_days.append(day_record)

        overall_metrics = _aggregate_segment(candidate_days)
        in_sample_days = [d for d in candidate_days if d["split"] == "in_sample"]
        held_out_days_list = [d for d in candidate_days if d["split"] == "held_out"]
        held_out_day_only_list = [d for d in candidate_days if d["is_held_out_day"]]
        held_out_round_only_list = [d for d in candidate_days if d["is_held_out_round"]]

        in_sample_metrics = _aggregate_segment(in_sample_days)
        held_out_metrics = _aggregate_segment(held_out_days_list)
        held_out_day_metrics = _aggregate_segment(held_out_day_only_list)
        held_out_round_metrics = _aggregate_segment(held_out_round_only_list)

        overfit_gap = (
            round(in_sample_metrics["mean_daily_pnl"] - held_out_metrics["mean_daily_pnl"], 2)
            if in_sample_metrics["day_count"] > 0 and held_out_metrics["day_count"] > 0
            else 0.0
        )

        candidate_results[candidate.name] = {
            "metrics": {
                "overall": overall_metrics,
                "in_sample": in_sample_metrics,
                "held_out": held_out_metrics,
                "held_out_days_only": held_out_day_metrics,
                "held_out_rounds_only": held_out_round_metrics,
                "overfit_gap": overfit_gap,
            },
            "days": candidate_days,
        }

        candidate_summaries.append(
            {
                "candidate": candidate.name,
                "overall_pnl": overall_metrics["total_pnl"],
                "in_sample_pnl": in_sample_metrics["total_pnl"],
                "held_out_pnl": held_out_metrics["total_pnl"],
                "overall_drawdown": overall_metrics["max_drawdown"],
                "held_out_drawdown": held_out_metrics["max_drawdown"],
                "overall_return_to_drawdown": overall_metrics["return_to_drawdown"],
                "held_out_return_to_drawdown": held_out_metrics["return_to_drawdown"],
                "in_sample_mean_daily_pnl": in_sample_metrics["mean_daily_pnl"],
                "held_out_mean_daily_pnl": held_out_metrics["mean_daily_pnl"],
                "overfit_gap": overfit_gap,
                "total_fills": overall_metrics["fills"],
                "total_volume": overall_metrics["traded_volume"],
                "rejections": overall_metrics["position_limit_rejections"],
            }
        )

    by_held_out_pnl = sorted(
        candidate_summaries,
        key=lambda s: cast(float, s["held_out_pnl"]),
        reverse=True,
    )
    by_overall_pnl = sorted(
        candidate_summaries,
        key=lambda s: cast(float, s["overall_pnl"]),
        reverse=True,
    )
    by_return_to_drawdown = sorted(
        candidate_summaries,
        key=lambda s: (
            float("-inf")
            if s["overall_return_to_drawdown"] is None
            else cast(float, s["overall_return_to_drawdown"])
        ),
        reverse=True,
    )

    rank_held_out_map = {row["candidate"]: idx + 1 for idx, row in enumerate(by_held_out_pnl)}
    for row in candidate_summaries:
        row["rank_held_out"] = rank_held_out_map[row["candidate"]]

    return {
        "matching_mode": match_trades,
        "fill_assumptions": {
            "displayed_book": "marketable orders fill at the opposing displayed price",
            "public_trades": "worse fills only when public trades pass the resting quote; all also includes equal prices",
            "queue_priority": "not modeled",
            "conversions_and_market_access_bids": "not modeled",
        },
        "partitions": {
            "evaluated_rounds": list(rounds),
            "held_out_rounds": sorted(held_out_rounds_set),
            "held_out_days": sorted(held_out_days_set),
        },
        "rankings": {
            "by_held_out_pnl": [c["candidate"] for c in by_held_out_pnl],
            "by_overall_pnl": [c["candidate"] for c in by_overall_pnl],
            "by_return_to_drawdown": [c["candidate"] for c in by_return_to_drawdown],
        },
        "comparison_summary": candidate_summaries,
        "candidates": candidate_results,
    }


def format_comparison_table(result: dict[str, Any]) -> str:
    """Format the strategy comparison summary as an ASCII table."""
    summaries: list[dict[str, Any]] = result.get("comparison_summary", [])
    if not summaries:
        return "No candidate strategies evaluated."

    headers = [
        "Candidate",
        "Overall P&L",
        "Held-Out P&L",
        "In-Sample P&L",
        "Drawdown",
        "Held-Out R/DD",
        "Overfit Gap",
        "Rank (Held-Out)",
    ]

    rows = []
    for s in summaries:
        r_dd_val = s["held_out_return_to_drawdown"]
        r_dd_str = f"{r_dd_val:.2f}" if r_dd_val is not None else "N/A"
        rows.append(
            [
                str(s["candidate"]),
                f"{s['overall_pnl']:,.2f}",
                f"{s['held_out_pnl']:,.2f}",
                f"{s['in_sample_pnl']:,.2f}",
                f"{s['overall_drawdown']:,.2f}",
                r_dd_str,
                f"{s['overfit_gap']:,.2f}",
                str(s.get("rank_held_out", "-")),
            ]
        )

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = "  ".join("-" * col_widths[i] for i in range(len(headers)))
    row_lines = ["  ".join(val.ljust(col_widths[i]) for i, val in enumerate(row)) for row in rows]

    return "\n".join([header_line, separator, *row_lines])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare candidate strategies on held-out days and rounds."
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=["round_1", "round_2"],
        help="Candidate strategies to compare (e.g. round_1 round_2 or paths to trader.py files).",
    )
    parser.add_argument(
        "--rounds",
        nargs="+",
        type=int,
        default=[1, 2],
        help="Rounds to evaluate across (default: 1 2).",
    )
    parser.add_argument(
        "--held-out-rounds",
        nargs="*",
        type=int,
        default=list(DEFAULT_HELD_OUT_ROUNDS),
        help="Rounds to treat as held-out / out-of-sample (default: 2).",
    )
    parser.add_argument(
        "--held-out-days",
        nargs="*",
        type=int,
        default=list(DEFAULT_HELD_OUT_DAYS),
        help="Days to treat as held-out across rounds (default: 0 1).",
    )
    parser.add_argument(
        "--match-trades",
        choices=("all", "worse", "none"),
        default="worse",
        help="Trade-matching mode for public trades (default: worse).",
    )
    parser.add_argument(
        "--format",
        choices=("json", "table"),
        default="json",
        help="Output format: json or table (default: json).",
    )

    args = parser.parse_args()

    comparison = compare_candidate_strategies(
        candidates=args.strategies,
        rounds=args.rounds,
        held_out_rounds=args.held_out_rounds,
        held_out_days=args.held_out_days,
        match_trades=args.match_trades,
    )

    if args.format == "table":
        print(format_comparison_table(comparison))
    else:
        print(json.dumps(comparison, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
