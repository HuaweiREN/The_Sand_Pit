# Raw Prompt: Game Arena Diagram (游戏场景示意图)

## Purpose
A top-down / bird's-eye-view diagram of the 50×50 grid arena showing Agent A (pursuer), Agent B (target), the wall obstacle, capture radii, and movement ranges. This should function as an infographic-style game board illustration.

## Scene Composition

### Arena
- A 50×50 square grid, light sand-colored background (#F5F5DC)
- Grid lines: Subtle light gray, every 5 units slightly darker for readability
- Coordinate labels on axes (0, 10, 20, 30, 40, 50)

### Wall
- A vertical wall running from top to bottom at x=25
- Gray-brown color (#6C757D), with a small gap (narrow passage) around y=25
- Wall is impassable except through the gap

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

### Direction / Flow
- A curved arrow showing Agent A's intended path: starts at Agent A, curves around the wall gap, then curves toward Agent B
- Arrow style: Dashed, coral red (#E76F51)

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
- Wall label: "Wall (x=25)" / "岩墙 (x=25)"
- Gap label: "Gap" / "缺口"
