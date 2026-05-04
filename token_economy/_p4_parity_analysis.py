import json
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

LOG_ROOT = Path("../log_final")
games = pd.read_csv('./all_games.csv')

flash_games = games[(games['model_name'] == 'deepseek-v4-flash') & (games['thinking_enabled'] == False) & (games['token_budget'] <= 2000)]
pro_games = games[(games['model_name'] == 'deepseek-v4-pro') & (games['thinking_enabled'] == False) & (games['token_budget'] <= 2000)]

def analyze_p4(model_name, gdf):
    print(f'\n{"="*70}')
    print(f'P4 PARITY ANALYSIS: {model_name}')
    print(f'{"="*70}')

    results = []
    for _, game in gdf.iterrows():
        gid = game['experiment_id']
        winner = game['winner']
        budget = game['token_budget']

        # Find log file
        found = False
        for model_dir in LOG_ROOT.iterdir():
            if not model_dir.is_dir():
                continue
            for jsonl_path in model_dir.glob(f"{gid}.jsonl"):
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    events = [json.loads(l.strip()) for l in f if l.strip()]

                # Find first P4 round
                p4_start_round = None
                p4_start_dist = None
                p4_start_parity = None
                p4_start_a_pos = None

                for e in events:
                    if e.get('event_type') == 'round_start':
                        gs = e.get('game_state', {})
                        dist = gs.get('distance', 999)
                        if dist <= 10 and p4_start_round is None:
                            p4_start_round = e.get('round')
                            p4_start_dist = dist
                            p4_start_parity = e.get('first_actor')
                            p4_start_a_pos = gs.get('agent_a', {}).get('position')

                if p4_start_round is None:
                    continue

                # Analyze P4 behavior
                p4_events = []
                for e in events:
                    if e.get('event_type') == 'round_start':
                        gs = e.get('game_state', {})
                        if gs.get('distance', 999) <= 10:
                            p4_events.append({
                                'round': e.get('round'),
                                'first_actor': e.get('first_actor'),
                                'start_dist': gs.get('distance'),
                                'a_pos': gs.get('agent_a', {}).get('position'),
                            })
                    elif e.get('event_type') == 'turn_end' and p4_events:
                        if e.get('agent') == 'Agent_A':
                            p4_events[-1]['a_pos_after'] = e.get('position_after')
                            p4_events[-1]['a_capture'] = e.get('capture_check', {}).get('captured')
                            p4_events[-1]['a_dist_after'] = e.get('capture_check', {}).get('distance')

                # Compute movement metrics
                dist_changes = []
                move_distances = []
                for i in range(len(p4_events)):
                    if 'a_pos_after' in p4_events[i] and 'a_pos' in p4_events[i]:
                        before = np.array(p4_events[i]['a_pos'])
                        after = np.array(p4_events[i]['a_pos_after'])
                        move_dist = np.linalg.norm(after - before)
                        move_distances.append(move_dist)
                    if i > 0 and 'start_dist' in p4_events[i] and 'start_dist' in p4_events[i-1]:
                        dist_changes.append(p4_events[i]['start_dist'] - p4_events[i-1]['start_dist'])

                # Check if A ever "waits" (moves less than 2.0)
                waits = [m for m in move_distances if m < 2.0]

                results.append({
                    'gid': gid,
                    'budget': budget,
                    'winner': winner if pd.notna(winner) else 'Draw',
                    'p4_start_round': p4_start_round,
                    'p4_start_dist': p4_start_dist,
                    'p4_start_parity': p4_start_parity,
                    'p4_rounds': len(p4_events),
                    'avg_move_dist': np.mean(move_distances) if move_distances else 0,
                    'avg_dist_change': np.mean(dist_changes) if dist_changes else 0,
                    'wait_count': len(waits),
                    'min_dist_reached': min(e.get('start_dist', 999) for e in p4_events),
                })
                found = True
                break
            if found:
                break

    df = pd.DataFrame(results)
    if len(df) == 0:
        return

    print(f'\nTotal P4 games: {len(df)}')

    # === PARITY HYPOTHESIS ===
    print('\n--- P4 Outcome by Starting Parity ---')
    for parity in ['Agent_A', 'Agent_B']:
        pdf = df[df['p4_start_parity'] == parity]
        print(f'\nP4 starts on {parity}-first round (N={len(pdf)}):')
        for outcome in ['Agent_A', 'Agent_B', 'Draw']:
            count = (pdf['winner'] == outcome).sum()
            print(f'  {outcome}: {count} ({count/len(pdf)*100:.1f}%)')

    # Test significance
    contingency = pd.crosstab(df['p4_start_parity'], df['winner'])
    print(f'\nContingency table:')
    print(contingency)

    if contingency.shape == (2, 3):
        chi2, p, dof, expected = stats.chi2_contingency(contingency)
        print(f'\nChi-square test: chi2={chi2:.3f}, p={p:.4f}')

    # === DISTANCE BAND HYPOTHESIS ===
    print('\n--- P4 Outcome by Starting Distance Band ---')
    df['dist_band'] = pd.cut(df['p4_start_dist'], bins=[0, 6, 7, 8, 9, 10], labels=['<=6', '6-7', '7-8', '8-9', '9-10'])
    for band in df['dist_band'].cat.categories:
        bdf = df[df['dist_band'] == band]
        if len(bdf) == 0:
            continue
        print(f'\nStart dist {band} (N={len(bdf)}):')
        for outcome in ['Agent_A', 'Agent_B', 'Draw']:
            count = (bdf['winner'] == outcome).sum()
            print(f'  {outcome}: {count} ({count/len(bdf)*100:.1f}%)')

    # === PARITY x DISTANCE ===
    print('\n--- P4 Outcome by Parity + Distance Band ---')
    for parity in ['Agent_A', 'Agent_B']:
        for band in ['7-8', '8-9']:
            sbdf = df[(df['p4_start_parity'] == parity) & (df['dist_band'] == band)]
            if len(sbdf) == 0:
                continue
            a_rate = (sbdf['winner'] == 'Agent_A').mean() * 100
            b_rate = (sbdf['winner'] == 'Agent_B').mean() * 100
            print(f'{parity} first, dist {band}: A={a_rate:.1f}%, B={b_rate:.1f}% (N={len(sbdf)})')

    # === STRATEGIC BEHAVIOR ===
    print('\n--- Strategic Behavior Analysis ---')
    print(f'Avg move distance in P4: {df["avg_move_dist"].mean():.2f} (max=3.0)')
    print(f'Games where A "waits" (move < 2.0): {(df["wait_count"] > 0).sum()}/{len(df)}')

    # Compare winners vs losers
    a_wins = df[df['winner'] == 'Agent_A']
    b_wins = df[df['winner'] == 'Agent_B']
    print(f'\nA-win games: avg move={a_wins["avg_move_dist"].mean():.2f}, waiters={(a_wins["wait_count"] > 0).sum()}')
    print(f'B-win games: avg move={b_wins["avg_move_dist"].mean():.2f}, waiters={(b_wins["wait_count"] > 0).sum()}')

    # === BUDGET EFFECT ===
    print('\n--- Budget Effect on P4 Outcome ---')
    for budget in sorted(df['budget'].unique()):
        bdf = df[df['budget'] == budget]
        a_rate = (bdf['winner'] == 'Agent_A').mean() * 100
        b_rate = (bdf['winner'] == 'Agent_B').mean() * 100
        print(f'Budget {budget}: A={a_rate:.1f}%, B={b_rate:.1f}% (N={len(bdf)})')

    return df

# Run for both models
flash_df = analyze_p4('Flash', flash_games)
pro_df = analyze_p4('Pro', pro_games)
