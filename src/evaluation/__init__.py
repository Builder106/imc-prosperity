"""Offline evaluation tools for competition strategies."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .strategy_comparison import (
        CandidateStrategy,
        compare_candidate_strategies,
        format_comparison_table,
        resolve_candidate,
    )
    from .strategy_replay import load_trader, load_trader_factory, run_day, run_round


def __getattr__(name: str) -> object:
    if name in {
        "CandidateStrategy",
        "compare_candidate_strategies",
        "format_comparison_table",
        "resolve_candidate",
    }:
        from . import strategy_comparison

        return getattr(strategy_comparison, name)
    if name in {"load_trader", "load_trader_factory", "run_day", "run_round"}:
        from . import strategy_replay

        return getattr(strategy_replay, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CandidateStrategy",
    "compare_candidate_strategies",
    "format_comparison_table",
    "load_trader",
    "load_trader_factory",
    "resolve_candidate",
    "run_day",
    "run_round",
]
