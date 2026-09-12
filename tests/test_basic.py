import chess

from analyzer import classify_move, _move_facts


def test_classification_thresholds():
    assert classify_move(0, is_best=True) == "Good"
    assert classify_move(49, is_best=False) == "Good"
    assert classify_move(50, is_best=False) == "Inaccuracy"
    assert classify_move(100, is_best=False) == "Mistake"
    assert classify_move(200, is_best=False) == "Blunder"


def test_brilliant_requires_best_capture_sacrifice():
    board = chess.Board("4k3/8/8/8/8/8/4P3/4R1K1 w - - 0 1")
    move = chess.Move.from_uci("e1e8")
    # This is only testing the classifier's contract, not engine strength.
    assert classify_move(0, is_best=True, is_sacrifice=True) == "Brilliant"


def test_move_facts_capture_and_check():
    board = chess.Board()
    move = chess.Move.from_uci("e2e4")
    after = board.copy(); after.push(move)
    facts = _move_facts(board, move, after)
    assert facts["piece"] == "P"
    assert facts["capture"] is False
    assert facts["check"] is False
