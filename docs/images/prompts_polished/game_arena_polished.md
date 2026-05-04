# Polished Prompt: The Sand Pit Arena Diagram
# Generated with baoyu-infographic (isometric-map layout × technical-schematic style)

Create a professional infographic following these specifications:

## Image Specifications

- **Type**: Infographic / Technical Diagram
- **Layout**: Isometric-Map — 3D-style spatial layout showing arena grid, obstacles, agent positions, and movement paths
- **Style**: Technical-Schematic — engineering precision with blueprint aesthetics, clean geometry, and dimension annotations
- **Aspect Ratio**: 4:3 (landscape)
- **Language**: Bilingual (English primary, Chinese secondary)

## Core Principles

- Follow the isometric-map layout precisely: consistent 30° angle, spatial relationships visible, bird's-eye view
- Apply technical-schematic aesthetics consistently: blueprint grid, dimension lines, technical symbols, all-caps labels
- Keep information concise; highlight spatial relationships and game mechanics
- Use ample whitespace for visual clarity; maintain clear visual hierarchy
- Preserve all measurements faithfully — grid size, coordinates, radii

## Text Requirements

- All text must match the technical-schematic style treatment: technical stencil or clean sans-serif, all-caps labels
- Main titles should be prominent and readable
- Key concepts ("Wall", "Perception", "Capture Radius") should be visually emphasized with callout lines
- Labels should be clear and appropriately sized
- Bilingual: English labels primary, Chinese annotations secondary in smaller size

## Layout Guidelines (Isometric-Map)

- Title block at top-left corner: "THE SAND PIT ARENA" / "沙盘竞技场"
- Main arena grid (center, 60% of frame): 50×50 grid in isometric 3D perspective
- Agent A zone (left of wall): Sand crab icon with movement/capture radii
- Agent B zone (right of wall): Sea anemone icon with capture radius
- Wall obstacle (center): Vertical barrier with gap
- Path indicator: Curved dashed arrow showing optimal route
- Legend panel (bottom-right or side): symbol explanations
- Coordinate rulers: X and Y axis markers (0, 10, 20, 30, 40, 50)

## Style Guidelines (Technical-Schematic)

