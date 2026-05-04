import pandas as pd
import numpy as np
from scipy import stats

rounds = pd.read_csv('all_rounds.csv')
games = pd.read_csv('all_games.csv')

# Helper: separate flash/pro/ds_all
flash_games = games[(games['model_name'] == 'deepseek-v4-flash') & (games['thinking_enabled'] == False) & (games['token_budget'] <= 2000)]
flash_rounds = rounds[(rounds['model_name'] == 'deepseek-v4-flash') & (rounds['thinking_enabled'] == False) & (rounds['token_budget'] <= 2000)]

pro_games = games[(games['model_name'] == 'deepseek-v4-pro') & (games['thinking_enabled'] == False) & (games['token_budget'] <= 2000)]
pro_rounds = rounds[(rounds['model_name'] == 'deepseek-v4-pro') & (rounds['thinking_enabled'] == False) & (rounds['token_budget'] <= 2000)]

ds_games = games[(games['model_name'].str.contains('deepseek')) & (games['thinking_enabled'] == False) & (games['token_budget'] <= 2000)]
ds_rounds = rounds[(rounds['model_name'].str.contains('deepseek')) & (rounds['thinking_enabled'] == False) & (rounds['token_budget'] <= 2000)]

print('='*70)
print('M1: GLOBAL WIN RATES')
print('='*70)

for name, gdf in [('Flash', flash_games), ('Pro', pro_games)]:
    print(f'\n=== {name} ===')
    for budget in sorted(gdf['token_budget'].unique()):
        bg = gdf[gdf['token_budget'] == budget]
        total = len(bg)
        a = (bg['winner'] == 'Agent_A').sum()
        b = (bg['winner'] == 'Agent_B').sum()
        d = bg['winner'].isna().sum()
        print(f'Budget {budget}: A={a}({a/total*100:.1f}%) B={b}({b/total*100:.1f}%) Draw={d}({d/total*100:.1f}%) | N={total}')

print('\n' + '='*70)
print('M2: DRAW ECONOMICS (Flash)')
print('='*70)

flash_outcome = flash_games.groupby('winner')['total_tokens_used'].agg(['count','mean','median','std'])
print(flash_outcome.round(0))

print('\n=== Draw vs Non-Draw rounds in P2 (Flash) ===')
for budget in [1200]:
    bg_ids = flash_games[flash_games['token_budget'] == budget]['experiment_id'].unique()
    draw_p2 = []
    win_p2 = []
    for gid in bg_ids:
        gr = flash_rounds[(flash_rounds['experiment_id'] == gid)]
        is_draw = flash_games[flash_games['experiment_id'] == gid]['winner'].isna().iloc[0]
        p2 = gr[gr['phase'] == 'phase2_wall_nav']
        if is_draw:
            draw_p2.append(len(p2))
        else:
            win_p2.append(len(p2))
    if draw_p2 and win_p2:
        print(f'Budget {budget}: Draw P2 median={sorted(draw_p2)[len(draw_p2)//2]}, Win P2 median={sorted(win_p2)[len(win_p2)//2]}')

print('\n' + '='*70)
print('M3: PHASE HETEROGENEITY')
print('='*70)

# Phase duration
for name, rdf in [('Flash', flash_rounds), ('Pro', pro_rounds)]:
    print(f'\n=== {name} Phase Duration ===')
    gids = rdf['experiment_id'].unique()
    for phase in ['phase1_prewall', 'phase2_wall_nav', 'phase3_postwall', 'phase4_hunt']:
        durs = []
        for gid in gids:
            gr = rdf[rdf['experiment_id'] == gid]
            durs.append(len(gr[gr['phase'] == phase]))
        if durs:
            print(f'{phase}: mean={np.mean(durs):.1f}, median={sorted(durs)[len(durs)//2]}, n_games_with_phase={sum(1 for d in durs if d > 0)}/{len(gids)}')

# P2 pass rate by budget (detailed)
print('\n=== P2 Pass Rate Detail ===')
for name, gdf, rdf in [('Flash', flash_games, flash_rounds), ('Pro', pro_games, pro_rounds)]:
    print(f'\n{name}:')
    for budget in sorted(gdf['token_budget'].unique()):
        bg = gdf[gdf['token_budget'] == budget]
        total = len(bg)
        passed = 0
        for gid in bg['experiment_id'].unique():
            gr = rdf[(rdf['experiment_id'] == gid)]
            if 'phase3_postwall' in gr['phase'].values or 'phase4_hunt' in gr['phase'].values:
                passed += 1
        print(f'  Budget {budget}: passed={passed}/{total} ({passed/total*100:.1f}%)')

