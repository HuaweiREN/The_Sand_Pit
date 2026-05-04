"""
Corrected Non-Parametric Tests with Effect Sizes
Replaces parametric tests that violated normality assumptions.
Follows statistical-analysis skill standards: report test statistic, p-value, effect size, CI.
"""

import numpy as np
import pandas as pd
from scipy import stats
from itertools import combinations
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = Path(".")

rounds = pd.read_csv(OUTPUT_DIR / "all_rounds.csv")
games = pd.read_csv(OUTPUT_DIR / "all_games.csv")

# Prepare data
rounds = rounds.sort_values(['experiment_id', 'round_num'])
rounds['prev_distance'] = rounds.groupby('experiment_id')['distance'].shift(1)
rounds['distance_reduction'] = rounds['prev_distance'] - rounds['distance']
rounds['token_efficiency'] = rounds['distance_reduction'] / rounds['tokens_used'].replace(0, np.nan)

def cat(w):
    if w == 'Agent_A': return 'A_Win'
    elif w == 'Agent_B': return 'B_Win'
    else: return 'Draw'
games['outcome'] = games['winner'].apply(cat)
rounds['outcome'] = rounds['winner'].apply(cat)

rounds_main = rounds[rounds['token_budget'] <= 2000].copy()
games_main = games[games['token_budget'] <= 2000].copy()

results = []

def _z_from_p(p: float, cap: float = 5.0) -> float:
    """Convert two-tailed p-value to z-score, capping to avoid inf."""
    if p >= 0.999:
        return 0.0
    # Prevent ppf(1.0) -> inf by bounding away from 1
    p_half = min(p / 2, 1 - 1e-15)
    return min(stats.norm.ppf(1 - p_half), cap)


def report(analysis, test, stat, p, effect_size=None, effect_label=None, note=""):
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    line = f"[{analysis}] {test}: stat={stat:.3f}, p={p:.4f} {sig}"
    if effect_size is not None:
        line += f", effect_size={effect_size:.3f} ({effect_label})"
    if note:
        line += f" | {note}"
    results.append(line)
    print(line)

print("=" * 70)
print("CORRECTED NON-PARAMETRIC TESTS WITH EFFECT SIZES")
print("=" * 70)

# =====================================================================
# TEST 1: Capture Speed by Budget (replaces ANOVA)
# =====================================================================
print("\n--- TEST 1: Capture Speed by Budget (Agent A wins only) ---")
a_wins = games_main[games_main['outcome'] == 'A_Win'].copy()
budgets = sorted(a_wins['token_budget'].unique())
groups = [a_wins[a_wins['token_budget'] == b]['total_rounds'].dropna().values for b in budgets]
groups = [g for g in groups if len(g) > 0]

# Kruskal-Wallis
h_stat, p_kw = stats.kruskal(*groups)
# Epsilon-squared effect size for Kruskal-Wallis
N = sum(len(g) for g in groups)
k = len(groups)
epsilon_sq = h_stat / (N - 1) if N > 1 else 0
report("Capture Speed by Budget", "Kruskal-Wallis", h_stat, p_kw, epsilon_sq, "epsilon-squared",
       f"N={N}, k={k}, budgets={budgets}")

# Pairwise Mann-Whitney U with Bonferroni correction
if p_kw < 0.05:
    print("  Post-hoc (Mann-Whitney U, Bonferroni corrected):")
    n_comparisons = len(list(combinations(budgets, 2)))
    alpha_corrected = 0.05 / n_comparisons
    for b1, b2 in combinations(budgets, 2):
        g1 = a_wins[a_wins['token_budget'] == b1]['total_rounds'].dropna().values
        g2 = a_wins[a_wins['token_budget'] == b2]['total_rounds'].dropna().values
        if len(g1) < 2 or len(g2) < 2:
            continue
        u, p_raw = stats.mannwhitneyu(g1, g2, alternative='two-sided')
        p_adj = min(p_raw * n_comparisons, 1.0)
        # Effect size r = Z / sqrt(N)
        z = _z_from_p(p_raw)
        n_total = len(g1) + len(g2)
        r = z / np.sqrt(n_total) if n_total > 0 else 0
        sig = "***" if p_adj < 0.001 else "**" if p_adj < 0.01 else "*" if p_adj < 0.05 else "ns"
        med1, med2 = np.median(g1), np.median(g2)
        print(f"    Budget {b1} vs {b2}: U={u:.0f}, p_adj={p_adj:.4f} {sig}, r={r:.3f}, medians={med1:.1f} vs {med2:.1f}")

# =====================================================================
# TEST 2: Total Tokens per Game by Outcome (replaces t-tests)
# =====================================================================
print("\n--- TEST 2: Total Tokens per Game by Outcome ---")
outcomes = ['A_Win', 'B_Win', 'Draw']
outcome_groups = [games_main[games_main['outcome'] == o]['total_tokens_used'].dropna().values for o in outcomes]

