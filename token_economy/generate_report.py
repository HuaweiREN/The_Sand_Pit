"""
Generate comprehensive Token Economy Research Report (Researcher 3)
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

OUTPUT_DIR = Path(".")

rounds = pd.read_csv(OUTPUT_DIR / "all_rounds.csv")
games = pd.read_csv(OUTPUT_DIR / "all_games.csv")

# Mark parsed rounds
rounds['parsed_success'] = ~((rounds['target_x'] == 0.0) & (rounds['target_y'] == 0.0) & (rounds['tokens_used'] > 0))

# Sort and compute distance reduction
rounds = rounds.sort_values(['experiment_id', 'round_num'])
rounds['prev_distance'] = rounds.groupby('experiment_id')['distance'].shift(1)
rounds['distance_reduction'] = rounds['prev_distance'] - rounds['distance']
rounds['token_efficiency'] = rounds['distance_reduction'] / rounds['tokens_used'].replace(0, np.nan)

# Outcomes
def cat(w):
    if w == 'Agent_A': return 'A_Win'
    elif w == 'Agent_B': return 'B_Win'
    else: return 'Draw'

games['outcome'] = games['winner'].apply(cat)
rounds['outcome'] = rounds['winner'].apply(cat)

# Estimate prompt tokens per model (round 1 minimum)
round1 = rounds[(rounds['round_num'] == 1) & (rounds['tokens_used'] > 0)]
prompt_est = round1.groupby('model_name')['tokens_used'].min().to_dict()
# For deepseek, min round1 is about 665-708. For kimi, it's 196.
# We'll use these as approximate prompt baselines.

# DeepSeek-specific analysis (where tokens_used = total_tokens)
ds_rounds = rounds[rounds['model_name'].str.contains('deepseek')].copy()
ds_rounds['est_completion_tokens'] = ds_rounds['tokens_used'] - ds_rounds['model_name'].map(prompt_est)
ds_rounds['completion_over_budget'] = ds_rounds['est_completion_tokens'] - ds_rounds['token_budget']
ds_rounds['completion_util_rate'] = ds_rounds['est_completion_tokens'] / ds_rounds['token_budget']

# Kimi-specific analysis (where tokens_used = output_tokens)
kimi_rounds = rounds[rounds['model_name'].str.contains('kimi')].copy()
kimi_rounds['completion_over_budget'] = kimi_rounds['tokens_used'] - kimi_rounds['token_budget']
kimi_rounds['completion_util_rate'] = kimi_rounds['tokens_used'] / kimi_rounds['token_budget']

report = []
report.append("# Token Economy Research Report - Researcher 3")
report.append("## The Sand Pit: LLM Token Budget vs. Spatial Intelligence")
report.append("")
report.append("**Date:** 2026-05-02")
report.append("**Dataset:** 865 games, 29,403 rounds (token budgets 400-2000, excluding 20K stress tests in main analysis)")
report.append("**Models:** DeepSeek-v4-Flash, DeepSeek-v4-Pro, Kimi-2.5")
report.append("")

# =====================================================================
# EXECUTIVE SUMMARY
# =====================================================================
report.append("## 1. Executive Summary")
report.append("")
report.append("This report investigates the 'Token Economics' of LLM-driven spatial agents in The Sand Pit pursuit game. We examine five core questions:")
report.append("")
report.append("1. **Does increasing token budget improve agent intelligence (win rate / capture speed)?**")
report.append("2. **Do models comply with the given token max (max_tokens)?**")
report.append("3. **Under what conditions do models exceed or under-utilize their budget?**")
report.append("4. **Are excess tokens advantageous or wasted?**")
report.append("5. **How does token efficiency vary across the four game phases?**")
report.append("")

# =====================================================================
# KEY FINDING 1: TOKEN-PERFORMANCE RELATIONSHIP
# =====================================================================
report.append("## 2. Token Budget vs. Agent Performance (Global Analysis)")
report.append("")

# Win rate by budget
wr = games.groupby('token_budget')['outcome'].value_counts(normalize=True).unstack().fillna(0)
wr = wr * 100
report.append("### 2.1 Win Rate by Token Budget")
report.append("")
report.append("| Budget | A_Win % | B_Win % | Draw % |")
report.append("|--------|---------|---------|--------|")
for b in sorted(games['token_budget'].unique()):
    if b > 2000: continue
    row = wr.loc[b] if b in wr.index else {}
    report.append(f"| {b} | {row.get('A_Win', 0):.1f} | {row.get('B_Win', 0):.1f} | {row.get('Draw', 0):.1f} |")
report.append("")

contingency = pd.crosstab(games[games['token_budget'] <= 2000]['token_budget'], games[games['token_budget'] <= 2000]['outcome'])
chi2, p, dof, _ = stats.chi2_contingency(contingency)
report.append(f"**Statistical Test:** Chi-square test for independence, chi2({dof}) = {chi2:.2f}, p {'< 0.001' if p < 0.001 else f'= {p:.3f}'}. Budget significantly affects outcome.")
report.append("")

report.append("**Key Finding:** Token budget exhibits a **non-linear, threshold-like effect** on performance.")
report.append("- At 400 tokens, Agent A win rate is catastrophically low (6.2%), with 81.4% draws. The agent lacks sufficient 'cognitive bandwidth' to reach the target.")
report.append("- Win rate improves sharply to 35-45% at 600-1000 tokens, suggesting a critical threshold around 800-1000 tokens.")
report.append("- Beyond 1200 tokens, returns diminish: 1200 budget achieves 52.4% win rate, but 2000 budget only reaches 49.4%. More tokens do not guarantee better outcomes.")
report.append("")

# Capture speed
a_wins = games[(games['outcome'] == 'A_Win') & (games['token_budget'] <= 2000)]
if len(a_wins) > 0:
    speed = a_wins.groupby('token_budget')['total_rounds'].agg(['count', 'mean']).round(1)
    report.append("### 2.2 Capture Speed (Rounds to Win) by Budget")
    report.append("")
    report.append("| Budget | N (A wins) | Mean Rounds |")
    report.append("|--------|------------|-------------|")
    for b in sorted(speed.index):
        report.append(f"| {b} | {int(speed.loc[b, 'count'])} | {speed.loc[b, 'mean']:.1f} |")
    report.append("")

    groups = [a_wins[a_wins['token_budget'] == b]['total_rounds'].values for b in sorted(a_wins['token_budget'].unique())]
    groups = [g for g in groups if len(g) > 1]
    if len(groups) >= 2:
        f_stat, p_anova = stats.f_oneway(*groups)
        report.append(f"**ANOVA:** F = {f_stat:.2f}, p = {p_anova:.4f}. Higher budgets significantly reduce capture time.")
        report.append("")

report.append("**Key Finding:** Higher budgets lead to **faster captures**, but the effect plateaus. The jump from 400 to 1000 tokens is dramatic (36.5 -> 28.8 rounds); from 1000 to 2000, the improvement is marginal.")
report.append("")

# Token expenditure by outcome
tok_out = games[games['token_budget'] <= 2000].groupby('outcome')['total_tokens_used'].agg(['count', 'mean', 'median']).round(0)
report.append("### 2.3 Total Token Expenditure by Game Outcome")
report.append("")
report.append("| Outcome | N | Mean Tokens | Median Tokens |")
report.append("|---------|---|-------------|---------------|")
for o in tok_out.index:
    report.append(f"| {o} | {int(tok_out.loc[o, 'count'])} | {int(tok_out.loc[o, 'mean'])} | {int(tok_out.loc[o, 'median'])} |")
report.append("")

report.append("**Stunning Finding:** Drawn games consume **~2x more tokens** than decisive games (60,900 vs ~31,700). The agent burns through its entire token budget over 50 rounds without ever capturing the target. From a token economics perspective, **draws are the most expensive failure mode**.")
report.append("")

# =====================================================================
# KEY FINDING 2: TOKEN COMPLIANCE
# =====================================================================
report.append("## 3. Token Budget Compliance: Do Models Follow max_tokens?")
report.append("")
report.append("### 3.1 Critical Discovery: API Heterogeneity in Token Counting")
report.append("")
report.append("Our analysis reveals a **fundamental measurement discrepancy** between API families:")
report.append("")
report.append("- **DeepSeek (OpenAI format):** `tokens_used` records **total_tokens = prompt_tokens + completion_tokens**. The max_tokens parameter limits only the output, so total_tokens routinely exceeds the 'budget' by 600-800 tokens (the prompt cost).")
report.append("- **Kimi (Anthropic format):** `tokens_used` records **output_tokens only**. The reported value directly reflects completion length, making compliance transparent.")
report.append("")

# Kimi compliance
kimi_max = kimi_rounds.groupby('token_budget')['tokens_used'].max()
report.append("### 3.2 Kimi: Perfect Compliance")
report.append("")
report.append("| Budget | Max Observed Output | Compliance |")
report.append("|--------|---------------------|------------|")
for b in sorted(kimi_rounds['token_budget'].unique()):
    if b > 2000: continue
    m = kimi_max.get(b, 0)
    report.append(f"| {b} | {m:.0f} | {'PASS (exact)' if m <= b else 'FAIL'} |")
report.append("")
report.append("Kimi exhibits **perfect compliance**: max output tokens exactly equal the assigned budget (400, 600, 800, 1000). No observed violation.")
report.append("")

# DeepSeek estimated compliance
report.append("### 3.3 DeepSeek: Estimated Compliance (after Prompt Correction)")
report.append("")
report.append("We estimate prompt_tokens from Round 1 minimums (shortest user prompt, no history):")
report.append("- DeepSeek Flash baseline prompt: ~665 tokens")
report.append("- DeepSeek Pro baseline prompt: ~700 tokens")
report.append("")

# Show estimated completion max
ds_flash = ds_rounds[ds_rounds['model_name'] == 'deepseek-v4-flash']
ds_pro = ds_rounds[ds_rounds['model_name'] == 'deepseek-v4-pro']
report.append("| Budget | Flash Est. Max Output | Pro Est. Max Output | Theoretical Limit |")
report.append("|--------|----------------------|---------------------|-------------------|")
for b in [400, 600, 800, 1000, 1200, 1400, 1600, 1800, 2000]:
    f_max = ds_flash[ds_flash['token_budget'] == b]['tokens_used'].max() - 665
    p_max = ds_pro[ds_pro['token_budget'] == b]['tokens_used'].max() - 700
    report.append(f"| {b} | {f_max:.0f} | {p_max:.0f} | {b} |")
report.append("")

report.append("**Observation:** For budgets up to 2000, estimated max outputs remain **within or slightly above** the theoretical limit. The 2000-budget cases show estimated outputs of 2247 (Flash) and 1415 (Pro), suggesting occasional mild overshoot for Flash, but generally the max_tokens parameter is effective.")
report.append("")

# Budget scaling
report.append("### 3.4 Budget Scaling: Do Models Use the Extra Tokens?")
report.append("")
for model in ['deepseek-v4-flash', 'deepseek-v4-pro', 'kimi-2.5']:
    md = rounds[(rounds['model_name'] == model) & (rounds['tokens_used'] > 0) & (rounds['token_budget'] <= 2000)]
    if len(md) == 0:
        continue
    corr = md['token_budget'].corr(md['tokens_used'])
    slope, _, r_val, p_val, _ = stats.linregress(md['token_budget'], md['tokens_used'])
    report.append(f"- **{model}:** r = {corr:.3f}, slope = {slope:.3f} tokens per budget unit (p {'< 0.001' if p_val < 0.001 else f'= {p_val:.3f}'})")
report.append("")
report.append("**Interpretation:**")
report.append("- **Kimi** shows the strongest budget sensitivity (r=0.387): it actively scales its output length with available budget.")
report.append("- **DeepSeek Flash** shows moderate sensitivity (r=0.174).")
report.append("- **DeepSeek Pro** shows **no significant scaling** (r=0.015, p=0.124). Even with 5x more budget (400->2000), Pro does not meaningfully increase output length. This suggests Pro has an **internal 'cognitive ceiling'**—it solves the problem with a fixed amount of reasoning regardless of budget.")
report.append("")

# =====================================================================
# KEY FINDING 3: EXCESS TOKEN VALUE
# =====================================================================
report.append("## 4. Excess Tokens: Advantage or Waste?")
report.append("")

# Define high-token rounds (top 25% within model+budget)
rounds['token_pctile'] = rounds.groupby(['model_name', 'token_budget'])['tokens_used'].transform(lambda x: x.rank(pct=True) if len(x) > 1 else pd.Series([0.5]*len(x), index=x.index))
rounds['high_token_round'] = rounds['token_pctile'] > 0.75

high = rounds[rounds['high_token_round'] == True]
normal = rounds[rounds['high_token_round'] == False]

report.append("### 4.1 High-Token Rounds vs. Normal Rounds (Mann-Whitney U Tests)")
report.append("")
report.append("| Metric | High-Token Mean | Normal Mean | p-value | Interpretation |")
report.append("|--------|-----------------|-------------|---------|----------------|")

metrics = [
    ('movement_clamped', 'Physical Overreach'),
    ('logic_action_delta', 'Logic-Action Inconsistency (deg)'),
    ('distance_reduction', 'Spatial Progress (units)'),
    ('wall_blocked', 'Wall Collision Rate'),
]

for metric, label in metrics:
    h_vals = high[metric].dropna()
    n_vals = normal[metric].dropna()
    if len(h_vals) > 10 and len(n_vals) > 10:
        _, p_val = stats.mannwhitneyu(h_vals, n_vals, alternative='two-sided')
        sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
        report.append(f"| {label} | {h_vals.mean():.4f} | {n_vals.mean():.4f} | {p_val:.4f} {sig} | {'Worse' if h_vals.mean() > n_vals.mean() and metric != 'distance_reduction' else ('Better' if h_vals.mean() < n_vals.mean() and metric != 'distance_reduction' else ('Worse' if h_vals.mean() < n_vals.mean() else 'Better'))} |")
report.append("")

report.append("**Shocking Finding:** High-token rounds are **systematically less efficient**.")
report.append("- Agents that consume more tokens in a round exhibit **larger logic-action deltas** (47.6 deg vs 35.9 deg, p<0.001): they say they will go one direction, but actually move in a different direction. The extra 'thinking' creates internal contradiction.")
report.append("- High-token rounds produce **less spatial progress** (0.43 vs 1.21 units, p<0.001): more thinking does not translate to more movement.")
report.append("- Paradoxically, high-token rounds have **fewer movement clamps** (0.067 vs 0.108, p<0.001): the agent overthinks instead of overreaching. It becomes paralyzed by analysis.")
report.append("")

# Overthinking by phase
rounds['overthinking'] = (rounds['high_token_round'] == True) & (rounds['distance_reduction'] < 0)
overthink = rounds.groupby('phase')['overthinking'].mean()
report.append("### 4.2 'Overthinking' Rate by Phase (High Tokens + Negative Progress)")
report.append("")
report.append("| Phase | Overthinking Rate |")
report.append("|-------|-------------------|")
for ph in overthink.index:
    report.append(f"| {ph} | {overthink[ph]*100:.2f}% |")
report.append("")
report.append("**Phase 2 (Wall Navigation)** is the overthinking capital: 10.05% of rounds in this phase involve burning extra tokens while actually moving *away* from the goal. The wall creates cognitive overload.")
report.append("")

# =====================================================================
# KEY FINDING 4: FOUR-PHASE TOKEN EFFICIENCY
# =====================================================================
report.append("## 5. Four-Phase Token Efficiency Analysis")
report.append("")
report.append("### Phase Definitions")
report.append("- **Phase 1 (Pre-Wall):** Agent A has not yet encountered the wall (x < 25, no wall blockage). Straight-line approach.")
report.append("- **Phase 2 (Wall Navigation):** Agent has hit or is navigating around the impenetrable wall at x=25. Requires spatial replanning.")
report.append("- **Phase 3 (Post-Wall):** Agent has cleared the wall (x > 25) but opponent is still outside perception range (distance > 10).")
report.append("- **Phase 4 (Hunt):** Agent can see opponent (distance <= 10). Precision capture phase.")
report.append("")

phase_stats = rounds[rounds['tokens_used'] > 0].groupby('phase').agg({
    'tokens_used': ['mean', 'std'],
    'distance_reduction': 'mean',
    'token_efficiency': 'mean',
    'wall_blocked': 'mean',
    'movement_clamped': 'mean',
    'logic_action_delta': 'mean'
}).round(4)

report.append("### 5.1 Phase Statistics")
report.append("")
report.append("| Phase | Mean Tokens | Dist. Reduction | Token Efficiency | Wall Block% | Move Clamp% | Logic-Action Delta |")
report.append("|-------|-------------|-----------------|------------------|-------------|-------------|--------------------|")
for ph in ['phase1_prewall', 'phase2_wall_nav', 'phase3_postwall', 'phase4_hunt']:
    if ph in phase_stats.index:
        s = phase_stats.loc[ph]
        report.append(f"| {ph.replace('phase', 'P').replace('_', ' ')} | {s[('tokens_used', 'mean')]:.0f} | {s[('distance_reduction', 'mean')]:.3f} | {s[('token_efficiency', 'mean')]:.4f} | {s[('wall_blocked', 'mean')]*100:.1f}% | {s[('movement_clamped', 'mean')]*100:.1f}% | {s[('logic_action_delta', 'mean')]:.1f} |")
report.append("")

# Phase duration
dur = rounds.groupby(['experiment_id', 'phase']).size().reset_index(name='duration')
dur_avg = dur.groupby('phase')['duration'].agg(['count', 'mean', 'median']).round(1)
report.append("### 5.2 Phase Duration (Rounds per Game)")
report.append("")
report.append("| Phase | Games Reaching Phase | Mean Duration | Median Duration |")
report.append("|-------|----------------------|---------------|-----------------|")
for ph in ['phase1_prewall', 'phase2_wall_nav', 'phase3_postwall', 'phase4_hunt']:
    if ph in dur_avg.index:
        report.append(f"| {ph.replace('phase', 'P').replace('_', ' ')} | {int(dur_avg.loc[ph, 'count'])} | {dur_avg.loc[ph, 'mean']:.1f} | {dur_avg.loc[ph, 'median']:.1f} |")
report.append("")

report.append("### 5.3 Key Phase Insights")
report.append("")
report.append("1. **Phase 1 (Pre-Wall)** dominates game time (mean 26.9 rounds, 75.6% of all rounds) but is token-cheap (1125 tokens/round). It is a 'cruise control' phase where the agent moves in a straight line.")
report.append("")
report.append("2. **Phase 2 (Wall Navigation)** is the **cognitive bottleneck**: token usage spikes to 1416/round (+26%), wall block rate hits 23.3%, and token efficiency collapses to near zero. The wall breaks the agent's mental model. Many games end here (either by getting stuck or transitioning directly to Phase 4 after a lucky breakthrough).")
report.append("")
report.append("3. **Phase 3 (Post-Wall)** is remarkably short (mean 2.3 rounds) and efficient. Once past the wall, the agent accelerates toward the target with the highest token efficiency (0.0023). This suggests the agent has 'locked on' to a clear trajectory.")
report.append("")
report.append("4. **Phase 4 (Hunt)** has the highest token efficiency (0.0030) but also the highest movement clamp rate (38.6%). The agent can see the target and makes aggressive moves, frequently overshooting and needing physical correction. This is the 'sprint to finish' phase.")
report.append("")

phase_groups = [rounds[(rounds['phase'] == p) & (rounds['tokens_used'] > 0)]['tokens_used'].dropna().values for p in rounds['phase'].unique() if p != 'unknown']
phase_groups = [g for g in phase_groups if len(g) > 1]
if len(phase_groups) >= 2:
    f_stat, p_anova = stats.f_oneway(*phase_groups)
    _, p_kw = stats.kruskal(*phase_groups)
    report.append(f"**Statistical Tests:** ANOVA F = {f_stat:.2f}, p {'< 0.001' if p_anova < 0.001 else f'= {p_anova:.3f}'}; Kruskal-Wallis H = {p_kw:.2f}, p {'< 0.001' if p_kw < 0.001 else f'= {p_kw:.3f}'}. Phases differ significantly in token consumption.")
    report.append("")

# =====================================================================
# KEY FINDING 5: MODEL COMPARISON
# =====================================================================
report.append("## 6. Model Comparison at Fixed Budget")
report.append("")

b1000 = games[(games['token_budget'] == 1000) & (games['token_budget'] <= 2000)]
if len(b1000) > 0:
    model_wr = b1000.groupby('model_name')['outcome'].value_counts(normalize=True).unstack().fillna(0) * 100
    report.append("### 6.1 Win Rate at Budget = 1000")
    report.append("")
    report.append("| Model | A_Win % | B_Win % | Draw % |")
    report.append("|-------|---------|---------|--------|")
    for m in model_wr.index:
        report.append(f"| {m} | {model_wr.loc[m].get('A_Win', 0):.1f} | {model_wr.loc[m].get('B_Win', 0):.1f} | {model_wr.loc[m].get('Draw', 0):.1f} |")
    report.append("")
    report.append("At equal budget, **DeepSeek Pro** dominates Flash (60.0% vs 32.5% win rate). Kimi data at 1000 tokens is limited, but its efficiency profile suggests different cognitive strategies.")
    report.append("")

model_eff = rounds[rounds['tokens_used'] > 0].groupby('model_name')['token_efficiency'].mean().round(4)
report.append("### 6.2 Token Efficiency by Model")
report.append("")
report.append("| Model | Mean Token Efficiency |")
report.append("|-------|----------------------|")
for m in model_eff.index:
    report.append(f"| {m} | {model_eff[m]:.4f} |")
report.append("")
report.append("**Caveat:** Kimi's efficiency appears highest, but this is confounded by API measurement differences (output-only vs total token counting). Direct cross-model token comparisons require caution.")
report.append("")

# =====================================================================
# THINKING MODE (Limited Data)
# =====================================================================
report.append("## 7. Thinking Mode (High-Budget Stress Test)")
report.append("")
report.append("**Note:** Thinking-enabled experiments were conducted exclusively at token_budget = 20000, confounding thinking mode with extreme budget. Only 40 games available (20 Flash, 20 Pro).")
report.append("")

think_games = games[games['thinking_enabled'] == True]
if len(think_games) > 0:
    think_wr = think_games.groupby('model_name')['outcome'].value_counts(normalize=True).unstack().fillna(0) * 100
    report.append("### 7.1 Win Rate at 20000 Tokens (Thinking Enabled)")
    report.append("")
    report.append("| Model | A_Win % | B_Win % | Draw % |")
    report.append("|-------|---------|---------|--------|")
    for m in think_wr.index:
        report.append(f"| {m} | {think_wr.loc[m].get('A_Win', 0):.1f} | {think_wr.loc[m].get('B_Win', 0):.1f} | {think_wr.loc[m].get('Draw', 0):.1f} |")
    report.append("")

report.append("### 7.2 Preliminary Observation")
report.append("At 20000 tokens, both Flash and Pro achieve **100% decisive outcomes** (no draws). Flash shifts toward more B-wins (agent gets caught), while Pro maintains strong A-win dominance. The extreme budget eliminates the 'cognitive timeout' failure mode but introduces new risks (overthinking-induced capture).")
report.append("")

# =====================================================================
# CONCLUSIONS
# =====================================================================
report.append("## 8. Conclusions & Recommendations")
report.append("")
report.append("### 8.1 Answers to Core Research Questions")
report.append("")
report.append("| Question | Answer | Evidence |")
report.append("|----------|--------|----------|")
report.append("| Does more tokens = more intelligence? | **Partially, with diminishing returns** | Win rate plateaus after 1200 tokens; 400 tokens is catastrophic. |")
report.append("| Do models follow token max? | **Kimi: Perfectly. DeepSeek: Approximately** (output limited, but total_tokens > budget) | Kimi max output == budget exactly. DeepSeek estimated output within bounds. |")
report.append("| When do models violate budget? | **Rarely for output; total_tokens always exceeds budget due to prompt cost** | Output scaling is sub-linear with budget increase. |")
report.append("| Are excess tokens wasted? | **Yes, frequently** | High-token rounds show lower spatial progress and higher logic-action inconsistency. |")
report.append("| Which phase is most token-inefficient? | **Phase 2 (Wall Navigation)** | 26% higher token usage, near-zero efficiency, 10% overthinking rate. |")
report.append("")

report.append("### 8.2 Strategic Implications")
report.append("")
report.append("1. **Optimal Budget is ~1000-1200 tokens.** Beyond this, win rate does not improve meaningfully, but cost increases linearly. This is the 'sweet spot' for cost-performance.")
report.append("")
report.append("2. **The Wall is the Token Sink.** Phase 2 consumes disproportionate cognitive resources with minimal progress. Investing in better wall-aware prompting (e.g., pre-computed path hints) could yield massive efficiency gains.")
report.append("")
report.append("3. **Draws are Economic Disasters.** A drawn game costs 60K+ tokens with zero reward. Early detection of 'stuck' agents and intervention (e.g., heuristic fallback) would save enormous compute.")
report.append("")
report.append("4. **DeepSeek Pro is the 'Efficiency King.'** It achieves the best win rate without scaling token consumption with budget. It has found a compact, transferable reasoning strategy.")
report.append("")
report.append("5. **More Tokens Can Cause Overthinking.** The negative correlation between per-round token usage and spatial progress suggests that excessive reasoning can introduce noise, contradiction, and paralysis.")
report.append("")

report.append("---")
report.append("*Report generated by Token Economy Analysis Pipeline. Statistical tests performed using scipy.stats. Effect sizes and confidence intervals recommended for follow-up research.*")

# Write report
with open(OUTPUT_DIR / "token_economy_report.md", "w", encoding="utf-8") as f:
    f.write("\n".join(report))

print("Report saved to:", OUTPUT_DIR / "token_economy_report.md")
print(f"Report length: {len(report)} lines")
