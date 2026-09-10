import os
import shutil
import chess
import chess.engine


class StockfishEngine:
    def __init__(self):
        configured = os.environ.get("STOCKFISH_PATH")
        self.path = configured or shutil.which("stockfish")
        self.engine = None

    def _connect(self):
        if self.engine is None:
            if not self.path:
                raise RuntimeError(
                    "Stockfish was not found. Install Stockfish and set "
                    "STOCKFISH_PATH to the executable, or put stockfish on PATH."
                )
            self.engine = chess.engine.SimpleEngine.popen_uci(self.path)

    def status(self):
        return {
            "available": bool(self.path),
            "path": self.path,
        }

    def analyze(self, board: chess.Board, depth: int = 14):
        self._connect()
        info = self.engine.analyse(board, chess.engine.Limit(depth=depth))
        score = info["score"].pov(board.turn)
        pv = info.get("pv", [])

        return {
            "score_cp": score.score(mate_score=100000),
            "score": str(score),
            "best_move": pv[0].uci() if pv else None,
            "pv": [move.uci() for move in pv[:8]],
        }

    def close(self):
        if self.engine is not None:
            self.engine.quit()
            self.engine = None
