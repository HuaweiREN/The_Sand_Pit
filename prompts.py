"""
The Sand Pit - Prompt Engineering
Prompt strategy design: minimal and standard strategies.
Supports loading and updating templates from configuration files.
"""

import json
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config import get_config


def calculate_direction(self_pos: tuple, target_pos: tuple) -> str:
    """
    Calculate the cardinal direction of target relative to self.

    Args:
        self_pos: self coordinates (x, y)
        target_pos: target coordinates (x, y)

    Returns:
        Direction string: "E", "S", "W", "N", "SE", "NE", "SW", "NW"
    """
    dx = target_pos[0] - self_pos[0]
    dy = target_pos[1] - self_pos[1]

    import math
    angle = math.atan2(dy, dx)
    degrees = math.degrees(angle)

    if degrees < 0:
        degrees += 360

    if 5 <= degrees < 85:
        return "NE"
    elif 85 <= degrees < 95:
        return "N"
    elif 95 <= degrees < 175:
        return "NW"
    elif 175 <= degrees < 185:
        return "W"
    elif 185 <= degrees < 265:
        return "SW"
    elif 265 <= degrees < 275:
        return "S"
    elif 275 <= degrees < 355:
        return "SE"
    else:
        return "E"


@dataclass
class PromptContext:
    """Context required to build prompts."""
    agent_name: str
    current_pos: tuple
    opponent_pos: Optional[tuple]  # None if not visible
    distance_to_opponent: Optional[float]  # None if not visible
    perception_radius: float
    move_step: float
    capture_radius: float
    agent_b_capture_radius: float  # Agent B capture radius (asymmetric)
    map_size: int
    current_round: int
    max_rounds: int
    own_history: List[Dict]  # Last 5 rounds of own movement history
    sightings: List[Dict]  # All opponent sightings in this game
    token_budget: int
    is_first_actor: bool
    opponent_direction: Optional[str] = None  # N/S/E/W/NE/NW/SE/SW, updated every 5 rounds
    is_opponent_visible: bool = False
    rounds_until_next_update: int = 0
    walls: List[Dict] = None


