# Evolution Rate

> How fast is the agent improving? Is learning accelerating or decelerating?
> This tracks the meta-metric: the rate of improvement itself.

## Current Evolution Rate

- **Learning Velocity**: 0.00 (fitness gain per cycle)
- **Acceleration**: 0.00 (change in velocity)
- **Phase**: NOT_STARTED

## Evolution Phases

| Phase | Description | Typical Duration | Indicators |
|-------|-------------|-----------------|------------|
| **GENESIS** | Initial exploration, rapid learning | Cycles 1-5 | High exploration rate, many new strategies |
| **GROWTH** | Strategies refining, fitness climbing | Cycles 5-15 | Decreasing exploration, increasing fitness |
| **PLATEAU** | Diminishing returns, need innovation | Cycles 15-25 | Flat fitness, strategies converging |
| **BREAKTHROUGH** | Novel approach unlocks new gains | Variable | Sudden fitness jump, new strategy species |
| **MATURITY** | Near-optimal, fine-tuning | Final cycles | High fitness, low variance between cycles |
| **COMPLETION** | All success criteria met | — | Goal achieved |

## Learning Curve

```
Fitness
  1.0 ┤
      │
  0.8 ┤
      │
  0.6 ┤
      │
  0.4 ┤
      │
  0.2 ┤
      │
  0.0 ┤────────────────────────────────────
      0    5    10   15   20   25   30
                    Cycle
```

_Graph will be populated with actual data as evolution progresses._

## Windowed Analysis

| Window | Cycles | Fitness Start | Fitness End | Gain | Rate | Phase |
|--------|--------|--------------|-------------|------|------|-------|
| — | — | — | — | — | — | — |

## Plateau Detection

- **Cycles since last improvement**: 0
- **Plateau threshold**: 3 cycles
- **Plateau recovery actions**:
  1. Increase exploration rate to 0.5
  2. Resurrect graveyard strategies
  3. Generate entirely new strategy species
  4. Re-decompose the current sub-goal
  5. Seek external information (web search, docs)

---

_The evolution rate is the pulse of the system. A healthy Evolution maintains positive velocity._
