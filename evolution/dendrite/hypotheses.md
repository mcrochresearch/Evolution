# Hypotheses

> Active hypotheses being tested — the scientific method applied to coding.
> Every action should ideally test a hypothesis. Every outcome updates beliefs.
> Inspired by Bayesian optimization and the scientific method.

## Hypothesis Lifecycle

```
PROPOSED → TESTING → CONFIRMED / REFUTED / SUSPENDED
```

- **PROPOSED**: Generated from reflections, pattern analysis, or exploration
- **TESTING**: Currently being evaluated by an active strategy
- **CONFIRMED**: Evidence strongly supports (posterior > 0.8)
- **REFUTED**: Evidence strongly contradicts (posterior < 0.2)
- **SUSPENDED**: Not enough evidence either way, deprioritized

## Active Hypotheses

_No hypotheses yet. Goal decomposition will generate the first batch._

### Hypothesis Format

```
## H[NNN]: [Hypothesis Statement]
- **Status**: PROPOSED / TESTING / CONFIRMED / REFUTED / SUSPENDED
- **Prior**: [0.0-1.0 — initial belief before evidence]
- **Posterior**: [0.0-1.0 — updated belief after evidence]
- **Evidence For**: [List of supporting episodes]
- **Evidence Against**: [List of contradicting episodes]
- **Information Gain if Tested**: [LOW / MEDIUM / HIGH]
- **Test Plan**: [Specific experiment to test this hypothesis]
- **Connected Strategy**: [Which strategy tests this — S00X]
- **Implications if True**: [What changes if confirmed]
- **Implications if False**: [What changes if refuted]
```

## Hypothesis Generation Rules

Generate new hypotheses from:
1. **Reflections** — "I think X failed because of Y" → H: "Y causes failure in X"
2. **Patterns** — "Changes of type A tend to work" → H: "Type A changes improve fitness"
3. **Blind spots** — "I haven't tried Z" → H: "Z might be better than current approach"
4. **Analogies** — "This is similar to problem P" → H: "Solution for P works here too"
5. **Inversions** — "Everything I've tried does X" → H: "Not-X might work better"

## Experiment Queue (Ranked by Expected Information Gain)

| Priority | Hypothesis | Info Gain | Expected Reward | Combined Score |
|----------|-----------|-----------|----------------|----------------|
| — | — | — | — | — |

---

_Hypotheses are the bridge between reflection and action. They turn learning into direction._
