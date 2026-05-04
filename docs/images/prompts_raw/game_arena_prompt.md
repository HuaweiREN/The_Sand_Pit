# Raw Prompt: Game Arena Diagram (游戏场景示意图) — Pure 2D Top-Down

## Purpose
A **pure 2D top-down / bird's-eye-view** diagram of the 50×50 grid arena. No isometric, no 3D, no perspective. Camera is directly above the grid looking straight down.

## Scene Composition

### Arena
- A 50×50 square grid, light sand-colored background (#F5F5DC)
- Grid lines: Subtle light gray, every 5 units slightly darker for readability
- Coordinate labels on all four edges: 0, 10, 20, 30, 40, 50
- Pure 2D flat view — all elements viewed from directly above

### Wall (精确坐标)
- 墙体是一个矩形障碍物，在 2D 俯视图上显示为一个**填充矩形块**
- 坐标范围：**x=25.0 ~ 26.0, y=10.0 ~ 48.0**
- 厚度：**1.0 单位**（x 方向）
- 在 y 轴上跨度：**10.0 ~ 48.0**
- 颜色：深灰 (#374151)，斜线阴影填充，明确标注四边坐标
- **注意：墙体并未贯穿整个地图**，上下两端各有一个天然缺口：
  - **下方缺口**：y = 0 ~ 10（x 方向完全开放）
  - **上方缺口**：y = 48 ~ 50（x 方向完全开放）
- 在图上清晰标注墙体四角坐标：(25,10), (26,10), (26,48), (25,48)

### Agent A (Pursuer — Sand Crab)
- Position: Left side of wall, approximately (5, 25)
- Icon: **Flat 2D top-down crab icon** — viewed directly from above, no side profile
  - Carapace: Warm sand color (#D4A373), roughly oval shape
  - Left claw: Coral red highlight (#E76F51), visible as asymmetric bulge on left side
- Movement indicator: A **flat dashed circle** on the 2D grid, radius = 3.0 units
- Capture radius: A **flat smaller solid circle**, radius = 0.5 units
- Perception radius: A **flat large dotted circle**, radius = 10.0 units
- All circles are pure 2D — no sphere-like shading

### Agent B (Target — Sea Anemone)
- Position: Right side of wall, approximately (40, 25)
- Icon: **Flat 2D top-down anemone icon** — viewed directly from above
  - Base: Teal rock (#A8DADC), circular shape
  - Tentacles: Pink gradient (#F4A3C0 to #E85D8A), shown as radiating petals in 2D top-down view
- Capture radius: A **flat dotted circle** on the 2D grid, radius = 3.0 units

### Phase 2 绕行路径（认知瓶颈）— 2D 平面箭头
- Agent A 初始在 (5, 25)，直线路径会被墙体（x=25~26, y=10~48）阻挡
- **2D 平面上的最优绕行路径**：
  1. 从 (5, 25) **向下**走到 (5, 8) 附近（接近下方缺口）
  2. **水平向右**穿过下方缺口（y≈8, x: 5→26）
  3. 从 (26, 8) **向右上**走向 Agent B (40, 25)
- 用**平面虚线箭头**在网格上标注完整路径，珊瑚红色 (#E76F51)
- 路径分段标注：P1（绿色）→ P2（黄色，绕行段）→ P3（绿色）→ P4（红色）

## Visual Style
- **Pure 2D top-down view**, flat infographic style
- No isometric, no 3D, no perspective distortion
- Clean, diagrammatic, technical blueprint aesthetic
- Light ocean/water tint overlay on grid (#E0F7FA at 20% opacity)
- Clear labels with clean sans-serif font
- Legend in one corner explaining symbols

## Legend Items
- Solid small circle = Agent A capture radius (0.5)
- Dashed circle = Agent A movement range (3.0)
- Dotted large circle = Agent A perception (10.0)
- Dotted circle = Agent B capture radius (3.0)
- Dashed arrow = Optimal path through lower gap
- Filled rectangle with hatch = Wall obstacle

## Text Elements
- Title: "The Sand Pit Arena" / "沙盘竞技场"
- Subtitle: "50×50 Grid Pursuit Game — Top-Down View" / "50×50 网格追逐博弈 — 俯视图"
- Wall label: "Wall (25~26, 10~48)" / "岩墙 (25~26, 10~48)"
- Lower gap: "Lower Gap (y=0~10)" / "下方缺口 (y=0~10)"
- Upper gap: "Upper Gap (y=48~50)" / "上方缺口 (y=48~50)"
- Path label: "P2 Detour (Lower Gap)" / "P2 绕行（下方缺口）"
