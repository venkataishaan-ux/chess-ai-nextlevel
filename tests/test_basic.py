from analyzer import build_summary


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
