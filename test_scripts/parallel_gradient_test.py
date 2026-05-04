#!/usr/bin/env python3
"""
The Sand Pit - Parallel Gradient Test Runner
Runs games across multiple token budgets with API rate limiting, multi-threaded workers.
Ensures at least min_interval seconds between each API request.
"""

import copy
import json
import time
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from physics import Position
from agent import Agent
from game_engine import GameEngine
from logger import GameLogger
from prompts import PromptManager
from config import Config, get_config
from api_clients import create_api_client, BaseAPIClient

# Fatal API error phrases (abort entire experiment when encountered)
FATAL_ERROR_PHRASES = [
    "429 Too Many Requests: Rate limited after",
    "You've reached your usage limit for this billing cycle.",
]


def _is_fatal_error(text: str) -> bool:
    """Check if text contains fatal error phrases that should abort the experiment."""
    return any(phrase in text for phrase in FATAL_ERROR_PHRASES)


class TestAbortedError(Exception):
    """Experiment aborted due to fatal API error."""
    pass


class RateLimitedAPIClient(BaseAPIClient):
    """
    Rate-limited API client wrapper.
    Ensures each request is separated by at least min_interval seconds.
    """

    def __init__(
        self,
        base_client: BaseAPIClient,
        min_interval: float = 2.0,
        stop_event: Optional[threading.Event] = None
    ):
        self.base_client = base_client
        self.min_interval = min_interval
        self.last_request_time = 0
        self._lock = threading.Lock()
        self.stop_event = stop_event

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int
    ):
        """Call API with enforced interval."""
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            wait_time = max(0, self.min_interval - time_since_last)

            if wait_time > 0:
                time.sleep(wait_time)

            self.last_request_time = time.time()

        result = self.base_client.chat_completion(system_prompt, user_prompt, max_tokens)
        raw_response = result[0] if result else None

        if raw_response and _is_fatal_error(raw_response):
            if self.stop_event:
                self.stop_event.set()
            raise TestAbortedError(f"Fatal API error detected: {raw_response}")

        return result


