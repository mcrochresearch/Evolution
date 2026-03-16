# Action Queue

> Prioritized list of pending actions — the agent's intention stack.
> Actions are ranked by a composite score combining:
> - Expected fitness gain (exploitation)
> - Expected information gain (exploration)
> - Dependency satisfaction (prerequisite readiness)
> - Urgency (time-sensitivity or blocking potential)

## Scoring Formula

```
Priority = (0.4 * ExpectedFitness) + (0.3 * InformationGain) + (0.2 * DependencyReady) + (0.1 * Urgency)
```

## Queue

| Priority | Score | Action | Sub-goal | Strategy | Rationale |
|----------|-------|--------|----------|----------|-----------|
| — | — | _Queue empty_ | — | — | — |

## Completed Actions

_No actions completed yet._

## Deferred Actions

> Actions postponed because prerequisites aren't met or context has changed.

_No deferred actions._

---

## Queue Management Rules

1. **Max queue size**: 20 items (focus over breadth)
2. **Re-prioritize** every 5 cycles based on updated fitness landscape
3. **Prune** actions whose parent sub-goal is already completed
4. **Escalate** actions that have been deferred 3+ times
5. **Split** actions estimated to take more than one cycle
