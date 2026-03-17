---
name: evolve-pivot
description: "Force a strategic pivot in Evolution — kill the current strategy, increase exploration, and try a fundamentally different approach."
user_invocable: true
---

# EVOLUTION PIVOT — Strategic Reset

A pivot has been triggered — the current approach isn't working and we need to try something fundamentally different. This may be self-triggered (stagnation detected) or user-triggered.

## Instructions

1. **Assess current state**: Read `evolution/cortex/working.md` and `evolution/genome/population.md`

2. **Kill the current strategy**:
   - Move the active strategy to `evolution/genome/graveyard.md` with cause: "USER_PIVOT"
   - Record the final fitness and failure analysis

3. **Exploration burst**:
   - Set exploration rate to 0.8 temporarily (in `cortex/working.md`)
   - Generate 3 NEW strategies that are fundamentally different from anything tried before
   - Use inversion thinking: "What's the opposite of what we've been doing?"
   - Use analogy thinking: "How would a different domain solve this?"
   - Use simplification: "What's the simplest possible approach we haven't tried?"

4. **Review the graveyard**: Check `evolution/genome/graveyard.md` — is there anything worth resurrecting in the new context?

5. **Update the goal tree**: Re-read `evolution/nucleus/goal.md` — does the decomposition still make sense? Restructure if needed.

6. **Report the pivot** to the user:

```
═══ EVOLUTION PIVOT ════════════════════════════════
Killed:    S[NNN] — [Name] (fitness: [X.XX])
Reason:    [Self-triggered / User-triggered / Plateau detected]

New Strategies:
  S[NNN] — [New approach 1]
  S[NNN] — [New approach 2]
  S[NNN] — [New approach 3]

Exploration Rate: 0.30 → 0.80 (temporary burst)
════════════════════════════════════════════════════
```

7. **Resume the Evolution Loop** with the new strategies.
