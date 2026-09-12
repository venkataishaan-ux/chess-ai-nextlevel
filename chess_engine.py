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
            # Render free instances have limited CPU/memory. One engine thread
            # keeps analysis predictable and avoids spawning extra workers.
            self.engine.configure({"Threads": 1, "Hash": 16})
        except Exception as exc:
            self._error = str(exc)

    def status(self):
        return {"available": self.engine is not None, "path": self.path, "error": self._error}

    def analyse(self, board: chess.Board, depth: int = 12, multipv: int = 1, time_limit: float = 0.18):
        if self.engine is None:
            raise RuntimeError(f"Stockfish is unavailable: {self._error or 'unknown error'}")
        # Use whichever limit is reached first. This keeps HTTP requests from
        # hitting Render/Gunicorn's worker timeout on longer games.
        limit = chess.engine.Limit(depth=depth, time=time_limit)
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
