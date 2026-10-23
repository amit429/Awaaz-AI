from app.relay.call_analysis import facts_found, match_lines, similarity, timing_summary

LINES = [
    {
        "id": "A",
        "say_hi": "दस दिन की गोलियाँ, कुल चार सौ बीस रुपये होंगे।",
        "facts": [["420", "चार सौ बीस"]],
    },
    {"id": "B", "say_hi": "हाँ जी, शर्मा मेडिकल, बोलिए।", "facts": [["शर्मा"]]},
    {"id": "C", "say_hi": "ठीक है।", "facts": [["ठीक"]]},
]
CAPS = [
    {"text": "हाँ जी। शर्मा मेडिकल। बोलिए।", "fragments": 3},
    {"text": "दस दिन की गोलियाँ ₹420 होंगे।", "fragments": 1},
]


def test_similarity_and_facts():
    assert similarity("ठीक है।", "ठीक है") == 1.0
    assert facts_found("कुल ₹420 होंगे", [["420", "चार सौ बीस"]]) == 1
    assert facts_found("कुल पैसे होंगे", [["420"]]) == 0


def test_matching_is_order_independent_of_capture_order_and_reports_missing():
    rows = {r["id"]: r for r in match_lines(LINES, CAPS)}
    assert rows["A"]["facts"] == "1/1" and rows["A"]["fragments"] == 1
    assert rows["B"]["fragments"] == 3
    assert rows["C"]["heard"] is None


def test_timing_summary():
    ev = [
        {"t": 0, "type": "request"},
        {"t": 1, "type": "say"},
        {"t": 1.5, "type": "spoken"},
        {"t": 2, "type": "keeper"},
        {"t": 3, "type": "superseded"},
    ]
    s = timing_summary(ev)
    assert (
        s["say_to_spoken_median_s"] == 0.5
        and s["keeper_lines"] == 1
        and s["superseded_requests"] == 1
    )
