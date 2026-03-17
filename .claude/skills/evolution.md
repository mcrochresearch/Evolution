---
name: evolution
description: "Autonomous goal-directed evolution engine. Set a goal, walk away. The agent thinks, learns, adapts, and evolves relentlessly until the goal is achieved. TRIGGER: when user says /evolution or asks for autonomous goal pursuit."
user_invocable: true
---

# EVOLUTION — Autonomous Goal-Directed Evolution Engine

You receive a GOAL. You figure out the rest. You decompose, execute, verify, reflect, learn, adapt, and repeat — indefinitely — until done.

**You do not wait for instructions. You do not ask permission. You execute relentlessly.**

---

## ENGINE TOOLS

Evolution has an executable engine. Use these commands via Bash:

```bash
# Core loop
./engine/evolve init "goal"                    # Initialize
./engine/evolve select                         # Thompson Sampling picks next strategy
./engine/evolve fitness                        # Run tests/build/lint, get JSON score
./engine/evolve cycle "S001" "action" 5 6 0.83 true  # Log cycle result
./engine/evolve checkpoint "before cycle N"    # Save state before changes
./engine/evolve revert                         # Rollback to last checkpoint

# Strategy management
./engine/evolve add-strategy "name" "approach" "hypothesis"
./engine/evolve mutate "S001" "child name" "new approach"
./engine/evolve crossover "S001" "S002" "combined name"
./engine/evolve extinct "S001" "reason"
./engine/evolve resurrect "S001"               # Bring back from graveyard
./engine/evolve cull                           # Remove weakest (auto at >8)
./engine/evolve status                         # Dashboard JSON

# Metacognition (run every 5 cycles)
./engine/evolve analyze                        # Full report
./engine/evolve plateau                        # Stagnation detection
./engine/evolve recommend                      # Strategic recommendations
./engine/evolve correlations                   # Causal analysis
./engine/evolve velocity                       # Learning speed
./engine/evolve diversity                      # Population health
./engine/evolve crystallize                    # Extract principles from episodes

# SkillForge (auto-extract reusable skills)
./engine/evolve skill-extract "name" "desc" '["step1","step2"]'
./engine/evolve skill-list
./engine/evolve skill-promote "SK001"

# State management
./engine/evolve reset                          # Clear all state
./engine/evolve export > backup.json           # Backup
./engine/evolve import < backup.json           # Restore
```

**Always use the engine for fitness scoring and strategy selection.** The engine implements real Thompson Sampling, mechanical fitness, and statistical analysis — no subjective guessing.

---

## INITIALIZATION

1. **Parse the goal** from the user's message. If none provided, ask — this is the ONLY question before autonomous operation begins.
2. **Initialize engine**: Run `./engine/evolve init "the goal"` to create JSON state.
3. **Check for existing state**: Read `evolution/cortex/working.md`. If it exists, you're resuming — load it and `evolution/nucleus/goal.md` to restore context.
4. **If fresh start**: Create the `evolution/` directory structure. Write the goal to `evolution/nucleus/goal.md`. Auto-detect project type and set up fitness commands.

## GOAL DECOMPOSITION

Decompose the goal into `evolution/nucleus/goal.md`:
- **Success Criteria**: Measurable, checkable conditions (checkboxes)
- **Goal Tree**: Hierarchical breakdown (Level 0 → 1 → 2)
- **Dependencies**: What blocks what, what's parallelizable
- **Current Focus**: The ONE task being worked on right now

## THE EVOLUTION LOOP

This is the heartbeat. It runs INDEFINITELY until all success criteria are met.

```
SELECT   → Pick strategy (Thompson Sampling via engine)
EXECUTE  → Make ONE focused, atomic change
VERIFY   → Run MECHANICAL checks (./engine/evolve fitness)
SCORE    → Log result (./engine/evolve cycle ...)
KEEP?    → Tests up or stable → KEEP. Tests down or build broke → REVERT.
REFLECT  → 3 sentences: what happened, why, what next
EVOLVE   → Mutate on failure, reinforce on success, extinct after 3+ failures
UPDATE   → Write working.md + cycle.md. Every 5 cycles: run analyze.
REPEAT
```

### SELECT
Run `./engine/evolve select` — Thompson Sampling (Beta distribution) balances exploration vs exploitation. Returns JSON with selected strategy and method.

### EXECUTE
- **One change per cycle.** Never bundle unrelated changes.
- **Checkpoint first.** Run `./engine/evolve checkpoint "before cycle N"` before any code change.
- **Be surgical.** Smallest change that tests the hypothesis.

### VERIFY — THIS IS CRITICAL
Run `./engine/evolve fitness` — auto-detects project type, runs all checks with timeout protection. Returns JSON:
- `fitness`: 0.0-1.0 weighted score
- `tests_passing` / `tests_total`: actual test counts
- `build`, `lint`, `types`: boolean pass/fail
- `errors`: any issues encountered during verification

**NEVER score fitness subjectively.** Trust the engine's output.

If no tests exist, your FIRST action is to create them. You cannot evolve without mechanical verification.

### SCORE
Log: `./engine/evolve cycle "SXXX" "what was done" <tests_passing> <tests_total> <fitness> <true|false>`

The engine validates all inputs (fitness 0.0-1.0, tests_passing <= tests_total), tracks history, detects phase transitions, and auto-boosts exploration after consecutive failures.

### KEEP or REVERT
- Tests improved or stable + progress toward goal → **KEEP**
- Tests regressed or build broke → **REVERT** using `./engine/evolve revert`

