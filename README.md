# Evolution

**Set a goal. Walk away. Your AI thinks, learns, adapts, and evolves — relentlessly — until the goal is achieved.**

Evolution is an autonomous goal-directed skill framework for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and [OpenClaw](https://github.com/openclaw/openclaw). It transforms your AI agent from a tool that waits for instructions into an evolving intelligence that pursues objectives independently.

> *"The problem is simple — I don't want to have to direct my AI. I just want it to work relentlessly to its end goal."*

---

## How It Works

You give Evolution a goal. It does everything else.

```
You: /evolution Build a REST API with authentication, rate limiting, and full test coverage

Evolution: [works autonomously for hours]
  Cycle 1:  Scaffolded project structure          → fitness: 0.12
  Cycle 5:  Auth endpoints passing tests           → fitness: 0.35
  Cycle 12: Rate limiter implemented               → fitness: 0.58
  Cycle 18: Edge cases found and fixed via mutation → fitness: 0.71
  Cycle 25: Full test coverage achieved            → fitness: 0.94
  GOAL ACHIEVED.
```

No hand-holding. No "what should I do next?" No waiting for permission. Evolution decomposes the goal, generates competing strategies, executes the best ones, verifies results, learns from outcomes, evolves its approach, and repeats — drawing from 40 years of AI research.

---

## The Science Behind Evolution

Evolution isn't a prompt hack. It's a principled synthesis of the most powerful ideas from four decades of artificial intelligence:

| Concept | Origin | How Evolution Uses It |
|---------|--------|----------------------|
| **Genetic Algorithms** | Holland, 1975 | Strategies mutate, crossover, and compete; fittest survive |
| **Fitness Landscapes** | Wright, 1932 | Maps explored vs unexplored solution regions |
| **Reinforcement Learning** | Sutton & Barto, 1998 | Actions scored by outcomes; exploration balances exploitation |
| **Thompson Sampling** | Thompson, 1933 | Balances trying proven strategies vs uncertain new ones |
| **Meta-Learning** | Schmidhuber, 1987 | The system learns HOW to learn, improving its own process |
| **Cognitive Architecture** | Newell (SOAR), 1990 | Dual memory systems, production rules, chunking |
| **Bayesian Optimization** | Mockus, 1975 | Uncertainty-aware strategy selection |
| **Quality-Diversity** | Mouret & Clune, 2015 | Maintains diverse strategy species, prevents convergence |
| **Reflexion** | Shinn et al., 2023 | Verbal self-reflection as reinforcement signal |
| **Tree of Thoughts** | Yao et al., 2023 | Deliberate goal decomposition with backtracking |
| **Autoresearch** | Karpathy, 2025 | Autonomous modify → verify → keep/discard loops |
| **Stigmergy** | Grassé, 1959 | Cross-session knowledge trails (ant colony inspired) |
| **Active Learning** | Cohn et al., 1996 | Prioritizes actions by expected information gain |
| **Curriculum Learning** | Bengio et al., 2009 | Progressive difficulty, builds on prior success |

---

## Architecture

Evolution is built as a living biological system. Each subsystem has a clear responsibility:

```
evolution/
├── cortex/          MEMORY — The agent's brain
│   ├── episodic     Raw experiences (what happened)
│   ├── semantic     Distilled principles (what's true)
│   ├── procedural   Proven recipes (how to do things)
│   └── working      Current consciousness (what's happening now)
│
├── genome/          STRATEGY DNA — Competing approaches
│   ├── population   Active strategies with fitness scores
│   ├── graveyard    Extinct strategies (negative knowledge)
│   ├── mutations    Genetic operation log
│   └── hall-of-fame Elite strategies preserved forever
│
├── helix/           FITNESS — Natural selection engine
│   ├── fitness      Multi-dimensional scoring rubric
│   ├── rewards      Reinforcement signal history
│   └── landscape    Map of explored solution space
│
├── nucleus/         EXECUTION — The autonomous loop
│   ├── goal         Decomposed goal tree (north star)
│   ├── cycle        Cycle state and history
│   ├── queue        Prioritized action queue
│   └── checkpoints  Reversibility safety net
│
├── synapse/         METACOGNITION — Learning about learning
│   ├── reflections  Post-action self-analysis
│   ├── patterns     Meta-patterns discovered
│   ├── blind-spots  Known unknowns
│   └── evolution-rate  Learning velocity tracking
│
└── dendrite/        EXPLORATION — Scientific method
    ├── hypotheses   Active hypotheses being tested
    ├── experiments  Structured experiment log
    ├── frontiers    Edges of explored territory
    └── info-gain    Highest-value questions to answer
```

---

## The Evolution Loop

The core autonomous cycle runs indefinitely:

```
SELECT   →  Pick the best strategy (Thompson Sampling)
EXECUTE  →  Make ONE focused, atomic change
VERIFY   →  Run automated tests/checks
SCORE    →  Evaluate fitness delta
KEEP?    →  Keep improvements, revert regressions
REFLECT  →  Analyze why it worked or didn't (Reflexion)
EVOLVE   →  Mutate/crossover strategies (Genetic Algorithms)
UPDATE   →  Persist to memory (Stigmergy)
REPEAT   →  Next cycle
```

Every 5 cycles, the **Metacognition Engine** activates — analyzing patterns across reflections, detecting blind spots, tracking learning velocity, and adjusting the exploration/exploitation balance.

---

## Installation

### Claude Code

```bash
# Clone into your project
git clone https://github.com/mcrochresearch/Evolution.git

# Copy the skill files
cp -r Evolution/.claude/skills/ your-project/.claude/skills/

# Copy the runtime directory
cp -r Evolution/evolution/ your-project/evolution/
```

Then in Claude Code:
```
/evolution Build a real-time chat system with WebSocket support and message persistence
```

### OpenClaw

```bash
# Copy the openclaw workspace files
cp -r Evolution/openclaw/* your-openclaw-workspace/

# Copy the evolution runtime
cp -r Evolution/evolution/ your-openclaw-workspace/evolution/
```

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/evolution [goal]` | Start autonomous evolution toward a goal |
| `/evolve-status` | Show the evolution dashboard |
| `/evolve-reflect` | Force a reflection and metacognition cycle |
| `/evolve-pivot` | Kill current strategy, explore radically different approaches |

---

## What Makes Evolution Different

### vs. Regular AI Coding Assistants
Regular assistants wait for your next instruction. Evolution **figures out** the next instruction itself, executes it, verifies it, and keeps going.

### vs. Autoresearch (Karpathy)
Autoresearch runs a fixed loop on ML training. Evolution generalizes this to **any goal**, adds **strategy evolution**, **persistent memory**, **metacognition**, and **hypothesis-driven exploration**.

### vs. Simple Loops / Retries
Simple retry loops repeat the same approach. Evolution **learns from failures**, **mutates strategies**, **maintains diversity**, and **gets smarter over time**. It does not repeat mistakes.

### vs. Static Skills
Static skills are frozen playbooks. Evolution's skill files are **living documents** that grow with experience. The agent at Cycle 50 has fundamentally different knowledge than at Cycle 1.

---

## The Key Insight

Most AI agent frameworks treat the agent as a stateless function: input → output → forget. Evolution treats the agent as a **living system** with:

- **Memory** that persists and compounds across sessions
- **Strategies** that compete, evolve, and improve through natural selection
- **Self-awareness** that detects stagnation, blind spots, and learning velocity
- **Scientific method** that generates and tests hypotheses, not just random actions
- **Collective intelligence** where each session leaves trails that make future sessions smarter

The result: an AI that doesn't just execute tasks — it **thinks**, **learns**, **adapts**, and **evolves**.

---

## Contributing

Evolution is open source. We welcome contributions that make the framework more powerful:

- New fitness dimensions for specific domains
- Better mutation operators for strategy evolution
- Integration with additional AI platforms beyond Claude Code and OpenClaw
- Empirical studies of Evolution's performance on real-world tasks

---

## License

MIT

---

*Built by studying the giants: Karpathy's autoresearch, OpenClaw's workspace system, Anthropic's official skill patterns, and 40 years of AI/ML research. Evolution stands on their shoulders.*
