
(() => {
  "use strict";

  const STARTING_FEN =
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

  const PIECES = {
    P: "♙",
    N: "♘",
    B: "♗",
    R: "♖",
    Q: "♕",
    K: "♔",
    p: "♟",
    n: "♞",
    b: "♝",
    r: "♜",
    q: "♛",
    k: "♚"
  };

  let game = null;
  let currentPly = 0;
  let lastAnalysis = null;

  const $ = (id) => document.getElementById(id);

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function safeClass(value) {
    return String(value ?? "unknown")
      .toLowerCase()
      .replace(/[^a-z0-9_-]/g, "-");
  }

  function setText(id, value) {
    const element = $(id);
    if (element) element.textContent = value;
  }

  function parseFen(fen) {
    const boardPart = String(fen || "").trim().split(/\s+/)[0];
    const rows = boardPart.split("/");

    if (rows.length !== 8) {
      throw new Error("Invalid FEN board.");
    }

    return rows.map((row) => {
      const cells = [];

      for (const character of row) {
        if (/^[1-8]$/.test(character)) {
          for (let i = 0; i < Number(character); i += 1) {
            cells.push(null);
          }
        } else if (PIECES[character]) {
          cells.push(character);
        } else {
          throw new Error("Invalid FEN piece.");
        }
      }

      if (cells.length !== 8) {
        throw new Error("Invalid FEN rank.");
      }

      return cells;
    });
  }

  function renderBoard(fen = STARTING_FEN) {
    const board = $("board");
    if (!board) return;

    let cells;

    try {
      cells = parseFen(fen);
    } catch (error) {
      board.textContent = error.message;
      return;
    }

    board.innerHTML = "";

    const analysisMove =
      lastAnalysis &&
      Array.isArray(lastAnalysis.moves) &&
      currentPly > 0
        ? lastAnalysis.moves[currentPly - 1]
        : null;

    const lastUci = analysisMove?.uci || "";

    cells.forEach((row, rankIndex) => {
      row.forEach((piece, fileIndex) => {
        const square = document.createElement("div");

        square.className =
          "square " +
          ((rankIndex + fileIndex) % 2 === 0 ? "light" : "dark");

        const squareName =
          String.fromCharCode(97 + fileIndex) + String(8 - rankIndex);

        square.dataset.square = squareName;

        if (piece) {
          const pieceElement = document.createElement("span");

          pieceElement.className =
            "piece " +
            (piece === piece.toUpperCase()
              ? "white-piece"
              : "black-piece");

          pieceElement.textContent = PIECES[piece];
          square.appendChild(pieceElement);
        }

        if (
          lastUci &&
          (squareName === lastUci.slice(0, 2) ||
            squareName === lastUci.slice(2, 4))
        ) {
          square.classList.add("last-move");
        }

        if (fileIndex === 0) {
          const rankLabel = document.createElement("span");
          rankLabel.className = "rank-label";
          rankLabel.textContent = String(8 - rankIndex);
          square.appendChild(rankLabel);
        }

        if (rankIndex === 7) {
          const fileLabel = document.createElement("span");
          fileLabel.className = "file-label";
          fileLabel.textContent = squareName[0];
          square.appendChild(fileLabel);
        }

        board.appendChild(square);
      });
    });
  }

  function updateControls() {
    const total = game?.moves?.length || 0;
    const currentMove =
      game && currentPly > 0 ? game.moves[currentPly - 1] : null;

    setText(
      "moveLabel",
      currentMove ? `${currentMove.ply}. ${currentMove.san}` : "Start"
    );

    setText("moveCounter", `${currentPly} / ${total}`);

    if ($("firstBtn")) $("firstBtn").disabled = currentPly <= 0;
    if ($("prevBtn")) $("prevBtn").disabled = currentPly <= 0;
    if ($("nextBtn")) $("nextBtn").disabled = !game || currentPly >= total;
    if ($("lastBtn")) $("lastBtn").disabled = !game || currentPly >= total;
  }

  function renderMoves() {
    const movesElement = $("moves");
    if (!movesElement) return;

    if (!game || !Array.isArray(game.moves) || game.moves.length === 0) {
      movesElement.innerHTML = '<div class="empty">No moves loaded.</div>';
      return;
    }

    movesElement.innerHTML = "";

    game.moves.forEach((move, index) => {
      const button = document.createElement("button");

      button.type = "button";
      button.className =
        "move " + (index + 1 === currentPly ? "active" : "");

      const result =
        lastAnalysis && Array.isArray(lastAnalysis.moves)
          ? lastAnalysis.moves[index]
          : null;

      const label = result?.label || "";

      const badge = label
        ? `<span class="mini-badge ${safeClass(label)}">${escapeHtml(
            label
          )}</span>`
        : "";

      button.innerHTML =
        `<span>${escapeHtml(move.ply)}. ${escapeHtml(move.san)}</span>` +
        badge;

      button.addEventListener("click", () => goToPly(index + 1));
      movesElement.appendChild(button);
    });
  }

  function goToPly(ply) {
    if (!game || !Array.isArray(game.moves)) return;

    currentPly = Math.max(
      0,
      Math.min(Number(ply) || 0, game.moves.length)
    );

    const fen =
      currentPly === 0
        ? game.initial_fen
        : game.moves[currentPly - 1].fen;

    renderBoard(fen || STARTING_FEN);
    renderMoves();
    updateControls();
  }

  async function loadGame() {
    const pgnElement = $("pgn");
    const pgn = pgnElement ? pgnElement.value.trim() : "";

    if (!pgn) {
      setText("status", "Paste a PGN first.");
      return;
    }

    setText("status", "Loading game...");

    try {
      const response = await fetch("/api/parse-pgn", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ pgn })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not load PGN.");
      }

      game = data;
      currentPly = 0;
      lastAnalysis = null;

      if ($("analysis")) {
        $("analysis").innerHTML =
          '<div class="empty">Run Stockfish analysis to generate the report.</div>';
      }

      goToPly(0);
      setText("status", `Loaded ${data.moves.length} ply.`);
    } catch (error) {
      game = null;
      currentPly = 0;
      lastAnalysis = null;

      renderBoard();
      renderMoves();
      updateControls();

      setText("status", error.message || "Could not load PGN.");
    }
  }

  function makeBadge(label) {
    return `<span class="badge ${safeClass(label)}">${escapeHtml(
      label
    )}</span>`;
  }

  async function requestRoast(item) {
    const modeElement = $("roastMode");
    const mode = modeElement ? modeElement.value : "off";

    if (mode === "off" || !item) return;

    try {
      const response = await fetch("/api/roast", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          label: item.label,
          san: item.san,
          intensity: mode
        })
      });

      const data = await response.json();

      if (!response.ok) return;

      const ply = String(item.ply ?? "").replace(/[^0-9]/g, "");
      const target = document.querySelector(
        `[data-roast-ply="${ply}"]`
      );

      if (target) {
        target.innerHTML =
          `<b>Coach:</b> ${escapeHtml(data.roast || "")}<br>` +
          `<b>Fix:</b> ${escapeHtml(data.advice || "")}`;
      }
    } catch (_) {
      // Optional feature. Do not break the main report.
    }
  }

  function renderIssue(item) {
    const issue = item || {};
    const explanation = issue.explanation || {};
    const label = issue.label || "Unknown";
    const ply = String(issue.ply ?? "").replace(/[^0-9]/g, "");

    return `
      <article class="issue ${safeClass(label)}">
        <div class="issue-top">
          <strong>
            ${escapeHtml(issue.move_number ?? "?")}${issue.side === "White" ? "." : "..."}
            ${escapeHtml(issue.san || "?")}
          </strong>
          ${makeBadge(label)}
        </div>

        <div class="issue-stats">
          <span>
            Loss:
            <b>${escapeHtml(issue.loss_cp ?? "n/a")} cp</b>
          </span>

          <span>
            Best:
            <b>${escapeHtml(issue.best_move_san || "n/a")}</b>
          </span>

          <span>
            Eval:
            <b>
              ${escapeHtml(issue.eval_before ?? "n/a")}
              →
              ${escapeHtml(issue.eval_after ?? "n/a")}
            </b>
          </span>
        </div>

        ${
          explanation.headline
            ? `<p><b>What happened:</b> ${escapeHtml(
                explanation.headline
              )}</p>`
            : ""
        }

        ${
          explanation.why
            ? `<p><b>Why:</b> ${escapeHtml(explanation.why)}</p>`
            : ""
        }

        ${
          explanation.lesson
            ? `<p><b>Lesson:</b> ${escapeHtml(explanation.lesson)}</p>`
            : ""
        }

        <div class="roast" data-roast-ply="${ply}"></div>
      </article>
    `;
  }

  function renderAnalysis(data) {
    const report = data || {};
    const summary = report.summary || {};

    const moves = Array.isArray(report.moves) ? report.moves : [];
    const critical = Array.isArray(report.critical)
      ? report.critical
      : [];
    const blunders = Array.isArray(report.blunder_breakdown)
      ? report.blunder_breakdown
      : [];
    const turningPoints = Array.isArray(report.turning_points)
      ? report.turning_points
      : [];

    const counts = [
      ["Brilliant", summary.brilliant],
      ["Good", summary.good],
      ["Inaccuracy", summary.inaccuracies],
      ["Mistake", summary.mistakes],
      ["Blunder", summary.blunders]
    ];

    const countHtml = counts
      .map(
        ([label, count]) =>
          `<div class="summary-card">
            <span>${escapeHtml(label)}</span>
            <strong>${escapeHtml(count ?? 0)}</strong>
          </div>`
      )
      .join("");

    const breakdownHtml = blunders.length
      ? blunders.map(renderIssue).join("")
      : '<div class="empty">No blunders detected at this depth. Good work.</div>';

    const criticalHtml = critical.length
      ? critical.map(renderIssue).join("")
      : '<div class="empty">No inaccuracies, mistakes, or blunders detected.</div>';

    const turningHtml = turningPoints.length
      ? turningPoints.map(renderIssue).join("")
      : '<div class="empty">No major turning points detected.</div>';

    const bestHtml = report.best_move
      ? renderIssue(report.best_move)
      : '<div class="empty">No move data.</div>';

    const worstHtml = report.worst_move
      ? renderIssue(report.worst_move)
      : '<div class="empty">No move data.</div>';

    const allMovesHtml = moves.length
      ? moves.map(renderIssue).join("")
      : '<div class="empty">No move data.</div>';

    const analysisElement = $("analysis");
    if (!analysisElement) return;

    analysisElement.innerHTML = `
      <section class="report-section">
        <h3>Move Classification</h3>
        <div class="summary-grid">${countHtml}</div>
      </section>

      <section class="report-section">
        <h3>⚠️ Blunder Breakdown</h3>
        ${breakdownHtml}
      </section>

      <section class="report-section">
        <h3>🎯 Turning Points</h3>
        ${turningHtml}
      </section>

      <section class="report-section">
        <h3>📌 Best Move</h3>
        ${bestHtml}
      </section>

      <section class="report-section">
        <h3>💥 Worst Move</h3>
        ${worstHtml}
      </section>

      <section class="report-section">
        <h3>🔎 Critical Mistakes</h3>
        ${criticalHtml}
      </section>

      <section class="report-section">
        <h3>📋 Full Move-by-Move Breakdown</h3>
        <div class="all-moves">${allMovesHtml}</div>
      </section>
    `;

    renderMoves();

    const roastMode = $("roastMode");

    if (roastMode && roastMode.value !== "off") {
      moves.forEach(requestRoast);
    }
  }

  async function runAnalysis() {
    const pgnElement = $("pgn");
    const pgn = pgnElement ? pgnElement.value.trim() : "";

    if (!pgn) {
      setText("status", "Paste a PGN first.");
      return;
    }

    setText("status", "Stockfish is calculating every move...");

    if ($("analysis")) {
      $("analysis").innerHTML =
        '<div class="empty">Analyzing the full game...</div>';
    }

    try {
      const depthElement = $("depth");
      const depth = depthElement
        ? Number(depthElement.value) || 12
        : 12;

      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ pgn, depth })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Analysis failed.");
      }

      lastAnalysis = data;
      window.lastReport = data;
      window.analysisReport = data;

      renderAnalysis(data);

      if (game) {
        goToPly(currentPly);
      }

      setText(
        "status",
        `Analysis complete: ${data.summary?.total_moves ?? 0} moves classified.`
      );
    } catch (error) {
      setText("status", error.message || "Analysis failed.");

      if ($("analysis")) {
        $("analysis").innerHTML =
          `<div class="empty">${escapeHtml(
            error.message || "Analysis failed."
          )}</div>`;
      }
    }
  }

  async function engineStatus() {
    try {
      const response = await fetch("/api/engine-status");
      const status = await response.json();

      const element = $("engineStatus");
      if (!element) return;

      element.textContent = status.available
        ? "● Stockfish online"
        : "○ Stockfish unavailable";

      element.className = status.available ? "online" : "offline";
    } catch (_) {
      setText("engineStatus", "○ Engine status unknown");
    }
  }

  async function uploadScreenshot() {
    const input = $("screenshotInput");
    const file = input?.files?.[0];

    if (!file) {
      setText("screenshotStatus", "Choose a screenshot first.");
      return;
    }

    const formData = new FormData();
    formData.append("image", file);

    setText("screenshotStatus", "Uploading screenshot...");

    try {
      const response = await fetch("/api/screenshot", {
        method: "POST",
        body: formData
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Screenshot processing failed."
        );
      }

      setText(
        "screenshotStatus",
        data.message || "Screenshot processed."
      );
    } catch (error) {
      setText(
        "screenshotStatus",
        error.message || "Screenshot processing failed."
      );
    }
  }

  function init() {
    const bindings = [
      ["loadBtn", loadGame],
      ["analyzeBtn", runAnalysis],
      ["firstBtn", () => goToPly(0)],
      ["prevBtn", () => goToPly(currentPly - 1)],
      ["nextBtn", () => goToPly(currentPly + 1)],
      ["lastBtn", () => goToPly(game ? game.moves.length : 0)],
      ["uploadScreenshotBtn", uploadScreenshot]
    ];

    bindings.forEach(([id, handler]) => {
      const element = $(id);

      if (element) {
        element.addEventListener("click", handler);
      }
    });

    renderBoard();
    renderMoves();
    updateControls();
    engineStatus();
  }

  window.ChessCoach = {
    loadGame,
    runAnalysis,
    uploadScreenshot,
    goToPly
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, {
      once: true
    });
  } else {
    init();
  }
})();
