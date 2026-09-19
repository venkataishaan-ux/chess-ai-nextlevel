# Chess Coach AI V11

V11 is the complete adaptive architecture layer for the project.

## Responsibility boundaries
- Vision/OCR: recognizes screenshots and proposes FEN/PGN.
- python-chess: legal positions, moves, FEN, PGN, validation.
- Stockfish: objective calculation, evaluations, best moves and variations.
- Gemini: explanation and teaching only, using supplied chess facts.
- SQLite: games, training, puzzles, lessons, achievements and profile history.

## Core loop
Play -> Analyze -> Understand -> Detect Weaknesses -> Targeted Training -> Practice -> Track Improvement -> Analyze Again.

## V11 API
- GET /api/v11/dashboard
- GET /api/v11/profile
- GET /api/v11/weaknesses
- GET /api/v11/games
- GET /api/v11/training
- POST /api/v11/game/save
- POST /api/v11/fen/validate
- POST /api/v11/fen/analyze
- POST /api/v11/puzzle/new
- POST /api/v11/puzzle/check
- POST /api/v11/practice/move
- POST /api/v11/training/result
- POST /api/v11/coach/explain
- GET /api/v11/best-move-of-day
- GET /api/v11/daily

Estimated Elo is explicitly an internal coaching indicator, never an official rating.

Set GEMINI_API_KEY only as a server environment variable. Never put it in frontend JavaScript or commit it.
