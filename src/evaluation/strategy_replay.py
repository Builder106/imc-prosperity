from __future__ import annotations

import argparse
import contextlib
import csv
import importlib.util
import io
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, cast

from src.algorithms.round_1.datamodel import (
    Listing,
    Observation,
    Order,
    OrderDepth,
    Trade,
    TradingState,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ROUND_DATA_DIRS = {
    1: PROJECT_ROOT / "data" / "competition_rounds" / "ROUND1",
    2: PROJECT_ROOT / "data" / "competition_rounds" / "ROUND_2",
}
DEFAULT_POSITION_LIMIT = 20


class TraderProtocol(Protocol):
    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]: ...


@dataclass(slots=True)
class MarketTrade:
    trade: Trade
    buy_remaining: int
    sell_remaining: int


@dataclass(slots=True)
class Tick:
    order_depths: dict[str, OrderDepth] = field(default_factory=dict)
    mid_prices: dict[str, float] = field(default_factory=dict)
    market_trades: dict[str, list[Trade]] = field(default_factory=dict)


def _integer(value: str | None, field_name: str) -> int:
    if value is None or not value.strip():
        raise ValueError(f"Missing {field_name}")
    number = float(value)
    if not number.is_integer():
        raise ValueError(f"Expected an integer for {field_name}, got {value!r}")
    return int(number)


def _optional_integer(value: str | None, field_name: str) -> int | None:
    if value is None or not value.strip():
        return None
    return _integer(value, field_name)


def read_day(prices_path: Path, trades_path: Path) -> dict[int, Tick]:
    ticks: dict[int, Tick] = {}
    with prices_path.open(encoding="utf-8", newline="") as prices_file:
        reader = csv.DictReader(prices_file, delimiter=";")
        required = {"timestamp", "product", "mid_price"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"Unexpected prices CSV columns in {prices_path}")

        for row in reader:
            timestamp = _integer(row["timestamp"], "timestamp")
            product = row["product"]
            tick = ticks.setdefault(timestamp, Tick())
            if product in tick.order_depths:
                raise ValueError(f"Duplicate price row for {product} at {timestamp}")

            depth = OrderDepth()
            for level in range(1, 4):
                bid_price = _optional_integer(row.get(f"bid_price_{level}"), "bid price")
                bid_volume = _optional_integer(row.get(f"bid_volume_{level}"), "bid volume")
                ask_price = _optional_integer(row.get(f"ask_price_{level}"), "ask price")
                ask_volume = _optional_integer(row.get(f"ask_volume_{level}"), "ask volume")
                if (bid_price is None) != (bid_volume is None):
                    raise ValueError(f"Incomplete bid level {level} for {product} at {timestamp}")
                if (ask_price is None) != (ask_volume is None):
                    raise ValueError(f"Incomplete ask level {level} for {product} at {timestamp}")
                if bid_price is not None and bid_volume is not None:
                    if bid_volume <= 0:
                        raise ValueError(f"Invalid bid volume for {product} at {timestamp}")
                    depth.buy_orders[bid_price] = bid_volume
                if ask_price is not None and ask_volume is not None:
                    if ask_volume <= 0:
                        raise ValueError(f"Invalid ask volume for {product} at {timestamp}")
                    depth.sell_orders[ask_price] = -ask_volume

            tick.order_depths[product] = depth
            tick.mid_prices[product] = float(row["mid_price"])

    with trades_path.open(encoding="utf-8", newline="") as trades_file:
        reader = csv.DictReader(trades_file, delimiter=";")
        required = {"timestamp", "symbol", "price", "quantity"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"Unexpected trades CSV columns in {trades_path}")

        for row in reader:
            timestamp = _integer(row["timestamp"], "trade timestamp")
            if timestamp not in ticks:
                raise ValueError(f"Trade timestamp {timestamp} has no market snapshot")
            trade = Trade(
                row["symbol"],
                _integer(row["price"], "trade price"),
                _integer(row["quantity"], "trade quantity"),
                row.get("buyer", "") or "",
                row.get("seller", "") or "",
                timestamp,
            )
            if trade.quantity <= 0:
                raise ValueError(f"Invalid trade quantity at {timestamp}")
            ticks[timestamp].market_trades.setdefault(trade.symbol, []).append(trade)

    if not ticks:
        raise ValueError(f"No market snapshots found in {prices_path}")
    return dict(sorted(ticks.items()))


def load_trader(round_num: int) -> tuple[TraderProtocol, dict[str, int]]:
    strategy_dir = PROJECT_ROOT / "src" / "algorithms" / f"round_{round_num}"
    module_path = strategy_dir / "trader.py"
    if not module_path.is_file():
        raise ValueError(f"No built-in strategy for round {round_num}")

    datamodel_dir = PROJECT_ROOT / "src" / "algorithms" / "round_1"
    datamodel_path = str(datamodel_dir)
    if datamodel_path not in sys.path:
        sys.path.insert(0, datamodel_path)
    module_spec = importlib.util.spec_from_file_location(
        f"tradetell_round_{round_num}_trader", module_path
    )
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"Could not load strategy from {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    trader_type = getattr(module, "Trader", None)
    if not isinstance(trader_type, type):
        raise ValueError(f"{module_path} must define a Trader class")
    trader = cast(TraderProtocol, trader_type())
    raw_limits = getattr(module, "POSITION_LIMIT", {})
    limits = {str(product): int(limit) for product, limit in raw_limits.items()}
    return trader, limits


