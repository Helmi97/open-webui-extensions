"""
title: 🐥 Flappy Bird Mini Game
author: Helmi Chaouachi
git_url: https://github.com/Helmi97/open-webui-extensions/tree/main/flappy_bird
description: A Flappy Bird style mini game with random pipe widths, gaps, and spacing, difficulty-based speed scaling, and configurable behavior via Open WebUI valves.
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
            description="Global speed multiplier (0.5x to 2.0x).",
        )
        gravity: float = Field(
            default=0.4,
            ge=0.2,
            le=1.0,
            description="Gravity strength applied each frame.",
        )
        jump_force: float = Field(
            default=-7.5,
            ge=-15.0,
            le=-3.0,
            description="Upward velocity applied on flap.",
        )
        min_gap: int = Field(
            default=90,
            ge=60,
            le=220,
            description="Minimum vertical gap between pipes.",
        )
        max_gap: int = Field(
            default=140,
            ge=70,
            le=260,
            description="Maximum vertical gap between pipes.",
        )
        min_pipe_distance: int = Field(
            default=150,
            ge=80,
            le=400,
            description="Minimum horizontal distance between pipes (px).",
        )
        max_pipe_distance: int = Field(
            default=260,
            ge=100,
            le=500,
            description="Maximum horizontal distance between pipes (px).",
        )
        min_pipe_width: int = Field(
            default=45,
            ge=30,
            le=120,
            description="Minimum pipe width (px).",
        )
        max_pipe_width: int = Field(
            default=65,
            ge=35,
            le=140,
            description="Maximum pipe width (px).",
        )
        save_scores: bool = Field(
            default=True,
            description="Persist best score in browser localStorage.",
        )
        difficulty: str = Field(
            default="normal",
            description="Difficulty preset (base speed and scaling).",
            json_schema_extra={"enum": ["easy", "normal", "hard"]},
        )

    def __init__(self):
        self.valves = self.Valves()

    def start_flappy_bird(self) -> HTMLResponse:
        v = self.valves

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Flappy Bird Mini Game</title>
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
      max-width: 480px;
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
        0 0 18px rgba(59, 130, 246, 0.45),
        0 0 6px rgba(59, 130, 246, 0.6),
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
    }}

    canvas {{
      display: block;
    }}

    .status {{
      margin-top: 6px;
      font-size: 11px;
      color: #9ca3af;
      text-align: center;
    }}

    .overlay {{
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      pointer-events: none;
    }}

    .overlay-content {{
      padding: 6px 12px;
      border-radius: 999px;
      background: rgba(15, 23, 42, 0.85);
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
      width: 280px;
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
      flex-wrap: wrap;
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

    .settings-row .value-label {{
      width: 50px;
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

    .settings-row .inline-inputs {{
      display: flex;
      gap: 4px;
      align-items: center;
    }}
    .settings-row .inline-inputs span {{
      font-size: 10px;
      color: #6b7280;
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <h1>Flappy Bird</h1>
    <p class="subtitle">Space or click to flap · Avoid the pipes</p>

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
        Press Space or click inside the game to start
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
              <div class="value-label" id="speed-value">1.0x</div>
            </div>

            <div class="settings-row">
              <label for="gravity-input">Gravity</label>
              <input id="gravity-input" type="range" min="0.2" max="1.0" step="0.05" />
              <div class="value-label" id="gravity-value">0.40</div>
            </div>

            <div class="settings-row">
              <label for="jump-input">Jump</label>
              <input id="jump-input" type="range" min="-15" max="-3" step="0.5" />
              <div class="value-label" id="jump-value">-7.5</div>
            </div>

            <div class="settings-row">
              <label>Gap (min / max)</label>
              <div class="inline-inputs">
                <input id="gap-min-input" type="number" min="60" max="260" />
                <span>/</span>
                <input id="gap-max-input" type="number" min="70" max="260" />
              </div>
            </div>

            <div class="settings-row">
              <label>Distance (min / max)</label>
              <div class="inline-inputs">
                <input id="dist-min-input" type="number" min="80" max="500" />
                <span>/</span>
                <input id="dist-max-input" type="number" min="100" max="500" />
              </div>
            </div>

            <div class="settings-row">
              <label>Width (min / max)</label>
              <div class="inline-inputs">
                <input id="width-min-input" type="number" min="30" max="140" />
                <span>/</span>
                <input id="width-max-input" type="number" min="35" max="140" />
              </div>
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
        gravity: {v.gravity},
        jumpForce: {v.jump_force},
        minGap: {v.min_gap},
        maxGap: {v.max_gap},
        minPipeDistance: {v.min_pipe_distance},
        maxPipeDistance: {v.max_pipe_distance},
        minPipeWidth: {v.min_pipe_width},
        maxPipeWidth: {v.max_pipe_width},
        saveScores: {str(v.save_scores).lower()},
        difficulty: "{v.difficulty.lower()}",
      }};

      const STORAGE_KEY = "flappy_best_v1";

      const gameCard = document.getElementById("game-card");
      const canvasWrapper = document.getElementById("canvas-wrapper");
      const canvas = document.getElementById("game");
      const scoreEl = document.getElementById("score");
      const bestEl = document.getElementById("best");
      const statusEl = document.getElementById("status");

      const overlay = document.getElementById("overlay");
      const overlayLabel = document.getElementById("overlay-label");
      const overlayRestart = document.getElementById("overlay-restart");

      const restartBtn = document.getElementById("restart-btn");
      const settingsBtn = document.getElementById("settings-btn");
      const settingsBackdrop = document.getElementById("settings-backdrop");
      const settingsClose = document.getElementById("settings-close");
      const settingsApply = document.getElementById("settings-apply");

      const difficultyInput = document.getElementById("difficulty-input");
      const speedInput = document.getElementById("speed-input");
      const speedValue = document.getElementById("speed-value");
      const gravityInput = document.getElementById("gravity-input");
      const gravityValue = document.getElementById("gravity-value");
      const jumpInput = document.getElementById("jump-input");
      const jumpValue = document.getElementById("jump-value");
      const gapMinInput = document.getElementById("gap-min-input");
      const gapMaxInput = document.getElementById("gap-max-input");
      const distMinInput = document.getElementById("dist-min-input");
      const distMaxInput = document.getElementById("dist-max-input");
      const widthMinInput = document.getElementById("width-min-input");
      const widthMaxInput = document.getElementById("width-max-input");
      const saveScoresInput = document.getElementById("save-scores-input");

      const WIDTH = 320;
      const HEIGHT = 480;
      const GROUND_HEIGHT = 40;
      const BIRD_X = 80;

      const BASE_PIPE_CONFIG = {{
        easy:   {{ baseSpeed: 1.6, accelPerScore: 0.03 }},
        normal: {{ baseSpeed: 2.1, accelPerScore: 0.05 }},
        hard:   {{ baseSpeed: 2.6, accelPerScore: 0.08 }},
      }};

      let ctx;

      let birdY;
      let birdVy;

      let pipes = [];
      let score = 0;
      let best = 0;

      let running = false;
      let paused = false;
      let gameOverFlag = false;
      let lastTime = 0;

      let animTime = 0;
      let lastFlapAt = 0;

      let speedMultiplier = TOOL_DEFAULTS.speed || 1.0;
      let gravity = TOOL_DEFAULTS.gravity || 0.4;
      let jumpForce = TOOL_DEFAULTS.jumpForce || -7.5;

      let minGap = TOOL_DEFAULTS.minGap || 90;
      let maxGap = TOOL_DEFAULTS.maxGap || 140;
      if (minGap > maxGap) [minGap, maxGap] = [maxGap, minGap];

      let minPipeDistance = TOOL_DEFAULTS.minPipeDistance || 150;
      let maxPipeDistance = TOOL_DEFAULTS.maxPipeDistance || 260;
      if (minPipeDistance > maxPipeDistance) [minPipeDistance, maxPipeDistance] = [maxPipeDistance, minPipeDistance];

      let minPipeWidth = TOOL_DEFAULTS.minPipeWidth || 45;
      let maxPipeWidth = TOOL_DEFAULTS.maxPipeWidth || 65;
      if (minPipeWidth > maxPipeWidth) [minPipeWidth, maxPipeWidth] = [maxPipeWidth, minPipeWidth];

      let saveScores = !!TOOL_DEFAULTS.saveScores;
      let difficulty = ["easy","normal","hard"].includes(TOOL_DEFAULTS.difficulty) ? TOOL_DEFAULTS.difficulty : "normal";

      let pipeSpeed = 2.0;
      let distanceSinceLastPipePx = 0;
      let nextPipeDistancePx = 0;

      function randInRange(min, max) {{
        return Math.random() * (max - min) + min;
      }}

      function pickNextPipeDistance() {{
        let minD = Math.max(80, Math.min(minPipeDistance, maxPipeDistance));
        let maxD = Math.max(minD + 10, Math.max(minPipeDistance, maxPipeDistance));

        const maxW = Math.max(minPipeWidth, maxPipeWidth);
        const safeMin = Math.max(minD, maxW + 20);
        const safeMax = Math.max(safeMin + 10, maxD);

        nextPipeDistancePx = randInRange(safeMin, safeMax);
      }}

      function setupCanvas() {{
        canvas.width = WIDTH;
        canvas.height = HEIGHT;
        canvasWrapper.style.width = WIDTH + "px";
        canvasWrapper.style.height = HEIGHT + "px";
        ctx = canvas.getContext("2d");
      }}

      function syncSettingsUI() {{
        difficultyInput.value = difficulty;

        speedInput.value = speedMultiplier.toFixed(1);
        speedValue.textContent = speedMultiplier.toFixed(1) + "x";

        gravityInput.value = gravity.toFixed(2);
        gravityValue.textContent = gravity.toFixed(2);

        jumpInput.value = jumpForce;
        jumpValue.textContent = jumpForce.toFixed(1);

        gapMinInput.value = minGap.toString();
        gapMaxInput.value = maxGap.toString();
        distMinInput.value = minPipeDistance.toString();
        distMaxInput.value = maxPipeDistance.toString();
        widthMinInput.value = minPipeWidth.toString();
        widthMaxInput.value = maxPipeWidth.toString();

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
        birdY = HEIGHT / 2;
        birdVy = 0;

        pipes = [];
        score = 0;
        scoreEl.textContent = "0";

        running = false;
        paused = false;
        gameOverFlag = false;
        lastTime = 0;
        animTime = 0;
        lastFlapAt = 0;

        distanceSinceLastPipePx = 0;
        pickNextPipeDistance();

        statusEl.textContent = "Press Space or click inside the game to start";

        overlay.style.display = "none";

        spawnPipe();
        draw(animTime);
      }}

      function flap() {{
        if (gameOverFlag) {{
          resetGame();
          return;
        }}
        if (!running) {{
          running = true;
          paused = false;
          statusEl.textContent = "Flap through the gaps and avoid the ground";
        }}
        birdVy = jumpForce;
        lastFlapAt = animTime;
      }}

      function spawnPipe() {{
        const groundY = HEIGHT - GROUND_HEIGHT;
        const margin = 40;

        let gapHMin = Math.max(60, Math.min(minGap, maxGap));
        let gapHMax = Math.max(gapHMin + 10, Math.max(minGap, maxGap));
        let gapHeight = randInRange(gapHMin, gapHMax);

        const maxGapHeightAllowed = groundY - margin * 2;
        if (gapHeight > maxGapHeightAllowed) gapHeight = maxGapHeightAllowed;

        const maxTop = groundY - margin - gapHeight;
        const minTop = margin;
        const gapTop = randInRange(minTop, maxTop);

        let wMin = Math.max(30, Math.min(minPipeWidth, maxPipeWidth));
        let wMax = Math.max(wMin + 5, Math.max(minPipeWidth, maxPipeWidth));
        const pipeWidth = randInRange(wMin, wMax);

        pipes.push({{
          x: WIDTH + pipeWidth,
          width: pipeWidth,
          gapTop,
          gapHeight,
          scored: false,
        }});
      }}

      function update(dt) {{
        if (!running || paused || gameOverFlag) return;

        const cfg = BASE_PIPE_CONFIG[difficulty] || BASE_PIPE_CONFIG.normal;
        pipeSpeed = (cfg.baseSpeed + cfg.accelPerScore * score) * (speedMultiplier || 1.0);

        birdVy += gravity;
        birdY += birdVy;

        const groundY = HEIGHT - GROUND_HEIGHT;
        if (birdY + 10 >= groundY || birdY - 10 <= 0) {{
          gameOver();
          return;
        }}

        for (let i = 0; i < pipes.length; i++) {{
          pipes[i].x -= pipeSpeed * dt;
        }}

        while (pipes.length && pipes[0].x + pipes[0].width < 0) {{
          pipes.shift();
        }}

        const birdRadius = 10;
        const birdLeft = BIRD_X - birdRadius;
        const birdRight = BIRD_X + birdRadius;
        const birdTop = birdY - birdRadius;
        const birdBottom = birdY + birdRadius;

        for (let i = 0; i < pipes.length; i++) {{
          const p = pipes[i];

          const pipeLeft = p.x;
          const pipeRight = p.x + p.width;
          const gapTop = p.gapTop;
          const gapBottom = p.gapTop + p.gapHeight;

          const horizontallyOverlapping = birdRight > pipeLeft && birdLeft < pipeRight;
          const verticallyOutsideGap = birdTop < gapTop || birdBottom > gapBottom;

          if (horizontallyOverlapping && verticallyOutsideGap) {{
            gameOver();
            return;
          }}

          if (!p.scored && pipeRight < BIRD_X) {{
            p.scored = true;
            score += 1;
            scoreEl.textContent = score.toString();
            if (score > best) {{
              best = score;
              bestEl.textContent = best.toString();
              saveBestToStorage();
            }}
          }}
        }}

        distanceSinceLastPipePx += pipeSpeed * dt;
        if (distanceSinceLastPipePx >= nextPipeDistancePx) {{
          distanceSinceLastPipePx = 0;
          pickNextPipeDistance();
          spawnPipe();
        }}
      }}

      function gameOver() {{
        running = false;
        paused = false;
        gameOverFlag = true;

        statusEl.textContent = "You crashed. Press Restart, Space, or click to try again";

        overlayLabel.textContent = "Game over";
        overlay.style.display = "flex";
      }}

      function drawBackground() {{
        const gradient = ctx.createLinearGradient(0, 0, 0, HEIGHT);
        gradient.addColorStop(0, "#0f172a");
        gradient.addColorStop(0.6, "#1f2937");
        gradient.addColorStop(1, "#0b1120");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, WIDTH, HEIGHT);
      }}

      function drawGround() {{
        const y = HEIGHT - GROUND_HEIGHT;
        ctx.fillStyle = "#064e3b";
        ctx.fillRect(0, y, WIDTH, GROUND_HEIGHT);
        ctx.fillStyle = "#16a34a";
        ctx.fillRect(0, y, WIDTH, 6);
      }}

      function drawPipes() {{
        const groundY = HEIGHT - GROUND_HEIGHT;
        ctx.fillStyle = "#22c55e";

        for (let i = 0; i < pipes.length; i++) {{
          const p = pipes[i];

          const pipeLeft = p.x;
          const pipeWidth = p.width;
          const gapTop = p.gapTop;
          const gapBottom = p.gapTop + p.gapHeight;

          const clampedGapTop = Math.max(0, Math.min(gapTop, groundY));
          const clampedGapBottom = Math.max(0, Math.min(gapBottom, groundY));

          const topHeight = clampedGapTop;
          const bottomHeight = groundY - clampedGapBottom;

          if (topHeight > 0) {{
            ctx.fillRect(pipeLeft, 0, pipeWidth, topHeight);
          }}

          if (bottomHeight > 0) {{
            ctx.fillRect(pipeLeft, clampedGapBottom, pipeWidth, bottomHeight);
          }}
        }}
      }}

      function drawBird(t) {{
        const r = 11;
        const centerX = BIRD_X;
        const centerY = birdY;

        const tilt = Math.max(-0.4, Math.min(0.9, birdVy / 9));

        const baseWave = Math.sin(t * 0.25) * 0.25;
        const sinceFlap = t - lastFlapAt;
        const flapBoost = Math.max(0, 1 - sinceFlap / 8);
        const wingAngle = baseWave + flapBoost * 0.9;

        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(tilt);

        ctx.beginPath();
        ctx.arc(0, 0, r, 0, Math.PI * 2);
        ctx.closePath();
        ctx.fillStyle = "#facc15";
        ctx.fill();

        ctx.beginPath();
        ctx.arc(-3, 3, r * 0.7, Math.PI * 0.2, Math.PI * 1.1);
        ctx.strokeStyle = "rgba(0,0,0,0.15)";
        ctx.lineWidth = 2;
        ctx.stroke();

        ctx.save();
        ctx.translate(-3, 0);
        ctx.rotate(wingAngle);
        ctx.beginPath();
        if (ctx.roundRect) {{
          ctx.roundRect(-6, -4, 12, 8, 3);
        }} else {{
          ctx.rect(-6, -4, 12, 8);
        }}
        ctx.fillStyle = "#eab308";
        ctx.fill();
        ctx.restore();

        ctx.beginPath();
        ctx.arc(4, -4, 3.2, 0, Math.PI * 2);
        ctx.fillStyle = "#f9fafb";
        ctx.fill();

        ctx.beginPath();
        ctx.arc(5, -4.3, 1.6, 0, Math.PI * 2);
        ctx.fillStyle = "#020617";
        ctx.fill();

        ctx.fillStyle = "#f97316";
        ctx.beginPath();
        ctx.moveTo(r, -1);
        ctx.lineTo(r + 7, -4);
        ctx.lineTo(r + 7, 2);
        ctx.closePath();
        ctx.fill();

        ctx.restore();
      }}

      function draw(t) {{
        if (!ctx) return;

        ctx.clearRect(0, 0, WIDTH, HEIGHT);

        drawBackground();
        drawPipes();
        drawGround();
        drawBird(t || 0);
      }}

      function loop(timestamp) {{
        requestAnimationFrame(loop);

        if (lastTime === 0) {{
          lastTime = timestamp;
          animTime = 0;
          draw(animTime);
          return;
        }}

        const dt = (timestamp - lastTime) / 16.67;
        lastTime = timestamp;

        animTime += dt;

        if (!running || paused) {{
          draw(animTime);
          return;
        }}

        update(dt);
        draw(animTime);
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

      gravityInput.addEventListener("input", () => {{
        const v = parseFloat(gravityInput.value) || 0.4;
        gravityValue.textContent = v.toFixed(2);
      }});

      jumpInput.addEventListener("input", () => {{
        const v = parseFloat(jumpInput.value) || -7.5;
        jumpValue.textContent = v.toFixed(1);
      }});

      settingsApply.addEventListener("click", () => {{
        const newDiff = difficultyInput.value;
        difficulty = ["easy","normal","hard"].includes(newDiff) ? newDiff : difficulty;

        const newSpeed = parseFloat(speedInput.value);
        if (!Number.isNaN(newSpeed) && newSpeed >= 0.5 && newSpeed <= 2.0) {{
          speedMultiplier = newSpeed;
        }}

        const newGravity = parseFloat(gravityInput.value);
        if (!Number.isNaN(newGravity) && newGravity >= 0.2 && newGravity <= 1.0) {{
          gravity = newGravity;
        }}

        const newJump = parseFloat(jumpInput.value);
        if (!Number.isNaN(newJump) && newJump >= -15 && newJump <= -3) {{
          jumpForce = newJump;
        }}

        let gMin = parseInt(gapMinInput.value, 10);
        let gMax = parseInt(gapMaxInput.value, 10);
        if (!Number.isNaN(gMin) && !Number.isNaN(gMax)) {{
          gMin = Math.max(60, Math.min(260, gMin));
          gMax = Math.max(70, Math.min(260, gMax));
          if (gMin > gMax) [gMin, gMax] = [gMax, gMin];
          minGap = gMin;
          maxGap = gMax;
        }}

        let dMin = parseInt(distMinInput.value, 10);
        let dMax = parseInt(distMaxInput.value, 10);
        if (!Number.isNaN(dMin) && !Number.isNaN(dMax)) {{
          dMin = Math.max(80, Math.min(500, dMin));
          dMax = Math.max(100, Math.min(500, dMax));
          if (dMin > dMax) [dMin, dMax] = [dMax, dMin];
          minPipeDistance = dMin;
          maxPipeDistance = dMax;
        }}

        let wMin = parseInt(widthMinInput.value, 10);
        let wMax = parseInt(widthMaxInput.value, 10);
        if (!Number.isNaN(wMin) && !Number.isNaN(wMax)) {{
          wMin = Math.max(30, Math.min(140, wMin));
          wMax = Math.max(35, Math.min(140, wMax));
          if (wMin > wMax) [wMin, wMax] = [wMax, wMin];
          minPipeWidth = wMin;
          maxPipeWidth = wMax;
        }}

        saveScores = saveScoresInput.checked;

        const maxW = Math.max(minPipeWidth, maxPipeWidth);
        if (minPipeDistance <= maxW + 10) {{
          minPipeDistance = maxW + 10;
        }}
        if (maxPipeDistance <= minPipeDistance + 10) {{
          maxPipeDistance = minPipeDistance + 10;
        }}

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

      function handleKey(e) {{
        const key = e.key.toLowerCase();
        if (key === " " || key === "spacebar") {{
          e.preventDefault();
          flap();
        }}
      }}

      function handleClick() {{
        flap();
      }}

      window.addEventListener("keydown", handleKey);
      canvasWrapper.addEventListener("click", handleClick);

      window.addEventListener("blur", () => {{
        gameCard.classList.remove("focused");
        if (running && !gameOverFlag) {{
          paused = true;
          statusEl.textContent = "Out of focus. Click back or press Space to resume";
        }}
      }});

      window.addEventListener("focus", () => {{
        gameCard.classList.add("focused");
        if (paused && running && !gameOverFlag) {{
          paused = false;
          statusEl.textContent = "Flap through the gaps and avoid the ground";
        }}
      }});

      // Init
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
