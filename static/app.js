const STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
let game = null;
let currentPly = 0;
let lastAnalysis = null;

const PIECES = { P:"♙", N:"♘", B:"♗", R:"♖", Q:"♕", K:"♔", p:"♟", n:"♞", b:"♝", r:"♜", q:"♛", k:"♚" };

function $(id) { return document.getElementById(id); }
function escapeHtml(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function parseFen(fen) {
  const rows = fen.split(" ")[0].split("/");
  if (rows.length !== 8) throw new Error("Invalid FEN board.");
  const board = [];
  for (const row of rows) {
    const cells = [];
    for (const ch of row) {
      if (/\d/.test(ch)) for (let i = 0; i < Number(ch); i++) cells.push(null);
      else cells.push(ch);
    }
    if (cells.length !== 8) throw new Error("Invalid FEN rank.");
    board.push(cells);
  }
  return board;
}

function renderBoard(fen = STARTING_FEN) {
  const boardEl = $("board");
  const cells = parseFen(fen);
  boardEl.innerHTML = "";
  const analysisMove = lastAnalysis?.moves?.[currentPly - 1];
  const lastUci = analysisMove?.uci;

  cells.forEach((row, rankIndex) => row.forEach((piece, fileIndex) => {
    const square = document.createElement("div");
    square.className = `square ${((rankIndex + fileIndex) % 2 === 0) ? "light" : "dark"}`;
    const squareName = String.fromCharCode(97 + fileIndex) + (8 - rankIndex);
    square.dataset.square = squareName;
    if (piece) {
      const span = document.createElement("span");
      span.className = `piece ${piece === piece.toUpperCase() ? "white-piece" : "black-piece"}`;
      span.textContent = PIECES[piece] || piece;
      square.appendChild(span);
    }
    if (lastUci && (squareName === lastUci.slice(0,2) || squareName === lastUci.slice(2,4))) square.classList.add("last-move");
    if (fileIndex === 0) {
      const rank = document.createElement("span"); rank.className = "rank-label"; rank.textContent = 8 - rankIndex; square.appendChild(rank);
    }
    if (rankIndex === 7) {
      const file = document.createElement("span"); file.className = "file-label"; file.textContent = squareName[0]; square.appendChild(file);
    }
    boardEl.appendChild(square);
  }));
}

function updateControls() {
  const total = game?.moves?.length ?? 0;
  $("moveLabel").textContent = game ? (currentPly === 0 ? "Start" : `${game.moves[currentPly-1].ply}. ${game.moves[currentPly-1].san}`) : "Start";
  $("moveCounter").textContent = game ? `${currentPly} / ${total}` : "0 / 0";
  $("firstBtn").disabled = currentPly <= 0;
  $("prevBtn").disabled = currentPly <= 0;
  $("nextBtn").disabled = !game || currentPly >= total;
  $("lastBtn").disabled = !game || currentPly >= total;
}

function renderMoves() {
  const movesEl = $("moves");
  if (!game?.moves?.length) { movesEl.innerHTML = '<div class="empty">No moves loaded.</div>'; return; }
  movesEl.innerHTML = "";
  game.moves.forEach((move, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `move ${index + 1 === currentPly ? "active" : ""}`;
    const result = lastAnalysis?.moves?.[index];
    const badge = result ? `<span class="mini-badge ${result.label.toLowerCase()}">${escapeHtml(result.label)}</span>` : "";
    button.innerHTML = `<span>${move.ply}. ${escapeHtml(move.san)}</span>${badge}`;
    button.addEventListener("click", () => goToPly(index + 1));
    movesEl.appendChild(button);
  });
}

function goToPly(ply) {
  if (!game) return;
  currentPly = Math.max(0, Math.min(ply, game.moves.length));
  const fen = currentPly === 0 ? game.initial_fen : game.moves[currentPly - 1].fen;
  renderBoard(fen); renderMoves(); updateControls();
}

async function loadGame() {
  const pgn = $("pgn").value.trim();
  if (!pgn) { $("status").textContent = "Paste a PGN first."; return; }
  $("status").textContent = "Loading game…";
  try {
    const response = await fetch("/api/parse-pgn", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({pgn}) });
    const data = await response.json(); if (!response.ok) throw new Error(data.error || "Could not load PGN.");
    game = data; currentPly = 0; lastAnalysis = null; $("analysis").innerHTML = '<div class="empty">Run Stockfish analysis to generate the V2.2 report.</div>';
    goToPly(0); $("status").textContent = `Loaded ${data.moves.length} ply.`;
  } catch (error) { game = null; currentPly = 0; updateControls(); renderBoard(); renderMoves(); $("status").textContent = error.message; }
}

