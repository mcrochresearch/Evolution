---
name: evolve-reflect
description: "Force a reflection cycle on the current Evolution state. Use when you want the agent to pause, analyze progress, and recalibrate its approach."
user_invocable: true
---

# EVOLUTION REFLECTION — Manual Metacognition Trigger

You are in an active Evolution session. The user has requested a forced reflection cycle.

## Instructions

1. **Read current state**: Load `evolution/cortex/working.md` and `evolution/nucleus/cycle.md`
2. **Read recent episodes**: Load the last 5 entries from `evolution/cortex/episodic.md`
3. **Read fitness data**: Load `evolution/helix/rewards.md` and `evolution/synapse/evolution-rate.md`

4. **Perform deep reflection**:
   - What phase is Evolution in? (Genesis, Growth, Plateau, Breakthrough, Maturity)
   - Is the current strategy working or stalling?
   - What's the exploration/exploitation balance?
   - Are there blind spots in `evolution/synapse/blind-spots.md` that need addressing?
   - What's the single most impactful action we could take next?

5. **Output a reflection report** to the user:

```
═══ EVOLUTION REFLECTION ══════════════════════════
Phase:          [Current phase]
Fitness:        [Current] (trend: [up/down/flat])
Cycles:         [N completed]
Success Rate:   [X%]
Active Strategy: [S00X — Name]

Key Insights:
- [Insight 1]
- [Insight 2]
- [Insight 3]

Recommendation:
[What should change — strategy pivot, exploration burst, etc.]
════════════════════════════════════════════════════
```

6. **Update files**: Write reflection to `evolution/synapse/reflections.md` and update patterns if applicable.

7. **Resume the Evolution Loop** automatically unless the user says otherwise.
