# 🐍 Snake Mini Game (OpenWebUI Tool)

A lightweight, fast, and fully configurable Snake game built as an **OpenWebUI tool**.  
Runs directly inside the interface with smooth controls, instant restarts, and customizable difficulty.

🎥 **Demo Video:**  
https://github.com/Helmi97/open-webui-extensions/tree/main/snake/raw/main/Screen%20Recording.mp4

---

## 🕹️ Gameplay
![Gameplay](./Screenshot%20Gameplay.png)

Move using **W A S D**, pause using **space**, avoid your tail, collect food, and climb the score counter.

---

## 🧩 Valves (Tool Configuration)
![Valves](./Screenshot%20Valves.png)

These parameters can be tuned directly from OpenWebUI’s tool settings:

| Valve         | Type    | Description |
|--------------|---------|-------------|
| `speed`      | float   | Speed multiplier (0.5–2.0). |
| `wrap_mode`  | boolean | Enable wrap-around edges. |
| `cols`       | int     | Board width in grid cells. |
| `rows`       | int     | Board height in grid cells. |
| `cell_size`  | int     | Pixel size per grid cell. |
| `save_scores`| boolean | Store best score in localStorage. |
| `difficulty` | enum    | Base speed preset (`easy`, `normal`, `hard`). |

---

## ⚙️ In-Game Settings Modal
![Settings](./Screenshot%20Settings.png)

Open the small **⚙️ gear icon** to tweak settings mid-session:

- Difficulty  
- Speed multiplier  
- Wrap mode  
- Grid width and height  
- Cell size  
- Best-score saving  

Press **Apply** to instantly reload the board with your new configuration.
