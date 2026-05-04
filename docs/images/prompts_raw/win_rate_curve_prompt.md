# Raw Prompt: Win Rate Curve (胜率曲线图)

## Purpose
A scientific data-visualization chart showing how Agent A's win rate changes across different token budgets (400–2000 tokens, plus 20K reasoning mode) for three models: DeepSeek Flash, DeepSeek Pro, and Kimi v2.6.

## Data Points to Visualize

### DeepSeek Flash (standard)
- 400: 2.5% win
- 600: 12.5%
- 800: 9.8%
- 1000: 32.5%
- 1200: 34.1%
- 1400: 32.5%
- 1600: 32.5%
- 1800: 45.0%
- 2000: 34.9%

### DeepSeek Pro (standard)
- 400: 12.5%
- 600: 55.0%
- 800: 37.5%
- 1000: 60.0%
- 1200: 70.7%
- 1400: 52.5%
- 1600: 52.5%
- 1800: 55.0%
- 2000: 65.0%

### Kimi v2.6
- 400: 0%
- 600: 46.2%
- 800: 58.8%
- 1000: 46.9%
- 1200: 51.4%
- 1400: 55.0%
- 1600: 75.0%
- 1800: 50.0%
- 2000: 50.0%

## Visual Requirements

- Chart type: Line chart with markers (scatter-line hybrid)
- X-axis: Token budget (400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000)
- Y-axis: Win rate (0% to 100%)
- Three colored lines, one per model
- Background: Light gray grid
- Highlight the three zones with subtle background colors:
  - Dead Zone (400-800): Light red tint
  - Transition Zone (800-1200): Light gold/yellow tint
  - Plateau (1200+): Light green tint
- Annotations:
  - Label "Dead Zone" on the left
  - Label "Transition Zone" in the middle with an arrow
  - Label "Plateau" on the right
  - Vertical dashed line at 1000-1200 marking "Pareto Optimal"
- Title: "Win Rate vs Token Budget" / "胜率随 Token 预算变化"
- Legend: Bottom or right side
- Style: Clean, academic, minimalist, suitable for a research README
