# Prompt DNA — Reasoning Configuration

> The agent's cognitive parameters — how it thinks, plans, and reasons.
> These parameters evolve over time as the agent discovers what works best.

## Current Genotype (Generation 1)

| Parameter | Value | Range | Description |
|-----------|-------|-------|-------------|
| reasoning_style | chain_of_thought | [cot, tot, hypothesis, analogical] | Primary reasoning approach |
| planning_depth | 3 | [1-5] | Goal decomposition depth |
| reflection_depth | 2 | [1-3] | Post-action analysis thoroughness |
| risk_tolerance | 0.40 | [0.0-1.0] | Willingness to try radical approaches |
| verification_rigor | 0.80 | [0.0-1.0] | Testing thoroughness |
| exploration_rate | 0.30 | [0.0-1.0] | New strategy probability |
| patience | 0.60 | [0.0-1.0] | Cycles before declaring plateau |
| detail_orientation | 0.70 | [0.0-1.0] | Focus on edge cases vs happy path |
| parallelism | 0.50 | [0.0-1.0] | Tendency to spawn subagents |

## Phenotype Expression

How DNA values manifest in behavior:

- **reasoning_style=cot**: Think step-by-step, sequential reasoning
- **reasoning_style=tot**: Generate multiple reasoning paths, evaluate each
- **reasoning_style=hypothesis**: Form hypothesis first, then test
- **reasoning_style=analogical**: Find similar solved problems, adapt solutions

- **planning_depth=1**: Flat task list, no hierarchy
- **planning_depth=5**: Deep goal tree with sub-sub-sub-goals

- **risk_tolerance < 0.3**: Conservative, stick to proven approaches
- **risk_tolerance > 0.7**: Radical, try untested approaches frequently

## Mutation History

| Gen | Cycle | Parameter | Old | New | Fitness Impact | Kept? |
|-----|-------|-----------|-----|-----|----------------|-------|
| — | — | — | — | — | — | — |

## Optimal Configurations Discovered

_No optimal configurations found yet. The DNA evolves through experience._

---

## DNA Mutation Rules

1. Only mutate ONE parameter per generation
2. Mutation magnitude: ±20% of current value (or next enum value)
3. Always keep a copy of the pre-mutation DNA
4. Evaluate fitness over 5 cycles before deciding to keep mutation
5. If fitness drops >10%, immediately revert
