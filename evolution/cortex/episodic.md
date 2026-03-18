# Episodic Memory

> Raw experience log — the autobiography of this agent's journey.
> Each episode is a timestamped record of what happened, unfiltered.
> This is the foundation from which all other knowledge is distilled.

## Memory Protocol

Every completed cycle logs an episode here. Episodes are the raw data
from which semantic principles and procedural recipes are extracted.

### Episode Format

```
## Episode [N] — [ISO Timestamp]
- **Context**: [Situation before the action — what sub-goal, what state]
- **Strategy**: [Which strategy was being executed — S00X]
- **Action**: [Exactly what was done — be specific]
- **Outcome**: [What happened — include test results, errors, etc.]
- **Surprise**: [0.0-1.0 — how unexpected was this outcome?]
- **Valence**: [POSITIVE / NEGATIVE / NEUTRAL]
- **Duration**: [How long did this cycle take?]
- **Tags**: [searchable tags for pattern mining]
```

### Pruning Rules
- Keep the 50 most recent episodes in full detail
- Episodes older than 50 cycles: keep only if Surprise > 0.7 or tagged as LANDMARK
- Landmark episodes: first success, biggest failure, breakthrough moments, paradigm shifts

---

## Episodes

_No episodes recorded yet. Evolution has not begun._
