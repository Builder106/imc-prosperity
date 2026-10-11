import csv

import pytest
from src.algorithms.round_1.datamodel import Order, OrderDepth, Trade, TradingState
from src.evaluation.strategy_replay import MarketTrade, _fill_order, read_day, run_day


@pytest.fixture
def market_files(tmp_path):
    prices = tmp_path / "prices_round_1_day_0.csv"
    trades = tmp_path / "trades_round_1_day_0.csv"
    columns = [
        "timestamp",
        "product",
        "mid_price",
        "bid_price_1",
        "bid_volume_1",
        "ask_price_1",
        "ask_volume_1",
    ]
    with prices.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(columns)
        writer.writerows([[100, "X", 100, 99, 4, 101, 3], [0, "X", 100, 99, 4, 101, 3]])
    trades.write_text(
        "timestamp;symbol;price;quantity;buyer;seller\n0;X;98;2;B;S\n", encoding="utf-8"
    )
    return prices, trades


def test_parser_sorts_ticks_and_preserves_order_book_volume_signs(market_files):
    ticks = read_day(*market_files)
    assert list(ticks) == [0, 100]
    assert ticks[0].order_depths["X"].buy_orders == {99: 4}
    assert ticks[0].order_depths["X"].sell_orders == {101: -3}
    assert ticks[0].market_trades["X"][0].quantity == 2


@pytest.mark.parametrize(
    ("data", "error"),
    [
        ("timestamp;symbol;price;quantity\n50;X;98;2\n", "no market snapshot"),
        ("timestamp;symbol;price;quantity\n0;X;98;0\n", "Invalid trade quantity"),
        ("timestamp;symbol;price;quantity\n0;X;98;1.5\n", "Expected an integer"),
    ],
)
def test_parser_rejects_invalid_trades(market_files, data, error):
    prices, trades = market_files
    trades.write_text(data, encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        read_day(prices, trades)


@pytest.mark.parametrize("side", [1, -1])
def test_marketable_fills_consume_book_liquidity_once_and_update_cash(side):
    depth = OrderDepth()
    depth.buy_orders = {99: 3}
    depth.sell_orders = {101: -3}
    positions, cash = {}, {}
    order = Order("X", 101 if side > 0 else 99, side * 5)
    fills = _fill_order(order, depth, [], "none", 0, positions, cash)
    assert sum(fill.quantity for fill in fills) == 3
    assert positions == {"X": side * 3}
    assert cash == {"X": -side * 3 * order.price}
    assert not _fill_order(order, depth, [], "none", 0, positions, cash)


@pytest.mark.parametrize("side", [1, -1])
@pytest.mark.parametrize(
    ("mode", "equal_fills"), [("none", False), ("worse", False), ("all", True)]
)
def test_public_trade_modes_and_shared_liquidity(side, mode, equal_fills):
    trade = MarketTrade(Trade("X", 100, 2, "B", "S", 0), 2, 2)
    depth = OrderDepth()
    positions, cash = {}, {}
    order = Order("X", 100, side * 5)
    fills = _fill_order(order, depth, [trade], mode, 0, positions, cash)
    assert sum(fill.quantity for fill in fills) == (2 if equal_fills else 0)
    if equal_fills:
        assert not _fill_order(order, depth, [trade], mode, 0, positions, cash)
    elif mode == "worse":
        order.price += side
        fills = _fill_order(order, depth, [trade], mode, 0, positions, cash)
        assert sum(fill.quantity for fill in fills) == 2
        assert cash == {"X": -side * 2 * order.price}


class ScriptedTrader:
    def __init__(self, quantity: int):
        self.quantity = quantity
        self.seen_trades: list[dict[str, list[Trade]]] = []
        self.seen_positions: list[dict[str, int]] = []
        self.seen_data: list[str] = []

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        self.seen_trades.append(state.market_trades)
        self.seen_positions.append(state.position.copy())
        self.seen_data.append(state.traderData)
        return {"X": [Order("X", 101, self.quantity)]}, 0, "saved"


def test_replay_marks_inventory_and_exposes_previous_tick_trades_only(market_files):
    trader = ScriptedTrader(2)
    prices, trades = market_files
    result = run_day(1, prices, trades, trader, {"X": 10}, "none")
    assert trader.seen_positions == [{}, {"X": 2}]
    assert trader.seen_data == ["", "saved"]
    assert trader.seen_trades[0] == {}
    assert trader.seen_trades[1]["X"][0].timestamp == 0
    assert result["ending_position"] == {"X": 4}
    assert result["total_pnl"] == -4
    assert result["max_drawdown"] == 4
    assert result["max_abs_position"] == {"X": 4}


def test_replay_rejects_orders_that_could_breach_limits(market_files):
    prices, trades = market_files
    result = run_day(1, prices, trades, ScriptedTrader(5), {"X": 4}, "none")
    assert result["fills"] == 0
    assert result["position_limit_rejections"] == 2
    assert result["total_pnl"] == 0
