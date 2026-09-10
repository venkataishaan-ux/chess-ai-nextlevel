[README.md](https://github.com/user-attachments/files/32058736/README.md)
# Chess Coach AI - V1

A first working foundation for a personalized chess coach.

## V1 features

- PGN parsing
- Interactive move replay
- FEN generation
- Stockfish integration
- Move-by-move evaluation
- Inaccuracy / mistake / blunder classification
- Best-move suggestions
- Basic coaching report

## Requirements

- Python 3.10+
- Stockfish installed separately

## Setup

### 1. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Stockfish

Install Stockfish using your operating system's package manager or official distribution.

If the executable is not on PATH, set:

Windows PowerShell:

```powershell
$env:STOCKFISH_PATH="C:\path\to\stockfish.exe"
```

macOS/Linux:

```bash
export STOCKFISH_PATH="/path/to/stockfish"
```

### 4. Start the app

```bash
python app.py
```

Open the local address shown by Flask.

## Important

V1 uses Stockfish for chess calculation. The AI explanation layer is intentionally kept simple at this stage. Later versions can add an LLM, screenshot recognition, player profiles, personalized training, practice games, and adaptive coaching.

## Architecture

```text
PGN
 ↓
python-chess
 ↓
Board / FEN
 ↓
Stockfish
 ↓
Move classification
 ↓
Coach report
```
