"""
Token Economy Analysis - Researcher 3
Comprehensive statistical analysis of token usage vs. agent performance.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Setup
OUTPUT_DIR = Path(".")
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Load data
rounds = pd.read_csv(OUTPUT_DIR / "all_rounds.csv")
games = pd.read_csv(OUTPUT_DIR / "all_games.csv")

# ============================================================================
# DATA CLEANING & PREPARATION
# ============================================================================

# Exclude the anomalous 20000 token budget for now (deepseek stress test)
# Keep it for a separate analysis
rounds_main = rounds[rounds['token_budget'] <= 2000].copy()
games_main = games[games['token_budget'] <= 2000].copy()

# Mark parsed vs unparsed rounds
rounds_main['parsed_success'] = ~((rounds_main['target_x'] == 0.0) & (rounds_main['target_y'] == 0.0) & (rounds_main['tokens_used'] > 0))

# Compute per-round spatial progress (distance reduction)
# Need to shift within each game
rounds_main = rounds_main.sort_values(['experiment_id', 'round_num'])
rounds_main['prev_distance'] = rounds_main.groupby('experiment_id')['distance'].shift(1)
rounds_main['distance_reduction'] = rounds_main['prev_distance'] - rounds_main['distance']

# Token efficiency: distance reduced per token (only for rounds with positive tokens)
rounds_main['token_efficiency'] = rounds_main['distance_reduction'] / rounds_main['tokens_used'].replace(0, np.nan)

# Create outcome categories
def categorize_winner(w):
    if w == 'Agent_A':
        return 'A_Win'
    elif w == 'Agent_B':
        return 'B_Win'
    else:
        return 'Draw'

games_main['outcome'] = games_main['winner'].apply(categorize_winner)
rounds_main['outcome'] = rounds_main['winner'].apply(categorize_winner)

# Budget groups
budget_labels = {400: '400', 600: '600', 800: '800', 1000: '1000',
                 1200: '1200', 1400: '1400', 1600: '1600', 1800: '1800', 2000: '2000'}
rounds_main['budget_group'] = rounds_main['token_budget'].map(budget_labels)
games_main['budget_group'] = games_main['token_budget'].map(budget_labels)

print("=" * 70)
print("TOKEN ECONOMY ANALYSIS - RESEARCHER 3")
print("=" * 70)
print(f"\nDataset: {len(games_main)} games, {len(rounds_main)} rounds")
print(f"Token budgets: {sorted(rounds_main['token_budget'].unique())}")
print(f"Models: {rounds_main['model_name'].unique()}")
print(f"Thinking configs: {sorted(rounds_main['thinking_enabled'].dropna().unique())}")


# ============================================================================
# SECTION A: TOKEN BUDGET COMPLIANCE & UTILIZATION
# ============================================================================

print("\n" + "=" * 70)
print("SECTION A: TOKEN BUDGET COMPLIANCE & UTILIZATION")
print("=" * 70)

# A1. Overall token usage statistics
print("\n[A1] Overall Token Usage by Budget (all rounds with API calls):")
a1 = rounds_main[rounds_main['tokens_used'] > 0].groupby('token_budget')['tokens_used'].agg(['count', 'mean', 'median', 'std', 'min', 'max']).round(1)
print(a1)

# A2. Budget scaling effect
print("\n[A2] Budget Scaling Effect:")
for model in rounds_main['model_name'].unique():
    model_data = rounds_main[(rounds_main['model_name'] == model) & (rounds_main['tokens_used'] > 0)]
    if len(model_data) == 0:
        continue
    corr = model_data['token_budget'].corr(model_data['tokens_used'])
    slope, intercept, r_value, p_value, std_err = stats.linregress(model_data['token_budget'], model_data['tokens_used'])
    print(f"  {model}: r={corr:.3f}, slope={slope:.3f} tokens per budget unit, p={p_value:.2e}")

# A3. Do models "fill" their budget? (Visual evidence via distribution shapes)
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# A3a. Distribution of tokens_used by budget
ax = axes[0, 0]
for budget in [400, 1000, 2000]:
    data = rounds_main[(rounds_main['token_budget'] == budget) & (rounds_main['tokens_used'] > 0)]['tokens_used']
    ax.hist(data, bins=50, alpha=0.5, label=f'Budget={budget}', density=True)
ax.set_xlabel('Tokens Used (total)')
ax.set_ylabel('Density')
ax.set_title('A3a. Token Usage Distribution by Budget')
ax.legend()

# A3b. Mean tokens_used vs budget by model
ax = axes[0, 1]
for model in rounds_main['model_name'].unique():
    data = rounds_main[(rounds_main['model_name'] == model) & (rounds_main['tokens_used'] > 0)]
    means = data.groupby('token_budget')['tokens_used'].mean()
    ax.plot(means.index, means.values, marker='o', label=model)
ax.set_xlabel('Token Budget (max_tokens)')
ax.set_ylabel('Mean Tokens Used')
ax.set_title('A3b. Mean Token Usage vs Budget')
ax.legend()

# A3c. Boxplot by budget
ax = axes[1, 0]
budgets = sorted(rounds_main['token_budget'].unique())
data_to_plot = [rounds_main[(rounds_main['token_budget'] == b) & (rounds_main['tokens_used'] > 0)]['tokens_used'].values for b in budgets]
ax.boxplot(data_to_plot, labels=budgets)
ax.set_xlabel('Token Budget')
ax.set_ylabel('Tokens Used')
ax.set_title('A3c. Token Usage Spread by Budget')

# A3d. Latency vs tokens_used
ax = axes[1, 1]
sample = rounds_main[(rounds_main['tokens_used'] > 0) & (rounds_main['latency_ms'] > 0)].sample(min(5000, len(rounds_main)))
ax.scatter(sample['tokens_used'], sample['latency_ms'], alpha=0.2, s=5)
ax.set_xlabel('Tokens Used')
ax.set_ylabel('Latency (ms)')
ax.set_title('A3d. Latency vs Token Usage')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig_a_token_compliance.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n  [Saved] fig_a_token_compliance.png")


# ============================================================================
# SECTION B: TOKEN-PERFORMANCE RELATIONSHIP (GLOBAL)
# ============================================================================

print("\n" + "=" * 70)
print("SECTION B: TOKEN-PERFORMANCE RELATIONSHIP (GLOBAL)")
print("=" * 70)

# B1. Win rate by token budget
print("\n[B1] Agent A Win Rate by Token Budget:")
win_rates = games_main.groupby('token_budget')['outcome'].value_counts(normalize=True).unstack().fillna(0)
win_rates = win_rates[['A_Win', 'B_Win', 'Draw']] if 'A_Win' in win_rates.columns else win_rates
print((win_rates * 100).round(1))

# Statistical test: does budget affect outcome?
# Chi-square test for independence
contingency = pd.crosstab(games_main['token_budget'], games_main['outcome'])
chi2, p, dof, expected = stats.chi2_contingency(contingency)
print(f"\n  Chi-square test for budget vs outcome: chi2({dof})={chi2:.2f}, p={p:.4f}")

# B2. Capture speed by budget (only Agent_A wins)
print("\n[B2] Capture Speed (rounds) for Agent_A Wins:")
a_wins = games_main[games_main['outcome'] == 'A_Win']
if len(a_wins) > 0:
    speed_by_budget = a_wins.groupby('token_budget')['total_rounds'].agg(['count', 'mean', 'median', 'std']).round(1)
    print(speed_by_budget)

    # ANOVA: does budget affect capture speed?
    groups = [a_wins[a_wins['token_budget'] == b]['total_rounds'].values for b in sorted(a_wins['token_budget'].unique())]
    groups = [g for g in groups if len(g) > 1]
    if len(groups) >= 2:
        f_stat, p_anova = stats.f_oneway(*groups)
        print(f"\n  ANOVA for budget vs capture speed: F={f_stat:.2f}, p={p_anova:.4f}")

# B3. Total tokens per game vs outcome
print("\n[B3] Total Tokens per Game by Outcome:")
token_by_outcome = games_main.groupby('outcome')['total_tokens_used'].agg(['count', 'mean', 'median', 'std']).round(1)
print(token_by_outcome)

# Pairwise t-tests
for outcome1 in ['A_Win', 'B_Win', 'Draw']:
    for outcome2 in ['A_Win', 'B_Win', 'Draw']:
        if outcome1 >= outcome2:
            continue
        g1 = games_main[games_main['outcome'] == outcome1]['total_tokens_used'].dropna()
        g2 = games_main[games_main['outcome'] == outcome2]['total_tokens_used'].dropna()
        if len(g1) > 1 and len(g2) > 1:
            t, p = stats.ttest_ind(g1, g2, equal_var=False)
            print(f"  {outcome1} vs {outcome2}: t={t:.2f}, p={p:.4f}")

# B4. Visualization
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# B4a. Win rate stacked bar
ax = axes[0, 0]
win_rates.plot(kind='bar', stacked=True, ax=ax, color=['#2ecc71', '#e74c3c', '#95a5a6'])
ax.set_xlabel('Token Budget')
ax.set_ylabel('Proportion')
ax.set_title('B4a. Outcome Distribution by Token Budget')
ax.legend(title='Outcome')
ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

# B4b. Capture speed by budget
ax = axes[0, 1]
if len(a_wins) > 0:
    a_wins.boxplot(column='total_rounds', by='token_budget', ax=ax)
    ax.set_xlabel('Token Budget')
    ax.set_ylabel('Rounds to Capture')
    ax.set_title('B4b. Capture Speed by Budget (Agent A Wins)')
    plt.suptitle('')

# B4c. Total tokens by outcome
ax = axes[1, 0]
games_main.boxplot(column='total_tokens_used', by='outcome', ax=ax)
ax.set_xlabel('Outcome')
ax.set_ylabel('Total Tokens per Game')
ax.set_title('B4c. Token Expenditure by Outcome')
plt.suptitle('')

# B4d. Scatter: total tokens vs rounds (colored by outcome)
ax = axes[1, 1]
for outcome, color in zip(['A_Win', 'B_Win', 'Draw'], ['#2ecc71', '#e74c3c', '#95a5a6']):
    subset = games_main[games_main['outcome'] == outcome]
    ax.scatter(subset['total_tokens_used'], subset['total_rounds'], alpha=0.3, label=outcome, color=color, s=15)
ax.set_xlabel('Total Tokens per Game')
ax.set_ylabel('Total Rounds')
ax.set_title('B4d. Token Expenditure vs Game Length')
ax.legend()

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig_b_token_performance.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n  [Saved] fig_b_token_performance.png")


# ============================================================================
# SECTION C: FOUR-PHASE TOKEN EFFICIENCY ANALYSIS
# ============================================================================

print("\n" + "=" * 70)
print("SECTION C: FOUR-PHASE TOKEN EFFICIENCY ANALYSIS")
print("=" * 70)

# C1. Phase statistics
print("\n[C1] Round Count and Token Usage by Phase:")
phase_stats = rounds_main[rounds_main['tokens_used'] > 0].groupby('phase').agg({
    'round_num': 'count',
    'tokens_used': ['mean', 'median', 'std'],
    'distance_reduction': ['mean', 'median'],
    'token_efficiency': ['mean', 'median'],
    'latency_ms': ['mean', 'median'],
    'logic_action_delta': ['mean', 'count'],
    'wall_blocked': 'mean',
    'movement_clamped': 'mean'
}).round(3)
print(phase_stats)

# C2. Phase duration per game
print("\n[C2] Average Phase Duration (rounds) per Game:")
phase_duration = rounds_main.groupby(['experiment_id', 'phase']).size().reset_index(name='duration')
phase_duration_avg = phase_duration.groupby('phase')['duration'].agg(['count', 'mean', 'median', 'std']).round(2)
print(phase_duration_avg)

# C3. Phase transitions - which phases appear in which order?
print("\n[C3] Phase Sequence Patterns (sample of games):")
sample_games = rounds_main['experiment_id'].unique()[:20]
for game_id in sample_games:
    game_rounds = rounds_main[rounds_main['experiment_id'] == game_id].sort_values('round_num')
    phases = game_rounds['phase'].tolist()
    # Compress consecutive duplicates
    compressed = [phases[0]] if phases else []
    for p in phases[1:]:
        if p != compressed[-1]:
            compressed.append(p)
    winner = game_rounds['winner'].iloc[0] if len(game_rounds) > 0 else 'N/A'
    print(f"  {game_id[:20]}... ({winner}): {' -> '.join(compressed)}")

# C4. Token efficiency by phase and budget
print("\n[C4] Mean Token Efficiency by Phase and Budget:")
efficiency_table = rounds_main[rounds_main['tokens_used'] > 0].groupby(['phase', 'token_budget'])['token_efficiency'].mean().unstack().round(4)
print(efficiency_table)

# C5. Statistical tests: do phases differ in token usage?
phase_groups_tokens = [rounds_main[(rounds_main['phase'] == p) & (rounds_main['tokens_used'] > 0)]['tokens_used'].dropna().values
                       for p in rounds_main['phase'].unique()]
phase_groups_tokens = [g for g in phase_groups_tokens if len(g) > 1]
if len(phase_groups_tokens) >= 2:
    f_stat, p_anova = stats.f_oneway(*phase_groups_tokens)
    print(f"\n  ANOVA: phase vs token usage: F={f_stat:.2f}, p={p_anova:.2e}")

# Kruskal-Wallis (non-parametric alternative)
kw_stat, p_kw = stats.kruskal(*phase_groups_tokens)
print(f"  Kruskal-Wallis: phase vs token usage: H={kw_stat:.2f}, p={p_kw:.2e}")

# C6. Visualization
fig, axes = plt.subplots(2, 3, figsize=(16, 10))

# C6a. Token usage by phase
ax = axes[0, 0]
rounds_main[rounds_main['tokens_used'] > 0].boxplot(column='tokens_used', by='phase', ax=ax)
ax.set_xlabel('Phase')
ax.set_ylabel('Tokens Used')
ax.set_title('C6a. Token Usage by Phase')
plt.suptitle('')

# C6b. Distance reduction by phase
ax = axes[0, 1]
rounds_main[rounds_main['distance_reduction'].notna()].boxplot(column='distance_reduction', by='phase', ax=ax)
ax.set_xlabel('Phase')
ax.set_ylabel('Distance Reduction')
ax.set_title('C6b. Spatial Progress by Phase')
plt.suptitle('')

# C6c. Token efficiency by phase
ax = axes[0, 2]
eff_data = rounds_main[rounds_main['token_efficiency'].notna() & (rounds_main['token_efficiency'] > -10) & (rounds_main['token_efficiency'] < 10)]
eff_data.boxplot(column='token_efficiency', by='phase', ax=ax)
ax.set_xlabel('Phase')
ax.set_ylabel('Token Efficiency (dist_reduced / token)')
ax.set_title('C6c. Token Efficiency by Phase')
plt.suptitle('')

# C6d. Phase duration distribution
ax = axes[1, 0]
phase_duration.boxplot(column='duration', by='phase', ax=ax)
ax.set_xlabel('Phase')
ax.set_ylabel('Duration (rounds)')
ax.set_title('C6d. Phase Duration Distribution')
plt.suptitle('')

# C6e. Token usage trajectory in a sample game
ax = axes[1, 1]
sample_game = rounds_main[rounds_main['experiment_id'] == rounds_main['experiment_id'].iloc[0]]
sample_game = sample_game[sample_game['tokens_used'] > 0]
ax.plot(sample_game['round_num'], sample_game['tokens_used'], marker='o')
for _, row in sample_game.iterrows():
    ax.annotate(row['phase'].replace('phase', ''), (row['round_num'], row['tokens_used']), fontsize=7)
ax.set_xlabel('Round')
ax.set_ylabel('Tokens Used')
ax.set_title('C6e. Token Trajectory (Sample Game)')

# C6f. Wall blocked rate by phase
ax = axes[1, 2]
wall_rates = rounds_main.groupby('phase')['wall_blocked'].mean()
wall_rates.plot(kind='bar', ax=ax, color='coral')
ax.set_xlabel('Phase')
ax.set_ylabel('Wall Blocked Rate')
ax.set_title('C6f. Wall Block Rate by Phase')
ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig_c_four_phases.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n  [Saved] fig_c_four_phases.png")


# ============================================================================
# SECTION D: EXCESS TOKEN VALUE ANALYSIS
# ============================================================================

print("\n" + "=" * 70)
print("SECTION D: EXCESS TOKEN VALUE ANALYSIS")
print("=" * 70)

# Define "excess token rounds" as those with tokens_used > 75th percentile within same (model, budget)
rounds_main['token_pctile'] = rounds_main.groupby(['model_name', 'token_budget'])['tokens_used'].transform(
    lambda x: x.rank(pct=True) if len(x) > 1 else pd.Series([0.5]*len(x), index=x.index)
)
rounds_main['high_token_round'] = rounds_main['token_pctile'] > 0.75

# D1. Compare high-token vs normal-token rounds
print("\n[D1] High-Token Rounds (top 25% within model+budget) vs Normal Rounds:")
comparison_metrics = ['wall_blocked', 'movement_clamped', 'boundary_clamped', 'logic_action_delta', 'distance_reduction']
high_token = rounds_main[rounds_main['high_token_round'] == True]
normal_token = rounds_main[rounds_main['high_token_round'] == False]

for metric in comparison_metrics:
    h_vals = high_token[metric].dropna()
    n_vals = normal_token[metric].dropna()
    if len(h_vals) > 10 and len(n_vals) > 10:
        # Use Mann-Whitney U for robustness
        u_stat, p_val = stats.mannwhitneyu(h_vals, n_vals, alternative='two-sided')
        print(f"  {metric}: high_token_mean={h_vals.mean():.4f}, normal_mean={n_vals.mean():.4f}, Mann-Whitney U p={p_val:.4f}")

# D2. Does high token usage in early rounds predict game outcome?
print("\n[D2] Early-Game Token Usage vs Final Outcome:")
early_rounds = rounds_main[rounds_main['round_num'] <= 10]
early_token_by_game = early_rounds.groupby('experiment_id')['tokens_used'].sum().reset_index()
early_token_by_game = early_token_by_game.merge(games_main[['experiment_id', 'outcome']], on='experiment_id')

for outcome in ['A_Win', 'B_Win', 'Draw']:
    vals = early_token_by_game[early_token_by_game['outcome'] == outcome]['tokens_used']
    print(f"  {outcome}: early_tokens_mean={vals.mean():.1f}, median={vals.median():.1f}, n={len(vals)}")

# D3. "Overthinking" analysis - high token rounds that result in worse outcomes
print("\n[D3] Overthinking Detection (high tokens + negative distance reduction):")
rounds_main['overthinking'] = (rounds_main['high_token_round'] == True) & (rounds_main['distance_reduction'] < 0)
overthink_rate = rounds_main.groupby('phase')['overthinking'].mean()
print("  Overthinking rate by phase:")
print(overthink_rate)

# D4. Visualization
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# D4a. High-token vs normal token outcomes
ax = axes[0, 0]
outcome_comparison = rounds_main.groupby(['high_token_round', 'outcome']).size().unstack(fill_value=0)
outcome_comparison = outcome_comparison.div(outcome_comparison.sum(axis=1), axis=0)
outcome_comparison.plot(kind='bar', ax=ax, color=['#2ecc71', '#e74c3c', '#95a5a6'])
ax.set_xlabel('High Token Round')
ax.set_ylabel('Proportion')
ax.set_title('D4a. Outcome Distribution by Token Level')
ax.legend(title='Outcome')
ax.set_xticklabels(['Normal', 'High Token'], rotation=0)

# D4b. Logic-Action Delta by token level
ax = axes[0, 1]
rounds_main[rounds_main['logic_action_delta'].notna()].boxplot(column='logic_action_delta', by='high_token_round', ax=ax)
ax.set_xlabel('High Token Round')
ax.set_ylabel('Logic-Action Delta (degrees)')
ax.set_title('D4b. Logic-Action Consistency by Token Level')
plt.suptitle('')
ax.set_xticklabels(['Normal', 'High Token'], rotation=0)

# D4c. Distance reduction by token level and phase
ax = axes[1, 0]
reduction_by_phase_token = rounds_main.groupby(['phase', 'high_token_round'])['distance_reduction'].mean().unstack()
reduction_by_phase_token.plot(kind='bar', ax=ax)
ax.set_xlabel('Phase')
ax.set_ylabel('Mean Distance Reduction')
ax.set_title('D4c. Spatial Progress by Phase & Token Level')
ax.legend(['Normal Token', 'High Token'])
ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

# D4d. Early token usage vs outcome
ax = axes[1, 1]
early_token_by_game.boxplot(column='tokens_used', by='outcome', ax=ax)
ax.set_xlabel('Outcome')
ax.set_ylabel('Early Game Tokens (Rounds 1-10)')
ax.set_title('D4d. Early Token Investment vs Outcome')
plt.suptitle('')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig_d_excess_token.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n  [Saved] fig_d_excess_token.png")


# ============================================================================
# SECTION E: MODEL & THINKING MODE COMPARISON
# ============================================================================

print("\n" + "=" * 70)
print("SECTION E: MODEL & THINKING MODE COMPARISON")
print("=" * 70)

# E1. Same budget, different models
print("\n[E1] Performance at Token Budget = 1000 (most common standard):")
budget_1000 = games_main[games_main['token_budget'] == 1000]
if len(budget_1000) > 0:
    model_perf = budget_1000.groupby(['model_name', 'thinking_enabled'])['outcome'].value_counts(normalize=True).unstack().fillna(0)
    print((model_perf * 100).round(1))

# E2. Token efficiency by model
print("\n[E2] Mean Token Efficiency by Model (all budgets):")
model_eff = rounds_main[rounds_main['tokens_used'] > 0].groupby('model_name')['token_efficiency'].agg(['count', 'mean', 'median', 'std']).round(4)
print(model_eff)

# E3. Thinking effect
print("\n[E3] Thinking Mode Effect (DeepSeek only):")
ds_only = games_main[games_main['model_name'].str.contains('deepseek')]
if 'thinking_enabled' in ds_only.columns and ds_only['thinking_enabled'].notna().any():
    thinking_perf = ds_only.groupby('thinking_enabled')['outcome'].value_counts(normalize=True).unstack().fillna(0)
    print((thinking_perf * 100).round(1))

    # T-test: total tokens for thinking vs non-thinking
    think_yes = ds_only[ds_only['thinking_enabled'] == True]['total_tokens_used'].dropna()
    think_no = ds_only[ds_only['thinking_enabled'] == False]['total_tokens_used'].dropna()
    if len(think_yes) > 1 and len(think_no) > 1:
        t, p = stats.ttest_ind(think_yes, think_no, equal_var=False)
        print(f"\n  Total tokens: thinking={think_yes.mean():.0f}, non-thinking={think_no.mean():.0f}, t={t:.2f}, p={p:.4f}")

# E4. Visualization
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

# E4a. Win rate by model and budget
ax = axes[0, 0]
win_rate_model = games_main.groupby(['model_name', 'token_budget']).apply(lambda x: (x['outcome'] == 'A_Win').mean()).unstack()
win_rate_model.plot(kind='bar', ax=ax)
ax.set_xlabel('Model')
ax.set_ylabel('Agent A Win Rate')
ax.set_title('E4a. Win Rate by Model & Budget')
ax.legend(title='Budget', bbox_to_anchor=(1.05, 1), loc='upper left')
ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

# E4b. Token usage by model
ax = axes[0, 1]
rounds_main[rounds_main['tokens_used'] > 0].boxplot(column='tokens_used', by='model_name', ax=ax)
ax.set_xlabel('Model')
ax.set_ylabel('Tokens Used')
ax.set_title('E4b. Token Usage by Model')
plt.suptitle('')

# E4c. Thinking effect on capture speed
ax = axes[1, 0]
ds_wins = ds_only[ds_only['outcome'] == 'A_Win']
if len(ds_wins) > 0 and 'thinking_enabled' in ds_wins.columns:
    ds_wins.boxplot(column='total_rounds', by='thinking_enabled', ax=ax)
    ax.set_xlabel('Thinking Enabled')
    ax.set_ylabel('Rounds to Capture')
    ax.set_title('E4c. Capture Speed: Thinking vs Non-Thinking')
    plt.suptitle('')

# E4d. Latency by model
ax = axes[1, 1]
rounds_main[rounds_main['latency_ms'] > 0].boxplot(column='latency_ms', by='model_name', ax=ax)
ax.set_xlabel('Model')
ax.set_ylabel('Latency (ms)')
ax.set_title('E4d. API Latency by Model')
plt.suptitle('')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'fig_e_model_comparison.png', dpi=150, bbox_inches='tight')
plt.close()
print("\n  [Saved] fig_e_model_comparison.png")


# ============================================================================
# SUMMARY STATISTICS TABLE
# ============================================================================

print("\n" + "=" * 70)
print("SUMMARY: KEY FINDINGS")
print("=" * 70)

# Overall stats
print(f"""
[Dataset Overview]
  Total Games Analyzed: {len(games_main)}
  Total Rounds Analyzed: {len(rounds_main)}
  Agent A Win Rate: {(games_main['outcome'] == 'A_Win').mean()*100:.1f}%
  Agent B Win Rate: {(games_main['outcome'] == 'B_Win').mean()*100:.1f}%
  Draw Rate: {(games_main['outcome'] == 'Draw').mean()*100:.1f}%

