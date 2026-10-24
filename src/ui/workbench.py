"""Data and URL helpers for the TradeTell workbench, kept free of Streamlit calls for testing."""

from __future__ import annotations

import csv
import gzip
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict, cast

from src.evaluation.strategy_replay import load_trader, run_day

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTARA_DIR = PROJECT_ROOT / "static" / "intara"
DAYS = (-2, -1, 0, 1)
TRADERS = (1, 2)
MATCHES = ("worse", "all", "none")
LAYERS = ("ground", "trader", "notes", "index")
PEPPER = "INTARIAN_PEPPER_ROOT"
OSMIUM = "ASH_COATED_OSMIUM"
DAY_SOURCES = {-2: "Round 1", -1: "Round 1", 0: "Round 1", 1: "Round 2"}


class Place(TypedDict):
    zoom: int | None
    day: int
    t: int


class ReplaySettings(TypedDict):
    trader: int
    day: int
    match: str


class Params(TypedDict):
    layer: str
    place: Place
    replay: ReplaySettings


class ReplayPayload(TypedDict):
    trader: int
    day: int
    match: str
    total_pnl: float
    product_pnl: dict[str, float]
    max_drawdown: float
    fills: int
    traded_volume: int
    position_limit_rejections: int
    equity: list[float]
    fill_log: list[list[int | str]]


class GoodSummary(TypedDict):
    open: float
    close: float
    low: float
    high: float
    trades: int


class Overview(TypedDict):
    stride: int
    pepper: list[float | None]
    osmium: list[float | None]


class DaySummary(TypedDict):
    day: int
    source: str
    goods: dict[str, GoodSummary]


def day_files(day: int) -> tuple[Path, Path]:
    return INTARA_DIR / f"prices_day_{day}.csv.gz", INTARA_DIR / f"trades_day_{day}.csv.gz"


def _int(value: str | None, fallback: int, allowed: tuple[int, ...]) -> int:
    try:
        number = int(value) if value is not None else fallback
    except ValueError:
        return fallback
    return number if number in allowed else fallback


def parse_params(params: Mapping[str, str]) -> Params:
    """Turn query parameters into a validated layer, probe place and replay settings."""
    layer = params.get("layer", "ground")
    if layer not in LAYERS:
        layer = "ground"
    zoom = params.get("zoom")
    try:
        t = int(params.get("t", "500000"))
    except ValueError:
        t = 500000
    match = params.get("match", "worse")
    return {
        "layer": layer,
        "place": {
            "zoom": _int(zoom, 0, DAYS) if zoom is not None else None,
            "day": _int(params.get("day"), 1, DAYS),
            "t": min(max(t - t % 100, 0), 999900),
        },
        "replay": {
            "trader": _int(params.get("trader"), 1, TRADERS),
            "day": _int(params.get("rday"), 0, DAYS),
            "match": match if match in MATCHES else "worse",
        },
    }


def place_params(place: Place) -> dict[str, str]:
    params = {"day": str(place["day"]), "t": str(place["t"])}
    if place["zoom"] is not None:
        params["zoom"] = str(place["zoom"])
    return params


def replay_payload(trader_round: int, day: int, match: str) -> ReplayPayload:
    """Replay a built-in Trader through one recorded day and shape it for the section."""
    prices, trades = day_files(day)
    trader, limits = load_trader(trader_round)
    result = run_day(trader_round, prices, trades, trader, limits, match, trace=True)
    fill_log = cast(list[tuple[int, str, int, int]], result["fill_log"])
    return {
        "trader": trader_round,
        "day": day,
        "match": match,
        "total_pnl": cast(float, result["total_pnl"]),
        "product_pnl": cast(dict[str, float], result["product_pnl"]),
        "max_drawdown": cast(float, result["max_drawdown"]),
        "fills": cast(int, result["fills"]),
        "traded_volume": cast(int, result["traded_volume"]),
        "position_limit_rejections": cast(int, result["position_limit_rejections"]),
        "equity": cast(list[float], result["equity"]),
        "fill_log": [list(fill) for fill in fill_log],
    }


def overview(stride: int = 25) -> Overview:
    """Every ``stride``-th mid price of each good across the record, so the section draws at once."""
    series: dict[str, list[float | None]] = {"pepper": [], "osmium": []}
    keys = {PEPPER: "pepper", OSMIUM: "osmium"}
    for day in DAYS:
        prices, _ = day_files(day)
        mids: dict[str, list[float | None]] = {"pepper": [None] * 10000, "osmium": [None] * 10000}
        with gzip.open(prices, "rt", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter=";"):
                key = keys.get(row["product"])
                mid = float(row["mid_price"] or 0)
                if key and mid > 0:
                    mids[key][int(row["timestamp"]) // 100] = mid
        for key, values in mids.items():
            series[key].extend(values[::stride])
    return {"stride": stride, "pepper": series["pepper"], "osmium": series["osmium"]}


def day_summary(day: int) -> DaySummary:
    """Open, close and range per good, plus public trade counts, for the index."""
    prices, trades = day_files(day)
    mids: dict[str, list[float]] = {PEPPER: [], OSMIUM: []}
    with gzip.open(prices, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            mid = float(row["mid_price"] or 0)
            if row["product"] in mids and mid > 0:
                mids[row["product"]].append(mid)
    counts = {PEPPER: 0, OSMIUM: 0}
    with gzip.open(trades, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            if row["symbol"] in counts:
                counts[row["symbol"]] += 1
    return {
        "day": day,
        "source": DAY_SOURCES[day],
        "goods": {
            product: {
                "open": values[0],
                "close": values[-1],
                "low": min(values),
                "high": max(values),
                "trades": counts[product],
            }
            for product, values in mids.items()
        },
    }