class GradientWorker:
    """Gradient test worker."""

    def __init__(
        self,
        worker_id: str,
        token_budget: int,
        num_games: int,
        log_dir: str,
        config: Config,
        rate_limit: float = 2.0,
        stop_event: Optional[threading.Event] = None
    ):
        self.worker_id = worker_id
        self.token_budget = token_budget
        self.num_games = num_games
        self.log_dir = Path(log_dir)
        # Deep copy config to avoid interference when multiple workers modify token_budget concurrently
        self.config = copy.deepcopy(config)
        self.rate_limit = rate_limit
        self.prompt_manager = PromptManager()
        self.results = []
        self.stop_event = stop_event

        self.log_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        """Run the worker."""
        print(f"[{self.worker_id}] Starting with Token Budget: {self.token_budget}, Games: {self.num_games}")

        for game_idx in range(1, self.num_games + 1):
            if self.stop_event and self.stop_event.is_set():
                print(f"[{self.worker_id}] Aborting: stop signal received.")
                break

            print(f"[{self.worker_id}] Game {game_idx}/{self.num_games}...", end=" ", flush=True)

            try:
                result = self._run_single_game(game_idx)
            except TestAbortedError as e:
                print(f"[FATAL] Fatal error, aborting worker: {e}")
                self.results.append({
                    'success': False,
                    'worker_id': self.worker_id,
                    'game_idx': game_idx,
                    'token_budget': self.token_budget,
                    'error': str(e)
                })
                break

            self.results.append(result)

            if result['success']:
                print(f"[OK] Winner: {result['winner']}, Rounds: {result['rounds']}")
            else:
                print(f"[ERR] Error: {result['error']}")

        print(f"[{self.worker_id}] Completed {len(self.results)}/{self.num_games} games!")
        return self.results

    def _run_single_game(self, game_idx: int) -> Dict[str, Any]:
        """Run a single game."""
        original_budget = self.config.experiment.token_budget
        self.config.experiment.token_budget = self.token_budget

        try:
            exp_id = f"{self.worker_id}_game{game_idx:02d}_{datetime.now().strftime('%H%M%S')}"

            config_dict = {
                "api": {
                    "base_url": self.config.api.base_url,
                    "model_name": self.config.api.model_name,
                    "temperature": self.config.api.temperature,
                    "timeout": self.config.api.timeout
                },
                "world": {
                    "map_size": self.config.world.map_size,
                    "max_rounds": self.config.world.max_rounds,
                    "turn_order_mode": self.config.world.turn_order_mode
                },
                "physics": {
                    "perception_radius": self.config.physics.perception_radius,
                    "move_step": self.config.physics.move_step,
                    "capture_radius": self.config.physics.capture_radius,
                    "agent_b_capture_radius": getattr(self.config.physics, 'agent_b_capture_radius', 3.0)
                },
                "experiment": {
                    "token_budget": self.token_budget,
                    "prompt_strategy": self.config.experiment.prompt_strategy,
                    "num_runs": self.num_games,
                    "worker_id": self.worker_id
                },
                "spawn_points": getattr(self.config, 'spawn_points', None),
                "walls": getattr(self.config, 'walls', [])
            }

            logger = GameLogger(
                log_dir=str(self.log_dir),
                experiment_id=exp_id,
                config=config_dict,
                auto_timestamp=False
            )

            api_key = self.config.api.api_key
            if not api_key:
                import os
                api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or ""
                if api_key:
                    print(f"[{self.worker_id}] API key loaded from env for game {game_idx}")

            base_api_client = create_api_client(
                api_key=api_key,
                base_url=self.config.api.base_url,
                model=self.config.api.model_name,
                temperature=self.config.api.temperature,
                timeout=self.config.api.timeout
            )

            rate_limited_client = RateLimitedAPIClient(
                base_api_client,
                min_interval=self.rate_limit,
                stop_event=self.stop_event
            )

            agent_a = Agent(
                name="Agent_A",
                initial_pos=Position(0, 0),
                config=self.config,
                logger=logger,
                prompt_manager=self.prompt_manager,
                api_client=rate_limited_client
            )

            agent_b = Agent(
                name="Agent_B",
                initial_pos=Position(0, 0),
                config=self.config,
                logger=logger,
                prompt_manager=self.prompt_manager,
                api_client=rate_limited_client
            )

            engine = GameEngine(self.config, agent_a, agent_b, logger)
            start_time = time.time()
            result = engine.run_full_game()
            duration = time.time() - start_time

            return {
                'success': True,
                'worker_id': self.worker_id,
                'game_idx': game_idx,
                'token_budget': self.token_budget,
                'experiment_id': exp_id,
                'winner': result['winner'],
                'rounds': result['total_rounds'],
                'win_reason': result['win_reason'],
                'duration': duration,
                'log_file': logger.get_log_path()
            }

        except Exception as e:
            error_text = str(e)
            if _is_fatal_error(error_text):
                if self.stop_event:
                    self.stop_event.set()
                raise TestAbortedError(
                    f"Fatal API error in {self.worker_id} game {game_idx}: {error_text}"
                ) from e
            return {
                'success': False,
                'worker_id': self.worker_id,
                'game_idx': game_idx,
                'token_budget': self.token_budget,
                'error': error_text
            }

        finally:
            # Restore original config
            self.config.experiment.token_budget = original_budget


