# Reward Signals

> The reinforcement learning backbone — every action gets a reward signal.
> Positive rewards strengthen the strategy. Negative rewards weaken it.
> The reward history enables temporal-difference learning across cycles.

## Reward Design (Reward Shaping)

### Immediate Rewards
| Signal | Reward | Description |
|--------|--------|-------------|
| Test passes increase | +0.10 per test | Direct evidence of correctness |
| Test passes decrease | -0.15 per test | Regression — penalize harder than reward |
| Build succeeds | +0.05 | Baseline requirement |
| Build fails | -0.20 | Critical failure |
| Lint errors decrease | +0.03 per error fixed | Quality improvement |
| Lint errors increase | -0.05 per error | Quality regression |
| Sub-goal completed | +0.50 | Major milestone |
| Goal completed | +1.00 | Ultimate reward |

### Shaped Rewards (Potential-Based)
| Signal | Reward | Description |
|--------|--------|-------------|
| Progress toward sub-goal | +0.05 | Estimated by task completion |
| Novel approach tried | +0.02 | Exploration bonus |
| Knowledge item created | +0.01 | Learning bonus |
| Hypothesis confirmed | +0.03 | Understanding deepened |
| Pattern discovered | +0.05 | Meta-learning bonus |

### Penalties
| Signal | Penalty | Description |
|--------|---------|-------------|
| Same action repeated | -0.05 | Stagnation penalty |
| Cycle with no change | -0.10 | Wasted cycle |
| Revert triggered | -0.03 | Failed experiment (mild — failure is learning) |

## Reward History

_No rewards recorded yet._

## Cumulative Reward

- **Total Reward**: 0.00
- **Average Reward per Cycle**: —
- **Best Single Cycle**: —
- **Worst Single Cycle**: —
- **Reward Trend**: —

## Temporal Difference Analysis

> TD learning: Was the outcome better or worse than expected?
> TD Error = Actual Reward - Expected Reward
> Positive TD = pleasant surprise. Negative TD = disappointed.

_No TD data yet._
