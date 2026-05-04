import json
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter

LOG_ROOT = Path("../log_final")
games = pd.read_csv('./all_games.csv')

# Find sample games that reached P4 and ended with different outcomes
flash_games = games[(games['model_name'] == 'deepseek-v4-flash') & (games['thinking_enabled'] == False) & (games['token_budget'] == 1200)]

samples = {
    'Agent_A': [],
    'Agent_B': [],
    'Draw': []
}

for _, game in flash_games.iterrows():
    gid = game['experiment_id']
    winner = game['winner']

    # Find the jsonl file
    for model_dir in LOG_ROOT.iterdir():
        if not model_dir.is_dir():
            continue
        for jsonl_path in model_dir.glob(f"{gid}.jsonl"):
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                events = [json.loads(l.strip()) for l in f if l.strip()]

            # Find P4 rounds (where distance <= 10 at round_start)
            p4_events = []
            for e in events:
                if e.get('event_type') == 'round_start':
                    gs = e.get('game_state', {})
                    dist = gs.get('distance', 999)
                    if dist <= 10:
                        p4_events.append({
                            'round': e.get('round'),
                            'first_actor': e.get('first_actor'),
                            'start_dist': dist,
                            'a_pos': gs.get('agent_a', {}).get('position'),
                            'b_pos': gs.get('agent_b', {}).get('position'),
                            'turns': []
                        })
                elif e.get('event_type') == 'turn_end' and p4_events:
                    p4_events[-1]['turns'].append({
                        'agent': e.get('agent'),
                        'pos_after': e.get('position_after'),
                        'capture': e.get('capture_check', {}),
                        'logic_delta': e.get('logic_action_delta')
                    })
                elif e.get('event_type') == 'game_end' and p4_events:
                    p4_events[-1]['game_end'] = e

            wkey = winner if pd.notna(winner) else 'Draw'
            if p4_events and len(samples.get(wkey, [])) < 3:
                samples[wkey].append({
                    'gid': gid,
                    'winner': winner,
                    'p4': p4_events
                })
            break

for winner_type, games_list in samples.items():
    print(f'\n{"="*70}')
    print(f'WINNER: {winner_type}')
    print(f'{"="*70}')
    for g in games_list[:2]:
        print(f'\nGame: {g["gid"]}')
        for r in g['p4']:
            print(f"  Round {r['round']} ({r['first_actor']} first): start_dist={r['start_dist']:.2f}, A={r['a_pos']}")
            for t in r['turns']:
                cap = t['capture']
                print(f"    {t['agent']}: pos={t['pos_after']}, dist={cap.get('distance', 'N/A'):.2f}, captured={cap.get('captured')}")
            if 'game_end' in r:
                print(f"    >>> GAME END: winner={r['game_end'].get('winner')}, reason={r['game_end'].get('win_reason')}")