# Kruskal-Wallis across all three outcomes
h_stat, p_kw = stats.kruskal(*outcome_groups)
N = sum(len(g) for g in outcome_groups)
epsilon_sq = h_stat / (N - 1) if N > 1 else 0
report("Total Tokens by Outcome", "Kruskal-Wallis", h_stat, p_kw, epsilon_sq, "epsilon-squared")

# Pairwise Mann-Whitney U with Bonferroni correction
print("  Post-hoc (Mann-Whitney U, Bonferroni corrected):")
n_comp = 3  # 3 pairwise comparisons
for o1, o2 in combinations(outcomes, 2):
    g1 = games_main[games_main['outcome'] == o1]['total_tokens_used'].dropna().values
    g2 = games_main[games_main['outcome'] == o2]['total_tokens_used'].dropna().values
    u, p_raw = stats.mannwhitneyu(g1, g2, alternative='two-sided')
    p_adj = min(p_raw * n_comp, 1.0)
    z = _z_from_p(p_raw)
    n_total = len(g1) + len(g2)
    r = z / np.sqrt(n_total) if n_total > 0 else 0
    sig = "***" if p_adj < 0.001 else "**" if p_adj < 0.01 else "*" if p_adj < 0.05 else "ns"
    med1, med2 = np.median(g1), np.median(g2)
    iqr1, iqr2 = np.percentile(g1, 75) - np.percentile(g1, 25), np.percentile(g2, 75) - np.percentile(g2, 25)
    print(f"    {o1} vs {o2}: U={u:.0f}, p_adj={p_adj:.4f} {sig}, r={r:.3f}")
    print(f"      Median (IQR): {o1}={med1:.0f} ({iqr1:.0f}), {o2}={med2:.0f} ({iqr2:.0f})")

# =====================================================================
# TEST 3: Token Usage by Budget (replaces ANOVA) - confirmatory
# =====================================================================
print("\n--- TEST 3: Token Usage by Budget (confirmatory) ---")
token_budget_groups = [rounds_main[(rounds_main['token_budget'] == b) & (rounds_main['tokens_used'] > 0)]['tokens_used'].dropna().values
                       for b in sorted(rounds_main['token_budget'].unique())]
token_budget_groups = [g for g in token_budget_groups if len(g) > 0]
h_stat, p_kw = stats.kruskal(*token_budget_groups)
N = sum(len(g) for g in token_budget_groups)
epsilon_sq = h_stat / (N - 1) if N > 1 else 0
report("Token Usage by Budget", "Kruskal-Wallis", h_stat, p_kw, epsilon_sq, "epsilon-squared",
       f"N={N}, k={len(token_budget_groups)}")

# =====================================================================
# TEST 4: Distance Reduction by Phase (confirmatory)
# =====================================================================
print("\n--- TEST 4: Distance Reduction by Phase ---")
phase_data = rounds_main[rounds_main['distance_reduction'].notna() & (rounds_main['tokens_used'] > 0)]
phases = ['phase1_prewall', 'phase2_wall_nav', 'phase3_postwall', 'phase4_hunt']
phase_groups = [phase_data[phase_data['phase'] == ph]['distance_reduction'].dropna().values for ph in phases]
phase_groups = [g for g in phase_groups if len(g) > 0]
h_stat, p_kw = stats.kruskal(*phase_groups)
N = sum(len(g) for g in phase_groups)
epsilon_sq = h_stat / (N - 1) if N > 1 else 0
report("Distance Reduction by Phase", "Kruskal-Wallis", h_stat, p_kw, epsilon_sq, "epsilon-squared",
       f"N={N}, phases={phases}")

# Post-hoc Dunn's equivalent (pairwise Mann-Whitney with Bonferroni)
if p_kw < 0.05:
    print("  Post-hoc (Mann-Whitney U, Bonferroni corrected):")
    n_comp = len(list(combinations(phases, 2)))
    for ph1, ph2 in combinations(phases, 2):
        g1 = phase_data[phase_data['phase'] == ph1]['distance_reduction'].dropna().values
        g2 = phase_data[phase_data['phase'] == ph2]['distance_reduction'].dropna().values
        if len(g1) < 2 or len(g2) < 2:
            continue
        u, p_raw = stats.mannwhitneyu(g1, g2, alternative='two-sided')
        p_adj = min(p_raw * n_comp, 1.0)
        z = _z_from_p(p_raw)
        n_total = len(g1) + len(g2)
        r = z / np.sqrt(n_total) if n_total > 0 else 0
        sig = "***" if p_adj < 0.001 else "**" if p_adj < 0.01 else "*" if p_adj < 0.05 else "ns"
        med1, med2 = np.median(g1), np.median(g2)
        print(f"    {ph1} vs {ph2}: U={u:.0f}, p_adj={p_adj:.4f} {sig}, r={r:.3f}, medians={med1:.3f} vs {med2:.3f}")

