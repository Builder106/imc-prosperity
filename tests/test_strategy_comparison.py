import csv
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from src.algorithms.round_1.datamodel import Order, TradingState
from src.evaluation import (
    CandidateStrategy,
    compare_candidate_strategies,
    format_comparison_table,
    load_trader,
    load_trader_factory,
    resolve_candidate,
)
from src.evaluation.strategy_replay import ROUND_DATA_DIRS


class ScriptedTrader:
    def __init__(self, quantity: int = 2):
        self.quantity = quantity

    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:
        return {"X": [Order("X", 101, self.quantity)]}, 0, ""


@pytest.fixture
def mock_round_data(tmp_path: Path):
    r1_dir = tmp_path / "ROUND1"
    r2_dir = tmp_path / "ROUND_2"
    r1_dir.mkdir()
    r2_dir.mkdir()

    cols = [
        "timestamp",
        "product",
        "mid_price",
        "bid_price_1",
        "bid_volume_1",
        "ask_price_1",
        "ask_volume_1",
    ]
    for r_dir, r_num, days in [(r1_dir, 1, [-2, -1, 0]), (r2_dir, 2, [-1, 0, 1])]:
        for day in days:
            p_file = r_dir / f"prices_round_{r_num}_day_{day}.csv"
            t_file = r_dir / f"trades_round_{r_num}_day_{day}.csv"
            with p_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(cols)
                writer.writerow([0, "X", 100, 99, 4, 101, 3])
            t_file.write_text("timestamp;symbol;price;quantity;buyer;seller\n", encoding="utf-8")

    return {1: r1_dir, 2: r2_dir}


def test_resolve_candidate_builtin_and_instance():
    c1 = resolve_candidate(1)
    assert c1.name == "round_1"
    assert callable(c1.factory)

    c2 = resolve_candidate("round_2")
    assert c2.name == "round_2"

    c_direct = CandidateStrategy(name="custom", factory=lambda: ScriptedTrader(1))
    assert resolve_candidate(c_direct) is c_direct


def test_resolve_candidate_file_and_errors(tmp_path: Path):
    strategy_file = tmp_path / "my_custom_trader.py"
    strategy_file.write_text(
        "POSITION_LIMIT = {'X': 15}\n"
        "class Trader:\n"
        "    def run(self, state):\n"
        "        return {}, 0, ''\n",
        encoding="utf-8",
    )
    resolved = resolve_candidate(strategy_file)
    assert resolved.name == "my_custom_trader"
    assert resolved.position_limits == {"X": 15}

    with pytest.raises(FileNotFoundError, match="not found"):
        resolve_candidate(tmp_path / "nonexistent.py")

    with pytest.raises(TypeError, match="Unsupported candidate strategy type"):
        resolve_candidate(3.14)  # type: ignore[arg-type]


def test_load_trader_and_factory():
    factory, limits = load_trader_factory(1)
    trader1 = factory()
    trader2 = factory()
    assert trader1 is not trader2
    assert "ASH_COATED_OSMIUM" in limits

    trader_inst, limits_inst = load_trader(2)
    assert hasattr(trader_inst, "run")
    assert limits_inst == limits

    with pytest.raises(ValueError, match="No built-in strategy"):
        load_trader_factory(99)


