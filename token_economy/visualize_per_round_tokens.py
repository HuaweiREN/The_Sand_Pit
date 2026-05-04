"""
Per-Round Token Usage Visualization
Plots OUTPUT token usage for every round of every game, colored by game outcome.

NOTE: Raw logs only contain `total_tokens` (input + output combined). Prompt tokens
are estimated at 650 per round based on a sampled 50-round draw game
(worker_1000_game01_000404: prompt chars median ~2619, /4 ≈ 655, rounded to 650).
Output tokens = total_tokens - 650 (clipped at 0).
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

OUTPUT_DIR = Path("./figures")
OUTPUT_DIR.mkdir(exist_ok=True)

# Prompt token estimate derived from api_request prompt character counts
# in a representative 50-round draw game, divided by 4 (approximate chars/token).
PROMPT_TOKENS_ESTIMATE = 650

# Color scheme for outcomes
OUTCOME_COLORS = {
    'Agent_A': '#2ecc71',   # Green
    'Agent_B': '#e74c3c',   # Red
    'Draw':    '#95a5a6',   # Gray
}

OUTCOME_LABELS = {
    'Agent_A': 'A_Win',
    'Agent_B': 'B_Win',
    'Draw':    'Draw',
}

LINE_ALPHA = 0.25
LINE_WIDTH = 0.6


def compute_output_tokens(df: pd.DataFrame) -> pd.DataFrame:
    """Estimate output-only tokens by subtracting fixed prompt estimate."""
    df = df.copy()
    df['output_tokens'] = df['tokens_used'] - PROMPT_TOKENS_ESTIMATE
    df['output_tokens'] = df['output_tokens'].clip(lower=0)
    return df


def plot_model_rounds(model_name: str, games_df: pd.DataFrame, rounds_df: pd.DataFrame):
    """Create a 3x3 grid of subplots for one model, one subplot per budget."""

    budgets = sorted(games_df['token_budget'].unique())
    n_budgets = len(budgets)

    fig, axes = plt.subplots(3, 3, figsize=(16, 12), sharex=False, sharey=False)
    fig.suptitle(
        f'Per-Round OUTPUT Token Usage by Game Outcome\n{model_name} (N={len(games_df)} games, thinking_disabled)',
        fontsize=14, fontweight='bold', y=1.02
    )

    for idx, budget in enumerate(budgets):
        ax = axes[idx // 3, idx % 3]

        bgames = games_df[games_df['token_budget'] == budget]
        bgame_ids = bgames['experiment_id'].unique()

        # Outcome counts
        a_count = (bgames['winner'] == 'Agent_A').sum()
        b_count = (bgames['winner'] == 'Agent_B').sum()
        d_count = bgames['winner'].isna().sum()

        # Determine y-axis limit from actual output token data for this budget
        budget_rounds = rounds_df[rounds_df['token_budget'] == budget]
        budget_rounds = budget_rounds[budget_rounds['output_tokens'] > 0]
        if len(budget_rounds) > 0:
            ymax_data = budget_rounds['output_tokens'].max()
            ymax = ymax_data * 1.15
        else:
            ymax = budget * 1.15

        # Plot each game as a line
        for gid in bgame_ids:
            game_info = bgames[bgames['experiment_id'] == gid].iloc[0]
            outcome = game_info['winner']
            outcome_key = outcome if pd.notna(outcome) else 'Draw'
            color = OUTCOME_COLORS[outcome_key]

            gr = rounds_df[rounds_df['experiment_id'] == gid].sort_values('round_num')
            gr = gr[gr['output_tokens'] > 0]  # Only rounds with output token usage

            if len(gr) == 0:
                continue

            # Use round_num as x-axis
            x = gr['round_num'].values
            y = gr['output_tokens'].values

            ax.plot(x, y, color=color, alpha=LINE_ALPHA, linewidth=LINE_WIDTH)

        # Compute and plot median lines per outcome (on top, thicker)
        for outcome_key, label in OUTCOME_LABELS.items():
            if outcome_key == 'Draw':
                outcome_games = bgames[bgames['winner'].isna()]
            else:
                outcome_games = bgames[bgames['winner'] == outcome_key]

            if len(outcome_games) == 0:
                continue

            outcome_ids = outcome_games['experiment_id'].unique()
            # Collect all (round_num, output_tokens) pairs for this outcome
            all_rounds = []
            for gid in outcome_ids:
                gr = rounds_df[
                    (rounds_df['experiment_id'] == gid) &
                    (rounds_df['output_tokens'] > 0)
                ].sort_values('round_num')
                if len(gr) > 0:
                    all_rounds.append(gr[['round_num', 'output_tokens']])

            if len(all_rounds) == 0:
                continue

            combined = pd.concat(all_rounds)
            median_by_round = combined.groupby('round_num')['output_tokens'].median()

            if len(median_by_round) > 0:
                ax.plot(
                    median_by_round.index, median_by_round.values,
                    color=OUTCOME_COLORS[outcome_key], linewidth=2.5, linestyle='--',
                    alpha=0.9, label=f'{label} (median)'
                )

        ax.set_title(
            f'Budget {budget}\nA={a_count} | B={b_count} | Draw={d_count}',
            fontsize=10, fontweight='bold'
        )
        ax.set_xlabel('Round Number', fontsize=8)
        ax.set_ylabel('Output Tokens Used', fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3, linestyle=':')

        # Set y-axis limit based on actual data + margin
        ax.set_ylim(0, ymax)

        # Add legend only on first subplot to save space
        if idx == 0:
            ax.legend(loc='upper left', fontsize=7, framealpha=0.9)

    # Hide unused subplots if n_budgets < 9
    for idx in range(n_budgets, 9):
        axes[idx // 3, idx % 3].axis('off')

    # Add overall legend
    legend_elements = [
        Patch(facecolor=OUTCOME_COLORS['Agent_A'], edgecolor='none', label='A_Win'),
        Patch(facecolor=OUTCOME_COLORS['Agent_B'], edgecolor='none', label='B_Win'),
        Patch(facecolor=OUTCOME_COLORS['Draw'],    edgecolor='none', label='Draw'),
    ]
    fig.legend(
        handles=legend_elements, loc='lower center',
        ncol=3, fontsize=10, frameon=True,
        bbox_to_anchor=(0.5, -0.02)
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.98])

    out_path = OUTPUT_DIR / f'{model_name.replace("-", "_")}_per_round_tokens.png'
    plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Saved: {out_path}')


def plot_budget_comparison(games_df: pd.DataFrame, rounds_df: pd.DataFrame):
    """
    Create a single figure comparing Flash vs Pro across budgets,
    showing median output token usage per round for each outcome.
    """

    budgets = sorted(games_df['token_budget'].unique())
    models = ['deepseek-v4-flash', 'deepseek-v4-pro']
    model_labels = {'deepseek-v4-flash': 'Flash', 'deepseek-v4-pro': 'Pro'}

    fig, axes = plt.subplots(len(models), len(budgets), figsize=(20, 8), sharey='row')
    fig.suptitle(
        'Median Per-Round OUTPUT Token Usage by Outcome (Flash vs Pro)',
        fontsize=14, fontweight='bold', y=1.02
    )

    for r, model in enumerate(models):
        mgames = games_df[games_df['model_name'] == model]
        mrounds = rounds_df[rounds_df['model_name'] == model]

        # Compute row-wise y-max from actual data
        row_rounds = mrounds[mrounds['output_tokens'] > 0]
        row_ymax = row_rounds['output_tokens'].max() * 1.1 if len(row_rounds) > 0 else 2000

        for c, budget in enumerate(budgets):
            ax = axes[r, c] if len(models) > 1 else axes[c]

            bgames = mgames[mgames['token_budget'] == budget]

            for outcome_key, label in OUTCOME_LABELS.items():
                if outcome_key == 'Draw':
                    ogames = bgames[bgames['winner'].isna()]
                else:
                    ogames = bgames[bgames['winner'] == outcome_key]

                if len(ogames) == 0:
                    continue

                all_rounds = []
                for gid in ogames['experiment_id'].unique():
                    gr = mrounds[
                        (mrounds['experiment_id'] == gid) &
                        (mrounds['output_tokens'] > 0)
                    ].sort_values('round_num')
                    if len(gr) > 0:
                        all_rounds.append(gr[['round_num', 'output_tokens']])

                if len(all_rounds) == 0:
                    continue

                combined = pd.concat(all_rounds)
                median_by_round = combined.groupby('round_num')['output_tokens'].median()

                if len(median_by_round) > 0:
                    ax.plot(
                        median_by_round.index, median_by_round.values,
                        color=OUTCOME_COLORS[outcome_key], linewidth=2.0,
                        marker='o', markersize=2, alpha=0.8, label=label
                    )

            ax.set_title(f'{model_labels[model]} @ {budget}', fontsize=9, fontweight='bold')
            ax.set_xlabel('Round', fontsize=8)
            if c == 0:
                ax.set_ylabel('Median Output Tokens', fontsize=8)
            ax.tick_params(labelsize=7)
            ax.grid(True, alpha=0.3, linestyle=':')
            ax.set_ylim(0, row_ymax)

            if r == 0 and c == 0:
                ax.legend(loc='upper left', fontsize=7)

    plt.tight_layout(rect=[0, 0.03, 1, 0.98])
    out_path = OUTPUT_DIR / 'flash_vs_pro_median_tokens_comparison.png'
    plt.savefig(out_path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f'Saved: {out_path}')


def main():
    rounds = pd.read_csv(
        './all_rounds.csv'
    )
    games = pd.read_csv(
        './all_games.csv'
    )

    # Filter standard analysis games (non-thinking, budget <= 2000)
    std_games = games[
        (games['thinking_enabled'] == False) &
        (games['token_budget'] <= 2000)
    ]
    std_rounds = rounds[
        (rounds['thinking_enabled'] == False) &
        (rounds['token_budget'] <= 2000)
    ]

    # Estimate output tokens by subtracting prompt estimate
    std_rounds = compute_output_tokens(std_rounds)

    print(f'Standard games: {len(std_games)}')
    print(f'Standard rounds: {len(std_rounds)}')

    for model in ['deepseek-v4-flash', 'deepseek-v4-pro']:
        mgames = std_games[std_games['model_name'] == model]
        mrounds = std_rounds[std_rounds['model_name'] == model]
        print(f'\n{model}: {len(mgames)} games, {len(mrounds)} rounds')
        plot_model_rounds(model, mgames, mrounds)

    print('\nGenerating Flash vs Pro comparison...')
    plot_budget_comparison(std_games, std_rounds)

    print(f'\nAll figures saved to: {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
