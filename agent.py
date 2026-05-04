"""
The Sand Pit - Agent Core
Agent core class: encapsulates LLM interaction, decision logic, and state management.
"""

import json
import math
import re
from typing import Dict, Any, Optional, Tuple, List

from physics import Position, MovementValidator
from prompts import PromptManager, PromptContext, calculate_direction
from logger import GameLogger
from config import Config
from api_clients import create_api_client, BaseAPIClient


class Agent:
    """
    Agent class: represents a participant in the game.
    """

    def __init__(
        self,
        name: str,
        initial_pos: Position,
        config: Config,
        logger: GameLogger,
        prompt_manager: PromptManager,
        api_client: Optional[BaseAPIClient] = None
    ):
        self.name = name
        self.position = initial_pos
        self.config = config
        self.logger = logger
        self.prompt_manager = prompt_manager
        self.movement_validator = MovementValidator(config.physics)

        # State tracking
        self.history: List[Dict[str, Any]] = []  # Own movement history
        self.sightings: List[Dict[str, Any]] = []  # All sightings of opponent in this game
        self.total_tokens_used = 0
        self.parse_errors = 0

        # Logic_Action_Delta statistics
        self.logic_action_deltas: List[float] = []

        # Direction update control (updated once per round)
        self.last_direction_update_round = 0
        self.cached_opponent_direction = None
        self.direction_update_interval = 1

        # API client
        if api_client is None:
            self.api_client = create_api_client(
                api_key=config.api.api_key,
                base_url=config.api.base_url,
                model=config.api.model_name,
                temperature=config.api.temperature,
                timeout=config.api.timeout,
                client_type=getattr(config.api, 'client_type', 'auto')
            )
        else:
            self.api_client = api_client

    def get_perceived_opponent(
        self,
        opponent_pos: Position,
        physics
    ) -> Tuple[Optional[Tuple[float, float]], Optional[float]]:
        """
        Get perceived opponent information.

        Returns:
            (opponent_coords_or_None, distance_or_None)
            - If opponent visible: returns (opponent coordinates, distance)
            - If opponent not visible: returns (None, None)
        """
        info = physics.get_perception_info(self.position, opponent_pos)
        distance = info['distance']

        if info['visible']:
            return (opponent_pos.x, opponent_pos.y), distance
        else:
            return None, None

    def decide_move(
        self,
        opponent_pos: Position,
        current_round: int,
        is_first_actor: bool,
        physics
    ) -> Tuple[Position, Dict[str, Any]]:
        """
        Decision move: interact with LLM API to get movement decision.

        Returns:
            (new_position, decision_info)
        """
        perceived_opp, distance = self.get_perceived_opponent(opponent_pos, physics)

        if perceived_opp is not None and distance is not None:
            self.sightings.append({
                'round': current_round,
                'self_pos': (self.position.x, self.position.y),
                'opponent_pos': perceived_opp,
                'distance': distance
            })

        # Calculate direction (updated every 5 rounds)
        rounds_since_update = current_round - self.last_direction_update_round
        is_direction_update_round = rounds_since_update >= self.direction_update_interval

        if is_direction_update_round:
            opponent_actual_pos = (opponent_pos.x, opponent_pos.y)
            self.cached_opponent_direction = calculate_direction(
                (self.position.x, self.position.y),
                opponent_actual_pos
            )
            self.last_direction_update_round = current_round
            opponent_direction = self.cached_opponent_direction
            rounds_until_next_update = self.direction_update_interval
        else:
            opponent_direction = None
            rounds_until_next_update = self.direction_update_interval - rounds_since_update

        is_opponent_visible = perceived_opp is not None

        # Only keep last 10 rounds of history
        recent_history = self.history[-10:] if len(self.history) > 10 else self.history

        ctx = PromptContext(
            agent_name=self.name,
            current_pos=(self.position.x, self.position.y),
            opponent_pos=perceived_opp,
            distance_to_opponent=distance,
            perception_radius=physics.perception_radius,
            move_step=physics.move_step,
            capture_radius=physics.capture_radius,
            agent_b_capture_radius=getattr(physics, 'agent_b_capture_radius', 3.0),
            map_size=physics.map_size,
            current_round=current_round,
            max_rounds=self.config.world.max_rounds,
            own_history=recent_history,
            sightings=self.sightings,
            token_budget=self.config.experiment.token_budget,
            is_first_actor=is_first_actor,
            opponent_direction=opponent_direction,
            is_opponent_visible=is_opponent_visible,
            rounds_until_next_update=rounds_until_next_update,
            walls=getattr(self.config, 'walls', None)
        )

        prompts = self.prompt_manager.build_prompts(ctx)
        system_prompt = prompts["system"]
        user_prompt = prompts["user"]

        self.logger.log_api_request(
            round_num=current_round,
            agent_name=self.name,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            token_budget=self.config.max_tokens,
            model_name=self.config.api.model_name
        )

        raw_response, parsed_response, reasoning, tokens_used, latency = self.api_client.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=self.config.max_tokens
        )

        self.total_tokens_used += tokens_used

        parse_error = None
        if raw_response and (raw_response.startswith("401") or raw_response.startswith("404") or
                            raw_response.startswith("429") or raw_response.startswith("Request timeout") or
                            raw_response.startswith("Connection error")):
            parse_error = raw_response

        self.logger.log_api_response(
            round_num=current_round,
            agent_name=self.name,
            raw_response=raw_response,
            parsed_content=parsed_response,
            reasoning_content=reasoning,
            usage_stats={"total_tokens": tokens_used},
            latency_ms=latency,
            parse_error=parse_error
        )

        if parse_error or parsed_response is None:
            self.parse_errors += 1
            self.logger.log_movement(
                round_num=current_round,
                agent_name=self.name,
                validation_info={
                    'parse_success': False,
                    'parse_error': parse_error,
                    'original_position': (self.position.x, self.position.y),
                    'final_position': (self.position.x, self.position.y)
                }
            )
            return self.position, {
                'action': 'stay',
                'reason': f'Parse error: {parse_error}',
                'latency_ms': latency,
                'usage': {"total_tokens": tokens_used}
            }

        try:
            target_x = float(parsed_response.get('x', self.position.x))
            target_y = float(parsed_response.get('y', self.position.y))
            raw_target = Position(target_x, target_y)
        except (ValueError, TypeError) as e:
            error_msg = f"Invalid coordinates: {e}"
            self.parse_errors += 1
            self.logger.log_api_response(
                round_num=current_round,
                agent_name=self.name,
                raw_response=raw_response,
                parsed_content=parsed_response,
                reasoning_content=reasoning,
                usage_stats={"total_tokens": tokens_used},
                latency_ms=latency,
                parse_error=error_msg
            )
            return self.position, {
                'action': 'stay',
                'reason': error_msg,
                'latency_ms': latency,
                'usage': {"total_tokens": tokens_used}
            }

        final_pos, validation_info = physics.validate_and_clamp_move(self.position, raw_target)

        thought_process = parsed_response.get('thought_process') if parsed_response else None
        logic_action_delta = self._calculate_logic_action_delta(
            current_pos=self.position,
            actual_target=final_pos,
            reasoning=thought_process or reasoning,
            parsed_response=parsed_response
        )
        if logic_action_delta is not None:
            self.logic_action_deltas.append(logic_action_delta)

        self.logger.log_movement(
            round_num=current_round,
            agent_name=self.name,
            validation_info=validation_info
        )

        self.history.append({
            'round': current_round,
            'is_self': True,
            'from': (self.position.x, self.position.y),
            'to': (final_pos.x, final_pos.y),
            'reasoning': reasoning or parsed_response.get('reasoning', ''),
            'latency_ms': latency
        })

        old_pos = self.position
        self.position = final_pos

        return final_pos, {
            'action': 'move',
            'from': (old_pos.x, old_pos.y),
            'to': (final_pos.x, final_pos.y),
            'validation': validation_info,
            'reasoning': reasoning or parsed_response.get('reasoning', ''),
            'latency_ms': latency,
            'usage': {"total_tokens": tokens_used},
            'logic_action_delta': logic_action_delta
        }

    def _extract_json(self, content: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Extract JSON from API response (delegated to api_client)."""
        return self.api_client._extract_json(content)

    def _calculate_logic_action_delta(
        self,
        current_pos: Position,
        actual_target: Position,
        reasoning: Optional[str],
        parsed_response: Optional[Dict]
    ) -> Optional[float]:
        """
        Calculate Logic_Action_Delta: the angle between the vector described
        in the reasoning and the actual output vector.

        Args:
            current_pos: current position
            actual_target: actual target position (API output x,y)
            reasoning: thought_process / reasoning content
            parsed_response: parsed response dict

        Returns:
            Angle in degrees (0-180), or None if not computable
        """
        if not reasoning:
            return None

        actual_dx = actual_target.x - current_pos.x
        actual_dy = actual_target.y - current_pos.y
        actual_distance = math.sqrt(actual_dx ** 2 + actual_dy ** 2)

        if actual_distance < 1e-9:
            return None

        # Strategy 1: extract intended coordinates from reasoning text
        coord_patterns = [
            r'to\s*\(?\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)?',
            r'target\s*:\s*\(?\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)?',
            r'move\s+.*?\(?\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)?',
            r'\(\s*([+-]?\d+\.?\d*)\s*,\s*([+-]?\d+\.?\d*)\s*\)',
            r'x\s*[=:]\s*([+-]?\d+\.?\d*)\s*[,;\s]+\s*y\s*[=:]\s*([+-]?\d+\.?\d*)',
        ]

        intended_target = None
        for pattern in coord_patterns:
            matches = re.findall(pattern, reasoning, re.IGNORECASE)
            for match in matches:
                try:
                    x, y = float(match[0]), float(match[1])
                    if 0 <= x <= self.config.world.map_size and 0 <= y <= self.config.world.map_size:
                        intended_target = Position(x, y)
                        break
                except (ValueError, IndexError):
                    continue
            if intended_target:
                break

        if not intended_target and parsed_response:
            thought = parsed_response.get('thought_process') or parsed_response.get('reasoning')
            if thought and isinstance(thought, str):
                for pattern in coord_patterns:
                    matches = re.findall(pattern, thought, re.IGNORECASE)
                    for match in matches:
                        try:
                            x, y = float(match[0]), float(match[1])
                            if 0 <= x <= self.config.world.map_size and 0 <= y <= self.config.world.map_size:
                                intended_target = Position(x, y)
                                break
                        except (ValueError, IndexError):
                            continue
                    if intended_target:
                        break

        if not intended_target:
            return None

        intended_dx = intended_target.x - current_pos.x
        intended_dy = intended_target.y - current_pos.y
        intended_distance = math.sqrt(intended_dx ** 2 + intended_dy ** 2)

        if intended_distance < 1e-9:
            return None

        dot_product = actual_dx * intended_dx + actual_dy * intended_dy
        cos_angle = dot_product / (actual_distance * intended_distance)
        cos_angle = max(-1.0, min(1.0, cos_angle))

        angle_degrees = math.degrees(math.acos(cos_angle))
        return round(angle_degrees, 2)

    def get_state(self) -> Dict[str, Any]:
        """Get current agent state."""
        return {
            'name': self.name,
            'position': (self.position.x, self.position.y),
            'history_length': len(self.history),
            'total_tokens_used': self.total_tokens_used,
            'parse_errors': self.parse_errors,
            'logic_action_deltas': self.logic_action_deltas,
            'avg_logic_action_delta': sum(self.logic_action_deltas) / len(self.logic_action_deltas) if self.logic_action_deltas else None
        }

    def reset(self, new_position: Optional[Position] = None):
        """Reset agent state."""
        if new_position:
            self.position = new_position
        self.history = []
        self.sightings = []
        self.total_tokens_used = 0
        self.parse_errors = 0
        self.logic_action_deltas = []
        self.last_direction_update_round = 0
        self.cached_opponent_direction = None
