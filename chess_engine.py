import os
import shutil
from typing import Optional

import chess
import chess.engine


class StockfishEngine:
    def __init__(self, path: Optional[str] = None):
        self.path = path or os.getenv("STOCKFISH_PATH") or shutil.which("stockfish") or "/usr/games/stockfish"
        self.engine = None
        self._error = None
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(self.path)
        except Exception as exc:
            self._error = str(exc)

    def status(self):
        return {
            "available": self.engine is not None,
            "path": self.path,
            "error": self._error,
        }

    def analyse(self, board: chess.Board, depth: int = 14, multipv: int = 1):
        if self.engine is None:
            raise RuntimeError(f"Stockfish is unavailable: {self._error or 'unknown error'}")
        limit = chess.engine.Limit(depth=depth)
        return self.engine.analyse(board, limit, multipv=multipv)

    def close(self):
        if self.engine is not None:
            try:
                self.engine.quit()
            finally:
                self.engine = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
