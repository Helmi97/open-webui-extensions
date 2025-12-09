"""
title: 🐍 Snake Mini Game
author: Helmi Chaouachi
git_url: https://github.com/Helmi97/open-webui-extensions/tree/main/snake
description: A minimalist Snake mini game tool with WASD controls.
required_open_webui_version: 0.4.0
requirements:
version: 1.2.0
licence: MIT
"""

from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        speed: float = Field(
            default=1.0,
            ge=0.5,
            le=2.0,
            description="Initial speed multiplier (0.5x to 2.0x).",
        )
        wrap_mode: bool = Field(
            default=False,
            description="Start with wrap-around walls enabled.",
        )
        cols: int = Field(
            default=46,
            ge=20,
            le=200,
            description="Initial number of columns in the grid (width).",
        )
        rows: int = Field(
            default=20,
            ge=10,
            le=40,
            description="Initial number of rows in the grid (height).",
        )
        cell_size: int = Field(
            default=18,
            ge=10,
            le=40,
            description="Pixel size of each grid cell.",
        )
        save_scores: bool = Field(
            default=True,
            description="Persist best score in browser localStorage.",
        )
        difficulty: str = Field(
            default="normal",
            description="Difficulty preset (affects base speed).",
            json_schema_extra={"enum": ["easy", "normal", "hard"]},
        )

    def __init__(self):
        self.valves = self.Valves()

    def start_snake_game(self) -> HTMLResponse:
        v = self.valves

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Snake Mini Game</title>
  <style>
    * {{
      box-sizing: border-box;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}

    body {{
      margin: 0;
      padding: 10px;
      background: #020617;
      color: #e5e7eb;
      display: flex;
      justify-content: center;
    }}

    .wrapper {{
      width: 100%;
      max-width: 1100px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}

    h1 {{
      margin: 0 0 4px 0;
      font-size: 16px;
      text-align: center;
      color: #e5e7eb;
    }}

    .subtitle {{
      margin: 0 0 8px 0;
      font-size: 11px;
      text-align: center;
      color: #9ca3af;
    }}

    .game-card {{
      position: relative;
      max-width: 100%;
      border-radius: 12px;
      padding: 10px;
      background: radial-gradient(circle at top, #1f2937 0, #020617 55%);
      box-shadow: 0 10px 24px rgba(0, 0, 0, 0.7);
      transition: box-shadow 0.2s ease-out;
    }}

    .game-card.focused {{
      box-shadow:
        0 0 18px rgba(16, 185, 129, 0.45),
        0 0 6px rgba(16, 185, 129, 0.6),
        0 10px 24px rgba(0, 0, 0, 0.7);
    }}

    .hud {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      font-size: 12px;
      color: #d1d5db;
      gap: 8px;
      flex-wrap: wrap;
    }}

    .hud-left {{
      display: flex;
      flex-direction: column;
      gap: 2px;
    }}

    .hud-row {{
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .pill {{
      padding: 2px 8px;
      border-radius: 999px;
      border: 1px solid rgba(52, 211, 153, 0.7);
      background: rgba(6, 95, 70, 0.2);
      font-size: 11px;
      color: #a7f3d0;
    }}

    .btn {{
      font-size: 11px;
      padding: 3px 9px;
      border-radius: 999px;
      border: 1px solid #4b5563;
      background: #020617;
      color: #e5e7eb;
      cursor: pointer;
      white-space: nowrap;
    }}
    .btn:hover {{
      background: #030712;
    }}

    .icon-btn {{
      width: 22px;
      height: 22px;
      border-radius: 999px;
      border: 1px solid #4b5563;
      background: #020617;
      color: #9ca3af;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      cursor: pointer;
      padding: 0;
    }}
    .icon-btn:hover {{
      background: #030712;
      color: #e5e7eb;
    }}

    .canvas-wrapper {{
      position: relative;
      border-radius: 10px;
      overflow: hidden;
      border: 1px solid #1f2933;
      background: #020617;
      /* width and height set by JS via canvas size */
    }}

    canvas {{
      display: block;
    }}

    .status {{
      margin-top: 6px;
      font-size: 15px;
      color: #9ca3af;
      text-align: center;
    }}

    .overlay {{
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      pointer-events: none; /* keep this */
    }}
    
    .overlay-content {{
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(248, 250, 252, 0.15);
      font-size: 12px;
      color: #e5e7eb;
      backdrop-filter: blur(3px);
    
      display: inline-flex;
      align-items: center;
      gap: 8px;
    
      pointer-events: auto;
    }}

    .settings-backdrop {{
      position: absolute;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(4px);
      z-index: 30;
    }}

    .settings-modal {{
      width: 260px;
      max-width: 90%;
      border-radius: 12px;
      background: #020617;
      border: 1px solid #1f2937;
      padding: 10px 12px 12px;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.8);
      font-size: 11px;
    }}

    .settings-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }}

    .settings-title {{
      font-size: 12px;
      font-weight: 500;
      color: #e5e7eb;
    }}

    .settings-body {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 8px;
    }}

    .settings-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
    }}

    .settings-row label {{
      color: #9ca3af;
      font-size: 11px;
    }}

    .settings-row input[type="number"],
    .settings-row select {{
      font-size: 11px;
      padding: 2px 4px;
      border-radius: 6px;
      border: 1px solid #4b5563;
      background: #020617;
      color: #e5e7eb;
      width: 70px;
    }}

    .settings-row input[type="range"] {{
      flex: 1;
    }}

    .settings-row .speed-value {{
      width: 40px;
      text-align: right;
      color: #e5e7eb;
      font-variant-numeric: tabular-nums;
    }}

    .settings-footer {{
      display: flex;
      justify-content: flex-end;
      gap: 6px;
    }}

    .settings-row input[type="checkbox"] {{
      transform: scale(0.88);
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <h1>🐍 Snake 🐍</h1>
    <div class="game-card" id="game-card">
      <div class="hud">
        <div class="hud-left">
          <div class="hud-row">
            <span>Score: <span id="score">0</span></span>
            <span>·</span>
            <span>Best: <span id="best">0</span></span>
          </div>
        </div>
        <div style="display:flex; align-items:center; gap:6px;">
          <button class="icon-btn" id="settings-btn" title="Settings">⚙</button>
          <button class="icon-btn" id="restart-btn" title="Restart">↻</button>
        </div>
      </div>

      <div class="canvas-wrapper" id="canvas-wrapper">
        <canvas id="game"></canvas>
        <div class="overlay" id="overlay" style="display:none;">
          <div class="overlay-content">
            <span id="overlay-label">Game over</span>
            <button class="btn" id="overlay-restart">↻</button>
          </div>
        </div>
      </div>

      <div class="status" id="status">
        Press 🅆 🄰 🅂 🄳 to start, Space to pause
      </div>

      <div class="settings-backdrop" id="settings-backdrop">
        <div class="settings-modal" id="settings-modal">
          <div class="settings-header">
            <div class="settings-title">Settings</div>
            <button class="icon-btn" id="settings-close" title="Close">✕</button>
          </div>
          <div class="settings-body">
            <div class="settings-row">
              <label for="difficulty-input">Difficulty</label>
              <select id="difficulty-input">
                <option value="easy">Easy</option>
                <option value="normal">Normal</option>
                <option value="hard">Hard</option>
              </select>
            </div>
            <div class="settings-row">
              <label for="speed-input">Speed</label>
              <input id="speed-input" type="range" min="0.5" max="2.0" step="0.1" />
              <div class="speed-value" id="speed-value">1.0x</div>
            </div>
            <div class="settings-row">
              <label for="wrap-input">Wrap walls</label>
              <input id="wrap-input" type="checkbox" />
            </div>
            <div class="settings-row">
              <label for="cols-input">Cols</label>
              <input id="cols-input" type="number" min="20" max="200" />
            </div>
            <div class="settings-row">
              <label for="rows-input">Rows</label>
              <input id="rows-input" type="number" min="10" max="40" />
            </div>
            <div class="settings-row">
              <label for="cell-size-input">Cell size</label>
              <input id="cell-size-input" type="number" min="10" max="40" />
            </div>
            <div class="settings-row">
              <label for="save-scores-input">Save best score</label>
              <input id="save-scores-input" type="checkbox" />
            </div>
          </div>
          <div class="settings-footer">
            <button class="btn" id="settings-apply">Apply</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    (function () {{
      const TOOL_DEFAULTS = {{
        speed: {v.speed},
        wrapMode: {str(v.wrap_mode).lower()},
        cols: {v.cols},
        rows: {v.rows},
        cellSize: {v.cell_size},
        saveScores: {str(v.save_scores).lower()},
        difficulty: "{v.difficulty.lower()}",
      }};

      const STORAGE_KEY = "snake_best_v1";

      const gameCard = document.getElementById("game-card");
      const canvasWrapper = document.getElementById("canvas-wrapper");
      const canvas = document.getElementById("game");
      const scoreEl = document.getElementById("score");
      const bestEl = document.getElementById("best");
      const statusEl = document.getElementById("status");
      const restartBtn = document.getElementById("restart-btn");
      const overlay = document.getElementById("overlay");
      const overlayLabel = document.getElementById("overlay-label");
      const overlayRestart = document.getElementById("overlay-restart");


      const settingsBtn = document.getElementById("settings-btn");
      const settingsBackdrop = document.getElementById("settings-backdrop");
      const settingsClose = document.getElementById("settings-close");
      const settingsApply = document.getElementById("settings-apply");

      const difficultyInput = document.getElementById("difficulty-input");
      const speedInput = document.getElementById("speed-input");
      const speedValue = document.getElementById("speed-value");
      const wrapInput = document.getElementById("wrap-input");
      const colsInput = document.getElementById("cols-input");
      const rowsInput = document.getElementById("rows-input");
      const cellSizeInput = document.getElementById("cell-size-input");
      const saveScoresInput = document.getElementById("save-scores-input");

      const MIN_COLS_HARD_LIMIT = 20;
      const MIN_ROWS_HARD_LIMIT = 10;

      const BASE_TICK_BY_DIFF = {{
        easy: 130,
        normal: 110,
        hard: 90,
      }};

      let ctx;
      let snake;
      let direction;
      let nextDirection;
      let food;
      let score = 0;
      let best = 0;
      let running = false;
      let paused = false;
      let lastTick = 0;
      let gameOverFlag = false;

      let cols = Math.max(MIN_COLS_HARD_LIMIT, TOOL_DEFAULTS.cols || MIN_COLS_HARD_LIMIT);
      let rows = Math.max(MIN_ROWS_HARD_LIMIT, TOOL_DEFAULTS.rows || 20);
      let cellSize = TOOL_DEFAULTS.cellSize || 18;
      let currentSpeed = TOOL_DEFAULTS.speed || 1.0;
      let wrapMode = !!TOOL_DEFAULTS.wrapMode;
      let saveScores = !!TOOL_DEFAULTS.saveScores;
      let difficulty = ["easy","normal","hard"].includes(TOOL_DEFAULTS.difficulty) ? TOOL_DEFAULTS.difficulty : "normal";
      let tickMs = 110;

      function updateTiming() {{
        const base = BASE_TICK_BY_DIFF[difficulty] || BASE_TICK_BY_DIFF.normal;
        tickMs = base / (currentSpeed || 1.0);
      }}

      function setupCanvas() {{
        const widthPx = cols * cellSize;
        const heightPx = rows * cellSize;

        canvas.width = widthPx;
        canvas.height = heightPx;
        canvasWrapper.style.width = widthPx + "px";
        canvasWrapper.style.height = heightPx + "px";

        ctx = canvas.getContext("2d");
      }}

      function syncSettingsUI() {{
        difficultyInput.value = difficulty;
        speedInput.value = currentSpeed.toFixed(1);
        speedValue.textContent = currentSpeed.toFixed(1) + "x";
        wrapInput.checked = wrapMode;
        colsInput.value = cols.toString();
        rowsInput.value = rows.toString();
        cellSizeInput.value = cellSize.toString();
        saveScoresInput.checked = saveScores;
      }}

      function loadBestFromStorage() {{
        if (!saveScores || !("localStorage" in window)) return;
        try {{
          const raw = window.localStorage.getItem(STORAGE_KEY);
          const n = raw ? parseInt(raw, 10) : NaN;
          if (!Number.isNaN(n) && n > 0) {{
            best = n;
            bestEl.textContent = best.toString();
          }}
        }} catch (_) {{}}
      }}

      function saveBestToStorage() {{
        if (!saveScores || !("localStorage" in window)) return;
        try {{
          window.localStorage.setItem(STORAGE_KEY, String(best));
        }} catch (_) {{}}
      }}

      function resetGame() {{
        const midRow = Math.floor(rows / 2);
        const midCol = Math.floor(cols / 2);

        snake = [
          {{ x: midCol - 1, y: midRow }},
          {{ x: midCol,     y: midRow }},
        ];

        direction = {{ x: 1, y: 0 }};
        nextDirection = {{ x: 1, y: 0 }};

        score = 0;
        scoreEl.textContent = score.toString();

        running = false;
        paused = false;
        gameOverFlag = false;
        lastTick = 0;

        statusEl.textContent = "Press 🅆 🄰 🅂 🄳 to start, Space to pause";

        overlay.style.display = "none";

        spawnFood();
        draw();
      }}

      function spawnFood() {{
        while (true) {{
          const x = Math.floor(Math.random() * cols);
          const y = Math.floor(Math.random() * rows);
          if (!snake.some(seg => seg.x === x && seg.y === y)) {{
            food = {{ x, y }};
            break;
          }}
        }}
      }}

      function setDirection(dx, dy) {{
        if (direction && dx === -direction.x && dy === -direction.y) return;

        if (gameOverFlag) resetGame();

        nextDirection = {{ x: dx, y: dy }};

        if (!running) {{
          running = true;
          paused = false;
          statusEl.textContent = wrapMode
            ? "Wrap mode on. Avoid your own tail."
            : "Avoid the walls and your own tail.";
        }}
      }}

      function handleKey(e) {{
        const key = e.key.toLowerCase();

        if (key === " ") {{
          if (running && !gameOverFlag) {{
            paused = !paused;

            if (paused) {{
              statusEl.textContent = "Paused - press Space to resume";
            }} else {{
              statusEl.textContent = wrapMode
                ? "Wrap mode on. Avoid your own tail."
                : "Avoid the walls and your own tail.";
            }}
          }}
          return;
        }}

        if (key === "w") setDirection(0, -1);
        else if (key === "s") setDirection(0, 1);
        else if (key === "a") setDirection(-1, 0);
        else if (key === "d") setDirection(1, 0);
      }}

      function update() {{
        direction = nextDirection;
        const head = snake[snake.length - 1];
        let newHead = {{
          x: head.x + direction.x,
          y: head.y + direction.y,
        }};

        if (wrapMode) {{
          newHead.x = (newHead.x + cols) % cols;
          newHead.y = (newHead.y + rows) % rows;
        }} else {{
          if (
            newHead.x < 0 ||
            newHead.y < 0 ||
            newHead.x >= cols ||
            newHead.y >= rows
          ) {{
            gameOver();
            return;
          }}
        }}

        if (snake.some(seg => seg.x === newHead.x && seg.y === newHead.y)) {{
          gameOver();
          return;
        }}

        snake.push(newHead);

        if (newHead.x === food.x && newHead.y === food.y) {{
          score += 1;
          scoreEl.textContent = score.toString();
          if (score > best) {{
            best = score;
            bestEl.textContent = best.toString();
            saveBestToStorage();
          }}
          spawnFood();
        }} else {{
          snake.shift();
        }}
      }}

      function gameOver() {{
        running = false;
        paused = false;
        gameOverFlag = true;

        statusEl.textContent = "You crashed - press Restart or 🅆 🄰 🅂 🄳 to try again";

        overlayLabel.textContent = "Game over";
        overlay.style.display = "flex";

      }}

      function drawCell(x, y, color) {{
        ctx.fillStyle = color;
        ctx.fillRect(x * cellSize, y * cellSize, cellSize, cellSize);
      }}

      function drawGrid() {{
        ctx.strokeStyle = "rgba(15, 23, 42, 0.7)";
        ctx.lineWidth = 1;

        ctx.beginPath();
        for (let i = 0; i <= cols; i++) {{
          const p = Math.round(i * cellSize) + 0.5;
          ctx.moveTo(p, 0);
          ctx.lineTo(p, canvas.height);
        }}
        for (let j = 0; j <= rows; j++) {{
          const p = Math.round(j * cellSize) + 0.5;
          ctx.moveTo(0, p);
          ctx.lineTo(canvas.width, p);
        }}
        ctx.stroke();
      }}

      function draw() {{
        if (!ctx || !snake || !food) return;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const gradient = ctx.createRadialGradient(
          canvas.width * 0.5,
          canvas.height * 0.2,
          0,
          canvas.width * 0.5,
          canvas.height * 0.5,
          canvas.width * 0.8
        );
        gradient.addColorStop(0, "#020617");
        gradient.addColorStop(1, "#020617");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        drawGrid();
        drawCell(food.x, food.y, "#22c55e");

        for (let i = 0; i < snake.length; i++) {{
          const seg = snake[i];
          const isHead = i === snake.length - 1;
          drawCell(seg.x, seg.y, isHead ? "#fbbf24" : "#38bdf8");
        }}
      }}

      function loop(timestamp) {{
        requestAnimationFrame(loop);

        if (!running || paused) {{
          draw();
          return;
        }}

        const delta = timestamp - lastTick;
        if (delta >= tickMs) {{
          lastTick = timestamp;
          update();
          draw();
        }}
      }}

      function openSettings() {{
        paused = true;
        settingsBackdrop.style.display = "flex";
        syncSettingsUI();
      }}

      function closeSettings() {{
        settingsBackdrop.style.display = "none";
      }}

      settingsBtn.addEventListener("click", openSettings);
      settingsClose.addEventListener("click", closeSettings);
      settingsBackdrop.addEventListener("click", (e) => {{
        if (e.target === settingsBackdrop) closeSettings();
      }});

      speedInput.addEventListener("input", () => {{
        const v = parseFloat(speedInput.value) || 1.0;
        speedValue.textContent = v.toFixed(1) + "x";
      }});

      settingsApply.addEventListener("click", () => {{
        const newDiff = difficultyInput.value;
        difficulty = ["easy","normal","hard"].includes(newDiff) ? newDiff : difficulty;

        const newSpeed = parseFloat(speedInput.value);
        if (!Number.isNaN(newSpeed) && newSpeed >= 0.5 && newSpeed <= 2.0) {{
          currentSpeed = newSpeed;
        }}

        wrapMode = wrapInput.checked;

        const newCols = parseInt(colsInput.value, 10);
        if (!Number.isNaN(newCols) && newCols >= MIN_COLS_HARD_LIMIT && newCols <= 200) {{
          cols = newCols;
        }}

        const newRows = parseInt(rowsInput.value, 10);
        if (!Number.isNaN(newRows) && newRows >= MIN_ROWS_HARD_LIMIT && newRows <= 40) {{
          rows = newRows;
        }}

        const newCellSize = parseInt(cellSizeInput.value, 10);
        if (!Number.isNaN(newCellSize) && newCellSize >= 10 && newCellSize <= 40) {{
          cellSize = newCellSize;
        }}

        saveScores = saveScoresInput.checked;

        updateTiming();
        setupCanvas();
        resetGame();
        loadBestFromStorage();
        closeSettings();
      }});

      restartBtn.addEventListener("click", () => {{
        resetGame();
      }});

      overlayRestart.addEventListener("click", () => {{
        resetGame();
      }});


      window.addEventListener("keydown", handleKey);

      window.addEventListener("blur", () => {{
        gameCard.classList.remove("focused");

        if (running && !gameOverFlag) {{
          paused = true;
          statusEl.textContent = "Out of focus - click back to resume";
        }}
      }});

      window.addEventListener("focus", () => {{
        gameCard.classList.add("focused");

        if (paused && running && !gameOverFlag) {{
          paused = false;
          statusEl.textContent = wrapMode
            ? "Wrap mode on. Avoid your own tail."
            : "Avoid the walls and your own tail.";
        }}
      }});

      // Init
      updateTiming();
      setupCanvas();
      resetGame();
      loadBestFromStorage();
      requestAnimationFrame(loop);
    }})();
  </script>
</body>
</html>"""

        headers = {
            "Content-Disposition": "inline",
            "Content-Type": "text/html; charset=utf-8",
        }
        return HTMLResponse(content=html_content, headers=headers)