# =====================================================================
# TEST 5: Token Efficiency by Phase (confirmatory)
# =====================================================================
print("\n--- TEST 5: Token Efficiency by Phase ---")
eff_data = phase_data[phase_data['token_efficiency'].notna()].copy()
eff_data = eff_data[(eff_data['token_efficiency'] > -0.01) & (eff_data['token_efficiency'] < 0.02)]
eff_groups = [eff_data[eff_data['phase'] == ph]['token_efficiency'].dropna().values for ph in phases]
eff_groups = [g for g in eff_groups if len(g) > 0]
h_stat, p_kw = stats.kruskal(*eff_groups)
N = sum(len(g) for g in eff_groups)
epsilon_sq = h_stat / (N - 1) if N > 1 else 0
report("Token Efficiency by Phase", "Kruskal-Wallis", h_stat, p_kw, epsilon_sq, "epsilon-squared")

# =====================================================================
# TEST 6: High-Token vs Normal-Token Rounds (confirmatory)
# =====================================================================
print("\n--- TEST 6: High-Token vs Normal-Token Rounds ---")
rounds_main['token_pctile'] = rounds_main.groupby(['model_name', 'token_budget'])['tokens_used'].transform(
    lambda x: x.rank(pct=True) if len(x) > 1 else pd.Series([0.5]*len(x), index=x.index)
)
rounds_main['high_token_round'] = rounds_main['token_pctile'] > 0.75

metrics_to_test = [
    ('movement_clamped', 'Physical Overreach'),
    ('logic_action_delta', 'Logic-Action Inconsistency'),
    ('distance_reduction', 'Spatial Progress'),
]

for col, label in metrics_to_test:
    high = rounds_main[rounds_main['high_token_round'] == True][col].dropna().values
    normal = rounds_main[rounds_main['high_token_round'] == False][col].dropna().values
    u, p_val = stats.mannwhitneyu(high, normal, alternative='two-sided')
    z = _z_from_p(p_val)
    r = z / np.sqrt(len(high) + len(normal))
    sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
    med_h, med_n = np.median(high), np.median(normal)
    print(f"  {label}: U={u:.0f}, p={p_val:.4f} {sig}, r={r:.3f}, medians={med_h:.4f} vs {med_n:.4f}")

# =====================================================================
# TEST 7: Budget-Performance Correlation (Spearman, replaces Pearson)
# =====================================================================
print("\n--- TEST 7: Budget-Win Rate Correlation (Spearman) ---")
# Create per-budget win rate
win_rates = games_main.groupby('token_budget').apply(lambda x: (x['outcome'] == 'A_Win').mean()).reset_index()
win_rates.columns = ['token_budget', 'a_win_rate']
rho, p_sp = stats.spearmanr(win_rates['token_budget'], win_rates['a_win_rate'])
report("Budget vs Win Rate", "Spearman", rho, p_sp, abs(rho), "|rho|",
       f"N_budgets={len(win_rates)}")

# =====================================================================
# TEST 8: Thinking Mode at 20000 tokens (Mann-Whitney)
# =====================================================================
print("\n--- TEST 8: Thinking Mode Effect (DeepSeek Pro, 20000 tokens) ---")
think_games = games[games['thinking_enabled'] == True]
if len(think_games) > 0:
    # Compare capture rounds: thinking vs non-thinking (approximate, using 2000 budget as proxy for non-thinking)
    think_pro = think_games[(think_games['model_name'].str.contains('pro')) & (think_games['outcome'] == 'A_Win')]['total_rounds'].dropna().values
    no_think_pro = games_main[(games_main['model_name'].str.contains('pro')) & (games_main['token_budget'] == 2000) & (games_main['outcome'] == 'A_Win')]['total_rounds'].dropna().values
    if len(think_pro) > 2 and len(no_think_pro) > 2:
        u, p_val = stats.mannwhitneyu(think_pro, no_think_pro, alternative='two-sided')
        z = _z_from_p(p_val)
        r = z / np.sqrt(len(think_pro) + len(no_think_pro))
        report("Thinking vs Non-Thinking (Pro, capture speed)", "Mann-Whitney U", u, p_val, r, "r",
               f"thinking_n={len(think_pro)}, non_thinking_n={len(no_think_pro)}")
        print(f"  Median capture rounds: thinking={np.median(think_pro):.1f}, non-thinking={np.median(no_think_pro):.1f}")

# =====================================================================
# SAVE RESULTS
# =====================================================================
print("\n" + "=" * 70)
print("ALL CORRECTED TESTS COMPLETE")
print("=" * 70)

with open(OUTPUT_DIR / "corrected_nonparametric_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print(f"Results saved to: {OUTPUT_DIR / 'corrected_nonparametric_results.txt'}")