def test_compare_candidate_strategies_mock_data(mock_round_data: dict[int, Path]):
    cand1 = CandidateStrategy("buyer_1", lambda: ScriptedTrader(1), {"X": 10})
    cand2 = CandidateStrategy("buyer_2", lambda: ScriptedTrader(2), {"X": 10})

    result = compare_candidate_strategies(
        candidates=[cand1, cand2],
        rounds=[1, 2],
        held_out_rounds=[2],
        held_out_days=[0, 1],
        match_trades="none",
        data_dirs=mock_round_data,
    )

    assert result["matching_mode"] == "none"
    assert result["partitions"]["evaluated_rounds"] == [1, 2]
    assert result["partitions"]["held_out_rounds"] == [2]
    assert result["partitions"]["held_out_days"] == [0, 1]

    assert len(result["candidates"]) == 2
    buyer1_metrics = result["candidates"]["buyer_1"]["metrics"]
    buyer2_metrics = result["candidates"]["buyer_2"]["metrics"]

    assert buyer1_metrics["overall"]["day_count"] == 6
    assert buyer2_metrics["overall"]["day_count"] == 6

    # buyer2 bought 2 each day at 101, mid was 100, so pnl per day is -2.0
    # buyer1 bought 1 each day at 101, mid was 100, so pnl per day is -1.0
    assert buyer1_metrics["overall"]["total_pnl"] == -6.0
    assert buyer2_metrics["overall"]["total_pnl"] == -12.0

    # buyer1 has higher held-out pnl than buyer2 (-4.0 vs -8.0)
    assert result["rankings"]["by_held_out_pnl"] == ["buyer_1", "buyer_2"]
    assert result["rankings"]["by_overall_pnl"] == ["buyer_1", "buyer_2"]


def test_compare_candidate_strategies_validation():
    with pytest.raises(ValueError, match="Unsupported trade matching mode"):
        compare_candidate_strategies(match_trades="invalid")

    with pytest.raises(ValueError, match="At least one candidate strategy"):
        compare_candidate_strategies(candidates=[])

    with pytest.raises(ValueError, match="At least one round"):
        compare_candidate_strategies(rounds=[])

    with pytest.raises(ValueError, match="Historical replay data is available"):
        compare_candidate_strategies(rounds=[5])


def test_compare_candidate_strategies_live_round1(mock_round_data: dict[int, Path]):
    data_dirs = None if ROUND_DATA_DIRS[1].is_dir() else mock_round_data
    result = compare_candidate_strategies(
        candidates=["round_1", "round_2"],
        rounds=[1],
        held_out_rounds=[],
        held_out_days=[0],
        match_trades="worse",
        data_dirs=data_dirs,
    )

    assert result["partitions"]["evaluated_rounds"] == [1]
    assert result["partitions"]["held_out_days"] == [0]
    assert "round_1" in result["candidates"]
    assert "round_2" in result["candidates"]

    summaries = result["comparison_summary"]
    assert len(summaries) == 2
    assert summaries[0]["rank_held_out"] in {1, 2}

    table = format_comparison_table(result)
    assert "round_1" in table
    assert "round_2" in table
    assert "Overall P&L" in table


def test_format_comparison_table_empty():
    assert format_comparison_table({}) == "No candidate strategies evaluated."


def test_main_cli_table(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    mock_round_data: dict[int, Path],
):
    if not ROUND_DATA_DIRS[1].is_dir():
        monkeypatch.setattr("src.evaluation.strategy_comparison.ROUND_DATA_DIRS", mock_round_data)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "strategy_comparison",
            "--rounds",
            "1",
            "--held-out-days",
            "0",
            "--held-out-rounds",
            "--format",
            "table",
        ],
    )
    from src.evaluation.strategy_comparison import main

    main()
    captured = capsys.readouterr()
    assert "round_1" in captured.out
    assert "round_2" in captured.out
    assert "Held-Out P&L" in captured.out


def test_main_cli_json(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    mock_round_data: dict[int, Path],
):
    if not ROUND_DATA_DIRS[1].is_dir():
        monkeypatch.setattr("src.evaluation.strategy_comparison.ROUND_DATA_DIRS", mock_round_data)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "strategy_comparison",
            "--rounds",
            "1",
            "--held-out-days",
            "0",
            "--held-out-rounds",
            "--format",
            "json",
        ],
    )
    from src.evaluation.strategy_comparison import main

    main()
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "candidates" in data
    assert "rankings" in data


def test_strategy_replay_cli_compare(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(sys, "argv", ["strategy_replay", "--compare"])
    from src.evaluation.strategy_replay import main

    # Mock compare_candidate_strategies so test runs fast
    with patch(
        "src.evaluation.strategy_comparison.compare_candidate_strategies",
        return_value={"mock": "done"},
    ):
        main()

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data == {"mock": "done"}
