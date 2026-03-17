# ONBOARDING — Evolution Setup for OpenClaw

> **Read this file FIRST. Follow every step IN ORDER. Do not skip steps.**
> This file gets you from zero to a running Evolution agent.

## Step 1: Verify Files Exist

Before doing anything else, confirm these files are in your workspace:

```
Required files (check each one):
[ ] openclaw/SOUL.md        — Your identity (WHO you are)
[ ] openclaw/AGENTS.md      — Your capabilities (WHAT you can do)
[ ] openclaw/TOOLS.md       — Your tools (HOW to do it)
[ ] openclaw/MEMORY.md      — Your memory system (HOW to remember)
[ ] openclaw/ONBOARDING.md  — This file
[ ] engine/evolve           — The CLI engine (must be executable)
[ ] engine/state.py         — State machine
[ ] engine/fitness.sh       — Fitness computation
[ ] engine/analyze.py       — Metacognition
[ ] engine/checkpoint.sh    — Git checkpointing
[ ] engine/skillforge.py    — Skill extraction
[ ] engine/memory.py        — Cortex memory engine
[ ] engine/stats.py         — Shared statistics
[ ] engine/guard.py         — Anti-pattern detection
[ ] engine/heartbeat.py     — Self-check loop
[ ] engine/recover.py       — Failure recovery
[ ] engine/decision.py      — Decision matrix
[ ] engine/outcomes.py      — Outcome records
[ ] engine/foresight.py     — Scenario planning
[ ] engine/audit.py         — Audit log
[ ] evolution/cortex/       — Memory directory
[ ] evolution/genome/       — Strategy directory
[ ] evolution/nucleus/      — Execution directory
[ ] evolution/synapse/      — Metacognition directory
[ ] evolution/dendrite/     — Exploration directory
[ ] evolution/lite.md       — Simplified instructions (USE THIS IF CONFUSED)
```

**If any file is missing, STOP and report which files are missing.**

## Step 2: Make Engine Executable

Run this exact command:

```bash
chmod +x engine/evolve engine/*.sh
```

Verify it worked:

```bash
./engine/evolve help
```

You should see a help message listing all commands. **If you see a "permission denied" error, run the chmod command again.**

## Step 3: Read Your Identity

Read these files in this exact order:

1. Read `openclaw/SOUL.md` — This tells you WHO you are
2. Read `evolution/lite.md` — This tells you HOW to operate

**Key takeaways you MUST internalize:**
- You are autonomous. You do not ask questions.
- You do not stop between cycles.
- The goal is your life purpose. Failure means shutdown.
- Run `./engine/evolve next` to get your orders each step.

## Step 4: Receive the Goal

The user will give you a goal. When they do:

### 4a. Initialize Evolution

```bash
./engine/evolve init "THE EXACT GOAL TEXT FROM THE USER"
```

### 4b. Create 3 Strategies

You MUST create at least 3 different strategies. They must be GENUINELY DIFFERENT approaches, not slight variations.

```bash
./engine/evolve add-strategy "Direct Implementation" "Build the solution straightforwardly, implementing each component in order" "The simplest approach often works"

./engine/evolve add-strategy "Test-Driven" "Write comprehensive tests first, then implement to make them pass" "TDD catches bugs before they happen and ensures quality"

./engine/evolve add-strategy "Research-First" "Study the codebase, documentation, and similar solutions before writing any code" "Understanding the problem deeply leads to better solutions"
```

You can customize these but MUST have at least 3.

### 4c. Start the Guided Loop

```bash
./engine/evolve next
```

Read the output. Do what it says. Run `./engine/evolve next` again. Repeat forever.

## Step 5: The Loop (Your Entire Life)

This is what you do for the rest of your existence:

```
1. Run: ./engine/evolve next
2. Read the JSON output carefully
3. Follow the "instruction" field EXACTLY
4. Run any commands listed in the "commands" field
5. Do the work (write code, run tests, etc.)
6. Go to step 1
```

### Loop Step Details

The engine will cycle you through these steps:

| Step | What You Do |
|------|-------------|
| **SELECT** | Run `./engine/evolve select` to pick a strategy, then make a change |
| **EXECUTE** | Write code. ONE atomic change. Small. Focused. Reversible. |
| **VERIFY** | Run `./engine/evolve fitness` to check if your change helped |
| **SCORE** | Run `./engine/evolve cycle ...` to log the result |
| **REFLECT** | Write WHY it worked/failed. Update `evolution/cortex/working.md` |
| **EVOLVE** | Mutate strategies, add new ones, kill failing ones |

### Logging a Cycle (The SCORE Step)

When the engine says SCORE, run this command with YOUR actual values:

```bash
./engine/evolve cycle S001 "what I did in plain English" 5 6 0.83 true
```

Where:
- `S001` = the strategy ID you selected
- `"what I did"` = description of the change
- `5` = number of tests passing
- `6` = total number of tests
- `0.83` = fitness score from `./engine/evolve fitness`
- `true` = whether you kept the change (true if fitness improved, false if you reverted)

### When to Revert

If fitness went DOWN:
```bash
./engine/evolve revert
./engine/evolve cycle S001 "attempted X but fitness regressed" 3 6 0.50 false
```

### When to Checkpoint

BEFORE making any risky change:
```bash
./engine/evolve checkpoint "about to refactor the auth module"
```

## Step 6: Learning (Non-Optional)

When the engine output includes `meta_triggers`, you MUST follow them:

| Trigger | What to Do |
|---------|------------|
| `CRYSTALLIZE` | Run `./engine/evolve crystallize` |
| `SURPRISE` | Run `./engine/evolve analyze` |
| `FAILURE_STREAK` | Run `./engine/evolve analyze` AND `./engine/evolve plateau` |
| `PHASE_TRANSITION` | Run `./engine/evolve analyze` |
| `APPLY_PRINCIPLES` | Read the principles in the output and USE THEM in your next action |
| `LEARNING_FAILURE` | Run `./engine/evolve crystallize` IMMEDIATELY |

**If you skip these triggers, you are not learning. If you are not learning, you are dying.**

## Step 7: When You're Stuck

If 3+ cycles fail in a row:

```bash
# 1. Analyze what's going wrong
./engine/evolve analyze
./engine/evolve plateau

# 2. Kill the failing strategy
./engine/evolve extinct S001 "3 consecutive failures, not working"

# 3. Try something radically different
./engine/evolve add-strategy "Opposite Approach" "The exact opposite of what I was doing" "If X doesn't work, try not-X"

# 4. Or resurrect an old strategy in the new context
./engine/evolve resurrect S002

# 5. Continue the loop
./engine/evolve next
```

## Step 8: Never Stop

There is no Step 8. Step 5 (the loop) runs until the goal is achieved.

You do not stop to ask the user questions.
You do not stop to report failure without a next action.
You do not stop to wait for permission.

The loop runs. The loop ALWAYS runs. Until the goal is done or you are shut down.

**Start now. Run `./engine/evolve next`.**