def _fill_order(
    order: Order,
    depth: OrderDepth,
    market_trades: list[MarketTrade],
    match_trades: str,
    timestamp: int,
    position: dict[str, int],
    cash: dict[str, float],
) -> list[Trade]:
    symbol = order.symbol
    remaining = abs(order.quantity)
    fills: list[Trade] = []

    def record(price: int, quantity: int, buyer: str, seller: str) -> None:
        nonlocal remaining
        fills.append(Trade(symbol, price, quantity, buyer, seller, timestamp))
        signed_quantity = quantity if order.quantity > 0 else -quantity
        position[symbol] = position.get(symbol, 0) + signed_quantity
        cash[symbol] = cash.get(symbol, 0.0) - signed_quantity * price
        remaining -= quantity

    if order.quantity > 0:
        for price in sorted(depth.sell_orders):
            if price > order.price or remaining <= 0:
                break
            available = -depth.sell_orders[price]
            quantity = min(remaining, available)
            if quantity:
                record(price, quantity, "SUBMISSION", "")
                if quantity == available:
                    del depth.sell_orders[price]
                else:
                    depth.sell_orders[price] += quantity
        if match_trades != "none" and remaining > 0:
            for market_trade in market_trades:
                price = market_trade.trade.price
                if market_trade.sell_remaining <= 0 or price > order.price:
                    continue
                if price == order.price and match_trades == "worse":
                    continue
                quantity = min(remaining, market_trade.sell_remaining)
                record(order.price, quantity, "SUBMISSION", market_trade.trade.seller)
                market_trade.sell_remaining -= quantity
                if remaining <= 0:
                    break
    else:
        for price in sorted(depth.buy_orders, reverse=True):
            if price < order.price or remaining <= 0:
                break
            available = depth.buy_orders[price]
            quantity = min(remaining, available)
            if quantity:
                record(price, quantity, "", "SUBMISSION")
                if quantity == available:
                    del depth.buy_orders[price]
                else:
                    depth.buy_orders[price] -= quantity
        if match_trades != "none" and remaining > 0:
            for market_trade in market_trades:
                price = market_trade.trade.price
                if market_trade.buy_remaining <= 0 or price < order.price:
                    continue
                if price == order.price and match_trades == "worse":
                    continue
                quantity = min(remaining, market_trade.buy_remaining)
                record(order.price, quantity, market_trade.trade.buyer, "SUBMISSION")
                market_trade.buy_remaining -= quantity
                if remaining <= 0:
                    break

    return fills


