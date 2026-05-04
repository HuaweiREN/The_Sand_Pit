# Experimental Results

This directory contains the aggregated win-rate data extracted from **724 controlled games** run across DeepSeek (Flash & Pro).

## Files

- `win_rate_data.json` — Machine-readable JSON with per-budget statistics for all experiments.

## Quick Reference: Win Rates by Model & Budget

### DeepSeek Flash (standard mode)

| Tokens | Wins | Draws | Losses | Win Rate | Draw Rate |
|--------|------|-------|--------|----------|-----------|
| 400    | 1    | 36    | 3      | 2.5%     | 90.0%     |
| 600    | 5    | 32    | 3      | 12.5%    | 80.0%     |
| 800    | 4    | 30    | 6      | 9.8%     | 73.2%     |
| 1000   | 13   | 18    | 9      | 32.5%    | 45.0%     |
| 1200   | 14   | 18    | 7      | 34.1%    | 43.9%     |
| 1400   | 13   | 20    | 7      | 32.5%    | 50.0%     |
| 1600   | 13   | 18    | 9      | 32.5%    | 45.0%     |
| 1800   | 18   | 13    | 9      | 45.0%    | 32.5%     |
| 2000   | 15   | 13    | 12     | 34.9%    | 30.2%     |

### DeepSeek Flash (reasoning / 20K)

| Tokens | Wins | Draws | Losses | Win Rate | Draw Rate |
|--------|------|-------|--------|----------|-----------|
| 20000  | 13   | 2     | 5      | 65.0%    | 10.0%     |

### DeepSeek Pro (standard mode)

| Tokens | Wins | Draws | Losses | Win Rate | Draw Rate |
|--------|------|-------|--------|----------|-----------|
| 400    | 5    | 26    | 9      | 12.5%    | 65.0%     |
| 600    | 22   | 5     | 13     | 55.0%    | 12.5%     |
| 800    | 15   | 5     | 20     | 37.5%    | 12.5%     |
| 1000   | 24   | 0     | 16     | 60.0%    | 0.0%      |
| 1200   | 29   | 2     | 10     | 70.7%    | 4.9%      |
| 1400   | 21   | 3     | 16     | 52.5%    | 7.5%      |
| 1600   | 21   | 2     | 17     | 52.5%    | 5.0%      |
| 1800   | 22   | 2     | 16     | 55.0%    | 5.0%      |
| 2000   | 26   | 1     | 13     | 65.0%    | 2.5%      |

### DeepSeek Pro (reasoning / 20K)

| Tokens | Wins | Draws | Losses | Win Rate | Draw Rate |
|--------|------|-------|--------|----------|-----------|
| 20000  | 16   | 0     | 4      | 80.0%    | 0.0%      |

## Interpretation

See the main [README.md](../README.md) for full discussion of the three-stage threshold effect and the five core findings.
