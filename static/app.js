const PIECES = {
  P: "♙", N: "♘", B: "♗", R: "♖", Q: "♕", K: "♔",
  p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚"
};

const FILES = ["a", "b", "c", "d", "e", "f", "g", "h"];
const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

let game = null;
let currentPly = 0;
let analysis = null;

const $ = id => document.getElementById(id);

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

function boardFromFen(fen) {
  const board = Array.from({ length: 8 }, () => Array(8).fill(null));
  const placement = String(fen || STARTING_FEN).split(/\s+/)[0];
  const rows = placement.split("/");

  if (rows.length !== 8) throw new Error("Invalid FEN: expected 8 ranks.");

  rows.forEach((row, r) => {
    let c = 0;
    for (const char of row) {
      if (/^[1-8]$/.test(char)) {
        c += Number(char);
      } else if (PIECES[char]) {
        if (c >= 8) throw new Error("Invalid FEN: rank is too long.");
        board[r][c++] = char;
      } else {
        throw new Error(`Invalid FEN piece: ${char}`);
      }
    }
    if (c !== 8) throw new Error("Invalid FEN: rank does not contain 8 squares.");
  });

  return board;
}

function squareName(row, col) {
  return `${FILES[col]}${8 - row}`;
}

function getLastMove() {
  if (!game || currentPly === 0) return null;
  const move = game.moves[currentPly - 1];
  if (!move || !move.uci || move.uci.length < 4) return null;
  return { from: move.uci.slice(0, 2), to: move.uci.slice(2, 4) };
}

function renderBoard(fen = STARTING_FEN) {
  const root = $("board");
  if (!root) return;

  let board;
  try {
    board = boardFromFen(fen);
  } catch (error) {
    console.error("Board render error:", error, fen);
    setStatus(`Board error: ${error.message}`);
    return;
  }

  const lastMove = getLastMove();
  root.innerHTML = "";

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const sq = document.createElement("div");
      const name = squareName(r, c);
      sq.className = `square ${(r + c) % 2 ? "dark" : "light"}`;
      sq.dataset.square = name;

      if (lastMove && (name === lastMove.from || name === lastMove.to)) {
        sq.classList.add("last-move");
      }

      const piece = board[r][c];
      if (piece) {
        const pieceEl = document.createElement("span");
        pieceEl.className = `piece ${piece === piece.toUpperCase() ? "white-piece" : "black-piece"}`;
        pieceEl.textContent = PIECES[piece];
        sq.appendChild(pieceEl);
      }

      // Coordinate labels make the board unambiguous and keep the grid looking like a real chessboard.
      if (c === 0) {
        const rank = document.createElement("span");
        rank.className = "rank-label";
        rank.textContent = String(8 - r);
        sq.appendChild(rank);
      }
      if (r === 7) {
        const file = document.createElement("span");
        file.className = "file-label";
        file.textContent = FILES[c];
        sq.appendChild(file);
      }

      root.appendChild(sq);
    }
  }
}

function renderMoves() {
  const root = $("moves");
  if (!root) return;
  root.innerHTML = "";

  if (!game || !game.moves.length) {
    root.innerHTML = '<p class="empty-state">Load a game to see the move list.</p>';
    return;
  }

  const list = document.createElement("div");
  list.className = "moves-list";

  game.moves.forEach((move, index) => {
    const el = document.createElement("button");
    el.type = "button";
    el.className = "move" + (index + 1 === currentPly ? " active" : "");
    el.textContent = `${Math.ceil(move.ply / 2)}${move.ply % 2 ? "." : "..."} ${move.san}`;
    el.addEventListener("click", () => goToPly(index + 1));
    list.appendChild(el);
  });

  root.appendChild(list);
}

function updateNavigationState() {
  const first = $("firstBtn");
  const prev = $("prevBtn");
  const next = $("nextBtn");
  const last = $("lastBtn");
  const hasGame = Boolean(game && Array.isArray(game.moves));
  const total = hasGame ? game.moves.length : 0;

  if (first) first.disabled = !hasGame || currentPly === 0;
  if (prev) prev.disabled = !hasGame || currentPly === 0;
  if (next) next.disabled = !hasGame || currentPly >= total;
  if (last) last.disabled = !hasGame || currentPly >= total;
}

