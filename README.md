# ♟️ Chess Coach AI — V11

**A personalized chess-learning, analysis, training, and improvement platform.**

Chess Coach AI combines **Stockfish**, **python-chess**, and **Gemini 2.5 Flash-Lite** to turn your games into actionable coaching. It analyzes moves, detects recurring weaknesses, creates targeted training, and keeps a long-term player profile.

## 🚀 V11 Features

### ♟️ Game Analysis
- PGN game input and replay
- Interactive chessboard
- First / previous / next / last move navigation
- Move-list position jumping
- Last-move highlighting
- Stockfish analysis of individual moves
- Best move, evaluation, centipawn loss, and position changes
- Move classifications such as **Brilliant, Good, Inaccuracy, Mistake, and Blunder**
- Turning points and blunder breakdown
- Coach explanations for important decisions

### 🧠 Personal Chess Coach
- Multi-game player profile
- Internal estimated skill indicators
- Opening, middlegame, tactics, endgame, defense, calculation, threat detection, and other training dimensions
- Recurring weakness detection
- Strength and weakness tracking
- Personalized lessons
- Personalized puzzles based on mistakes
- Best Move of the Day
- Daily training
- Progress tracking
- Unrated practice and adaptive training foundations

> Skill and rating values are **internal coaching estimates**, not official Elo ratings.

### 🎯 V11 Training Ecosystem
The V11 system follows:

**Play → Analyze → Understand → Detect Weaknesses → Train → Practice → Track Improvement → Analyze Again**

It is designed to become a continuously improving personal chess coach rather than just a game analyzer.

### 🤖 Gemini Teaching Layer
Gemini is used for explanations and teaching, while Stockfish remains the authority for chess calculation.

- Gemini model: `gemini-2.5-flash-lite` by default
- Coach Q&A
- Personalized explanations
- Friendly, Tactical, Puzzle, and Roast coach personalities
- Configurable roast intensity

**Important:** Gemini should explain engine results, not invent chess evaluations.

### 👁️ Position & FEN Tools
- FEN validation
- FEN position analysis
- Board reconstruction foundations
- Screenshot-input foundation for future vision/OCR integration

### 💾 Persistent Player History

V11 supports **PostgreSQL for persistent long-term history**.

Production architecture:

```
                 ┌─────────────────┐
                 │   Chess Coach AI │
                 │    Flask App     │
                 └────────┬────────┘
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
        PostgreSQL    Stockfish      Gemini
       Player Data    Calculation    Teaching
```

- **Render** runs the Flask web application.
- **PostgreSQL** stores long-term games, training results, profiles, puzzles, lessons, and achievements.
- **Stockfish** performs chess calculations.
- **Gemini 2.5 Flash-Lite** provides teaching and explanations.
- SQLite remains available as a local-development fallback.
- Database credentials stay in environment variables and should never be committed to GitHub.

### 🧭 New V11 Frontend

The frontend now includes a redesigned V11 header with:

- Personal Chess Intelligence branding
- Dashboard navigation
- Analyze Game navigation
- Training navigation
- Responsive layout
- Quick access to the main coaching areas

## 🏗️ Architecture

**Stockfish = chess calculation**  
**python-chess = legal chess rules and position handling**  
**Gemini = teaching and explanations**  
**PostgreSQL = persistent player history**  
**Flask = application/API layer**

Keeping these responsibilities separate makes the system easier to improve and test.

## 🔌 V11 API

| Endpoint | Purpose |
|---|---|
| `GET /api/v11/health` | System health |
| `GET /api/v11/profile` | Player profile |
| `GET /api/v11/dashboard` | Personalized dashboard |
| `POST /api/v11/game/save` | Save analyzed game |
| `GET /api/v11/games` | Recent games |
| `GET /api/v11/training` | Training history |
| `POST /api/v11/training/result` | Save training result |
| `GET /api/v11/weaknesses` | Recurring weaknesses |
| `POST /api/v11/fen/validate` | Validate FEN |
| `POST /api/v11/fen/analyze` | Analyze FEN |
| `POST /api/v11/puzzle/new` | Generate puzzle |
| `POST /api/v11/puzzle/check` | Check puzzle move |
| `POST /api/v11/practice/move` | Practice move |
| `POST /api/v11/coach/explain` | Ask the coach |
| `GET /api/v11/best-move-of-day` | Best move of the day |
| `GET /api/v11/daily` | Daily training |

## 🛠️ Run Locally

```bash
pip install -r requirements.txt
python app.py
```

Stockfish must be installed and available as `stockfish`, or configure:

```text
STOCKFISH_PATH=/path/to/stockfish
```

For PostgreSQL, configure:

```text
DATABASE_URL=your-postgresql-connection-string
```

For Gemini:

```text
GEMINI_API_KEY=your-api-key
GEMINI_MODEL=gemini-2.5-flash-lite
```

Never put real API keys or database credentials in source code.

## ☁️ Deployment Architecture

For production:

**Render → Flask → PostgreSQL**

with:

**Flask → Stockfish** for calculation  
**Flask → Gemini 2.5 Flash-Lite** for coaching

Render's normal application filesystem should not be treated as the permanent database. PostgreSQL is the persistent storage layer.

## 📈 Roadmap

### Completed foundation
- V11 adaptive coach architecture
- PostgreSQL-compatible persistence layer
- Multi-game profile foundation
- Weakness detection
- Personalized puzzle foundation
- FEN tools
- Daily training
- Gemini coaching layer
- Redesigned frontend navigation

### Next development
- Full screenshot board recognition with vision/OCR
- Automatic move-list screenshot recognition
- Correction UI for recognition errors
- Rich interactive variation explorer
- More accurate skill-estimation model
- User accounts and per-player data isolation
- Database migrations and indexes
- Full practice-board interaction
- More advanced adaptive training
- Automated persistence and deployment tests

## 📜 Project Philosophy

Chess Coach AI is built around one idea:

> **Don't just tell the player what move was wrong. Teach them why, identify the pattern, and train that exact weakness.**

