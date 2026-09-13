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


ROAST_BANK = {
    'gentle': {
        'blunder': [
            'That move dropped material. Let’s slow down and check what is defended.',
            'The position had a small trap, and this move stepped right into it.',
            'A costly moment, but every blunder is a useful training clue.',
        ],
        'mistake': [
            'That move was playable-looking, but one more safety check would help.',
            'The idea was understandable. The calculation just needed one extra beat.',
            'A little too optimistic. Check the opponent’s reply before committing.',
        ],
        'inaccuracy': [
            'Slightly imprecise. A stronger move was hiding nearby.',
            'Not disastrous, just a small opportunity missed.',
            'The move works, but the position offered a cleaner option.',
        ],
        'good': ['Nice, sensible chess. Keep checking the opponent’s threats.'],
        'brilliant': ['Excellent find. That move spotted something important in the position.'],
    },
    'playful': {
        'blunder': [
            'That move donated material. The opponent should at least send a thank-you note.',
            'The chessboard just opened a lost-and-found department for your pieces.',
            'You played “surprise me” and unfortunately surprised your own army.',
            'That was not a sacrifice. That was a very generous subscription plan.',
            'Your piece has officially changed teams without telling you.',
        ],
        'mistake': [
            'That move had grandmaster confidence and calculator-battery percentage.',
            'The idea was spicy, but the position requested less hot sauce.',
            'You saw a plan. The board saw a plot twist.',
            'That move walked into the room before checking whether the room was safe.',
            'A decent idea wearing slightly mismatched shoes.',
        ],
        'inaccuracy': [
            'The move is legal, but the position wanted a little more seasoning.',
            'Not a disaster. Just a tiny tactical banana peel.',
            'The engine found a cleaner route. Your move took the scenic tour.',
            'A respectable move with one eyebrow raised by the chess gods.',
            'You were close. The position hid the answer behind a curtain.',
        ],
        'good': [
            'Solid move. The chess gremlins have temporarily approved your application.',
            'Clean and useful. No fireworks, just proper chess.',
            'Nice move. Your pieces are beginning to trust you again.',
        ],
        'brilliant': [
            'Okay, tactical chef, that was genuinely spicy.',
            'That move had main-character energy and actual calculation to back it up.',
            'Beautiful find. The opponent’s position just received a software update.',
        ],
    },
    'spicy': {
        'blunder': [
            'That move was a full material giveaway. Even the pawns are asking questions.',
            'You did not lose a piece. You launched a donation campaign.',
            'The opponent’s calculator made one click and your position started smoking.',
            'That move belongs in a museum titled “What Was the Plan?”',
            'Your piece saw the danger, packed a bag, and left anyway.',
        ],
        'mistake': [
            'That move was confidently incorrect with premium packaging.',
            'The plan had potential, but the calculation was still loading.',
            'You challenged the position to a duel and forgot to bring a weapon.',
            'The move looked clever until the opponent was allowed to respond.',
            'A bold idea, powered by approximately three seconds of thought.',
        ],
        'inaccuracy': [
            'Not terrible, but the engine found a move with fewer decorative mistakes.',
            'You chose the second-best road and paid a small toll.',
            'The position asked for precision. You supplied personality.',
            'A tiny slip, but chess is very good at charging interest.',
            'The move survived, although it did not exactly impress the jury.',
        ],
        'good': [
            'Good move. Your pieces may now stop drafting a formal complaint.',
            'Correct and practical. The board is no longer in emergency mode.',
            'That was clean. Keep this level of discipline going.',
        ],
        'brilliant': [
            'That was outrageous in the best possible way. Proper tactical cooking.',
            'You found the move the position was trying to hide. Respect.',
            'Brilliant. The opponent’s pieces are currently holding a crisis meeting.',
        ],
    },
}