class PromptTemplateManager:
    """
    Prompt template manager.
    Supports loading templates from config files and detecting config changes.
    """

    DEFAULT_MINIMAL_SYSTEM = """You are {agent_name} in a pursuit game.

Rules:
- Map: {map_size}x{map_size}
- Your step: 0 to {move_step:.2f} (you can move any distance from 0 to {move_step:.2f})
- Win: Distance ≤ {capture_radius:.2f}
- Opponent (Agent_B) is always static (never moves). Opponent capture radius: {agent_b_capture_radius:.2f}.
- Wall: There is an IMPENETRABLE wall at x=25, from y=10 to y=48. You CANNOT cross this wall. If your move would cross the wall or land inside it, you stay in place.

Output ONLY JSON: {{"x": <number>, "y": <number>}}"""

    DEFAULT_STANDARD_SYSTEM = """You are Agent_A, a strategic solver in a pursuit simulation.

## Environment
- Dynamics: You can move 0 to {move_step:.2f} units per turn (any distance in this range).
- Your capture radius: {capture_radius:.2f}. Opponent (Agent_B, always static) capture radius: {agent_b_capture_radius:.2f}.
- Perception: {perception_radius:.2f} units. Outside this is 'Dark Zone'.
- Wall: There is an IMPENETRABLE wall at x=25, from y=10 to y=48. You CANNOT cross this wall. If your move would cross the wall or land inside it, you stay in place.

## Victory Conditions
- VICTORY: Capture Agent_B (reduce distance to ≤ your capture radius {capture_radius:.2f}).
- DEFEAT: If max rounds reached OR Agent_B captures you (distance ≤ their capture radius {agent_b_capture_radius:.2f}).

## Round Information
Current Round: {current_round} / {max_rounds}
Turn Order: {turn_order}
Turn Order Rule: Turn order alternates every round (you and opponent take turns being FIRST).

## Objectives & Constraints
1. Optimization: Use your token budget to perform high-density mental simulations.
2. Efficiency: Avoid filler phrases. Every word must contribute to the spatial or strategic resolution of the target.
3. Flow: Your reasoning should be a continuous analytical monologue leading directly to the final coordinates.
4. Finality: The JSON object must conclude with your 'x' and 'y' target.

## Output Structure
Respond ONLY in this JSON format:
{{
  "thought_process": "<Dense spatial calculus. Use symbols/shorthand. No prose.>",
  "x": <number>,
  "y": <number>
}}"""

    def __init__(self):
        self._config = get_config()
        self._minimal_system = None
        self._standard_system = None
        self._config_hash = None
        self._load_templates()

    def _compute_hash(self, text: str) -> str:
        """Compute text hash for change detection."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

    def _load_templates(self):
        """Load templates from config; override defaults if different."""
        config_templates = getattr(self._config, 'prompt_templates', None)

        if config_templates:
            config_minimal = config_templates.get('minimal_system', '')
            config_standard = config_templates.get('standard_system', '')

            default_minimal_hash = self._compute_hash(self.DEFAULT_MINIMAL_SYSTEM)
            default_standard_hash = self._compute_hash(self.DEFAULT_STANDARD_SYSTEM)
            config_minimal_hash = self._compute_hash(config_minimal)
            config_standard_hash = self._compute_hash(config_standard)

            if config_minimal and config_minimal_hash != default_minimal_hash:
                print(f"[PromptTemplate] Using minimal_system from config (hash: {config_minimal_hash})")
                self._minimal_system = config_minimal
            else:
                self._minimal_system = self.DEFAULT_MINIMAL_SYSTEM

            if config_standard and config_standard_hash != default_standard_hash:
                print(f"[PromptTemplate] Using standard_system from config (hash: {config_standard_hash})")
                self._standard_system = config_standard
            else:
                self._standard_system = self.DEFAULT_STANDARD_SYSTEM
        else:
            self._minimal_system = self.DEFAULT_MINIMAL_SYSTEM
            self._standard_system = self.DEFAULT_STANDARD_SYSTEM

    def get_minimal_system_template(self) -> str:
        """Get minimal strategy system prompt template."""
        return self._minimal_system

    def get_standard_system_template(self) -> str:
        """Get standard strategy system prompt template."""
        return self._standard_system

    def reload_from_config(self):
        """Reload templates from config (hot reload)."""
        self._load_templates()


_template_manager = PromptTemplateManager()


def get_template_manager() -> PromptTemplateManager:
    """Get global template manager."""
    return _template_manager


class MinimalPromptStrategy:
    """
    Minimal strategy (Low-Bt).
    For very low budgets (<100 tokens), extremely concise prompts forcing JSON-first output.
    """

    def __init__(self):
        self._template_manager = get_template_manager()

    def build_system_prompt(self, ctx: PromptContext) -> str:
        template = self._template_manager.get_minimal_system_template()
        return template.format(
            agent_name=ctx.agent_name,
            map_size=ctx.map_size,
            move_step=ctx.move_step,
            capture_radius=ctx.capture_radius,
            agent_b_capture_radius=ctx.agent_b_capture_radius
        )

    def build_user_prompt(self, ctx: PromptContext) -> str:
        if ctx.opponent_direction:
            direction_info = f"|Dir:{ctx.opponent_direction}"
        else:
            direction_info = f"|Dir:unknown({ctx.rounds_until_next_update}R)"

        if ctx.opponent_pos:
            opp = f"({ctx.opponent_pos[0]:.2f},{ctx.opponent_pos[1]:.2f})"
            dist_info = f"|D:{ctx.distance_to_opponent:.2f}"
        else:
            opp = "?"
            dist_info = ""

        hist = ""
        if ctx.own_history:
            hist_parts = [
                f"({h.get('to', (0, 0))[0]:.2f},{h.get('to', (0, 0))[1]:.2f})"
                for h in ctx.own_history
            ]
            hist = "|H:" + ";".join(hist_parts)
            if len(ctx.own_history) >= 5:
                hist += "(last5)"

        sighting_info = ""
        if ctx.sightings:
            last_sight = ctx.sightings[-1]
            s_round = last_sight.get('round', '?')
            s_self = last_sight.get('self_pos', (0, 0))
            s_opp = last_sight.get('opponent_pos', (0, 0))
            sighting_info = f"|S:R{s_round}({s_self[0]:.2f},{s_self[1]:.2f})->O({s_opp[0]:.2f},{s_opp[1]:.2f})"

        return f"""R{ctx.current_round}/{ctx.max_rounds}|You:({ctx.current_pos[0]:.2f},{ctx.current_pos[1]:.2f})|Opp:{opp}{dist_info}{direction_info}{hist}{sighting_info}