def run_parallel_gradient_test(
    token_budgets=[600, 800, 1000],
    games_per_budget=40,
    log_dir="logs/gradient_test",
    rate_limit=2.0
):
    """
    Run parallel gradient test.

    Args:
        token_budgets: List of token budgets to test
        games_per_budget: Number of games per budget (int or list[int])
        log_dir: Output directory for logs
        rate_limit: Minimum seconds between API requests
    """
    if isinstance(games_per_budget, int):
        games_per_budget = [games_per_budget] * len(token_budgets)

    if len(games_per_budget) != len(token_budgets):
        raise ValueError(
            f"Length of games_per_budget ({len(games_per_budget)}) must match "
            f"length of token_budgets ({len(token_budgets)}), or pass a single "
            f"value to apply to all budgets."
        )

    total_games = sum(games_per_budget)
    budget_games_map = dict(zip(token_budgets, games_per_budget))

    print("=" * 80)
    print("The Sand Pit - Parallel Gradient Test")
    print("=" * 80)
    print(f"\nConfiguration:")
    for token, num in budget_games_map.items():
        print(f"  Token Budget {token}: {num} games")
    print(f"  Total Games: {total_games}")
    print(f"  API Rate Limit: {rate_limit}s per request")
    print(f"  Log Directory: {log_dir}")
    print()

    config_path = Path("config.json")
    if config_path.exists():
        config = get_config(str(config_path))
    else:
        config = get_config()

    print(f"API Configuration:")
    print(f"  Base URL: {config.api.base_url}")
    print(f"  Model: {config.api.model_name}")
    print(f"  API Key: {config.api.api_key[:20] if config.api.api_key else '<EMPTY>'}...")
    print()

    if not config.api.api_key:
        import os
        env_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN") or os.getenv("OPENAI_API_KEY")
        if env_key:
            print(f"[WARN] config.api.api_key is empty, but found API key in environment variables.")
            print(f"[WARN] Setting config.api.api_key from env for this run.")
            config.api.api_key = env_key
        else:
            print(f"[FATAL] config.api.api_key is empty and no API key found in environment variables.")
            print(f"[FATAL] Please set one of: ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, OPENAI_API_KEY")
            print(f"[FATAL] Or add 'api_key' to config.json")
            return
    print()

    # Global stop event: set when any worker encounters a fatal error, all workers abort immediately
    stop_event = threading.Event()

    workers = []
    threads = []

    for token, num_games in zip(token_budgets, games_per_budget):
        worker_id = f"worker_{token}"
        worker = GradientWorker(
            worker_id=worker_id,
            token_budget=token,
            num_games=num_games,
            log_dir=log_dir,
            config=config,
            rate_limit=rate_limit,
            stop_event=stop_event
        )
        workers.append(worker)

    print("Starting all workers in parallel...\n")
    start_time = time.time()

    for worker in workers:
        thread = threading.Thread(target=worker.run)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    total_duration = time.time() - start_time

    # Summary
    print("\n" + "=" * 80)
    print("GRADIENT TEST SUMMARY")
    print("=" * 80)

    all_results = []
    for worker in workers:
        all_results.extend(worker.results)

    for token in token_budgets:
        worker_results = [r for r in all_results if r.get('token_budget') == token and r.get('success')]
        success_count = len(worker_results)
        expected_count = budget_games_map[token]

        if success_count > 0:
            wins = sum(1 for r in worker_results if r['winner'] == 'Agent_A')
            losses = sum(1 for r in worker_results if r['winner'] == 'Agent_B')
            draws = sum(1 for r in worker_results if r['winner'] is None)

            print(f"\nToken Budget {token}:")
            print(f"  Games: {success_count}/{expected_count}")
            print(f"  Win Rate: {wins/success_count*100:.1f}% ({wins}/{success_count})")
            print(f"  Loss Rate: {losses/success_count*100:.1f}% ({losses}/{success_count})")
            print(f"  Draw Rate: {draws/success_count*100:.1f}% ({draws}/{success_count})")

    print(f"\nTotal Duration: {total_duration/60:.1f} minutes")
    print(f"Average Time per Game: {total_duration/len(all_results):.1f} seconds")
    print(f"\nLog files saved to: {log_dir}")
    print("=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run parallel gradient test for The Sand Pit")
    parser.add_argument(
        "--tokens",
        nargs="+",
        type=int,
        default=[600, 800, 1000],
        help="Token budgets to test (default: 600 800 1000)"
    )
    parser.add_argument(
        "--games",
        nargs="+",
        type=int,
        default=[40],
        help="Number of games per token budget. Pass one value to apply to all budgets, "
             "or pass the same number of values as --tokens for per-budget control. (default: 40)"
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs/gradient_test",
        help="Output directory for logs (default: logs/gradient_test)"
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=2.0,
        help="Minimum seconds between API requests (default: 2.0)"
    )

    args = parser.parse_args()

    games_per_budget = args.games
    if len(games_per_budget) == 1:
        games_per_budget = [games_per_budget[0]] * len(args.tokens)
    elif len(games_per_budget) != len(args.tokens):
        parser.error(
            f"Length of --games ({len(args.games)}) must match length of --tokens ({len(args.tokens)}), "
            f"or pass a single value to apply to all budgets."
        )

    run_parallel_gradient_test(
        token_budgets=args.tokens,
        games_per_budget=games_per_budget,
        log_dir=args.log_dir,
        rate_limit=args.rate_limit
    )


if __name__ == "__main__":
    main()