@app.post('/api/roast')
def roast():
    data = request.get_json(silent=True) or {}
    label = str(data.get('label', 'mistake')).lower().strip()
    san = str(data.get('san', 'that move'))
    intensity = str(data.get('intensity', 'playful')).lower().strip()
    if intensity not in ROAST_BANK:
        intensity = 'playful'
    pool = ROAST_BANK[intensity].get(label) or ROAST_BANK[intensity]['mistake']
    # Stable variety: the same move gets a repeatable line, while different moves vary.
    seed = f'{label}|{san}|{intensity}'
    index = sum((position + 1) * ord(char) for position, char in enumerate(seed)) % len(pool)
    roast_text = pool[index]
    advice = (
        f"Before playing {san}, scan checks, captures, and threats. "
        "Then ask what your opponent will do immediately after your move."
    )
    return jsonify({'roast': roast_text, 'advice': advice, 'intensity': intensity, 'label': label})

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

# --- Training features: bots, live coach, lessons, and weakness-based puzzles ---
@app.get('/api/bot/move')
def bot_move():
    fen = request.args.get('fen', '').strip()
    if not fen:
        return jsonify({'error': 'FEN is required.'}), 400
    try:
        board = chess.Board(fen)
        info = engine.analyse(board, depth=12, multipv=1, time_limit=0.25)
        pv = info.get('pv') or []
        if not pv:
            return jsonify({'error': 'The engine returned no move.'}), 503
        move = pv[0]
        return jsonify({'uci': move.uci(), 'san': board.san(move), 'fen': board.fen()})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.post('/api/coach/check')
def coach_check():
    data = request.get_json(silent=True) or {}
    fen = str(data.get('fen', '')).strip()
    uci = str(data.get('uci', '')).strip()
    if not fen or not uci:
        return jsonify({'error': 'FEN and UCI move are required.'}), 400
    try:
        board = chess.Board(fen)
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            return jsonify({'correct': False, 'label': 'Illegal', 'message': 'That move is not legal in this position.'})
        san = board.san(move)
        before = engine.analyse(board, depth=12, multipv=1, time_limit=0.25)
        best = (before.get('pv') or [None])[0]
        best_san = board.san(best) if best and best in board.legal_moves else None
        board.push(move)
        after = engine.analyse(board, depth=12, multipv=1, time_limit=0.25)
        before_score = before.get('score').pov(not board.turn)
        after_score = after.get('score').pov(not board.turn)
        before_cp = before_score.score(mate_score=100000) or 0
        after_cp = after_score.score(mate_score=100000) or 0
        loss = max(0, before_cp - after_cp)
        if best and move == best:
            label, correct = 'Best move', True
        elif loss >= 200:
            label, correct = 'Blunder', False
        elif loss >= 100:
            label, correct = 'Mistake', False
        elif loss >= 50:
            label, correct = 'Inaccuracy', False
        else:
            label, correct = 'Playable', True
        return jsonify({'correct': correct, 'label': label, 'san': san, 'best_move': best_san, 'loss_cp': loss,
                        'message': f'{san}: {label}. ' + (f'Try {best_san}.' if best_san and best_san != san else 'Keep going!')})
    except Exception as exc:
        return jsonify({'error': str(exc)}), 400


@app.post('/api/training-plan')
def training_plan():
    data = request.get_json(silent=True) or {}
    report = data.get('report') or {}
    summary = report.get('summary') or {}
    weaknesses = []
    if summary.get('blunders', 0) or summary.get('mistakes', 0):
        weaknesses.append({'topic': 'Blunder prevention', 'reason': 'You are losing evaluation through tactical oversights.', 'lesson': 'Checks, captures, threats, and one-move blunder checks.', 'puzzle_type': 'hanging pieces'})
    if summary.get('inaccuracies', 0):
        weaknesses.append({'topic': 'Calculation and precision', 'reason': 'Several playable moves were not the most accurate.', 'lesson': 'Candidate moves and calculating the opponent’s best reply.', 'puzzle_type': 'best continuation'})
    if not weaknesses:
        weaknesses.append({'topic': 'Tactical sharpness', 'reason': 'No major weakness was detected in this sample.', 'lesson': 'Forks, pins, discovered attacks, and forcing moves.', 'puzzle_type': 'tactical pattern'})
    return jsonify({'weaknesses': weaknesses, 'daily_plan': ['Review one lesson', 'Solve 5 focused puzzles', 'Replay one critical game position without engine help']})
