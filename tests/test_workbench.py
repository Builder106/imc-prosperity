from src.ui.workbench import (
    DAYS,
    OSMIUM,
    PEPPER,
    day_summary,
    overview,
    parse_params,
    place_params,
    replay_payload,
)


def test_params_fall_back_to_safe_defaults():
    parsed = parse_params({"layer": "vault", "day": "9", "t": "abc", "trader": "7", "match": "x"})
    assert parsed["layer"] == "ground"
    assert parsed["place"] == {"zoom": None, "day": 1, "t": 500000}
    assert parsed["replay"] == {"trader": 1, "day": 0, "match": "worse"}


def test_params_keep_a_valid_place_and_round_t_to_a_tick():
    parsed = parse_params(
        {
            "layer": "trader",
            "zoom": "-1",
            "day": "-1",
            "t": "41234",
            "rday": "1",
            "trader": "2",
            "match": "all",
        }
    )
    assert parsed["layer"] == "trader"
    assert parsed["place"] == {"zoom": -1, "day": -1, "t": 41200}
    assert parsed["replay"] == {"trader": 2, "day": 1, "match": "all"}
    assert place_params(parsed["place"]) == {"day": "-1", "t": "41200", "zoom": "-1"}
    assert place_params({"zoom": None, "day": 0, "t": 0}) == {"day": "0", "t": "0"}


def test_record_shows_the_root_growing_and_osmium_holding():
    summaries = [day_summary(day) for day in DAYS]
    pepper_open = summaries[0]["goods"][PEPPER]["open"]
    pepper_close = summaries[-1]["goods"][PEPPER]["close"]
    assert 3900 < pepper_close - pepper_open < 4100
    for summary in summaries:
        osmium = summary["goods"][OSMIUM]
        assert 9950 < osmium["low"] <= osmium["high"] < 10050


def test_replay_payload_traces_a_full_day():
    payload = replay_payload(1, 0, "worse")
    assert payload["day"] == 0
    assert len(payload["equity"]) == 10000
    assert payload["fills"] == len(payload["fill_log"])
    assert payload["total_pnl"] == round(sum(payload["product_pnl"].values()), 2)


def test_overview_samples_both_goods_across_the_record():
    record = overview(stride=100)
    assert record["stride"] == 100
    assert len(record["pepper"]) == len(record["osmium"]) == 400
    first, last = record["pepper"][0], record["pepper"][-1]
    assert first is not None
    assert last is not None
    assert first < 10100
    assert last > 13900
