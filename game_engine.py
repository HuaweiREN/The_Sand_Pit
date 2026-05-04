"""
The Sand Pit - Game Engine
Turn execution protocol
"""

import random
from enum import Enum
from typing import Dict, Any, Optional, Tuple, Callable, List
from dataclasses import dataclass

from physics import PhysicsEngine, Position
from agent import Agent
from logger import GameLogger
from prompts import PromptManager
from config import Config, TurnOrderMode


class GameState(Enum):
    """Game state machine."""
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"


@dataclass
class TurnResult:
    """Result of a single round."""
    round_num: int
    first_actor: str
    second_actor: str
    winner: Optional[str]
    game_over: bool
    state_snapshot: Dict[str, Any]


class GameEngine:
    """
    Game engine: manages the complete turn execution protocol.
    """

    def __init__(
        self,
        config: Config,
        agent_a: Agent,
        agent_b: Agent,
        logger: GameLogger,
        state_callback: Optional[Callable] = None
    ):
        self.config = config
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.logger = logger
        self.state_callback = state_callback

        self.physics = PhysicsEngine(
            map_size=config.world.map_size,
            move_step=config.physics.move_step,
            perception_radius=config.physics.perception_radius,
            capture_radius=config.physics.capture_radius,
            agent_b_capture_radius=getattr(config.physics, 'agent_b_capture_radius', 3.0),
            walls=getattr(config, 'walls', [])
        )

        self.state = GameState.READY
        self.current_round = 0
        self.first_actor = "Agent_A"
        self.winner: Optional[str] = None
        self.win_reason: str = ""
        self.round_history: List[Dict[str, Any]] = []

    def reset(self):
        """Reset game state."""
        self.state = GameState.READY
        self.current_round = 0
        self.first_actor = "Agent_A"
        self.winner = None
        self.win_reason = ""
        self.round_history = []
        self._initialize_positions()

    def _initialize_positions(self):
        """Initialize agent positions (fixed spawn points)."""
        spawn_points = getattr(self.config, 'spawn_points', None)
        if spawn_points is None:
            spawn_points = {}

        agent_a_spawn = spawn_points.get('agent_a', [0, 0])
        self.agent_a.position = Position(x=float(agent_a_spawn[0]), y=float(agent_a_spawn[1]))

        agent_b_spawn = spawn_points.get('agent_b', [40, 35])
        self.agent_b.position = Position(x=float(agent_b_spawn[0]), y=float(agent_b_spawn[1]))

        self.agent_a.reset(self.agent_a.position)
        self.agent_b.reset(self.agent_b.position)

    def _determine_first_actor(self) -> str:
        """
        Determine first actor for the current round based on turn_order_mode.
        """
        mode = self.config.world.turn_order_mode

        if mode == TurnOrderMode.RANDOM:
            return random.choice(["Agent_A", "Agent_B"])
        elif mode == TurnOrderMode.ALTERNATING:
            return "Agent_A" if self.current_round % 2 == 1 else "Agent_B"
        else:
            return "Agent_A"

    def _get_agent_by_name(self, name: str) -> Agent:
        return self.agent_a if name == "Agent_A" else self.agent_b

    def _get_opponent_by_name(self, name: str) -> Agent:
        return self.agent_b if name == "Agent_A" else self.agent_a

    def _execute_turn(
        self,
        agent: Agent,
        opponent: Agent,
        is_first_actor: bool
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute a single turn.

        Returns:
            (captured, turn_info)
        """
        turn_info = {
            "agent": agent.name,
            "round": self.current_round,
            "is_first_actor": is_first_actor,
            "position_before": (agent.position.x, agent.position.y),
            "opponent_position": (opponent.position.x, opponent.position.y)
        }

        # Agent_B does not call API; stays stationary
        if agent.name == "Agent_B":
            new_pos = agent.position
            decision_info = {
                "raw_response": "Agent_B is stationary (no API call)",
                "parsed_response": {"x": agent.position.x, "y": agent.position.y, "reasoning": "Stationary"},
                "reasoning": "Agent_B does not move",
                "tokens_used": 0,
                "latency_ms": 0,
                "parse_error": None
            }
        else:
            # Agent_A makes a normal decision and moves
            new_pos, decision_info = agent.decide_move(
                opponent_pos=opponent.position,
                current_round=self.current_round,
                is_first_actor=is_first_actor,
                physics=self.physics
            )

        turn_info["decision"] = decision_info
        turn_info["position_after"] = (new_pos.x, new_pos.y)

        # Capture check with asymmetric radii
        distance = self.physics.get_distance(self.agent_a.position, self.agent_b.position)
        if agent.name == "Agent_A":
            captured = distance <= self.physics.capture_radius
        else:
            captured = distance <= getattr(self.physics, 'agent_b_capture_radius', 3.0)
        turn_info["captured"] = captured

        self.logger.log_turn_end(
            round_num=self.current_round,
            agent_name=agent.name,
            position_before=turn_info["position_before"],
            position_after=turn_info["position_after"],
            capture_check={
                "captured": captured,
                "distance": self.physics.get_distance(self.agent_a.position, self.agent_b.position),
                "capture_radius": self.physics.capture_radius
            },
            logic_action_delta=decision_info.get("logic_action_delta")
        )

        return captured, turn_info

    def run_round(self) -> TurnResult:
        """
        Run a complete round following the serial execution protocol.
        """
        if self.state == GameState.FINISHED:
            return self._create_turn_result()

        if self.state == GameState.READY:
            self.state = GameState.RUNNING

        self.current_round += 1

        # 1. Determine first actor
        first_actor_name = self._determine_first_actor()
        second_actor_name = "Agent_B" if first_actor_name == "Agent_A" else "Agent_A"
        self.first_actor = first_actor_name

        # Log round start
        self.logger.log_round_start(
            round_num=self.current_round,
            first_actor=first_actor_name,
            game_state=self.get_state_snapshot()
        )

        first_agent = self._get_agent_by_name(first_actor_name)
        second_agent = self._get_opponent_by_name(first_actor_name)

        # 2. First actor executes (Turn A)
        captured, first_turn_info = self._execute_turn(
            agent=first_agent,
            opponent=second_agent,
            is_first_actor=True
        )

        if captured:
            self.winner = first_actor_name
            self.win_reason = f"Captured opponent in round {self.current_round}"
            self.state = GameState.FINISHED
            self._finish_game()
            return self._create_turn_result()

        # 3. Second actor executes (Turn B)
        captured, second_turn_info = self._execute_turn(
            agent=second_agent,
            opponent=first_agent,
            is_first_actor=False
        )

        if captured:
            self.winner = second_actor_name
            self.win_reason = f"Captured opponent in round {self.current_round}"
            self.state = GameState.FINISHED
            self._finish_game()
            return self._create_turn_result()

        # 4. State update
        round_data = {
            "round": self.current_round,
            "first_actor": first_actor_name,
            "first_turn": first_turn_info,
            "second_turn": second_turn_info,
            "final_positions": {
                "Agent_A": (self.agent_a.position.x, self.agent_a.position.y),
                "Agent_B": (self.agent_b.position.x, self.agent_b.position.y)
            },
            "distance": self.physics.get_distance(self.agent_a.position, self.agent_b.position)
        }
        self.round_history.append(round_data)

        # Check max rounds
        if self.current_round >= self.config.world.max_rounds:
            self.win_reason = f"Max rounds ({self.config.world.max_rounds}) reached"
            self.state = GameState.FINISHED
            self._finish_game()

        if self.state_callback:
            self.state_callback(self.get_state_snapshot())

        return self._create_turn_result()

    def _create_turn_result(self) -> TurnResult:
        return TurnResult(
            round_num=self.current_round,
            first_actor=self.first_actor,
            second_actor="Agent_B" if self.first_actor == "Agent_A" else "Agent_A",
            winner=self.winner,
            game_over=self.state == GameState.FINISHED,
            state_snapshot=self.get_state_snapshot()
        )

    def _finish_game(self):
        """End the game and record final state."""
        if self.winner is None:
            dist = self.physics.get_distance(self.agent_a.position, self.agent_b.position)
            if dist <= self.physics.capture_radius:
                self.winner = "Tie"
            else:
                self.winner = None  # Draw

        self.logger.log_game_end(
            winner=self.winner,
            final_round=self.current_round,
            win_reason=self.win_reason,
            final_state=self.get_state_snapshot()
        )

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get current state snapshot."""
        return {
            "state": self.state.value,
            "round": self.current_round,
            "first_actor": self.first_actor,
            "winner": self.winner,
            "agent_a": self.agent_a.get_state(),
            "agent_b": self.agent_b.get_state(),
            "distance": self.physics.get_distance(self.agent_a.position, self.agent_b.position),
            "capture_radius": self.physics.capture_radius
        }

    def run_full_game(self) -> Dict[str, Any]:
        """Run a full game until completion."""
        self.reset()

        while self.state != GameState.FINISHED:
            self.run_round()

        return {
            "winner": self.winner,
            "total_rounds": self.current_round,
            "win_reason": self.win_reason,
            "agent_a_stats": {
                "tokens_used": self.agent_a.total_tokens_used,
                "parse_errors": self.agent_a.parse_errors
            },
            "agent_b_stats": {
                "tokens_used": self.agent_b.total_tokens_used,
                "parse_errors": self.agent_b.parse_errors
            }
        }

    def pause(self):
        if self.state == GameState.RUNNING:
            self.state = GameState.PAUSED

    def resume(self):
        if self.state == GameState.PAUSED:
            self.state = GameState.RUNNING
