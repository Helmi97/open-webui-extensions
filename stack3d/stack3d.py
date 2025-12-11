"""
title: 🧱 Stack 3D Mini Game
author: Helmi Chaouachi

git_url: https://github.com/Helmi97/open-webui-extensions/tree/main/stack3d
description: A sleek and satisfying 3D stacking game built directly into OpenWebUI.
required_open_webui_version: 0.4.0
requirements:
version: 1.1.0
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
            description="Global slide speed multiplier (0.5x to 2.0x).",
        )
        drop_altitude: float = Field(
            default=0.5,
            ge=0.0,
            le=5.0,
            description="Vertical distance between tower top and bottom of new block.",
        )
        ping_pong: bool = Field(
            default=False,
            description="If true, blocks move back and forth over the tower instead of passing once.",
        )
        save_scores: bool = Field(
            default=True,
            description="Persist best score in browser localStorage.",
        )
        difficulty: str = Field(
            default="normal",
            description="Difficulty preset (tolerance and speed curve).",
            json_schema_extra={"enum": ["easy", "normal", "hard"]},
        )

    def __init__(self):
        self.valves = self.Valves()

    def start_stack_game(self) -> HTMLResponse:
        v = self.valves

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Stack 3D Mini Game</title>
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
      max-width: 520px;
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
      width: 320px;
      height: 480px;
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
      flex-wrap: wrap;
    }}

    .settings-row label {{
      color: #9ca3af;
      font-size: 11px;
    }}

    .settings-row select,
    .settings-row input[type="checkbox"],
    .settings-row input[type="range"] {{
      cursor: pointer;
    }}

    .settings-row select {{
      font-size: 11px;
      padding: 2px 4px;
      border-radius: 6px;
      border: 1px solid #4b5563;
      background: #020617;
      color: #e5e7eb;
      width: 90px;
    }}

    .settings-row input[type="range"] {{
      flex: 1;
    }}

    .settings-row .value-label {{
      width: 60px;
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
      transform: scale(0.9);
    }}
  </style>
</head>
<body>
  <div class="wrapper">
    <h1>Stack 3D</h1>
    <p class="subtitle">Click or press Space to time your drops and build the tower</p>

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
        <div class="overlay" id="overlay" style="display:none;">
          <div class="overlay-content">
            <span id="overlay-label">Game over</span>
            <button class="btn" id="overlay-restart">↻</button>
          </div>
        </div>
      </div>

      <div class="status" id="status">
        First click / Space starts the movement · next clicks drop blocks
      </div>

      <div class="settings-backdrop" id="settings-backdrop">
        <div class="settings-modal">
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
              <label for="drop-input">Drop height</label>
              <input id="drop-input" type="range" min="0" max="3" step="0.1" />
              <div class="value-label" id="drop-value">0.5</div>
            </div>

            <div class="settings-row">
              <label for="ping-input">Back and forth</label>
              <input id="ping-input" type="checkbox" />
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

  <script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>
  <script>
    (function () {{
      const TOOL_DEFAULTS = {{
        speed: {v.speed},
        dropAltitude: {v.drop_altitude},
        pingPong: {str(v.ping_pong).lower()},
        saveScores: {str(v.save_scores).lower()},
        difficulty: "{v.difficulty.lower()}",
      }};

      const STORAGE_KEY = "stack3d_best_v1";

      const gameCard = document.getElementById("game-card");
      const canvasWrapper = document.getElementById("canvas-wrapper");
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
      const dropInput = document.getElementById("drop-input");
      const dropValue = document.getElementById("drop-value");
      const pingInput = document.getElementById("ping-input");
      const saveScoresInput = document.getElementById("save-scores-input");

      const VIEW_WIDTH = 320;
      const VIEW_HEIGHT = 480;
      const LAYER_HEIGHT = 0.8;
      const START_SIZE = 3.0;

      const DIFF_CONFIG = {{
        easy:   {{ baseSpeed: 1.2, growth: 0.02, toleranceBoost: 0.35 }},
        normal: {{ baseSpeed: 1.6, growth: 0.04, toleranceBoost: 0.2 }},
        hard:   {{ baseSpeed: 2.0, growth: 0.06, toleranceBoost: 0.06 }},
      }};

      let renderer;
      let scene;
      let camera;
      let ambientLight;
      let keyLight;

      let tower = [];
      let scraps = [];

      let running = false;
      let gameOverFlag = false;
      let paused = false;

      let lastTime = 0;
      let currentDirection = "x";
      let slideSpeed = 1.5;
      let speedMultiplier = TOOL_DEFAULTS.speed || 1.0;
      let difficulty = ["easy","normal","hard"].includes(TOOL_DEFAULTS.difficulty) ? TOOL_DEFAULTS.difficulty : "normal";
      let saveScores = !!TOOL_DEFAULTS.saveScores;
      let dropAltitude = TOOL_DEFAULTS.dropAltitude || 0.5;
      let pingPong = !!TOOL_DEFAULTS.pingPong;

      let score = 0;
      let best = 0;

      function rand(min, max) {{
        return Math.random() * (max - min) + min;
      }}

      function setupRenderer() {{
        renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setPixelRatio(window.devicePixelRatio || 1);
        renderer.setSize(VIEW_WIDTH, VIEW_HEIGHT);
        renderer.setClearColor(0x020617, 1);
        canvasWrapper.innerHTML = "";
        canvasWrapper.appendChild(renderer.domElement);
      }}

      function setupScene() {{
        scene = new THREE.Scene();

        const aspect = VIEW_WIDTH / VIEW_HEIGHT;
        camera = new THREE.PerspectiveCamera(40, aspect, 0.1, 100);
        camera.position.set(6, 7, 10);
        camera.lookAt(new THREE.Vector3(0, 0, 0));

        ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        scene.add(ambientLight);

        keyLight = new THREE.DirectionalLight(0xffffff, 0.8);
        keyLight.position.set(6, 12, 6);
        scene.add(keyLight);

        tower = [];
        scraps = [];
      }}

      function getLayerColor(level) {{
        const baseHue = 160;
        const shift = (level * 11) % 180;
        const h = (baseHue + shift) % 360;
        const s = 65;
        const l = 52;
        const color = new THREE.Color();
        color.setHSL(h / 360, s / 100, l / 100);
        return color;
      }}

      function createLayerMesh(w, d, y, x, z, level) {{
        const geometry = new THREE.BoxGeometry(w, LAYER_HEIGHT, d);
        const material = new THREE.MeshStandardMaterial({{
          color: getLayerColor(level),
          roughness: 0.35,
          metalness: 0.05,
        }});
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.set(x, y, z);
        mesh.castShadow = false;
        mesh.receiveShadow = false;
        scene.add(mesh);
        return mesh;
      }}

      function addBaseLayer() {{
        const y = LAYER_HEIGHT * 0;
        const mesh = createLayerMesh(START_SIZE, START_SIZE, y, 0, 0, 0);
        tower.push({{
          mesh,
          width: START_SIZE,
          depth: START_SIZE,
          direction: null,
          slideDir: 0,
        }});
      }}

      function addMovingLayer() {{
        const level = tower.length;
        const prev = tower[tower.length - 1];

        // New block center Y so that the distance between previous top
        // and this block's bottom equals dropAltitude
        const y = prev.mesh.position.y + LAYER_HEIGHT + dropAltitude;

        currentDirection = currentDirection === "x" ? "z" : "x";
        const width = prev.width;
        const depth = prev.depth;

        const startOffset = 6;
        let x = prev.mesh.position.x;
        let z = prev.mesh.position.z;

        if (currentDirection === "x") {{
          x = prev.mesh.position.x - startOffset;
        }} else {{
          z = prev.mesh.position.z - startOffset;
        }}

        const mesh = createLayerMesh(width, depth, y, x, z, level);
        tower.push({{
          mesh,
          width,
          depth,
          direction: currentDirection,
          slideDir: 1,
        }});
      }}

      function spawnScrap(x, y, z, w, d, level, directionSign) {{
        if (w <= 0 || d <= 0) return;
        const mesh = createLayerMesh(w, d, y, x, z, level);
        scraps.push({{
          mesh,
          vy: rand(-0.2, -0.05),
          vx: 0,
          vz: 0,
          rx: rand(0.6, 1.3) * directionSign,
          rz: rand(0.4, 1.0) * directionSign,
        }});
      }}

        function placeLayer() {{
          if (gameOverFlag) {{
            resetGame();
            return;
          }}
        
          // First click starts the game
          if (!running) {{
            running = true;
            paused = false;
            statusEl.textContent = "Drop each block when it is centered on the tower";
            return;
          }}
        
          if (tower.length < 2) return;
        
          const top = tower[tower.length - 1];
          const prev = tower[tower.length - 2];
        
          const dir = top.direction;
          const size = dir === "x" ? top.width : top.depth;
        
          const posTop = top.mesh.position[dir];
          const posPrev = prev.mesh.position[dir];
        
          const delta = posTop - posPrev;
          const overlap = size - Math.abs(delta);
        
          const diffCfg = DIFF_CONFIG[difficulty] || DIFF_CONFIG.normal;
          const effectiveTolerance = size * (0.02 + diffCfg.toleranceBoost);
        
          // Miss
          if (overlap <= 0 || overlap < effectiveTolerance * 0.2) {{
            fail(top, prev);
            return;
          }}
        
          // New dimensions
          const newWidth = dir === "x" ? overlap : top.width;
          const newDepth = dir === "z" ? overlap : top.depth;
        
          const overhangSize = size - overlap;
          const sign = Math.sign(delta) || 1;
        
          // Scrap shift
          const overhangShift = (overlap / 2 + overhangSize / 2) * sign;
        
          let scrapX = top.mesh.position.x;
          let scrapZ = top.mesh.position.z;
        
          if (dir === "x") {{
            scrapX += overhangShift;
          }} else {{
            scrapZ += overhangShift;
          }}
        
          const scrapWidth = dir === "x" ? overhangSize : top.width;
          const scrapDepth = dir === "z" ? overhangSize : top.depth;
        
          // Final Y without any gap
          const snappedY = prev.mesh.position.y + LAYER_HEIGHT;
        
          // Spawn the scrap piece
          spawnScrap(
            scrapX,
            snappedY,
            scrapZ,
            scrapWidth,
            scrapDepth,
            tower.length,
            sign
          );
        
          // Apply new sizes
          if (dir === "x") {{
            top.width = newWidth;
          }} else {{
            top.depth = newDepth;
          }}
        
          // Scale & align horizontally
          const scaleFactor = overlap / size;
          top.mesh.scale[dir] = scaleFactor;
          top.mesh.position[dir] = posPrev + delta / 2;
        
          // Snap to tower top so there is ZERO gap
          top.mesh.position.y = snappedY;
        
          // Score update
          score += 1;
          scoreEl.textContent = String(score);
        
          if (score > best) {{
            best = score;
            bestEl.textContent = String(best);
            saveBest();
          }}
        
          // Spawn next moving layer at the proper height
          addMovingLayer();
        }}


      function fail(top, prev) {{
        gameOverFlag = true;
        running = false;
        paused = false;

        const dir = top.direction;
        const topY = top.mesh.position.y;
        const sign = 1;

        spawnScrap(
          top.mesh.position.x,
          topY,
          top.mesh.position.z,
          top.width,
          top.depth,
          tower.length,
          sign
        );

        scene.remove(top.mesh);
        tower.pop();

        statusEl.textContent = "You missed. Press Restart or Space to try again";
        overlayLabel.textContent = "Game over";
        overlay.style.display = "flex";
      }}

      function resetGame() {{
        score = 0;
        scoreEl.textContent = "0";
        gameOverFlag = false;
        running = false;
        paused = false;
        lastTime = 0;
        currentDirection = "x";

        overlay.style.display = "none";
        statusEl.textContent = "First click / Space starts the movement · next clicks drop blocks";

        tower.forEach(l => scene.remove(l.mesh));
        scraps.forEach(s => scene.remove(s.mesh));
        tower = [];
        scraps = [];

        addBaseLayer();
        addMovingLayer();

        camera.position.set(6, 7, 10);
        camera.lookAt(new THREE.Vector3(0, LAYER_HEIGHT * 1.5, 0));
      }}

      function moveTopLayer(dt) {{
        if (!running || gameOverFlag || tower.length < 2) return;

        const cfg = DIFF_CONFIG[difficulty] || DIFF_CONFIG.normal;
        slideSpeed = (cfg.baseSpeed + cfg.growth * score) * (speedMultiplier || 1.0);

        const top = tower[tower.length - 1];
        const prev = tower[tower.length - 2];
        const dir = top.direction;

        if (!dir) return;

        if (typeof top.slideDir !== "number" || top.slideDir === 0) {{
          top.slideDir = 1;
        }}

        let pos = top.mesh.position[dir];
        const move = top.slideDir * slideSpeed * dt;
        pos += move;

        if (pingPong) {{
          const maxOffset = 4.0;
          const center = prev.mesh.position[dir];
          const minPos = center - maxOffset;
          const maxPos = center + maxOffset;

          if (pos > maxPos) {{
            pos = maxPos;
            top.slideDir = -1;
          }} else if (pos < minPos) {{
            pos = minPos;
            top.slideDir = 1;
          }}

          top.mesh.position[dir] = pos;
        }} else {{
          top.mesh.position[dir] = pos;
          const limit = 7.0;
          if (Math.abs(top.mesh.position[dir]) > limit) {{
            fail(top, prev);
          }}
        }}
      }}

      function updateScraps(dt) {{
        const gravity = -9.8;
        const floorY = -10;

        for (let i = scraps.length - 1; i >= 0; i--) {{
          const s = scraps[i];
          s.vy += gravity * dt * 0.3;
          s.mesh.position.y += s.vy;
          s.mesh.position.x += s.vx * dt;
          s.mesh.position.z += s.vz * dt;
          s.mesh.rotation.x += s.rx * dt;
          s.mesh.rotation.z += s.rz * dt;

          if (s.mesh.position.y < floorY) {{
            scene.remove(s.mesh);
            scraps.splice(i, 1);
          }}
        }}
      }}

      function updateCamera(dt) {{
        const targetY = LAYER_HEIGHT * (tower.length + 1);
        const targetZ = 10 + Math.min(6, tower.length * 0.1);
        const lerpFactor = 1.5 * dt;

        camera.position.y += (targetY - camera.position.y) * lerpFactor;
        camera.position.z += (targetZ - camera.position.z) * lerpFactor;

        camera.lookAt(new THREE.Vector3(0, LAYER_HEIGHT * (tower.length - 0.5), 0));
      }}

      function loop(ts) {{
        requestAnimationFrame(loop);

        if (!lastTime) {{
          lastTime = ts;
          renderer.render(scene, camera);
          return;
        }}

        const dt = (ts - lastTime) / 1000;
        lastTime = ts;

        if (!paused) {{
          moveTopLayer(dt);
          updateScraps(dt);
          updateCamera(dt);
        }}

        renderer.render(scene, camera);
      }}

      function syncSettingsUI() {{
        difficultyInput.value = difficulty;
        speedInput.value = speedMultiplier.toFixed(1);
        speedValue.textContent = speedMultiplier.toFixed(1) + "x";
        dropInput.value = dropAltitude.toFixed(1);
        dropValue.textContent = dropAltitude.toFixed(1);
        pingInput.checked = pingPong;
        saveScoresInput.checked = saveScores;
      }}

      function loadBest() {{
        if (!saveScores || !("localStorage" in window)) return;
        try {{
          const raw = localStorage.getItem(STORAGE_KEY);
          const n = raw ? parseInt(raw, 10) : NaN;
          if (!Number.isNaN(n) && n > 0) {{
            best = n;
            bestEl.textContent = String(best);
          }}
        }} catch (_) {{}}
      }}

      function saveBest() {{
        if (!saveScores || !("localStorage" in window)) return;
        try {{
          localStorage.setItem(STORAGE_KEY, String(best));
        }} catch (_) {{}}
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

      dropInput.addEventListener("input", () => {{
        const v = parseFloat(dropInput.value) || 0;
        dropValue.textContent = v.toFixed(1);
      }});

      settingsApply.addEventListener("click", () => {{
        const newDiff = difficultyInput.value;
        difficulty = ["easy","normal","hard"].includes(newDiff) ? newDiff : difficulty;

        const newSpeed = parseFloat(speedInput.value);
        if (!Number.isNaN(newSpeed) && newSpeed >= 0.5 && newSpeed <= 2.0) {{
          speedMultiplier = newSpeed;
        }}

        const newDrop = parseFloat(dropInput.value);
        if (!Number.isNaN(newDrop) && newDrop >= 0 && newDrop <= 3) {{
          dropAltitude = newDrop;
        }}

        pingPong = !!pingInput.checked;
        saveScores = !!saveScoresInput.checked;

        resetGame();
        loadBest();
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
          placeLayer();
        }}
      }}

      function handleClick() {{
        placeLayer();
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
          statusEl.textContent = "Drop each block when it is centered on the tower";
        }}
      }});

      setupRenderer();
      setupScene();
      addBaseLayer();
      addMovingLayer();
      loadBest();
      syncSettingsUI();
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
