import pandas as pd
import numpy as np
from scipy import stats

rounds = pd.read_csv('./all_rounds.csv')
games = pd.read_csv('./all_games.csv')

flash_games = games[(games['model_name'] == 'deepseek-v4-flash') & (games['thinking_enabled'] == False) & (games['token_budget'] <= 2000)]
flash_rounds = rounds[(rounds['model_name'] == 'deepseek-v4-flash') & (rounds['thinking_enabled'] == False) & (rounds['token_budget'] <= 2000)]

pro_games = games[(games['model_name'] == 'deepseek-v4-pro') & (games['thinking_enabled'] == False) & (games['token_budget'] <= 2000)]
pro_rounds = rounds[(rounds['model_name'] == 'deepseek-v4-pro') & (rounds['thinking_enabled'] == False) & (rounds['token_budget'] <= 2000)]

print('='*70)
print('P4 HUNT PHASE ANALYSIS')
print('='*70)

for name, gdf, rdf in [('Flash', flash_games, flash_rounds), ('Pro', pro_games, pro_rounds)]:
    print(f'\n=== {name} ===')

    p4_games = []
    for gid in gdf['experiment_id'].unique():
        gr = rdf[rdf['experiment_id'] == gid]
        p4 = gr[gr['phase'] == 'phase4_hunt']
        if len(p4) == 0:
            continue

        game = gdf[gdf['experiment_id'] == gid].iloc[0]
        winner = game['winner']
        budget = game['token_budget']

        first_p4 = p4.iloc[0]
        last_p4 = p4.iloc[-1]
        p4_rounds = len(p4)

        first_dist = first_p4['distance']
        last_dist = last_p4['distance']
        min_dist = p4['distance'].min()

        danger_rounds = p4[(p4['distance'] <= 3.0) & (p4['distance'] > 0.5)]
        capture_rounds = p4[p4['distance'] <= 0.5]

        p4_movements = []
        for i in range(1, len(p4)):
            prev = p4.iloc[i-1]
            curr = p4.iloc[i]
            dist_change = curr['distance'] - prev['distance']
            p4_movements.append(dist_change)

        p4_games.append({
            'gid': gid,
            'budget': budget,
            'winner': winner,
            'p4_rounds': p4_rounds,
            'first_dist': first_dist,
            'last_dist': last_dist,
            'min_dist': min_dist,
            'danger_count': len(danger_rounds),
            'capture_count': len(capture_rounds),
            'avg_dist_change': np.mean(p4_movements) if p4_movements else 0,
        })

    df = pd.DataFrame(p4_games)
    if len(df) == 0:
        continue

    print(f'Total games reaching P4: {len(df)}')
    print(f'Winners: A={(df["winner"]=="Agent_A").sum()}, B={(df["winner"]=="Agent_B").sum()}, Draw={df["winner"].isna().sum()}')

    for budget in sorted(df['budget'].unique()):
        bdf = df[df['budget'] == budget]
        print(f'\n  Budget {budget} (N={len(bdf)}):')
        a_wins = (bdf['winner'] == 'Agent_A').sum()
        b_wins = (bdf['winner'] == 'Agent_B').sum()
        draws = bdf['winner'].isna().sum()
        print(f'    A_Win={a_wins}({a_wins/len(bdf)*100:.1f}%) B_Win={b_wins}({b_wins/len(bdf)*100:.1f}%) Draw={draws}({draws/len(bdf)*100:.1f}%)')
        print(f'    P4 rounds: {bdf["p4_rounds"].median():.0f} (median)')
        print(f'    Min distance reached: {bdf["min_dist"].median():.2f} (median)')
        print(f'    Games entering danger zone (d<=3.0, d>0.5): {(bdf["danger_count"] > 0).sum()}')
        print(f'    Games reaching capture range (d<=0.5): {(bdf["capture_count"] > 0).sum()}')

print('\n' + '='*70)
print('P4 DETAILED BEHAVIOR: Distance Trajectories')
print('='*70)

# Flash @ 1200 - look at distance trajectories in P4
for name, gdf, rdf in [('Flash', flash_games, flash_rounds)]:
    for gid in gdf[gdf['token_budget'] == 1200]['experiment_id'].unique()[:10]:
        gr = rdf[rdf['experiment_id'] == gid]
        p4 = gr[gr['phase'] == 'phase4_hunt']
        if len(p4) == 0:
            continue
        game = gdf[gdf['experiment_id'] == gid].iloc[0]
        winner = game['winner']
        dists = p4['distance'].tolist()
        print(f'{gid}: winner={winner}, P4 dists={["%.1f" % d for d in dists]}')