function badge(label) { return `<span class="badge ${label.toLowerCase()}">${escapeHtml(label)}</span>`; }
function renderIssue(item) {
  const ex = item.explanation || {};
  return `<article class="issue ${item.label.toLowerCase()}">
    <div class="issue-top"><strong>${escapeHtml(item.move_number)}${item.side === "White" ? "." : "..."} ${escapeHtml(item.san)}</strong>${badge(item.label)}</div>
    <div class="issue-stats"><span>Loss: <b>${escapeHtml(item.loss_cp)} cp</b></span><span>Best: <b>${escapeHtml(item.best_move_san || "n/a")}</b></span><span>Eval: <b>${escapeHtml(item.eval_before)} → ${escapeHtml(item.eval_after)}</b></span></div>
    ${ex.headline ? `<p><b>What happened:</b> ${escapeHtml(ex.headline)}</p>` : ""}
    ${ex.why ? `<p><b>Why:</b> ${escapeHtml(ex.why)}</p>` : ""}
    ${ex.lesson ? `<p><b>Lesson:</b> ${escapeHtml(ex.lesson)}</p>` : ""}
    ${item.variation?.length ? `<p><b>Suggested line:</b> <code>${escapeHtml(item.variation.join(" "))}</code></p>` : ""}
  </article>`;
}

function renderAnalysis(data) {
  const s = data.summary || {};
  const moves = data.moves || [];
  const critical = data.critical || [];
  const blunders = data.blunder_breakdown || [];
  const turning = data.turning_points || [];
  const counts = [["Brilliant",s.brilliant], ["Good",s.good], ["Inaccuracy",s.inaccuracies], ["Mistake",s.mistakes], ["Blunder",s.blunders]];
  const countHtml = counts.map(([label,n]) => `<div class="summary-card"><span>${label}</span><strong>${n ?? 0}</strong></div>`).join("");
  const breakdown = blunders.length ? blunders.map(renderIssue).join("") : '<div class="empty">No blunders detected at this depth. That is a good thing. 🧠</div>';
  const criticalHtml = critical.length ? critical.map(renderIssue).join("") : '<div class="empty">No inaccuracies, mistakes, or blunders detected.</div>';
  const turningHtml = turning.length ? turning.map(renderIssue).join("") : '<div class="empty">No major turning points detected.</div>';
  const best = data.best_move ? renderIssue(data.best_move) : '<div class="empty">No move data.</div>';
  const worst = data.worst_move ? renderIssue(data.worst_move) : '<div class="empty">No move data.</div>';
  const allMoves = moves.map(renderIssue).join("");

  $("analysis").innerHTML = `
    <section class="report-section"><h3>Opening</h3><p class="opening-name">${escapeHtml(data.opening || "Opening not identified")}</p></section>
    <section class="report-section"><h3>Move Classification</h3><div class="summary-grid">${countHtml}</div></section>
    <section class="report-section"><h3>⚠️ Blunder Breakdown</h3>${breakdown}</section>
    <section class="report-section"><h3>🎯 Turning Points</h3>${turningHtml}</section>
    <section class="report-section"><h3>📌 Best Move</h3>${best}</section>
    <section class="report-section"><h3>💥 Worst Move</h3>${worst}</section>
    <section class="report-section"><h3>🔎 Critical Mistakes</h3>${criticalHtml}</section>
    <section class="report-section"><h3>📋 Full Move-by-Move Breakdown</h3><div class="all-moves">${allMoves}</div></section>`;
  renderMoves();
}

async function runAnalysis() {
  const pgn = $("pgn").value.trim(); if (!pgn) { $("status").textContent = "Paste a PGN first."; return; }
  $("status").textContent = "Stockfish is calculating every move…"; $("analysis").innerHTML = '<div class="empty">Analyzing the full game…</div>';
  try {
    const depth = Number($("depth").value) || 12;
    const response = await fetch("/api/analyze", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({pgn, depth}) });
    const data = await response.json(); if (!response.ok) throw new Error(data.error || "Analysis failed.");
    lastAnalysis = data; renderAnalysis(data); if (game) goToPly(currentPly); $("status").textContent = `Analysis complete: ${data.summary.total_moves} moves classified.`;
  } catch (error) { $("status").textContent = error.message; $("analysis").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`; }
}

async function engineStatus() {
  try { const r = await fetch("/api/engine-status"); const s = await r.json(); $("engineStatus").textContent = s.available ? "● Stockfish online" : "○ Stockfish unavailable"; $("engineStatus").className = s.available ? "online" : "offline"; }
  catch { $("engineStatus").textContent = "○ Engine status unknown"; }
}

function init() {
  $("loadBtn").addEventListener("click", loadGame); $("analyzeBtn").addEventListener("click", runAnalysis);
  $("firstBtn").addEventListener("click", () => goToPly(0)); $("prevBtn").addEventListener("click", () => goToPly(currentPly - 1));
  $("nextBtn").addEventListener("click", () => goToPly(currentPly + 1)); $("lastBtn").addEventListener("click", () => goToPly(game ? game.moves.length : 0));
  renderBoard(); renderMoves(); updateControls(); engineStatus();
}
document.addEventListener("DOMContentLoaded", init);
