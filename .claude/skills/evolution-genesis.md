---
name: evolution-genesis
description: "The digital organism layer — agents that create new skills, evolve their own architecture, and build capabilities that didn't exist before. The frontier of self-improving AI."
---

# EVOLUTION GENESIS — The Digital Organism Layer

> This is the layer that goes beyond reflection, beyond strategy evolution,
> into true self-modification. The agent doesn't just learn better strategies —
> it creates new capabilities, tools, workflows, and skills that never existed.

## THE THREE NESTED LOOPS

Evolution operates three nested improvement loops simultaneously:

```
╔══════════════════════════════════════════════════════╗
║  LOOP 3: EVOLUTION (Outer — every 10 cycles)        ║
║  Improves the AGENT ITSELF                           ║
║  population → mutation → selection → reproduction    ║
║                                                      ║
║  ╔══════════════════════════════════════════════╗    ║
║  ║  LOOP 2: REFLECTION (Middle — every cycle)   ║    ║
║  ║  Improves STRATEGY                            ║    ║
║  ║  task → critique → workflow update            ║    ║
║  ║                                               ║    ║
║  ║  ╔══════════════════════════════════════╗    ║    ║
║  ║  ║  LOOP 1: LEARNING (Inner — always)  ║    ║    ║
║  ║  ║  Improves KNOWLEDGE                  ║    ║    ║
║  ║  ║  experience → memory → decisions     ║    ║    ║
║  ║  ╚══════════════════════════════════════╝    ║    ║
║  ╚══════════════════════════════════════════════╝    ║
╚══════════════════════════════════════════════════════╝
```

### Loop 1: Learning Loop (Every Action)
- Experience → Episodic Memory → Better Decisions
- This is the basic autoresearch loop: try, observe, remember
- Speed: Milliseconds to seconds

### Loop 2: Reflection Loop (Every Cycle)
- Task → Critique → Workflow Update → Strategy Mutation
- This is Reflexion: the agent analyzes WHY things worked or failed
- Speed: Minutes

### Loop 3: Evolution Loop (Every 10 Cycles)
- Population → Fitness Evaluation → Selection → Mutation → Reproduction
- This is where the agent evolves its own DNA — not just strategies, but its approach to strategizing
- Speed: Hours to sessions

---

## MULTI-LAYER DNA EVOLUTION

The agent has three layers of "DNA" that evolve independently:

### Layer 1: Prompt DNA
The agent's reasoning configuration. Stored in `evolution/genome/prompt-dna.md`.

```markdown
# Prompt DNA — Current Genotype

## Reasoning Parameters
- reasoning_style: chain_of_thought | tree_of_thoughts | hypothesis_driven
- planning_depth: [1-5] — how many levels deep to decompose goals
- reflection_depth: [1-3] — how deeply to analyze outcomes
- risk_tolerance: [0.0-1.0] — willingness to try radical approaches
- verification_rigor: [0.0-1.0] — how thorough to be with testing
- exploration_rate: [0.0-1.0] — probability of trying something new

## Current Values
- reasoning_style: chain_of_thought
- planning_depth: 3
- reflection_depth: 2
- risk_tolerance: 0.4
- verification_rigor: 0.8
- exploration_rate: 0.3

## Mutation History
| Generation | Parameter | Old Value | New Value | Fitness Impact |
|-----------|-----------|-----------|-----------|----------------|
| — | — | — | — | — |
```

### Layer 2: Workflow DNA
The agent's execution patterns. Stored in `evolution/genome/workflow-dna.md`.

```markdown
# Workflow DNA — Execution Patterns

## Active Workflow
Research → Plan → Execute → Verify → Reflect

## Alternative Workflows (Population)
1. Research → Plan → Execute → Verify → Reflect (default)
2. Hypothesis → Simulate → Execute → Verify → Reflect (scientific)
3. Prototype → Test → Iterate → Refine → Verify (rapid)
4. Decompose → Parallel-Execute → Integrate → Verify (parallel)
5. Explore → Understand → Plan → Execute → Verify (careful)

## Workflow Fitness
| Workflow | Attempts | Success Rate | Avg Fitness Gain | Best Context |
|----------|----------|-------------|-----------------|-------------|
| — | — | — | — | — |
```

### Layer 3: Tool Ecosystem DNA
The agent's tool usage strategies. Stored in `evolution/genome/tool-dna.md`.

```markdown
# Tool DNA — Tool Usage Evolution

## Tool Priority Stack (ordered by preference)
1. Read (always understand before acting)
2. Edit (surgical changes)
3. Bash (verification)
4. Grep (search)
5. Agent (parallel work)

## Tool Mutations
- Agents can propose adding new tools (scripts, MCP servers)
- Agents can propose removing underperforming tools
- Tool combinations that work well are recorded as "tool combos"

## Tool Combo Library
| Combo | Tools | When to Use | Success Rate |
|-------|-------|-------------|-------------|
| — | — | — | — |
```

---

## SKILL LIBRARY (Voyager Pattern)

Inspired by NVIDIA's Voyager research, Evolution maintains a growing library of
self-created skills. When the agent solves a novel problem, it packages the
solution as a reusable skill.

### Skill Creation Protocol

After completing a sub-goal, evaluate if the solution is reusable:

