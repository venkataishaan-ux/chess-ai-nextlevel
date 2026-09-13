from __future__ import annotations

from io import StringIO
from typing import Any

import chess
import chess.pgn


# Centipawn-loss thresholds. These are deliberately conservative so the app
# does not manufacture blunders just to make a report look dramatic.
INACCURACY_CP = 50
MISTAKE_CP = 100
BLUNDER_CP = 200


def _score_cp(score: chess.engine.PovScore | Any, color: chess.Color) -> tuple[int | None, int | None]:
    """Return (centipawns, mate) from `color`'s point of view."""
    pov = score.pov(color)
    if pov.is_mate():
        mate = pov.mate()
        return None, mate
    return pov.score(mate_score=100000), None


def _score_label(cp: int | None, mate: int | None) -> str:
    if mate is not None:
        return f"M{mate:+d}"
    if cp is None:
        return "?"
    return f"{cp / 100:+.2f}"


def _relative_loss(before_score, after_score, mover: chess.Color) -> int:
    """Positive loss in centipawns from the mover's perspective."""
    before_cp, before_mate = _score_cp(before_score, mover)
    after_cp, after_mate = _score_cp(after_score, mover)

    # Mate transitions are handled with a large finite scale. A move that
    # loses a forced mate is therefore always treated as a major error.
    def value(cp, mate):
        if mate is not None:
            sign = 1 if mate > 0 else -1
            return sign * (100000 - min(abs(mate), 1000) * 100)
        return cp if cp is not None else 0

    return max(0, value(before_cp, before_mate) - value(after_cp, after_mate))


def _best_info(engine, board: chess.Board, depth: int):
    # Keep each engine call short enough for Render free instances. The
    # selected depth remains the requested ceiling, while chess_engine also
    # applies a small wall-clock limit.
    result = engine.analyse(board, depth=depth, multipv=1, time_limit=0.18)
    if isinstance(result, list):
        result = result[0]
    return result


def _pv_san(board: chess.Board, pv, max_moves: int = 8) -> list[str]:
    temp = board.copy()
    out = []
    for move in (pv or [])[:max_moves]:
        if move not in temp.legal_moves:
            break
        out.append(temp.san(move))
        temp.push(move)
    return out


def _move_facts(before: chess.Board, move: chess.Move, after: chess.Board) -> dict[str, Any]:
    piece = before.piece_at(move.from_square)
    captured = before.piece_at(move.to_square)
    en_passant = before.is_en_passant(move)
    if en_passant:
        captured = chess.Piece(chess.PAWN, not before.turn)
    return {
        "piece": piece.symbol() if piece else None,
        "piece_name": chess.piece_name(piece.piece_type) if piece else None,
        "capture": before.is_capture(move),
        "captured_piece": captured.symbol() if captured else None,
        "captured_piece_name": chess.piece_name(captured.piece_type) if captured else None,
        "check": after.is_check(),
        "checkmate": after.is_checkmate(),
        "castle": before.is_castling(move),
        "promotion": chess.piece_name(move.promotion) if move.promotion else None,
        "en_passant": en_passant,
    }


def _is_sacrifice(before: chess.Board, move: chess.Move, best_move: chess.Move | None) -> bool:
    if not best_move or move != best_move:
        return False
    if not before.is_capture(move):
        return False
    # A capture can be brilliant when the captured piece is substantially
    # cheaper than the attacking piece and the move is the engine's top move.
    attacker = before.piece_at(move.from_square)
    victim = before.piece_at(move.to_square)
    values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}
    return bool(attacker and victim and values[attacker.piece_type] > values[victim.piece_type])


def classify_move(loss_cp: int, *, is_best: bool, is_sacrifice: bool = False) -> str:
    if is_best and is_sacrifice:
        return "Brilliant"
    if loss_cp >= BLUNDER_CP:
        return "Blunder"
    if loss_cp >= MISTAKE_CP:
        return "Mistake"
    if loss_cp >= INACCURACY_CP:
        return "Inaccuracy"
    return "Good"


def _lesson_for(label: str, facts: dict[str, Any]) -> str:
    if label == "Blunder":
        return "Before committing, scan your opponent's forcing replies: checks, captures, and threats."
    if label == "Mistake":
        return "Compare the move with the opponent's strongest reply before playing it."
    if label == "Inaccuracy":
        return "Look for the most active or precise continuation instead of settling for the first playable move."
    if label == "Brilliant":
        return "This is a strong tactical decision. Notice what concrete calculation makes it work."
    if facts.get("check"):
        return "Checks can be useful, but keep checking whether the move improves the position after the forcing sequence ends."
    if facts.get("capture"):
        return "When you capture, recalculate the opponent's recapture and the resulting material balance."
    return "Good move. Keep checking the opponent's forcing options before your next decision."


