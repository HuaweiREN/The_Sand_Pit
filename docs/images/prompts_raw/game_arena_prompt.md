# Raw Prompt: Game Arena Diagram (游戏场景示意图)

## Purpose
A top-down / bird's-eye-view diagram of the 50×50 grid arena showing Agent A (pursuer), Agent B (target), the wall obstacle, capture radii, and movement ranges. This should function as an infographic-style game board illustration.

## Scene Composition

### Arena
- A 50×50 square grid, light sand-colored background (#F5F5DC)
- Grid lines: Subtle light gray, every 5 units slightly darker for readability
- Coordinate labels on axes (0, 10, 20, 30, 40, 50)

### Wall (精确坐标)
- 墙体是一个矩形障碍物，坐标范围：**x=25.0 ~ 26.0, y=10.0 ~ 48.0**
- 厚度：**1.0 单位**（x 方向）
- 高度：**38.0 单位**（y 方向）
- 颜色：深灰 (#374151)，斜线阴影填充
- **注意：墙体并未贯穿整个地图**，上下两端各有一个天然缺口：
  - **下方缺口**：y = 0 ~ 10（高度 10，较宽）
  - **上方缺口**：y = 48 ~ 50（高度 2，较窄）
- Agent A 必须从上方或下方缺口绕行，无法直接穿透墙体

### Agent A (Pursuer — Sand Crab)
- Position: Left side of the wall, approximately (5, 25)
- Icon: A small sand crab emoji-style illustration or simplified top-down crab shape
- Color: Warm sand (#D4A373) with coral red claw highlight (#E76F51)
- Movement indicator: A dashed circle around Agent A showing max move range (3.0 units radius)
- Capture radius: A smaller solid circle around Agent A (0.5 units radius)
- Label: "Agent A (Pursuer)" with arrow

### Agent B (Target — Sea Anemone)
- Position: Right side of the wall, approximately (40, 25)
- Icon: A small sea anemone emoji-style illustration or simplified top-down anemone shape
- Color: Pink (#F4A3C0) with magenta tentacle tips (#E85D8A)
- Capture radius: A larger circle around Agent B (3.0 units radius, dotted line)
- Label: "Agent B (Target)" with arrow

### Perception Radius
- A large dotted circle around Agent A (10.0 units radius)
- Label: "Perception = 10.0"

### Phase 2 绕行路径（认知瓶颈）
- Agent A 初始在 (5, 25)，直线路径会被墙体（x=25~26, y=10~48）阻挡
- 由于 Agent A 在 y=25 处，距离下方缺口（y=10）约 15 单位，距离上方缺口（y=48）约 23 单位
- **最优路径**：向下绕行 → 穿过下方缺口 → 再向上接近 Agent B
- 路径箭头（珊瑚红虚线 #E76F51）：
  1. 从 (5, 25) 向下走到 (5, 8) 附近
  2. 向右水平穿过下方缺口（x: 5→26, y≈8）
  3. 再向右上方走向 Agent B (40, 25)
- 在路径旁标注 "P2: Cognitive Bottleneck" / "P2: 认知瓶颈"

## Visual Style
- Top-down bird's eye view, isometric or flat 2D
- Clean, diagrammatic, educational infographic style
- Light ocean/water tint overlay on the entire grid (subtle teal #E0F7FA at 20% opacity)
- Clear labels with clean sans-serif font
- Legend in one corner explaining symbols

## Legend Items
- Solid small circle = Agent A capture radius (0.5)
- Dashed circle = Agent A movement range (3.0)
- Dotted large circle = Agent A perception (10.0)
- Dotted circle = Agent B capture radius (3.0)
- Dashed arrow = Optimal path around wall

## Text Elements
- Title: "The Sand Pit Arena" / "沙盘竞技场"
- Subtitle: "50×50 Grid Pursuit Game" / "50×50 网格追逐博弈"
- Wall label: "Wall (25~26, 10~48)" / "岩墙 (25~26, 10~48)"
- Lower gap label: "Lower Gap (y=0~10)" / "下方缺口 (y=0~10)"
- Upper gap label: "Upper Gap (y=48~50)" / "上方缺口 (y=48~50)"
- Path label: "P2 Detour (Lower Gap)" / "P2 绕行（下方缺口）"
