from io import StringIO
import chess
import chess.pgn


def classify_move(before, played_info, best_info, mover):
    played = played_info["score_cp"]
    best = best_info["score_cp"]

    # Score is from the side-to-move perspective on each position.
    loss = max(0, best - played)

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


def _move_facts(before, move, after):
    piece = before.piece_at(move.from_square)
    captured = before.piece_at(move.to_square)
    return {
        "piece": piece.symbol().upper() if piece else "piece",
        "capture": before.is_capture(move),
        "captured_piece": captured.symbol().upper() if captured else None,
        "check": after.is_check(),
        "castle": before.is_castling(move),
        "promotion": move.promotion is not None,
    }


def _lesson_for(label, facts):
    if label == "Blunder":
        if facts["check"]:
            return "When you find a forcing move, calculate the opponent's strongest reply before committing."
        if facts["capture"]:
            return "Before every move, check whether the piece you are moving leaves something else hanging."
        return "Use Checks, Captures, Threats before moving. A quick blunder-check can prevent a large evaluation swing."

    if label == "Mistake":
        return "Look one move deeper: ask what your opponent can do immediately after your move."

    if label == "Inaccuracy":
        return "When several moves look playable, compare the opponent's threats and choose the move that improves your position most."

    if label == "Excellent":
        return "Keep looking for forcing moves and moves that improve your pieces while limiting the opponent's options."

    return "Keep checking your opponent's threats before you commit to your plan."


def build_explanation(before, move, after, item, best_info):
    facts = _move_facts(before, move, after)
    best_move = chess.Move.from_uci(best_info["best_move"])
    best_san = before.san(best_move)
    loss = item["eval_loss_cp"] / 100
    player = item["player"]

    if item["label"] in {"Good", "Excellent"}:
        opening = f"{player} played {item['san']}."
        if facts["check"]:
            opening += " The move gives check."
        elif facts["capture"]:
            opening += " The move wins or exchanges material by capturing."
        else:
            opening += " The move keeps the position on a strong track."
        why = f"Stockfish's top choice is {best_san}, and your move is within {loss:.2f} pawns of that choice."
    else:
        opening = f"{player} played {item['san']}, but Stockfish prefers {best_san}."
        if facts["check"]:
            opening += " Your move gives check, so it is forcing, but the engine still finds a stronger continuation."
        elif facts["capture"]:
            opening += " Your move captures, but the engine finds a more valuable way to handle the position."
        else:
            opening += " The move changes the position in a way that gives up part of the advantage or worsens the position."

        why = f"The engine estimates a loss of about {loss:.2f} pawns compared with its preferred move."

    if best_info["pv"]:
        pv_text = " ".join(best_info["pv"][:6])
        why += f" Its preferred line starts: {pv_text}."

    if item["label"] == "Blunder":
        missed = "The main thing to investigate is the opponent's immediate reply after your move."
    elif item["label"] == "Mistake":
        missed = "The key miss was the stronger defensive or attacking resource available in the position."
    elif item["label"] == "Inaccuracy":
        missed = "The position had a more precise option that preserved more of your advantage or reduced your risk."
    else:
        missed = "The move fits the position well according to the engine."

    return {
        "headline": opening,
        "why": why,
        "missed": missed,
        "lesson": _lesson_for(item["label"], facts),
        "best_move_san": best_san,
        "move_facts": facts,
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

        item = classify_move(before, played_info, best_info, mover)
        item.update({
            "ply": ply,
            "san": played_san,
            "fen": before.fen(),
            "after_fen": board.fen(),
            "best_pv": best_info["pv"],
            "best_score": best_info["score_cp"],
        })
        item["explanation"] = build_explanation(
            before,
            move,
            board,
            item,
            best_info,
        )

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
