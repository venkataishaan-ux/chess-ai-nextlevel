import chess

from analyzer import build_explanation, build_summary


def test_summary_counts():
    rows = [
        {"label": "Good", "eval_loss_cp": 0},
        {"label": "Blunder", "eval_loss_cp": 300},
        {"label": "Mistake", "eval_loss_cp": 120},
    ]
    summary = build_summary(rows)

    assert summary["move_count"] == 3
    assert summary["counts"]["Blunder"] == 1
    assert summary["biggest_issue"]["label"] == "Blunder"


def test_build_explanation_has_coaching_fields():
    before = chess.Board()
    move = chess.Move.from_uci("e2e4")
    after = before.copy()
    after.push(move)
    best_info = {
        "best_move": "e2e4",
        "pv": ["e2e4", "e7e5", "g1f3"],
    }
    item = {
        "label": "Excellent",
        "eval_loss_cp": 0,
        "player": "White",
        "san": "e4",
    }

    explanation = build_explanation(before, move, after, item, best_info)

    assert explanation["best_move_san"] == "e4"
    assert explanation["lesson"]
    assert explanation["why"]
    assert explanation["move_facts"]["piece"] == "P"
