"""
The Sand Pit - Physics Engine
Physics rules and hard constraints (safety fences)
"""

import math
from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any


@dataclass
class Position:
    """2D coordinate position."""
    x: float
    y: float

    def __post_init__(self):
        self.x = float(self.x)
        self.y = float(self.y)

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def distance_to(self, other: 'Position') -> float:
        """Calculate Euclidean distance to another position."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __str__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f})"

    def __repr__(self) -> str:
        return f"Position({self.x:.2f}, {self.y:.2f})"


class PhysicsEngine:
    """
    Physics engine: enforces all physical rules.
    Does not trust API outputs; all coordinates must pass validation here.
    """

    def __init__(self, map_size: int, move_step: float, perception_radius: float,
                 capture_radius: float, agent_b_capture_radius: float = 3.0, walls: list = None):
        self.map_size = map_size
        self.move_step = move_step
        self.perception_radius = perception_radius
        self.capture_radius = capture_radius
        self.agent_b_capture_radius = agent_b_capture_radius
        self.walls = walls or []

    def clamp_to_boundary(self, pos: Position) -> Tuple[Position, bool]:
        """
        Boundary clamp: force coordinates inside the map bounds.

        Returns:
            (clamped_position, was_clamped)
        """
        was_clamped = False
        new_x, new_y = pos.x, pos.y

        if new_x < 0:
            new_x = 0
            was_clamped = True
        elif new_x > self.map_size:
            new_x = self.map_size
            was_clamped = True

        if new_y < 0:
            new_y = 0
            was_clamped = True
        elif new_y > self.map_size:
            new_y = self.map_size
            was_clamped = True

        return Position(new_x, new_y), was_clamped

    def clamp_movement(self, current: Position, target: Position) -> Tuple[Position, bool]:
        """
        Movement clamp: limit displacement to at most move_step.

        If the distance between current and target exceeds S, project the target
        onto the circle centered at current with radius S.

        Returns:
            (clamped_target, was_clamped)
        """
        distance = current.distance_to(target)

        if distance <= self.move_step:
            return target, False

        dx = target.x - current.x
        dy = target.y - current.y
        scale = self.move_step / distance

        new_x = current.x + dx * scale
        new_y = current.y + dy * scale

        return Position(new_x, new_y), True

    def validate_and_clamp_move(self, current: Position, raw_target: Position) -> Tuple[Position, dict]:
        """
        Full movement validation pipeline.

        1. Movement clamp (speed limit)
        2. Boundary clamp
        3. Wall collision detection

        Returns:
            (final_position, clamp_info)
        """
        clamp_info = {
            'original_target': (raw_target.x, raw_target.y),
            'movement_clamped': False,
            'boundary_clamped': False,
            'wall_blocked': False,
            'wall_hit': None,
            'original_distance': current.distance_to(raw_target)
        }

        # Step 1: movement clamp
        clamped_target, was_movement_clamped = self.clamp_movement(current, raw_target)
        clamp_info['movement_clamped'] = was_movement_clamped

        if was_movement_clamped:
            clamp_info['clamped_distance'] = self.move_step

        # Step 2: boundary clamp
        final_pos, was_boundary_clamped = self.clamp_to_boundary(clamped_target)
        clamp_info['boundary_clamped'] = was_boundary_clamped

        # Step 3: wall collision detection
        wall_hit = self.check_wall_collision(current, final_pos)
        if wall_hit:
            clamp_info['wall_blocked'] = True
            clamp_info['wall_hit'] = wall_hit
            return current, clamp_info

        return final_pos, clamp_info

    def check_capture(self, pos_a: Position, pos_b: Position) -> bool:
        """
        Check if capture condition is met.
        Capture succeeds when distance D <= capture radius.
        """
        distance = pos_a.distance_to(pos_b)
        return distance <= self.capture_radius

    def get_perception_info(self, observer: Position, target: Position) -> dict:
        """
        Get perception information.

        Returns:
            {
                'visible': bool,
                'distance': float,
                'relative_position': Optional[Tuple[float, float]]
            }
        """
        distance = observer.distance_to(target)
        visible = distance <= self.perception_radius

        result = {
            'visible': visible,
            'distance': distance,
            'relative_position': None
        }

        if visible:
            rel_x = target.x - observer.x
            rel_y = target.y - observer.y
            result['relative_position'] = (rel_x, rel_y)

        return result

    def get_distance(self, pos_a: Position, pos_b: Position) -> float:
        """Calculate distance between two positions."""
        return pos_a.distance_to(pos_b)

    def is_valid_position(self, pos: Position) -> bool:
        """Check if coordinates are within valid bounds."""
        return 0 <= pos.x <= self.map_size and 0 <= pos.y <= self.map_size

    def check_wall_collision(self, current: Position, target: Position) -> Optional[Dict[str, Any]]:
        """
        Check if moving from current to target collides with a wall.
        Walls are defined as rectangular regions (x1,y1) to (x2,y2).

        Args:
            current: current position
            target: target position

        Returns:
            Wall info if collision detected, else None
        """
        for wall in self.walls:
            wall_left = min(wall['x1'], wall['x2'])
            wall_right = max(wall['x1'], wall['x2'])
            wall_top = min(wall['y1'], wall['y2'])
            wall_bottom = max(wall['y1'], wall['y2'])

            # Check 1: target point inside wall rectangle
            if (wall_left <= target.x <= wall_right and
                wall_top <= target.y <= wall_bottom):
                return wall

            # Check 2: movement path intersects wall rectangle
            if self._line_intersects_rect(
                current.x, current.y, target.x, target.y,
                wall_left, wall_top, wall_right, wall_bottom
            ):
                return wall

        return None

    def _line_intersects_rect(self, x1: float, y1: float, x2: float, y2: float,
                               rx1: float, ry1: float, rx2: float, ry2: float) -> bool:
        """Check if line segment (x1,y1)-(x2,y2) intersects rectangle (rx1,ry1)-(rx2,ry2)."""
        # Quick reject: if segment is completely on one side, no intersection
        if max(x1, x2) < rx1 or min(x1, x2) > rx2 or max(y1, y2) < ry1 or min(y1, y2) > ry2:
            return False

        rect_edges = [
            (rx1, ry1, rx1, ry2),  # left
            (rx2, ry1, rx2, ry2),  # right
            (rx1, ry1, rx2, ry1),  # top
            (rx1, ry2, rx2, ry2),  # bottom
        ]

        for ex1, ey1, ex2, ey2 in rect_edges:
            if self._line_segments_intersect(x1, y1, x2, y2, ex1, ey1, ex2, ey2):
                return True

        if self._point_in_rect(x1, y1, rx1, ry1, rx2, ry2):
            return True

        return False

    def _line_segments_intersect(self, x1: float, y1: float, x2: float, y2: float,
                                  x3: float, y3: float, x4: float, y4: float) -> bool:
        """Check if two line segments intersect."""
        def orientation(px, py, qx, qy, rx, ry):
            val = (qy - py) * (rx - qx) - (qx - px) * (ry - qy)
            if abs(val) < 1e-9:
                return 0
            return 1 if val > 0 else 2

        def on_segment(px, py, qx, qy, rx, ry):
            return (min(px, rx) - 1e-9 <= qx <= max(px, rx) + 1e-9 and
                    min(py, ry) - 1e-9 <= qy <= max(py, ry) + 1e-9)

        o1 = orientation(x1, y1, x2, y2, x3, y3)
        o2 = orientation(x1, y1, x2, y2, x4, y4)
        o3 = orientation(x3, y3, x4, y4, x1, y1)
        o4 = orientation(x3, y3, x4, y4, x2, y2)

        if o1 != o2 and o3 != o4:
            return True

        if o1 == 0 and on_segment(x1, y1, x3, y3, x2, y2):
            return True
        if o2 == 0 and on_segment(x1, y1, x4, y4, x2, y2):
            return True
        if o3 == 0 and on_segment(x3, y3, x1, y1, x4, y4):
            return True
        if o4 == 0 and on_segment(x3, y3, x2, y2, x4, y4):
            return True

        return False

    def _point_in_rect(self, px: float, py: float, rx1: float, ry1: float, rx2: float, ry2: float) -> bool:
        """Check if point is inside rectangle (inclusive)."""
        return (rx1 <= px <= rx2 and ry1 <= py <= ry2)


class MovementValidator:
    """
    Movement validator: dedicated to parsing and validating API movement commands.
    """

    def __init__(self, physics: PhysicsEngine):
        self.physics = physics

    def parse_and_validate(self, current_pos: Position, api_response: dict) -> Tuple[Optional[Position], dict]:
        """
        Parse API response and validate movement command.

        Args:
            current_pos: current position
            api_response: parsed API response JSON, must contain 'x' and 'y'

        Returns:
            (final_position, validation_info)
            final_position is None if parsing failed
        """
        validation_info = {
            'parse_success': False,
            'parse_error': None,
            'raw_response': api_response,
            'original_position': (current_pos.x, current_pos.y)
        }

        try:
            if not isinstance(api_response, dict):
                raise ValueError(f"Response is not a dict: {type(api_response)}")

            if 'x' not in api_response or 'y' not in api_response:
                raise ValueError("Missing 'x' or 'y' in response")

            raw_x = float(api_response['x'])
            raw_y = float(api_response['y'])

            raw_target = Position(raw_x, raw_y)
            validation_info['parse_success'] = True
            validation_info['parsed_target'] = (raw_x, raw_y)

        except (KeyError, ValueError, TypeError) as e:
            validation_info['parse_error'] = str(e)
            return None, validation_info

        # Physics validation
        final_pos, clamp_info = self.physics.validate_and_clamp_move(current_pos, raw_target)
        validation_info.update(clamp_info)
        validation_info['final_position'] = (final_pos.x, final_pos.y)

        return final_pos, validation_info