# P3->P4 conversion
print('\n=== P3->P4 Conversion ===')
for name, gdf, rdf in [('Flash', flash_games, flash_rounds), ('Pro', pro_games, pro_rounds)]:
    p3_games = 0
    p4_games = 0
    for gid in gdf['experiment_id'].unique():
        gr = rdf[rdf['experiment_id'] == gid]
        has_p3 = 'phase3_postwall' in gr['phase'].values
        has_p4 = 'phase4_hunt' in gr['phase'].values
        if has_p3:
            p3_games += 1
            if has_p4:
                p4_games += 1
    print(f'{name}: P3 games={p3_games}, reached P4={p4_games} ({p4_games/p3_games*100:.1f}%)')

print('\n' + '='*70)
print('M4: OVERTHINKING PARADOX')
print('='*70)

flash_rounds['token_pctile'] = flash_rounds.groupby('token_budget')['tokens_used'].transform(lambda x: x.rank(pct=True) if len(x) > 1 else pd.Series([0.5]*len(x), index=x.index))
flash_rounds['high_token'] = flash_rounds['token_pctile'] > 0.75

high = flash_rounds[flash_rounds['high_token'] == True]
normal = flash_rounds[flash_rounds['high_token'] == False]

for metric in ['wall_blocked', 'movement_clamped', 'logic_action_delta']:
    h = high[metric].dropna()
    n = normal[metric].dropna()
    if len(h) > 10 and len(n) > 10:
        u, p = stats.mannwhitneyu(h, n, alternative='two-sided')
        print(f'{metric}: high_mean={h.mean():.4f}, normal_mean={n.mean():.4f}, p={p:.4f}')

# distance_reduction
h = high['distance_reduction'].dropna()
n = normal['distance_reduction'].dropna()
if len(h) > 10 and len(n) > 10:
    u, p = stats.mannwhitneyu(h, n, alternative='two-sided')
    print(f'distance_reduction: high_mean={h.mean():.4f}, normal_mean={n.mean():.4f}, p={p:.4f}')

print('\n' + '='*70)
print('M5: MODEL DIFFERENCES')
print('='*70)

# Correlation budget vs tokens_used
for name, rdf in [('Flash', flash_rounds), ('Pro', pro_rounds)]:
    data = rdf[rdf['tokens_used'] > 0]
    corr = data['token_budget'].corr(data['tokens_used'])
    slope, intercept, r_value, p_value, std_err = stats.linregress(data['token_budget'], data['tokens_used'])
    print(f'{name}: r={corr:.3f}, slope={slope:.3f}, p={p_value:.2e}')

    # Mean tokens by budget
    means = data.groupby('token_budget')['tokens_used'].mean()
    print(f'  Mean tokens by budget:')
    for b, m in means.items():
        print(f'    {b}: {m:.0f}')

print('\n' + '='*70)
print('M6: THINKING MODE')
print('='*70)

thinking_games = games[
    (games['model_name'].str.contains('deepseek')) &
    (games['thinking_enabled'] == True)
]
print(f'Thinking games total: {len(thinking_games)}')
for budget in sorted(thinking_games['token_budget'].unique()):
    bg = thinking_games[thinking_games['token_budget'] == budget]
    total = len(bg)
    a = (bg['winner'] == 'Agent_A').sum()
    b = (bg['winner'] == 'Agent_B').sum()
    d = bg['winner'].isna().sum()
    print(f'Budget {budget}: A={a}({a/total*100:.1f}%) B={b}({b/total*100:.1f}%) Draw={d}({d/total*100:.1f}%) | N={total}')

# Non-thinking for comparison at same budgets
print('\nNon-thinking comparison:')
non_think = games[
    (games['model_name'].str.contains('deepseek')) &
    (games['thinking_enabled'] == False) &
    (games['token_budget'].isin(thinking_games['token_budget'].unique()))
]
for budget in sorted(non_think['token_budget'].unique()):
    bg = non_think[non_think['token_budget'] == budget]
    total = len(bg)
    a = (bg['winner'] == 'Agent_A').sum()
    b = (bg['winner'] == 'Agent_B').sum()
    d = bg['winner'].isna().sum()
    print(f'Budget {budget}: A={a}({a/total*100:.1f}%) B={b}({b/total*100:.1f}%) Draw={d}({d/total*100:.1f}%) | N={total}')