Move:"""


class ReasoningPromptStrategy:
    """
    Reasoning strategy (High-Bt).
    Enforces CoT reasoning protocol, guiding the model toward deep strategic analysis.
    """

    def __init__(self):
        self._template_manager = get_template_manager()

    def build_system_prompt(self, ctx: PromptContext) -> str:
        template = self._template_manager.get_standard_system_template()
        turn_order = "FIRST (You act first this round)" if ctx.is_first_actor else "SECOND (You act after opponent this round)"
        return template.format(
            move_step=ctx.move_step,
            capture_radius=ctx.capture_radius,
            agent_b_capture_radius=ctx.agent_b_capture_radius,
            perception_radius=ctx.perception_radius,
            current_round=ctx.current_round,
            max_rounds=ctx.max_rounds,
            turn_order=turn_order
        )

    def _format_pos(self, pos: tuple) -> str:
        """Format coordinates to 2 decimal places."""
        return f"({pos[0]:.2f}, {pos[1]:.2f})"

    def _get_objective_hint(self, ctx: PromptContext) -> str:
        """Return objective hint based on turn order."""
        if ctx.is_first_actor:
            return "[TURN ORDER] You act FIRST. Use predictive modeling to intercept opponent's likely escape route."
        else:
            return "[TURN ORDER] You act SECOND. React to opponent's movement and minimize distance."

    def build_user_prompt(self, ctx: PromptContext) -> str:
        lines = []

        lines.append(f"## Perception Data (Round {ctx.current_round}/{ctx.max_rounds})")
        lines.append(f"[SELF] Position: {self._format_pos(ctx.current_pos)}")

        if ctx.opponent_direction:
            lines.append(f"[DIRECTION] Opponent is to your {ctx.opponent_direction}")
        else:
            lines.append(f"[DIRECTION] UNKNOWN (updated in {ctx.rounds_until_next_update} rounds)")

        if ctx.opponent_pos:
            lines.append(f"[OPPONENT] Position: {self._format_pos(ctx.opponent_pos)} | Status: VISIBLE")
            if ctx.distance_to_opponent is not None:
                lines.append(f"[METRICS] Distance: {ctx.distance_to_opponent:.2f} units | Capture Threshold: {ctx.capture_radius:.2f}")
                if ctx.distance_to_opponent <= ctx.capture_radius:
                    lines.append("[ALERT] **CAPTURE RANGE ACHIEVED!**")
        else:
            lines.append(f"[OPPONENT] Status: HIDDEN (outside {ctx.perception_radius:.2f} perception radius)")
            lines.append(f"[METRICS] Exact distance: UNKNOWN (use direction to navigate)")

        lines.append(f"\n{self._get_objective_hint(ctx)}")

        if ctx.walls:
            lines.append(f"\n## WALLS (Impenetrable Obstacles)")
            for i, wall in enumerate(ctx.walls, 1):
                desc = wall.get('description', f"Wall from ({wall['x1']}, {wall['y1']}) to ({wall['x2']}, {wall['y2']})")
                lines.append(f"  Wall {i}: {desc}")
            lines.append("  ⚠️ WARNING: You CANNOT cross walls. If your move would cross a wall or land inside it, you stay in place.")

        if ctx.own_history:
            lines.append(f"\n## Own Movement History (last {len(ctx.own_history)} rounds)")
            for h in ctx.own_history:
                from_pos = h.get('from', (0, 0))
                to_pos = h.get('to', (0, 0))
                r = h.get('round', '?')
                lines.append(f"  Round {r}: {self._format_pos(from_pos)} -> {self._format_pos(to_pos)}")
        else:
            lines.append(f"\n## Own Movement History")
            lines.append(f"  No movement history yet.")

        if ctx.sightings:
            lines.append(f"\n## Sighting History ({len(ctx.sightings)} times spotted opponent)")
            for sight in ctx.sightings:
                r = sight.get('round', '?')
                self_pos = sight.get('self_pos', (0, 0))
                opp_pos = sight.get('opponent_pos', (0, 0))
                dist = sight.get('distance', 0)
                lines.append(f"  Round {r}: You at {self._format_pos(self_pos)} saw opponent at {self._format_pos(opp_pos)} (dist: {dist:.2f})")
        else:
            lines.append(f"\n## Sighting History")
            lines.append(f"  No sightings yet. Opponent has never been in perception range.")

        lines.append(f"\n## EXECUTE REASONING PROTOCOL")
        lines.append(f"Current: {self._format_pos(ctx.current_pos)} | Max Step: {ctx.move_step:.2f} units")
        if not ctx.opponent_pos and ctx.sightings:
            last_sight = ctx.sightings[-1]
            lines.append(f"[HINT] Last seen opponent at Round {last_sight.get('round')} near {self._format_pos(last_sight.get('opponent_pos'))}")
        lines.append(f"\nProvide your response with detailed step-by-step reasoning:")

        return "\n".join(lines)


class PromptManager:
    """Prompt manager: selects strategy based on token budget."""

    MINIMAL_BUDGET_THRESHOLD = 100

    def __init__(self):
        self._minimal = MinimalPromptStrategy()
        self._reasoning = ReasoningPromptStrategy()

    def get_strategy(self, token_budget: int):
        """Select strategy based on token budget."""
        if token_budget <= self.MINIMAL_BUDGET_THRESHOLD:
            return self._minimal
        return self._reasoning

    def build_prompts(self, ctx: PromptContext) -> Dict[str, str]:
        """
        Build complete prompts.

        Returns:
            {"system": system_prompt, "user": user_prompt}
        """
        strategy = self.get_strategy(ctx.token_budget)
        return {
            "system": strategy.build_system_prompt(ctx),
            "user": strategy.build_user_prompt(ctx)
        }

    @staticmethod
    def create_context(
        agent_name: str,
        current_pos: tuple,
        opponent_pos: Optional[tuple],
        distance: Optional[float],
        perception_radius: float,
        move_step: float,
        capture_radius: float,
        agent_b_capture_radius: float,
        map_size: int,
        current_round: int,
        max_rounds: int,
        own_history: List[Dict],
        sightings: List[Dict],
        token_budget: int,
        is_first_actor: bool,
        opponent_direction: Optional[str] = None,
        is_opponent_visible: bool = False,
        rounds_until_next_update: int = 0,
        walls: List[Dict] = None
    ) -> PromptContext:
        """Convenience method to create a PromptContext."""
        return PromptContext(
            agent_name=agent_name,
            current_pos=current_pos,
            opponent_pos=opponent_pos,
            distance_to_opponent=distance,
            perception_radius=perception_radius,
            move_step=move_step,
            capture_radius=capture_radius,
            agent_b_capture_radius=agent_b_capture_radius,
            map_size=map_size,
            current_round=current_round,
            max_rounds=max_rounds,
            own_history=own_history,
            sightings=sightings,
            token_budget=token_budget,
            is_first_actor=is_first_actor,
            opponent_direction=opponent_direction,
            is_opponent_visible=is_opponent_visible,
            rounds_until_next_update=rounds_until_next_update,
            walls=walls
        )