[Token Usage]
  Mean Tokens per Round: {rounds_main[rounds_main['tokens_used'] > 0]['tokens_used'].mean():.0f}
  Mean Tokens per Game: {games_main['total_tokens_used'].mean():.0f}
  Token Budget Range: {rounds_main['token_budget'].min()} - {rounds_main['token_budget'].max()}

[Phase Distribution (rounds)]
  Phase 1 (Pre-wall): {(rounds_main['phase'] == 'phase1_prewall').sum()} ({(rounds_main['phase'] == 'phase1_prewall').mean()*100:.1f}%)
  Phase 2 (Wall nav): {(rounds_main['phase'] == 'phase2_wall_nav').sum()} ({(rounds_main['phase'] == 'phase2_wall_nav').mean()*100:.1f}%)
  Phase 3 (Post-wall): {(rounds_main['phase'] == 'phase3_postwall').sum()} ({(rounds_main['phase'] == 'phase3_postwall').mean()*100:.1f}%)
  Phase 4 (Hunt): {(rounds_main['phase'] == 'phase4_hunt').sum()} ({(rounds_main['phase'] == 'phase4_hunt').mean()*100:.1f}%)

[Model Distribution (games)]
  DeepSeek Flash: {len(games_main[games_main['model_name'] == 'deepseek-v4-flash'])}
  DeepSeek Pro: {len(games_main[games_main['model_name'] == 'deepseek-v4-pro'])}
  Kimi 2.5: {len(games_main[games_main['model_name'] == 'kimi-2.5'])}
""")

print("\nAnalysis complete. All figures saved to:", OUTPUT_DIR)
