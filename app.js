const PIECES = {
  P: "♙", N: "♘", B: "♗", R: "♖", Q: "♕", K: "♔",
  p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚"
};

let game = null;
let currentPly = 0;
let analysis = null;

const $ = id => document.getElementById(id);

function setStatus(text) {
  $("status").textContent = text;
}

function emptyBoard() {
  return Array.from({length: 8}, () => Array(8).fill(null));
}

function boardFromFen(fen) {
  const board = emptyBoard();
  const rows = fen.split(" ")[0].split("/");
  rows.forEach((row, r) => {
    let c = 0;
    for (const char of row) {
      if (/[1-8]/.test(char)) c += Number(char);
      else board[r][c++] = char;
    }
  });
  return board;
}

function renderBoard(fen) {
  const board = boardFromFen(fen);
  const root = $("board");
  root.innerHTML = "";

  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const sq = document.createElement("div");
      sq.className = `square ${(r + c) % 2 ? "dark" : "light"}`;
      const piece = board[r][c];
      if (piece) sq.textContent = PIECES[piece] || "";
      root.appendChild(sq);
    }
  }
}

function renderMoves() {
  const root = $("moves");
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
  if (!pgn) return setStatus("Paste a PGN first.");

  setStatus("Parsing PGN...");
  const response = await fetch("/api/parse-pgn", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({pgn})
  });
  const data = await response.json();

  if (!response.ok) return setStatus(data.error || "Could not parse PGN.");

  game = data;
  analysis = null;
  currentPly = 0;
  updatePosition();
  $("report").innerHTML = "<p>Game loaded. Click <b>Analyze with Stockfish</b> to generate the report.</p>";
  setStatus(`Loaded ${data.moves.length} plies.`);
}

async function runAnalysis() {
  const pgn = $("pgn").value.trim();
  if (!pgn) return setStatus("Load a PGN first.");

  setStatus("Stockfish is analyzing. Deeper analysis may take longer...");
  const depth = Number($("depth").value);

  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({pgn, depth})
  });

  const data = await response.json();
  if (!response.ok) return setStatus(data.error || "Analysis failed.");

  analysis = data;
  renderReport();
  setStatus("Analysis complete.");
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
      const best = item.best_move || "N/A";
      html += `
        <div class="issue">
          <strong>${item.label}: ${item.player} move ${Math.ceil(item.ply / 2)} ${item.san}</strong>
          <span>Best move: <b>${best}</b></span><br>
          <span>Evaluation loss: ${(item.eval_loss_cp / 100).toFixed(2)} pawns</span>
          <br><small>PV: ${item.best_pv.join(" ")}</small>
        </div>
      `;
    });
  }

  $("report").innerHTML = html;
}

$("loadBtn").onclick = loadGame;
$("analyzeBtn").onclick = runAnalysis;
$("firstBtn").onclick = () => { if (game) { currentPly = 0; updatePosition(); } };
$("prevBtn").onclick = () => { if (game) { currentPly = Math.max(0, currentPly - 1); updatePosition(); } };
$("nextBtn").onclick = () => { if (game) { currentPly = Math.min(game.moves.length, currentPly + 1); updatePosition(); } };
$("lastBtn").onclick = () => { if (game) { currentPly = game.moves.length; updatePosition(); } };
