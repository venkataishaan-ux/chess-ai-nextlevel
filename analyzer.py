from io import StringIO
import chess
import chess.pgn


def classify_move(before, played_info, best_info, mover):
    played = played_info["score_cp"]
    best = best_info["score_cp"]

    # Score is from the side-to-move perspective on each position.
    loss = best - played

    if loss >= 250:
        label = "Blunder"
    elif loss >= 100:
        label = "Mistake"
    elif loss >= 50:
        label = "Inaccuracy"
    elif played >= best - 20:
        label = "Excellent"
    else:
        label = "Good"

    return {
        "label": label,
        "eval_loss_cp": loss,
        "best_move": best_info["best_move"],
        "played_move": played_info.get("played_move"),
        "player": "White" if mover == chess.WHITE else "Black",
    }


def analyze_game(pgn_text, engine, depth=14):
    game = chess.pgn.read_game(StringIO(pgn_text))
    if game is None:
        raise ValueError("Could not parse the PGN.")

    board = game.board()
    rows = []
    critical = []

    for ply, move in enumerate(game.mainline_moves(), start=1):
        mover = board.turn
        before = board.copy()

        best_info = engine.analyze(before, depth)
        played_san = before.san(move)

        board.push(move)
        after_info = engine.analyze(board, depth)

        # Re-evaluate the played move from the mover's perspective.
        played_score = -after_info["score_cp"]
        played_info = {
            "score_cp": played_score,
            "played_move": move.uci(),
        }

        item = classify_move(
            before,
            played_info,
            best_info,
            mover,
        )
        item.update({
            "ply": ply,
            "san": played_san,
            "fen": before.fen(),
            "after_fen": board.fen(),
            "best_pv": best_info["pv"],
            "best_score": best_info["score_cp"],
        })

        rows.append(item)
        if item["label"] in {"Blunder", "Mistake", "Inaccuracy"}:
            critical.append(item)

    return {
        "headers": dict(game.headers),
        "moves": rows,
        "critical": critical,
        "summary": build_summary(rows),
    }


def build_summary(rows):
    counts = {}
    for row in rows:
        counts[row["label"]] = counts.get(row["label"], 0) + 1

    return {
        "move_count": len(rows),
        "counts": counts,
        "biggest_issue": max(
            rows,
            key=lambda x: x["eval_loss_cp"],
            default=None,
        ),
    }
