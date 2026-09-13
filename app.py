from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename
from pathlib import Path
from io import StringIO
import chess
import chess.pgn

from analyzer import analyze_game
from chess_engine import StockfishEngine

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
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

@app.post('/api/profile')
def profile():
    data = request.get_json(silent=True) or {}
    games = data.get('games') or []
    counts = {'games': len(games), 'blunders': 0, 'mistakes': 0, 'inaccuracies': 0, 'brilliant': 0, 'good': 0}
    for game in games:
        for move in game.get('moves', []):
            label = move.get('label', '').lower()
            if label == 'blunder': counts['blunders'] += 1
            elif label == 'mistake': counts['mistakes'] += 1
            elif label == 'inaccuracy': counts['inaccuracies'] += 1
            elif label == 'brilliant': counts['brilliant'] += 1
            elif label == 'good': counts['good'] += 1
    total = sum(counts[k] for k in ('blunders','mistakes','inaccuracies','brilliant','good')) or 1
    accuracy = round(100 * (counts['good'] + counts['brilliant']) / total)
    return jsonify({'counts': counts, 'estimated_skills': {
        'Tactics': max(400, min(2400, 900 + counts['brilliant']*35 - counts['blunders']*18)),
        'Calculation': max(400, min(2400, 900 + counts['brilliant']*25 - counts['mistakes']*12)),
        'Defense': max(400, min(2400, 900 - counts['blunders']*15)),
        'Opening': max(400, min(2400, 1000 + accuracy*4)),
        'Middlegame': max(400, min(2400, 900 + accuracy*5)),
        'Endgame': max(400, min(2400, 950 + accuracy*4)),
        'Threat Detection': max(400, min(2400, 850 - counts['blunders']*10)),
        'King Safety': max(400, min(2400, 900 - counts['mistakes']*8)),
        'Conversion': max(400, min(2400, 900 + accuracy*3)),
    }, 'note': 'These are rough coaching indicators, not official Elo ratings.'})


@app.post('/api/roast')
def roast():
    data = request.get_json(silent=True) or {}
    label = str(data.get('label', 'mistake')).lower()
    san = data.get('san', 'that move')
    intensity = str(data.get('intensity', 'playful')).lower()
    lines = {
        'blunder': 'That move donated material to the opponent. The chessboard is not a charity drive.',
        'mistake': 'That move had the confidence of a grandmaster and the calculation of a sleepy toaster.',
        'inaccuracy': 'A little wobbly. The position asked for precision, and this move brought vibes.',
        'good': 'Solid move. The chess gremlins approve.',
        'brilliant': 'Okay, tactical chef, that was genuinely spicy.'
    }
    roast_text = lines.get(label, 'The move was certainly a decision.')
    if intensity == 'gentle': roast_text = roast_text.split('.')[0] + '.'
    return jsonify({"roast": roast_text, "advice": f"Before playing {san}, check your opponent\'s forcing moves: checks, captures, and threats. Then compare the candidate moves."})

@app.post('/api/screenshot')
def screenshot_input():
    file = request.files.get('image')
    if not file or not file.filename:
        return jsonify({'error': 'Upload a screenshot first.'}), 400
    name = secure_filename(file.filename)
    if not name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        return jsonify({'error': 'Use PNG, JPG, JPEG, or WEBP.'}), 400
    raw = file.read()
    if not raw:
        return jsonify({'error': 'The uploaded image is empty.'}), 400
    # Vision/OCR provider hook. A real model can be connected here later.
    return jsonify({'status': 'received', 'filename': name, 'message': 'Screenshot received. Vision/OCR is not configured yet; paste the detected FEN or PGN for exact reconstruction.', 'fen': None, 'pgn': None}), 200
