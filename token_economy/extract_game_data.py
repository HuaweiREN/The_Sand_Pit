"""
Token Economy Data Extractor
Extract per-round token usage, positions, and game phases from all log files.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import csv

LOG_ROOT = Path("../log_final")
OUTPUT_DIR = Path(".")


@dataclass
class RoundData:
    round_num: int
    agent_a_pos: tuple
    agent_b_pos: tuple
    distance: float
    token_budget: int
    tokens_used: int
    latency_ms: float
    raw_content: str
    thought_process: str
    target_x: float
    target_y: float
    wall_blocked: bool
    movement_clamped: bool
    boundary_clamped: bool
    logic_action_delta: Optional[float]
    is_opponent_visible: bool
    phase: str = "unknown"


@dataclass
class GameData:
    experiment_id: str
    model_name: str
    token_budget: int
    thinking_enabled: Optional[bool]
    winner: Optional[str]
    total_rounds: int
    win_reason: str
    rounds: List[RoundData]
    total_tokens_used: int
    parse_errors: int


def parse_jsonl(filepath: Path) -> List[Dict[str, Any]]:
    events = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def determine_phase(round_data: RoundData) -> str:
    """
    Determine game phase for this round.
    Revised definition based on proximity to wall (Researcher 3):
    - phase1: Before approaching wall (x < 22, i.e., >1 move_step away from wall)
    - phase2: Wall navigation zone (x in [22, 28], covering approach, collision,
              detour, and immediate post-wall transition)
    - phase3: Post-wall approach (x > 28, i.e., >1 move_step past wall,
              opponent not yet visible)
    - phase4: Hunt/kill (opponent visible, i.e., distance <= 10 at round start)
    """
    x = round_data.agent_a_pos[0]

    # Phase 4: opponent is visible
    if round_data.is_opponent_visible:
        return "phase4_hunt"

    # Phase 2: within wall influence zone [22, 28]
    # 22 = 25 - move_step (3): within one move from wall on left side
    # 28 = 25 + move_step (3): within one move from wall on right side
    if 22 <= x <= 28:
        return "phase2_wall_nav"

    # Phase 3: clearly past wall (x > 28) but opponent not visible yet
    if x > 28:
        return "phase3_postwall"

    # Phase 1: default before wall (x < 22)
    return "phase1_prewall"


def extract_game_data(jsonl_path: Path, summary_path: Path) -> Optional[GameData]:
    events = parse_jsonl(jsonl_path)
    if not events:
        return None

    # Parse summary
    with open(summary_path, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    # Extract config from first event
    config = events[0].get('config', {})
    model_name = config.get('api', {}).get('model_name', 'unknown')
    token_budget = config.get('experiment', {}).get('token_budget', 0)

    # Detect thinking mode from model name or path
    thinking_enabled = None
    path_str = str(jsonl_path).lower()
    if 'thinking_enabled' in path_str:
        thinking_enabled = True
    elif 'thinking_disabled' in path_str:
        thinking_enabled = False

    rounds_data = []
    current_round = 0
    round_tokens = 0
    round_latency = 0.0
    round_raw = ""
    round_thought = ""
    round_target_x = 0.0
    round_target_y = 0.0
    round_wall_blocked = False
    round_movement_clamped = False
    round_boundary_clamped = False
    round_logic_delta = None
    round_a_pos = (0.0, 0.0)
    round_b_pos = (40.0, 15.0)
    round_distance = 42.72
    round_visible = False
    round_budget = token_budget

    ever_wall_blocked = False
    ever_seen_opponent = False
    passed_wall = False

    for event in events:
        etype = event.get('event_type')

        if etype == 'round_start':
            current_round = event.get('round', 0)
            gs = event.get('game_state', {})
            ags = gs.get('agent_a', {})
            bgs = gs.get('agent_b', {})
            round_a_pos = tuple(ags.get('position', [0.0, 0.0]))
            round_b_pos = tuple(bgs.get('position', [40.0, 15.0]))
            round_distance = gs.get('distance', 42.72)
            round_visible = round_distance <= 10.0
            if round_visible:
                ever_seen_opponent = True
            if round_a_pos[0] > 25:
                passed_wall = True

            # Reset per-round accumulators
            round_tokens = 0
            round_latency = 0.0
            round_raw = ""
            round_thought = ""
            round_target_x = 0.0
            round_target_y = 0.0
            round_wall_blocked = False
            round_movement_clamped = False
            round_boundary_clamped = False
            round_logic_delta = None

        elif etype == 'api_request':
            round_budget = event.get('token_budget', token_budget)

        elif etype == 'api_response':
            resp = event.get('response', {})
            round_raw = resp.get('raw_content', '')
            round_latency = event.get('latency_ms', 0.0)
            usage = resp.get('usage', {})
            round_tokens = usage.get('total_tokens', 0)

            parsed = resp.get('parsed_content')
            if parsed:
                round_target_x = float(parsed.get('x', 0.0))
                round_target_y = float(parsed.get('y', 0.0))
                round_thought = parsed.get('thought_process', '') or parsed.get('reasoning', '')
            else:
                # Try to extract from raw content if parsed is null
                raw = resp.get('raw_content', '')
                if '"thought_process"' in raw:
                    try:
                        # crude extraction
                        start = raw.find('"thought_process"')
                        end = raw.find('"x"', start)
                        round_thought = raw[start:end].replace('"thought_process":', '').strip().strip(',').strip().strip('"')
                    except Exception:
                        round_thought = ""

        elif etype == 'movement':
            val = event.get('validation', {})
            round_wall_blocked = val.get('wall_blocked', False)
            round_movement_clamped = val.get('movement_clamped', False)
            round_boundary_clamped = val.get('boundary_clamped', False)
            if round_wall_blocked:
                ever_wall_blocked = True

        elif etype == 'turn_end':
            agent_name = event.get('agent', '')
            if 'Agent_A' in agent_name:
                round_logic_delta = event.get('logic_action_delta')
                # Record round data
                rd = RoundData(
                    round_num=current_round,
                    agent_a_pos=round_a_pos,
                    agent_b_pos=round_b_pos,
                    distance=round_distance,
                    token_budget=round_budget,
                    tokens_used=round_tokens,
                    latency_ms=round_latency,
                    raw_content=round_raw[:500],  # truncate for memory
                    thought_process=round_thought[:500],
                    target_x=round_target_x,
                    target_y=round_target_y,
                    wall_blocked=round_wall_blocked,
                    movement_clamped=round_movement_clamped,
                    boundary_clamped=round_boundary_clamped,
                    logic_action_delta=round_logic_delta,
                    is_opponent_visible=round_visible
                )
                rd.phase = determine_phase(rd)
                rounds_data.append(rd)

    # Compute total tokens from rounds
    total_tokens = sum(r.tokens_used for r in rounds_data)

    return GameData(
        experiment_id=summary.get('experiment_id', ''),
        model_name=model_name,
        token_budget=token_budget,
        thinking_enabled=thinking_enabled,
        winner=summary.get('result', {}).get('winner'),
        total_rounds=summary.get('result', {}).get('total_rounds', 0),
        win_reason=summary.get('result', {}).get('win_reason', ''),
        rounds=rounds_data,
        total_tokens_used=total_tokens,
        parse_errors=summary.get('statistics', {}).get('parse_errors', 0)
    )


def main():
    all_games = []

    for model_dir in LOG_ROOT.iterdir():
        if not model_dir.is_dir():
            continue
        print(f"Processing {model_dir.name} ...")
        jsonl_files = list(model_dir.glob("*.jsonl"))
        for jsonl_path in jsonl_files:
            summary_path = jsonl_path.with_suffix('').with_name(jsonl_path.stem + "_summary.json")
            if not summary_path.exists():
                continue
            try:
                game = extract_game_data(jsonl_path, summary_path)
                if game:
                    all_games.append(game)
            except Exception as e:
                print(f"  Error processing {jsonl_path.name}: {e}")

    print(f"\nTotal games extracted: {len(all_games)}")

    # Write CSV: per-round data
    csv_path = OUTPUT_DIR / "all_rounds.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'experiment_id', 'model_name', 'thinking_enabled', 'token_budget',
            'winner', 'total_rounds', 'win_reason',
            'round_num', 'phase',
            'agent_a_x', 'agent_a_y', 'agent_b_x', 'agent_b_y',
            'distance', 'is_opponent_visible',
            'tokens_used', 'token_budget_round', 'latency_ms',
            'wall_blocked', 'movement_clamped', 'boundary_clamped',
            'logic_action_delta', 'target_x', 'target_y'
        ])
        for game in all_games:
            for r in game.rounds:
                writer.writerow([
                    game.experiment_id, game.model_name, game.thinking_enabled, game.token_budget,
                    game.winner, game.total_rounds, game.win_reason,
                    r.round_num, r.phase,
                    r.agent_a_pos[0], r.agent_a_pos[1], r.agent_b_pos[0], r.agent_b_pos[1],
                    r.distance, r.is_opponent_visible,
                    r.tokens_used, r.token_budget, r.latency_ms,
                    r.wall_blocked, r.movement_clamped, r.boundary_clamped,
                    r.logic_action_delta, r.target_x, r.target_y
                ])

    # Write CSV: per-game summary
    csv_game_path = OUTPUT_DIR / "all_games.csv"
    with open(csv_game_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'experiment_id', 'model_name', 'thinking_enabled', 'token_budget',
            'winner', 'total_rounds', 'win_reason',
            'total_tokens_used', 'parse_errors', 'num_rounds_with_data'
        ])
        for game in all_games:
            writer.writerow([
                game.experiment_id, game.model_name, game.thinking_enabled, game.token_budget,
                game.winner, game.total_rounds, game.win_reason,
                game.total_tokens_used, game.parse_errors, len(game.rounds)
            ])

    print(f"Saved {csv_path}")
    print(f"Saved {csv_game_path}")

    # Print quick stats
    from collections import Counter
    model_counts = Counter(g.model_name for g in all_games)
    print("\nGames per model:")
    for m, c in model_counts.most_common():
        print(f"  {m}: {c}")

    winner_counts = Counter(str(g.winner) for g in all_games)
    print("\nWinners overall:")
    for w, c in winner_counts.most_common():
        print(f"  {w}: {c}")


if __name__ == "__main__":
    main()