### Color Palette
- Background: Deep blueprint blue (#1E3A5F) with white grid lines, OR light gray (#F5F5F5) with dark grid
- Primary: Blues (#2563EB), teals (#0891B2), grays
- Accents: Amber highlights (#F59E0B) for Agent A elements, cyan callouts (#06B6D4) for Agent B elements
- Wall: Dark charcoal (#374151) with hatch pattern
- Grid lines: Light gray (#D1D5DB) on light background, or white (#FFFFFF) at 30% opacity on blueprint background

### Visual Elements
- Geometric precision throughout: exact 30° isometric angle
- Grid pattern with coordinate markers every 5 units
- Dimension lines and measurement annotations (e.g., "50×50", "x=25", "3.0 units")
- Technical symbols: circles with cross-hair centers for radii, arrowheads for direction
- Clean vector shapes: no sketchy or organic lines
- Consistent stroke weights: hairlines for grid, medium for boundaries, thick for wall
- Callout lines with dots at attachment points, label boxes at endpoints
- Optional zoomed detail section for the wall gap

### Typography
- Technical stencil or clean sans-serif
- All-caps labels for major elements ("AGENT A", "AGENT B", "WALL")
- Measurement annotations in smaller size with unit suffix
- Floating labels for isometric elements
- Coordinate labels: "X=0", "X=25", "X=50", "Y=0", "Y=50"

### Style Enforcement
- Strictly systematic line weights and color usage
- Sufficient fine grid lines and coordinate annotations throughout
- Blueprint aesthetic: mix of macroscopic arena view and microscopic dimension details
- No cute or cartoonish doodles; maintain engineering precision

---

## Content — Scene Elements

### Arena Grid
- Square grid: 50×50 units
- Grid lines: Subtle, every 1 unit faint, every 5 units slightly darker
- Coordinate labels on all four edges: 0, 10, 20, 30, 40, 50
- Background fill: Very light sand color (#F5F5DC) inside grid area

### Wall Obstacle (精确坐标)
- Position: Rectangular obstacle spanning **x=25.0 to x=26.0, y=10.0 to y=48.0**
- Appearance: Dark gray (#374151), **1-unit thick**, with diagonal hatch pattern
- **Critical: The wall does NOT span the full map height**. Two natural gaps exist at both ends:
  - **Lower Gap**: y = 0 ~ 10 (height 10, wider) — labeled "LOWER GAP" / "下方缺口"
  - **Upper Gap**: y = 48 ~ 50 (height 2, narrower) — labeled "UPPER GAP" / "上方缺口"
- Wall label: "WALL (25~26, 10~48)" / "岩墙 (25~26, 10~48)"
- Note annotation: "Agent A must detour through upper or lower gap" / "Agent A 必须从上方或下方缺口绕行"

### Agent A — Sand Crab (Pursuer)
- Position: Left side of wall, approximately (5, 25)
- Icon: Simplified top-down isometric crab shape
  - Carapace: Warm sand color (#D4A373)
  - Left claw: Coral red highlight (#E76F51), oversized
  - Eyes: Two small amber dots (#F4A261)
- Movement range: Dashed circle, radius = 3.0 units, labeled "MOVE = 3.0"
- Capture radius: Smaller solid circle, radius = 0.5 units, labeled "CAPTURE A = 0.5"
- Perception radius: Large dotted circle, radius = 10.0 units, labeled "PERCEPTION = 10.0"
- Label: "AGENT A (PURSUER)" / "Agent A（追击者）"

### Agent B — Sea Anemone (Target)
- Position: Right side of wall, approximately (40, 25)
- Icon: Simplified top-down isometric anemone shape
  - Base: Teal rock (#A8DADC)
  - Tentacles: Pink gradient (#F4A3C0 to #E85D8A), radiating outward
- Capture radius: Dotted circle, radius = 3.0 units, labeled "CAPTURE B = 3.0"
- Label: "AGENT B (TARGET)" / "Agent B（目标）"

### Optimal Path & Phase 2 Detour (P2 绕行路径)
- Agent A starts at (5, 25). A straight path to Agent B at (40, 25) is blocked by the wall (x=25~26, y=10~48).
- From y=25, the distance to the lower gap (y=10) is ~15 units; to the upper gap (y=48) is ~23 units. The lower gap is closer.
- **Phase 2 path (cognitive bottleneck / 认知瓶颈)**:
  1. From (5, 25), move **downward** to approximately (5, 8) — approaching the lower gap
  2. Move **horizontally right** through the lower gap (x: 5→26, y≈8) — crossing to the other side of the wall
  3. From (26, 8), move **up and right** toward Agent B (40, 25)
- Arrow style: Coral red (#E76F51), dashed line, arrowhead at end near Agent B
- Path segmented with phase labels:
  - **P1** (green dot): (5,25) → descent start — "Phase 1: Straight Commute"
  - **P2** (yellow dot): downward detour + gap crossing — "Phase 2: Cognitive Bottleneck / 认知瓶颈"
  - **P3** (green dot): post-wall approach — "Phase 3: Open Field"
  - **P4** (red dot): final hunt near Agent B — "Phase 4: Parity Determinism"
- Label: "OPTIMAL PATH (Lower Gap Detour)" / "最优路径（下方缺口绕行）"

## Legend Panel

| Symbol | Meaning |
|--------|---------|
| Small solid circle | Agent A capture radius (0.5) |
| Dashed circle | Agent A movement range (3.0) |
| Large dotted circle | Agent A perception (10.0) |
| Dotted circle | Agent B capture radius (3.0) |
| Dashed arrow | Optimal path: lower gap detour (down → through y=0~10 → up) |

## Text Labels (Bilingual)

- Title: "THE SAND PIT ARENA" / "沙盘竞技场"
- Subtitle: "50×50 Grid Pursuit Game" / "50×50 网格追逐博弈"
- Wall: "WALL (25~26, 10~48)" / "岩墙 (25~26, 10~48)"
- Lower Gap: "LOWER GAP (y=0~10)" / "下方缺口 (y=0~10)"
- Upper Gap: "UPPER GAP (y=48~50)" / "上方缺口 (y=48~50)"
- Path: "OPTIMAL PATH (Lower Gap Detour)" / "最优路径（下方缺口绕行）"
- Agent A: "AGENT A (PURSUER)" / "Agent A（追击者）"
- Agent B: "AGENT B (TARGET)" / "Agent B（目标）"
- Move: "MOVE = 3.0"
- Capture A: "CAPTURE A = 0.5"
- Perception: "PERCEPTION = 10.0"
- Capture B: "CAPTURE B = 3.0"
- Path: "OPTIMAL PATH" / "最优路径"
- Max Rounds: "MAX ROUNDS = 50"
- Legend title: "LEGEND" / "图例"