function updatePosition() {
  if (!game) {
    currentPly = 0;
    renderBoard(STARTING_FEN);
    $("moveLabel").textContent = "Start";
    renderMoves();
    updateNavigationState();
    return;
  }

  const total = game.moves.length;
  currentPly = Math.max(0, Math.min(currentPly, total));
  const fen = currentPly === 0 ? game.initial_fen : game.moves[currentPly - 1].fen;

  renderBoard(fen);
  $("moveLabel").textContent = currentPly === 0
    ? "Start"
    : `${currentPly} / ${total} · ${game.moves[currentPly - 1].san}`;

  renderMoves();
  updateNavigationState();
}

function goToPly(ply) {
  if (!game) return;
  currentPly = Math.max(0, Math.min(ply, game.moves.length));
  updatePosition();
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pgn })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not parse PGN.");
    if (!data.initial_fen || !Array.isArray(data.moves)) throw new Error("The server returned an invalid game response.");

    for (const move of data.moves) {
      if (!move.fen || !move.uci || !move.san) throw new Error("The server returned an incomplete move list.");
    }

    game = data;
    analysis = null;
    currentPly = 0;
    updatePosition();
    $("report").innerHTML = "<p>Game loaded. Click <b>Analyze with Stockfish</b> to generate the report.</p>";
    setStatus(`Loaded ${data.moves.length} plies. Use the replay controls or click any move.`);
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pgn, depth })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Analysis failed.");

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
      <div class="coach-section"><b>🧠 What happened</b><p>${escapeHtml(explanation.headline || "Stockfish found a difference between the played move and its preferred move.")}</p></div>
      <div class="coach-section"><b>🔎 Why it matters</b><p>${escapeHtml(explanation.why || `Evaluation loss: ${loss} pawns.`)}</p></div>
      <div class="coach-section"><b>👀 What you missed</b><p>${escapeHtml(explanation.missed || "Look for the opponent's strongest reply after your move.")}</p></div>
      <div class="best-move"><b>♟️ Better move:</b> ${escapeHtml(best)}</div>
      <div class="coach-section"><b>🎯 Coach lesson</b><p>${escapeHtml(explanation.lesson || "Check your opponent's threats before moving.")}</p></div>
      ${pv ? `<details><summary>Engine continuation</summary><small>${escapeHtml(pv)}</small></details>` : ""}
      <small>Engine difference: ${escapeHtml(loss)} pawns</small>
    </article>
  `;
}

function renderReport() {
  const s = analysis.summary;
  const counts = s.counts;
  let html = `<p><b>${s.move_count}</b> plies analyzed.</p><p>Inaccuracies: <b>${counts.Inaccuracy || 0}</b> · Mistakes: <b>${counts.Mistake || 0}</b> · Blunders: <b>${counts.Blunder || 0}</b></p><h3>Critical moments</h3>`;

  if (!analysis.critical.length) html += "<p>Nice. No major inaccuracies, mistakes, or blunders were detected at this depth.</p>";
  else analysis.critical.forEach(item => { html += renderIssue(item); });

  $("report").innerHTML = html;
}

function init() {
  renderBoard(STARTING_FEN);
  renderMoves();
  updateNavigationState();

  $("loadBtn")?.addEventListener("click", loadGame);
  $("analyzeBtn")?.addEventListener("click", runAnalysis);
  $("firstBtn")?.addEventListener("click", () => goToPly(0));
  $("prevBtn")?.addEventListener("click", () => goToPly(currentPly - 1));
  $("nextBtn")?.addEventListener("click", () => goToPly(currentPly + 1));
  $("lastBtn")?.addEventListener("click", () => goToPly(game ? game.moves.length : 0));
}

document.addEventListener("DOMContentLoaded", init);
