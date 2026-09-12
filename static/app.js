const PIECES = {
  P: "♙", N: "♘", B: "♗", R: "♖", Q: "♕", K: "♔",
  p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚"
};

let game = null;
let currentPly = 0;
let analysis = null;

const $ = id => document.getElementById(id);

const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

function setStatus(text) {
  const status = $("status");
  if (status) status.textContent = text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function emptyBoard() {
  return Array.from({length: 8}, () => Array(8).fill(null));
}

function boardFromFen(fen) {
  const board = emptyBoard();
  const rows = String(fen || STARTING_FEN).split(" ")[0].split("/");

  rows.forEach((row, r) => {
    let c = 0;
    for (const char of row) {
      if (/[1-8]/.test(char)) c += Number(char);
      else if (c < 8) board[r][c++] = char;
    }
  });

  return board;
}

function renderBoard(fen = STARTING_FEN) {
  const board = boardFromFen(fen);
  const root = $("board");
  if (!root) return;

  root.innerHTML = "";

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const sq = document.createElement("div");
      sq.className = `square ${(r + c) % 2 ? "dark" : "light"}`;
      const piece = board[r][c];
      if (piece) {
        sq.classList.add(piece === piece.toUpperCase() ? "white-piece" : "black-piece");
        sq.textContent = PIECES[piece] || "";
      }
      root.appendChild(sq);
    }
  }
}

function renderMoves() {
  const root = $("moves");
  if (!root) return;
  root.innerHTML = "";
  if (!game) return;

  const list = document.createElement("div");
  list.className = "moves-list";

  game.moves.forEach((move, index) => {
    const el = document.createElement("div");
    el.className = "move" + (index + 1 === currentPly ? " active" : "");
    el.textContent = `${Math.ceil(move.ply / 2)}${move.ply % 2 ? "." : "..."} ${move.san}`;
    el.onclick = () => {
      currentPly = index + 1;
      updatePosition();
    };
    list.appendChild(el);
  });

  root.appendChild(list);
}

function updatePosition() {
  if (!game) {
    renderBoard(STARTING_FEN);
    $("moveLabel").textContent = "Start";
    return;
  }

  const fen = currentPly === 0
    ? game.initial_fen
    : game.moves[currentPly - 1].fen;

  renderBoard(fen);
  $("moveLabel").textContent = currentPly === 0
    ? "Start"
    : `Move ${currentPly}`;

  renderMoves();
}

async function loadGame() {
  const pgn = $("pgn").value.trim();
  if (!pgn) {
    setStatus("Paste a PGN first.");
    return;
  }

  setStatus("Parsing PGN...");

  try {
    const response = await fetch("/api/parse-pgn", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({pgn})
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not parse PGN.");
    }

    if (!data.initial_fen || !Array.isArray(data.moves)) {
      throw new Error("The server returned an invalid game response.");
    }

    game = data;
    analysis = null;
    currentPly = 0;
    updatePosition();
    $("report").innerHTML = "<p>Game loaded. Click <b>Analyze with Stockfish</b> to generate the report.</p>";
    setStatus(`Loaded ${data.moves.length} plies.`);
  } catch (error) {
    console.error("Load game error:", error);
    setStatus(`Could not load game: ${error.message}`);
  }
}

async function runAnalysis() {
  const pgn = $("pgn").value.trim();
  if (!pgn) {
    setStatus("Load a PGN first.");
    return;
  }

  setStatus("Stockfish is analyzing. Deeper analysis may take longer...");
  const depth = Number($("depth").value);

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({pgn, depth})
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Analysis failed.");
    }

    analysis = data;
    renderReport();
    setStatus("Analysis complete.");
  } catch (error) {
    console.error("Analysis error:", error);
    setStatus(`Analysis failed: ${error.message}`);
  }
}

function renderIssue(item) {
  const explanation = item.explanation || {};
  const best = explanation.best_move_san || item.best_move || "N/A";
  const loss = (item.eval_loss_cp / 100).toFixed(2);
  const pv = (item.best_pv || []).slice(0, 8).join(" ");

  return `
    <article class="issue">
      <strong>${escapeHtml(item.label)}: ${escapeHtml(item.player)} move ${Math.ceil(item.ply / 2)} ${escapeHtml(item.san)}</strong>
      <div class="coach-section">
        <b>🧠 What happened</b>
        <p>${escapeHtml(explanation.headline || "Stockfish found a difference between the played move and its preferred move.")}</p>
      </div>
      <div class="coach-section">
        <b>🔎 Why it matters</b>
        <p>${escapeHtml(explanation.why || `Evaluation loss: ${loss} pawns.`)}</p>
      </div>
      <div class="coach-section">
        <b>👀 What you missed</b>
        <p>${escapeHtml(explanation.missed || "Look for the opponent's strongest reply after your move.")}</p>
      </div>
      <div class="best-move">
        <b>♟️ Better move:</b> ${escapeHtml(best)}
      </div>
      <div class="coach-section">
        <b>🎯 Coach lesson</b>
        <p>${escapeHtml(explanation.lesson || "Check your opponent's threats before moving.")}</p>
      </div>
      ${pv ? `<details><summary>Engine continuation</summary><small>${escapeHtml(pv)}</small></details>` : ""}
      <small>Engine difference: ${escapeHtml(loss)} pawns</small>
    </article>
  `;
}

function renderReport() {
  const s = analysis.summary;
  const counts = s.counts;
  let html = `
    <p><b>${s.move_count}</b> plies analyzed.</p>
    <p>
      Inaccuracies: <b>${counts.Inaccuracy || 0}</b> ·
      Mistakes: <b>${counts.Mistake || 0}</b> ·
      Blunders: <b>${counts.Blunder || 0}</b>
    </p>
    <h3>Critical moments</h3>
  `;

  if (!analysis.critical.length) {
    html += "<p>Nice. No major inaccuracies, mistakes, or blunders were detected at this depth.</p>";
  } else {
    analysis.critical.forEach(item => {
      html += renderIssue(item);
    });
  }

  $("report").innerHTML = html;
}

function init() {
  renderBoard(STARTING_FEN);
  $("loadBtn").onclick = loadGame;
  $("analyzeBtn").onclick = runAnalysis;
  $("firstBtn").onclick = () => { if (game) { currentPly = 0; updatePosition(); } };
  $("prevBtn").onclick = () => { if (game) { currentPly = Math.max(0, currentPly - 1); updatePosition(); } };
  $("nextBtn").onclick = () => { if (game) { currentPly = Math.min(game.moves.length, currentPly + 1); updatePosition(); } };
  $("lastBtn").onclick = () => { if (game) { currentPly = game.moves.length; updatePosition(); } };
}

document.addEventListener("DOMContentLoaded", init);
