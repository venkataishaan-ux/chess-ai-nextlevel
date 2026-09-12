from flask import Flask, jsonify, render_template, request
from io import StringIO
import chess
import chess.pgn

from analyzer import analyze_game
from chess_engine import StockfishEngine

app = Flask(__name__)
engine = StockfishEngine()


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/parse-pgn")
def parse_pgn():
    data = request.get_json(silent=True) or {}
    pgn_text = data.get("pgn", "").strip()
    if not pgn_text:
        return jsonify({"error": "Please provide a PGN."}), 400
    try:
        game = chess.pgn.read_game(StringIO(pgn_text))
        if game is None:
            raise ValueError("Could not parse the PGN.")
        board = game.board()
        moves = []
        for ply, move in enumerate(game.mainline_moves(), start=1):
            san = board.san(move)
            board.push(move)
            moves.append({
                "ply": ply,
                "move_number": (ply + 1) // 2,
                "side": "White" if board.turn == chess.BLACK else "Black",
                "san": san,
                "uci": move.uci(),
                "fen": board.fen(),
            })
        return jsonify({
            "headers": dict(game.headers),
            "initial_fen": game.board().fen(),
            "moves": moves,
            "final_fen": board.fen(),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.post("/api/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    pgn_text = data.get("pgn", "").strip()
    try:
        depth = max(8, min(int(data.get("depth", 14)), 24))
    except (TypeError, ValueError):
        depth = 14
    if not pgn_text:
        return jsonify({"error": "Please provide a PGN."}), 400
    try:
        return jsonify(analyze_game(pgn_text, engine, depth=depth))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@app.get("/api/engine-status")
def engine_status():
    return jsonify(engine.status())


if __name__ == "__main__":
    app.run(debug=True)