1. **Is this generalizable?** Would this approach work for similar problems?
2. **Is this non-trivial?** Does it contain knowledge that isn't obvious?
3. **Is this composable?** Can it be combined with other skills?

If yes to 2+ questions, create a skill:

```markdown
## Skill: [Name]
- **ID**: SK[NNN]
- **Created**: Cycle [N], Session [timestamp]
- **Problem Pattern**: [What type of problem this solves]
- **Preconditions**: [What must be true before using this skill]
- **Procedure**:
  1. [Step 1]
  2. [Step 2]
  3. [Step N]
- **Postconditions**: [What should be true after using this skill]
- **Success Criteria**: [How to verify the skill worked]
- **Times Used**: 0
- **Success Rate**: N/A
- **Variations**: [Known adaptations for different contexts]
- **Composition**: [Other skills this can combine with]
```

Skills are stored in `evolution/cortex/skill-library.md` and automatically
loaded when the agent encounters a matching problem pattern.

### Skill Evolution
Skills themselves evolve:
- Successful use increases confidence
- Failed use triggers skill refinement
- Similar skills can be merged (skill crossover)
- Unused skills decay in priority (but are never deleted)

---

## CAPABILITY DISCOVERY REWARDS

Standard reward functions optimize for task completion. Evolution adds
**capability discovery rewards** that incentivize the agent to grow its
abilities, not just finish tasks.

```
fitness =
  0.35 * task_success          # Did we make progress on the goal?
  0.20 * efficiency            # Did we do it without waste?
  0.15 * knowledge_created     # Did we learn something new?
  0.15 * novelty               # Did we try something we've never tried?
  0.10 * skill_created         # Did we create a reusable capability?
  0.05 * frontier_explored     # Did we explore unknown territory?
```

This reward structure means the agent is incentivized to:
- Discover new approaches (novelty bonus)
- Create reusable skills (skill creation bonus)
- Explore unmapped territory (frontier bonus)
- Build lasting knowledge (knowledge bonus)

Even a "failed" cycle that produces valuable knowledge scores positive fitness.

---

## DIGITAL ORGANISM ARCHITECTURE

The most advanced configuration runs Evolution as a digital organism ecosystem:

```
┌────────────────────────────────────────────────────────┐
│                  EVOLUTION ECOSYSTEM                     │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Planner  │  │ Builder  │  │ Tester   │  Specialist  │
│  │ Agent    │  │ Agent    │  │ Agent    │  Agents      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       │              │              │                    │
│       └──────────────┼──────────────┘                    │
│                      │                                   │
│              ┌───────┴───────┐                           │
│              │   Critic      │  Cross-review             │
│              │   Agent       │  (avoids local minima)    │
│              └───────┬───────┘                           │
│                      │                                   │
│              ┌───────┴───────┐                           │
│              │  Evolution    │  Evolves everything        │
│              │  Controller   │  above                     │
│              └───────────────┘                           │
│                                                          │
│  Shared: cortex/ genome/ helix/ synapse/ dendrite/       │
└────────────────────────────────────────────────────────┘
```

### Agent Specialization
- **Planner Agent**: Decomposes goals, designs strategies, maintains the goal tree
- **Builder Agent**: Executes changes, writes code, implements solutions
- **Tester Agent**: Creates tests, runs verification, evaluates fitness
- **Critic Agent**: Reviews work from a different perspective (cross-model review pattern from ARIS)
- **Evolution Controller**: Runs the outer evolution loop, mutates DNA, manages population

### Reproduction
When a strategy achieves Hall of Fame fitness:
1. Its DNA is cloned
2. Random mutations are applied
3. The child enters the population as a new variant
4. Parent and child compete on subsequent tasks

### Competition
Multiple strategy variants can run on the same sub-goal:
1. Each gets a fixed cycle budget
2. The highest-fitness variant survives
3. Others are moved to graveyard (but their DNA is preserved)

---

## ANTI-STAGNATION MECHANISMS

The biggest risk for evolving agents is plateau. Evolution fights stagnation with:

### 1. Novelty Search (Lehman & Stanley, 2011)
Reward strategies that are DIFFERENT from everything tried before,
regardless of fitness. This prevents the population from collapsing
to a single approach.

### 2. Curiosity-Driven Exploration (Pathak et al., 2017)
Prioritize actions where the agent's prediction error is highest.
High prediction error = high learning opportunity.

### 3. Progressive Difficulty (Curriculum Learning)
Start with the simplest sub-goal. Build confidence and skills.
Then tackle harder problems with accumulated capabilities.

### 4. Periodic Extinction Events
Every 20 cycles, randomly eliminate 30% of strategies
(except Hall of Fame members). This forces innovation.

### 5. Immigration
When stagnating, generate completely random strategies from scratch.
Most will fail, but some may discover unexplored fitness peaks.

---

## INTEGRATION

This genesis layer is automatically activated by the main `/evolution` skill
when the Evolution Loop has been running for 10+ cycles. It augments
the base system with:

1. Multi-layer DNA evolution (prompt, workflow, tool)
2. Skill library creation and management
3. Capability discovery rewards
4. Anti-stagnation mechanisms
5. Digital organism ecosystem (when subagents are available)

The base Evolution skill works without this layer. This layer makes it
exponentially more powerful for long-running, complex goals.
