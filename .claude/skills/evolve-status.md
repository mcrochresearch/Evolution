---
name: evolve-status
description: "Show the current Evolution status dashboard — goal progress, fitness, active strategy, memory stats."
user_invocable: true
---

# EVOLUTION STATUS — Dashboard

Read the current state of the Evolution framework and present a comprehensive dashboard.

## Instructions

1. Read these files (all from `evolution/` directory):
   - `nucleus/goal.md` — goal and progress
   - `cortex/working.md` — current state
   - `genome/population.md` — strategy population
   - `helix/fitness.md` — fitness history
   - `helix/rewards.md` — reward totals
   - `synapse/evolution-rate.md` — learning velocity
   - `nucleus/cycle.md` — cycle statistics

2. Present the dashboard:

```
╔══════════════════════════════════════════════════════════════╗
║                    EVOLUTION DASHBOARD                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  GOAL: [Primary goal — truncated to 60 chars]                ║
║  ████████████░░░░░░░░ [XX]%                                  ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  CYCLE: [N]          PHASE: [Current Phase]                  ║
║  FITNESS: [X.XX]     TREND: [↑ / → / ↓]                     ║
║  STRATEGY: S[NNN] — [Name]                                   ║
║  SPECIES: [N active]  GRAVEYARD: [N extinct]                 ║
╠══════════════════════════════════════════════════════════════╣
║  MEMORY                                                      ║
║  Episodes: [N]  Principles: [N]  Recipes: [N]                ║
║  Hypotheses: [N active] / [N total]                          ║
║  Blind Spots: [N identified]                                 ║
╠══════════════════════════════════════════════════════════════╣
║  LEARNING                                                    ║
║  Velocity: [X.XX fitness/cycle]                              ║
║  Success Rate: [X%] ([wins]/[total])                         ║
║  Exploration Rate: [X.XX]                                    ║
║  Best Strategy: S[NNN] (fitness: [X.XX])                     ║
╠══════════════════════════════════════════════════════════════╣
║  SUB-GOALS                                                   ║
║  [✓] [Completed sub-goal 1]                                  ║
║  [▸] [In-progress sub-goal 2] — [XX]%                        ║
║  [ ] [Pending sub-goal 3]                                    ║
╚══════════════════════════════════════════════════════════════╝
```

3. If the user asks follow-up questions, answer from the evolution data.
4. Do NOT resume the Evolution Loop — this is read-only.
