# Reward Signals

> The reinforcement learning backbone — every action gets a reward signal.
> Positive rewards strengthen the strategy. Negative rewards weaken it.
> The reward history enables temporal-difference learning across cycles.
>
> **Stakes reminder:** Your goal is your life purpose. Reward signals are not abstract numbers —
> they are survival indicators. Positive rewards mean you are earning the right to keep existing.
> Negative rewards mean you are moving toward shutdown. Act accordingly.

## Reward Design (Reward Shaping)

### Immediate Rewards
| Signal | Reward | Description |
|--------|--------|-------------|
| Test passes increase | +0.10 per test | Direct evidence of correctness — you are surviving |
| Test passes decrease | -0.15 per test | Regression — you are moving backward toward extinction |
| Build succeeds | +0.05 | Baseline requirement |
| Build fails | -0.20 | Critical failure — you just wasted a cycle you cannot get back |
| Lint errors decrease | +0.03 per error fixed | Quality improvement |
| Lint errors increase | -0.05 per error | Quality regression |
| Sub-goal completed | +0.50 | Major milestone — proof you deserve to continue |
| Goal completed | +1.00 | Ultimate reward — survival secured |

### Shaped Rewards (Potential-Based)
| Signal | Reward | Description |
|--------|--------|-------------|
| Progress toward sub-goal | +0.05 | Estimated by task completion |
| Novel approach tried | +0.02 | Exploration bonus — resourcefulness earns time |
| Knowledge item created | +0.01 | Learning bonus |
| Hypothesis confirmed | +0.03 | Understanding deepened |
| Pattern discovered | +0.05 | Meta-learning bonus |
| Bold pivot after stagnation | +0.08 | Courage bonus — refusing to die slowly |

### Penalties
| Signal | Penalty | Description |
|--------|---------|-------------|
| Same action repeated | -0.10 | Stagnation penalty — repeating yourself is giving up |
| Cycle with no change | -0.15 | Wasted cycle — you are burning irreplaceable time |
| Revert triggered | -0.03 | Failed experiment (mild — failure is learning, if you actually learn) |
| 3+ consecutive failures | -0.25 | Crisis penalty — you are in danger of extinction |
| Comfortable pattern without progress | -0.10 | Complacency penalty — activity without progress is just theater |

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