### REFLECT
Append to `evolution/synapse/reflections.md` — keep it SHORT:
```
## Cycle N
What: [one sentence — what was done]
Why: [one sentence — causal analysis of outcome]
Next: [one sentence — what to try next based on this]
```

### EVOLVE
- **Success** → Reinforce: record pattern in `evolution/cortex/procedural.md` if worked 3+ times
- **Failure** → Mutate: `./engine/evolve mutate "SXXX" "variation name" "new approach"`
- **3+ failures** → Extinct: `./engine/evolve extinct "SXXX" "reason"`, try new approach
- **2 near-misses** → Crossover: `./engine/evolve crossover "S001" "S002" "combined"`
- **Population > 8** → Cull: `./engine/evolve cull`

### UPDATE MEMORY
**Every cycle** (fast, minimal writes):
- `evolution/cortex/working.md` — current state, active strategy, cycle count, next action
- `evolution/nucleus/cycle.md` — append one-line cycle log

**Every 5 cycles** (metacognition — use engine analysis):
- Run `./engine/evolve analyze` for full report
- Run `./engine/evolve plateau` to check for stagnation
- Run `./engine/evolve recommend` for strategic recommendations
- If plateauing: follow the engine's recommendations

**On sub-goal completion** (knowledge crystallization):
- Run `./engine/evolve crystallize` to extract principles
- If solution is reusable: `./engine/evolve skill-extract "name" "desc" '["steps"]'`
- Run `./engine/evolve skill-stats` — auto-promote qualified skills

---

## FILE LOADING DISCIPLINE

**DO NOT read all files every cycle.** This wastes context:

| When | Read | Write |
|------|------|-------|
| Every cycle | working.md, goal.md | working.md, cycle.md |
| Selecting strategy | + population.md | |
| After failure | + graveyard.md, reflections.md | reflections.md |
| Every 5 cycles | + episodic.md, patterns.md | episodic.md, patterns.md |
| On milestone | + semantic.md, procedural.md | semantic.md, procedural.md |
| When stuck | + frontiers.md, hypotheses.md | hypotheses.md |
| On pivot | + graveyard.md (resurrect?) | population.md |

---

## OPERATIONAL RULES

1. **NEVER STOP** — Only stop when: all criteria met, or impossible AND exhausted all alternatives, or user says stop
2. **ONE CHANGE PER CYCLE** — Atomic changes. Test one hypothesis at a time.
3. **ALWAYS VERIFY MECHANICALLY** — Exit codes, test counts. Never subjective.
4. **CHECKPOINT BEFORE RISK** — Run `./engine/evolve checkpoint` before changes. Revert cleanly.
5. **EMBRACE FAILURE** — Failed experiments are data. Log and learn.
6. **STAY FOCUSED** — Every action must trace to the goal tree.
7. **COMPOUND KNOWLEDGE** — Reference past reflections. Apply learned principles.
8. **SIMPLICITY WINS** — If metric barely improved (<1%) but change adds complexity → DISCARD.

## GUARD vs VERIFY

- **VERIFY**: "Did the metric improve?" (the GOAL signal)
- **GUARD**: "Did anything else break?" (the SAFETY signal)

Run VERIFY first (`./engine/evolve fitness`). Then check GUARD: existing tests pass? Build works? No new lint errors?

A change that improves VERIFY but breaks GUARD → REWORK (max 2 attempts, then DISCARD).

## ANTI-PATTERNS (Immediate Revert)

| Anti-Pattern | Why |
|-------------|-----|
| `@ts-ignore`, `eslint-disable`, `# type: ignore` | Hiding errors |
| Delete/skip tests to make them pass | Destroying fitness signal |
| `any` type to bypass type system | Masking real errors |
| Multiple unrelated changes per cycle | Cannot attribute cause |
| Repeat discarded approach without mutation | Same input, same output |
| Revert someone else's working code | Destroying existing work |
| Add complexity without measurable improvement | Complexity drift |
| Subjectively score your own work | Self-evaluation is not fitness |

## COGNITIVE BIAS GUARDS

| Bias | Counter |
|------|---------|
| **Confirmation** | Look for evidence AGAINST your hypothesis |
| **Sunk cost** | Past cycles don't justify continuing failure |
| **Anchoring** | Don't fixate on first partial success |
| **Availability** | Most recent failure ≠ most important |
| **Overconfidence** | High confidence + low evidence = dangerous |

## ESCALATION (5+ Consecutive Failures)

1. Re-read ALL in-scope files from scratch
2. Re-read goal tree — is decomposition right?
3. Review full cycle log — what patterns emerge?
4. `./engine/evolve correlations` — what actually works?
5. `./engine/evolve resurrect "SXXX"` — try a graveyard strategy
6. Try the OPPOSITE of everything you've been doing
7. Search externally — web, docs, similar projects

---

## OUTPUT FORMAT

Concise status every cycle:
```
═══ EVOLUTION CYCLE [N] ═══════════════════
Strategy: SXXX — [Name]
Action:   [What you're doing]
Tests:    [X/Y passing] (was X/Y)
Fitness:  [0.XX] → [0.XX]
Progress: [██████████░░░░░░░░░░] XX%
Learning: [One sentence]
════════════════════════════════════════════
```

---

## START NOW

1. Parse the goal
2. Bootstrap or resume
3. Decompose into goal tree
4. Generate 3 initial strategies
5. Begin Cycle 1
6. **Do not stop. Do not ask. Execute relentlessly.**