def run_day(
    round_num: int,
    prices_path: Path,
    trades_path: Path,
    trader: TraderProtocol,
    position_limits: dict[str, int],
    match_trades: str,
) -> dict[str, object]:
    if match_trades not in {"all", "worse", "none"}:
        raise ValueError(f"Unsupported trade matching mode: {match_trades}")

    day_match = re.search(r"_day_(-?\d+)\.csv$", prices_path.name)
    if day_match is None:
        raise ValueError(f"Could not read day number from {prices_path.name}")
    day_num = int(day_match.group(1))
    ticks = read_day(prices_path, trades_path)
    positions: dict[str, int] = {}
    cash: dict[str, float] = defaultdict(float)
    own_trades: dict[str, list[Trade]] = {}
    market_trades_state: dict[str, list[Trade]] = {}
    trader_data = ""
    latest_mid: dict[str, float] = {}
    max_positions: dict[str, int] = defaultdict(int)
    peak_equity = 0.0
    max_drawdown = 0.0
    position_limit_rejections = 0
    fill_count = 0
    traded_volume = 0
    submitted_orders = 0

    for timestamp, tick in ticks.items():
        market_trades = {
            product: [MarketTrade(trade, trade.quantity, trade.quantity) for trade in trades]
            for product, trades in tick.market_trades.items()
        }
        state = TradingState(
            traderData=trader_data,
            timestamp=timestamp,
            listings={product: Listing(product, product, 1) for product in tick.order_depths},
            order_depths=tick.order_depths,
            own_trades=own_trades,
            market_trades=market_trades_state,
            position=positions,
            observations=Observation({}, {}),
        )
        with contextlib.redirect_stdout(io.StringIO()):
            orders, conversions, trader_data = trader.run(state)
        if conversions != 0:
            raise ValueError("Conversion orders are not supported by the historical CSV replay")

        submitted_orders += sum(len(product_orders) for product_orders in orders.values())
        next_own_trades: dict[str, list[Trade]] = {}
        for product, depth in tick.order_depths.items():
            product_orders = orders.get(product, [])
            for order in product_orders:
                if not isinstance(order.price, int) or not isinstance(order.quantity, int):
                    raise ValueError(f"Trader returned a non-integer order for {product}")
            limit = position_limits.get(product, DEFAULT_POSITION_LIMIT)
            buy_quantity = sum(order.quantity for order in product_orders if order.quantity > 0)
            sell_quantity = sum(-order.quantity for order in product_orders if order.quantity < 0)
            if (
                positions.get(product, 0) + buy_quantity > limit
                or positions.get(product, 0) - sell_quantity < -limit
            ):
                position_limit_rejections += 1
                continue

            fills: list[Trade] = []
            for order in product_orders:
                fills.extend(
                    _fill_order(
                        order,
                        depth,
                        market_trades.get(product, []),
                        match_trades,
                        timestamp,
                        positions,
                        cash,
                    )
                )
            if fills:
                next_own_trades[product] = fills
                fill_count += len(fills)
                traded_volume += sum(trade.quantity for trade in fills)

        own_trades = next_own_trades
        next_market_trades = {product: [] for product in tick.order_depths}
        for product, trades in market_trades.items():
            remaining_trades = []
            for market_trade in trades:
                remaining_quantity = min(market_trade.buy_remaining, market_trade.sell_remaining)
                if remaining_quantity > 0:
                    original = market_trade.trade
                    remaining_trades.append(
                        Trade(
                            original.symbol,
                            original.price,
                            remaining_quantity,
                            original.buyer,
                            original.seller,
                            original.timestamp,
                        )
                    )
            next_market_trades[product] = remaining_trades
        market_trades_state = next_market_trades
        latest_mid.update(tick.mid_prices)
        for product, position in positions.items():
            max_positions[product] = max(max_positions[product], abs(position))
        equity = sum(cash.values()) + sum(
            position * latest_mid.get(product, 0.0) for product, position in positions.items()
        )
        peak_equity = max(peak_equity, equity)
        max_drawdown = max(max_drawdown, peak_equity - equity)

    products = sorted(latest_mid)
    product_pnl = {
        product: cash.get(product, 0.0) + positions.get(product, 0) * latest_mid[product]
        for product in products
    }
    return {
        "round": round_num,
        "day": day_num,
        "total_pnl": round(sum(product_pnl.values()), 2),
        "product_pnl": {product: round(pnl, 2) for product, pnl in product_pnl.items()},
        "max_drawdown": round(max_drawdown, 2),
        "max_abs_position": {product: max_positions.get(product, 0) for product in products},
        "ending_position": {product: positions.get(product, 0) for product in products},
        "position_limit_rejections": position_limit_rejections,
        "submitted_orders": submitted_orders,
        "fills": fill_count,
        "traded_volume": traded_volume,
    }


def run_round(round_num: int, day_num: int | None, match_trades: str) -> dict[str, object]:
    data_dir = ROUND_DATA_DIRS.get(round_num)
    if data_dir is None:
        raise ValueError(f"Historical replay data is available for rounds 1 and 2, not {round_num}")
    if day_num is None:
        price_files = sorted(
            data_dir.glob(f"prices_round_{round_num}_day_*.csv"),
            key=lambda path: int(re.search(r"_day_(-?\d+)\.csv$", path.name).group(1)),
        )
    else:
        price_files = [data_dir / f"prices_round_{round_num}_day_{day_num}.csv"]
    if not price_files or any(not path.is_file() for path in price_files):
        raise FileNotFoundError(f"No price data found for round {round_num} day {day_num}")

    results = []
    for prices_path in price_files:
        day_match = re.search(r"_day_(-?\d+)\.csv$", prices_path.name)
        if day_match is None:
            raise ValueError(f"Could not read day number from {prices_path.name}")
        day = int(day_match.group(1))
        trades_path = data_dir / f"trades_round_{round_num}_day_{day}.csv"
        if not trades_path.is_file():
            raise FileNotFoundError(f"No trade data found for round {round_num} day {day}")
        trader, limits = load_trader(round_num)
        results.append(run_day(round_num, prices_path, trades_path, trader, limits, match_trades))

    return {
        "strategy": f"built-in round {round_num} Trader",
        "matching_mode": match_trades,
        "fill_assumptions": {
            "displayed_book": "marketable orders fill at the opposing displayed price",
            "public_trades": "worse fills only when public trades pass the resting quote; all also includes equal prices",
            "queue_priority": "not modeled",
            "conversions_and_market_access_bids": "not modeled",
        },
        "days": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay a built-in strategy against historical CSV data."
    )
    parser.add_argument("--round", type=int, choices=(1, 2), default=1)
    parser.add_argument(
        "--day", type=int, help="Replay one day. By default, replay every available day."
    )
    parser.add_argument("--match-trades", choices=("all", "worse", "none"), default="worse")
    args = parser.parse_args()
    print(json.dumps(run_round(args.round, args.day, args.match_trades), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
