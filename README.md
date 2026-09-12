[README.md](https://github.com/user-attachments/files/32139215/README.md)
# Chess Coach AI — V2.1.5

Personalized chess analysis app built with Flask, python-chess, and Stockfish.

## V2.1.5

- Every move receives one classification: **Brilliant, Good, Inaccuracy, Mistake, Blunder**.
- Stockfish remains the source of evaluation and classification.
- Full move-by-move breakdown with centipawn loss, evaluation before/after, best move, and coach lesson.
- Dedicated **Blunder Breakdown**.
- Sparse **Turning Points** section for the largest mistakes.
- Best and worst move sections.
- Interactive FEN-based board replay with working first/previous/next/last controls.
- Move-list buttons jump to the exact position.
- Last played move is highlighted on the board.
- Responsive dark dashboard UI.

## Architecture

**Stockfish = calculates**  
**python-chess = position facts and legal move handling**  
**Coach layer = explains and teaches**

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Stockfish must be installed and available as `stockfish`, or set `STOCKFISH_PATH`.

## Docker / Render

The included Dockerfile installs Stockfish and starts Gunicorn. On Render, use a Docker Web Service connected to this repository.

## Classification

Thresholds are intentionally conservative:

- Good: < 50 cp loss
- Inaccuracy: 50–99 cp loss
- Mistake: 100–199 cp loss
- Blunder: 200+ cp loss
- Brilliant: a Stockfish top move that also meets the app's conservative tactical-sacrifice condition

These labels are engine-based heuristics, not official chess annotations or Elo measurements.