def build_explanation(before: chess.Board, move: chess.Move, after: chess.Board, item: dict, best_info: dict) -> dict:
    facts = _move_facts(before, move, after)
    best_move = best_info.get("pv", [None])[0] if best_info.get("pv") else None
    best_san = before.san(best_move) if best_move and best_move in before.legal_moves else None
    played_san = before.san(move)
    label = item["label"]

    if label == "Blunder":
        headline = f"{played_san} drops a major amount of evaluation."
    elif label == "Mistake":
        headline = f"{played_san} gives the opponent a noticeably stronger position."
    elif label == "Inaccuracy":
        headline = f"{played_san} is playable, but Stockfish prefers a more precise move."
    elif label == "Brilliant":
        headline = f"{played_san} is a standout tactical decision."
    else:
        headline = f"{played_san} keeps the position under control."

    if best_san and best_san != played_san:
        why = f"Stockfish prefers {best_san}, which keeps a better evaluation for the player to move."
        missed = f"You missed the stronger continuation {best_san}."
    elif best_san:
        why = "You played Stockfish's top move in this position."
        missed = "No stronger engine move was identified at this depth."
    else:
        why = "The engine did not return a usable principal variation for this position."
        missed = "No specific alternative is available."

    return {
        "headline": headline,
        "why": why,
        "missed": missed,
        "lesson": _lesson_for(label, facts),
        "best_move_san": best_san,
        "move_facts": facts,
    }


def _parse_game(pgn_text: str) -> chess.pgn.Game:
    game = chess.pgn.read_game(StringIO(pgn_text))
    if game is None:
        raise ValueError("Could not parse the PGN.")
    return game


def analyze_game(pgn_text: str, engine, depth: int = 12) -> dict[str, Any]:
    game = _parse_game(pgn_text)
    # Render-safe ceiling. Depth is still user-selectable, but very deep
    # settings should not be allowed to monopolize a free web worker.
    depth = max(8, min(int(depth), 16))
    board = game.board()
    rows = []

    for ply, move in enumerate(game.mainline_moves(), start=1):
        before = board.copy()
        san = before.san(move)
        mover = before.turn

        before_info = _best_info(engine, before, depth)
        best_move = before_info.get("pv", [None])[0] if before_info.get("pv") else None
        best_score = before_info.get("score")

        board.push(move)
        after = board.copy()
        after_info = _best_info(engine, after, depth)
        after_score = after_info.get("score")

        loss = _relative_loss(best_score, after_score, mover)
        is_best = bool(best_move and move == best_move)
        facts = _move_facts(before, move, after)
        brilliant = _is_sacrifice(before, move, best_move)
        label = classify_move(loss, is_best=is_best, is_sacrifice=brilliant)

        item = {
            "ply": ply,
            "move_number": (ply + 1) // 2,
            "side": "White" if mover == chess.WHITE else "Black",
            "san": san,
            "uci": move.uci(),
            "label": label,
            "loss_cp": loss,
            "best_move_san": before.san(best_move) if best_move and best_move in before.legal_moves else None,
            "eval_before": _score_label(*_score_cp(best_score, mover)),
            "eval_after": _score_label(*_score_cp(after_score, mover)),
            "fen": after.fen(),
            "turning_point": False,
            "explanation": {},
        }
        item["explanation"] = build_explanation(before, move, after, item, before_info)
        rows.append(item)

    critical = [r for r in rows if r["label"] in {"Inaccuracy", "Mistake", "Blunder"}]
    blunders = [r for r in rows if r["label"] == "Blunder"]
    mistakes = [r for r in rows if r["label"] == "Mistake"]
    inaccuracies = [r for r in rows if r["label"] == "Inaccuracy"]
    brilliant = [r for r in rows if r["label"] == "Brilliant"]
    good = [r for r in rows if r["label"] == "Good"]

    # Turning points are the largest evaluation losses in the game. Keep the
    # signal sparse so a report does not call every imperfect move a turning point.
    ranked = sorted(rows, key=lambda r: r["loss_cp"], reverse=True)
    for row in ranked[:3]:
        if row["loss_cp"] >= MISTAKE_CP:
            row["turning_point"] = True
    turning_points = [r for r in rows if r["turning_point"]]

    worst = max(rows, key=lambda r: r["loss_cp"]) if rows else None
    best = next((r for r in rows if r["label"] == "Brilliant"), None)
    if best is None:
        best = max(rows, key=lambda r: -r["loss_cp"]) if rows else None

    return {
        "headers": dict(game.headers),
        "summary": {
            "total_moves": len(rows),
            "brilliant": len(brilliant),
            "good": len(good),
            "inaccuracies": len(inaccuracies),
            "mistakes": len(mistakes),
            "blunders": len(blunders),
        },
        "moves": rows,
        "critical": critical,
        "blunder_breakdown": [
            {
                "ply": r["ply"],
                "move_number": r["move_number"],
                "side": r["side"],
                "san": r["san"],
                "label": r["label"],
                "best_move": r["best_move_san"],
                "eval_before": r["eval_before"],
                "eval_after": r["eval_after"],
                "loss_cp": r["loss_cp"],
                "explanation": r["explanation"],
            }
            for r in blunders
        ],
        "turning_points": turning_points,
        "best_move": best,
        "worst_move": worst,
    }
