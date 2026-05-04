"""
The Sand Pit - Granular Logging System
Full-audit logging system ("black box" level recording)
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import threading


class GameLogger:
    """
    Game logger: records all communication details, state changes, and physics validation info.
    """

    # Coordinate precision: keep 2 decimal places
    COORD_PRECISION = 2

    def __init__(self, log_dir: str = "logs", experiment_id: Optional[str] = None,
                 config: Optional[Dict[str, Any]] = None, auto_timestamp: bool = True):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique timestamp (millisecond precision)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

        if experiment_id is None:
            experiment_id = f"exp_{timestamp}"
        elif auto_timestamp:
            experiment_id = f"{experiment_id}_{timestamp}"
        self.experiment_id = experiment_id

        self.config = config or {}

        self.log_file = self.log_dir / f"{experiment_id}.jsonl"
        self.summary_file = self.log_dir / f"{experiment_id}_summary.json"

        # Thread lock for concurrency safety
        self._lock = threading.Lock()

        # Runtime statistics
        self.round_count = 0
        self.api_calls = 0
        self.parse_errors = 0
        self.movement_clamps = 0
        self.boundary_clamps = 0

        self._write_header()

    @staticmethod
    def _round_coord(value) -> Any:
        """Round coordinate value to 2 decimal places."""
        if isinstance(value, float):
            return round(value, GameLogger.COORD_PRECISION)
        return value

    @classmethod
    def _round_coords_in_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively round all float coordinates in a dict to 2 decimal places."""
        if not isinstance(data, dict):
            return cls._round_coord(data)

        result = {}
        for key, value in data.items():
            if isinstance(value, float):
                result[key] = round(value, cls.COORD_PRECISION)
            elif isinstance(value, (list, tuple)) and len(value) == 2:
                if all(isinstance(v, (int, float)) for v in value):
                    result[key] = [round(v, cls.COORD_PRECISION) for v in value]
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = cls._round_coords_in_dict(value)
            elif isinstance(value, (list, tuple)):
                result[key] = [cls._round_coords_in_dict(v) if isinstance(v, dict) else cls._round_coord(v) for v in value]
            else:
                result[key] = value
        return result

    @classmethod
    def _round_coords_in_tuple(cls, pos: tuple) -> tuple:
        """Round coordinate tuple to 2 decimal places."""
        return tuple(round(v, cls.COORD_PRECISION) for v in pos)

    def _write_header(self):
        """Write log file header with configuration."""
        header = {
            "event_type": "experiment_start",
            "timestamp": datetime.now().isoformat(),
            "experiment_id": self.experiment_id,
            "log_version": "1.0",
            "config": self.config
        }
        self._append_jsonl(header)

    def _append_jsonl(self, data: Dict[str, Any]):
        """Append a line to the JSONL file."""
        with self._lock:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, default=str)
                f.write('\n')

    def log_round_start(self, round_num: int, first_actor: str, game_state: Dict[str, Any]):
        """Log round start."""
        self.round_count = round_num
        entry = {
            "event_type": "round_start",
            "timestamp": datetime.now().isoformat(),
            "round": round_num,
            "first_actor": first_actor,
            "game_state": game_state
        }
        self._append_jsonl(entry)

    def log_api_request(
        self,
        round_num: int,
        agent_name: str,
        system_prompt: str,
        user_prompt: str,
        token_budget: int,
        model_name: str
    ):
        """
        Log API request details including full prompts.
        """
        entry = {
            "event_type": "api_request",
            "timestamp": datetime.now().isoformat(),
            "round": round_num,
            "agent": agent_name,
            "model": model_name,
            "token_budget": token_budget,
            "request": {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }
        }
        self.api_calls += 1
        self._append_jsonl(entry)

    def log_api_response(
        self,
        round_num: int,
        agent_name: str,
        raw_response: str,
        parsed_content: Optional[Dict],
        reasoning_content: Optional[str],
        usage_stats: Optional[Dict[str, Any]],
        latency_ms: float,
        parse_error: Optional[str] = None
    ):
        """
        Log API response details including raw response, reasoning chain, and usage stats.
        """
        if parse_error:
            self.parse_errors += 1

        entry = {
            "event_type": "api_response",
            "timestamp": datetime.now().isoformat(),
            "round": round_num,
            "agent": agent_name,
            "latency_ms": round(latency_ms, 2),
            "response": {
                "raw_content": raw_response,
                "parsed_content": parsed_content,
                "reasoning_content": reasoning_content,
                "usage": usage_stats,
                "parse_error": parse_error
            }
        }
        self._append_jsonl(entry)

    def log_movement(
        self,
        round_num: int,
        agent_name: str,
        validation_info: Dict[str, Any]
    ):
        """
        Log movement details including coordinate parsing and physics clamp info.
        """
        if validation_info.get('movement_clamped'):
            self.movement_clamps += 1
        if validation_info.get('boundary_clamped'):
            self.boundary_clamps += 1

        rounded_validation = self._round_coords_in_dict(validation_info)

        entry = {
            "event_type": "movement",
            "timestamp": datetime.now().isoformat(),
            "round": round_num,
            "agent": agent_name,
            "validation": rounded_validation
        }
        self._append_jsonl(entry)

    def log_turn_end(
        self,
        round_num: int,
        agent_name: str,
        position_before: tuple,
        position_after: tuple,
        capture_check: Dict[str, Any],
        logic_action_delta: Optional[float] = None
    ):
        """Log turn end (coordinates rounded to 2 decimal places)."""
        rounded_capture_check = self._round_coords_in_dict(capture_check)

        entry = {
            "event_type": "turn_end",
            "timestamp": datetime.now().isoformat(),
            "round": round_num,
            "agent": agent_name,
            "position_before": self._round_coords_in_tuple(position_before),
            "position_after": self._round_coords_in_tuple(position_after),
            "capture_check": rounded_capture_check,
            "logic_action_delta": logic_action_delta
        }
        self._append_jsonl(entry)

    def log_game_end(
        self,
        winner: Optional[str],
        final_round: int,
        win_reason: str,
        final_state: Dict[str, Any]
    ):
        """Log game end (coordinates rounded to 2 decimal places)."""
        rounded_final_state = self._round_coords_in_dict(final_state)

        entry = {
            "event_type": "game_end",
            "timestamp": datetime.now().isoformat(),
            "winner": winner,
            "final_round": final_round,
            "win_reason": win_reason,
            "final_state": rounded_final_state
        }
        self._append_jsonl(entry)

        self._write_summary(winner, final_round, win_reason)

    def _write_summary(self, winner: Optional[str], final_round: int, win_reason: str):
        """Generate experiment summary."""
        summary = {
            "experiment_id": self.experiment_id,
            "timestamp": datetime.now().isoformat(),
            "result": {
                "winner": winner,
                "total_rounds": final_round,
                "win_reason": win_reason
            },
            "statistics": {
                "total_api_calls": self.api_calls,
                "parse_errors": self.parse_errors,
                "parse_error_rate": round(self.parse_errors / max(self.api_calls, 1) * 100, 2),
                "movement_clamps": self.movement_clamps,
                "boundary_clamps": self.boundary_clamps
            }
        }

        with open(self.summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    def get_log_path(self) -> str:
        """Get log file path."""
        return str(self.log_file)

    def get_summary(self) -> Dict[str, Any]:
        """Get current summary."""
        return {
            "experiment_id": self.experiment_id,
            "rounds_completed": self.round_count,
            "api_calls": self.api_calls,
            "parse_errors": self.parse_errors,
            "movement_clamps": self.movement_clamps,
            "boundary_clamps": self.boundary_clamps
        }


class BatchLogger:
    """
    Batch experiment logger.
    Records aggregated results across multiple experiments.
    """

    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def create_batch_log(self, token_budget: int) -> GameLogger:
        """Create a logger for a specific token budget."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exp_id = f"batch_{token_budget}tokens_{timestamp}"
        return GameLogger(str(self.results_dir), exp_id)

    def write_batch_summary(
        self,
        token_budget: int,
        num_runs: int,
        results: List[Dict[str, Any]]
    ):
        """Write batch experiment summary."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.results_dir / f"summary_{token_budget}tokens_{timestamp}.json"

        wins_a = sum(1 for r in results if r.get('winner') == 'Agent_A')
        wins_b = sum(1 for r in results if r.get('winner') == 'Agent_B')
        draws = sum(1 for r in results if r.get('winner') is None)

        avg_rounds = sum(r.get('final_round', 0) for r in results) / max(len(results), 1)
        avg_tokens = sum(r.get('total_tokens_used', 0) for r in results) / max(len(results), 1)

        total_api_calls = sum(r.get('api_calls', 0) for r in results)
        total_parse_errors = sum(r.get('parse_errors', 0) for r in results)
        logic_failure_rate = (total_parse_errors / max(total_api_calls, 1)) * 100

        summary = {
            "token_budget": token_budget,
            "num_runs": num_runs,
            "timestamp": timestamp,
            "win_rate_agent_a": round(wins_a / num_runs * 100, 2),
            "win_rate_agent_b": round(wins_b / num_runs * 100, 2),
            "draw_rate": round(draws / num_runs * 100, 2),
            "avg_rounds": round(avg_rounds, 2),
            "avg_tokens_used": round(avg_tokens, 2),
            "logic_failure_rate": round(logic_failure_rate, 2),
            "individual_results": results
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        return str(filename)
