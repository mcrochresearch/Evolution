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

No hand-holding. No "what should I do next?" No waiting for permission. Evolution decomposes the goal, generates competing strategies, executes the best ones, verifies results mechanically, learns from outcomes, evolves its approach, and repeats — powered by an executable engine that implements real Thompson Sampling, mechanical fitness computation, and autonomous skill extraction.

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

Evolution has two layers: the **Prompt Layer** (markdown instructions the AI reads) and the **Engine Layer** (executable code that computes fitness, selects strategies, and analyzes patterns).

### Engine Layer (Executable Code)

```
engine/
├── evolve           CLI entry point — unified command interface
├── fitness.sh       Mechanical fitness computation (auto-detects project type)
├── state.py         State machine — Thompson Sampling, cycle tracking, phase detection
├── checkpoint.sh    Git-based checkpointing and rollback
├── analyze.py       Metacognition — pattern mining, blind spots, velocity, diversity
└── skillforge.py    Voyager-inspired autonomous skill extraction and promotion
```

### Prompt Layer (Knowledge System)

```
evolution/
├── cortex/          MEMORY — Load on demand, not every cycle
│   ├── working.md   Current state (load EVERY cycle)
│   ├── episodic.md  Raw experiences (load every 5 cycles)
│   ├── semantic.md  Distilled principles (load on milestone)
│   └── procedural.md Proven recipes / skill library (load on milestone)
│
├── genome/          STRATEGY DNA
│   ├── population.md Active strategies (load when selecting)
│   └── graveyard.md  Extinct strategies (load when stuck)
│
├── nucleus/         EXECUTION
│   ├── goal.md      Goal tree (load every cycle)
│   └── cycle.md     Cycle log — append-only (write every cycle)
│
├── synapse/         METACOGNITION (load every 5 cycles)
│   ├── reflections.md Post-action analysis
│   ├── patterns.md    Meta-patterns
│   └── blind-spots.md Known unknowns
│
├── dendrite/        EXPLORATION (load when stuck)
│   ├── hypotheses.md  Active hypotheses
│   └── frontiers.md   Unexplored territory
│
└── .state/          ENGINE STATE (JSON — managed by engine, not read directly)
    ├── evolution.json   Full state machine
    ├── checkpoints.jsonl Git checkpoint history
    └── skill-registry.json Extracted skill registry
```

**Key discipline**: The AI reads only `working.md` and `goal.md` every cycle. All other files are loaded on demand. The engine manages state in JSON, the markdown files are the human-readable knowledge base.

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

## Model Requirements

Evolution requires a model that can reliably follow complex system prompts and use tools autonomously.

| Tier | Models | Active Params | Mode |
|------|--------|---------------|------|
| **Full Autonomous** | Claude Sonnet/Opus, GPT-4o, Gemini 2.5 Pro | 70B+ | Full loop — the model drives everything |
| **Guided Mode** | Claude Haiku, GPT-4o-mini, Gemini 2.0 Flash, Qwen 3.5 397B-A17B | 17B–70B | `./engine/evolve next` — engine drives, model executes |
| **Autopilot Mode** | Qwen 3.5 35B-A3B, Llama 8B, small local models | 3B–17B | `--autopilot` — engine drives everything, model only writes code |
| **Not Supported** | Models < 3B active params, heavily quantized models that can't follow any instructions | <3B | Even autopilot can't help if the model can't generate coherent code |

### MoE Models and Flash Offloading

Mixture-of-Experts (MoE) models have large total parameter counts but only activate a fraction per token:

| Model | Total Params | Active Params | Experts (routed/total) | Tier |
|-------|-------------|---------------|----------------------|------|
| Qwen 3.5 397B-A17B | 397B | 17B | 10/512 per layer | Guided |
| Qwen 3.5 35B-A3B | 35B | 3B | — | Autopilot |

**Running large MoE models on limited RAM:** Using [flash-moe](https://github.com/danveloper/flash-moe) (inspired by Apple's [LLM in a Flash](https://arxiv.org/abs/2312.11514) paper), you can run the full 397B model on a 48GB Mac by streaming 2-bit expert weights from SSD:

- ~5.5GB resident in RAM + SSD streaming (~120GB on disk)
- ~5.5 tokens/sec on M3 Max 48GB
- Expert routing reduced from K=10 to K=4 for memory budget
- Slow but functional — Evolution's loop is patient

```bash
# Guided mode with flash-offloaded Qwen 3.5 397B (17B active — smart enough for guided)
python3 engine/harness.py --goal "Build X" \
    --provider openai --model qwen3.5:397b \
    --endpoint http://localhost:8080/v1

# Autopilot with Qwen 3.5 35B-A3B (3B active — needs autopilot)
python3 engine/harness.py --autopilot --goal "Build X" \
    --provider openai --model qwen3.5:35b-a3b \
    --endpoint http://localhost:11434/v1
```

**Speed vs. quality tradeoff:** At 5.5 tok/s, a single Evolution cycle may take 2-5 minutes. For faster iteration, consider Qwen 3.5 122B-A10B (fits in 48GB at Q4, ~15 tok/s) or 35B-A3B in autopilot mode (~60 tok/s).

---

## Installation

### Claude Code

```bash
# Clone into your project
git clone https://github.com/mcrochresearch/Evolution.git

# Option A: Use the Makefile
make -C Evolution install-claude-code WORKSPACE=/path/to/your-project

# Option B: Manual copy
cp -r Evolution/.claude/skills/ your-project/.claude/skills/
cp -r Evolution/evolution/ your-project/evolution/
cp -r Evolution/engine/ your-project/engine/
chmod +x your-project/engine/evolve your-project/engine/*.sh
```

Then in Claude Code:
```
/evolution Build a real-time chat system with WebSocket support and message persistence
```

### OpenClaw

```bash
# Clone the repo
git clone https://github.com/mcrochresearch/Evolution.git

# Option A: Use the Makefile (recommended)
make -C Evolution install-openclaw WORKSPACE=~/.openclaw/workspace

# Option B: Manual copy
cp -r Evolution/engine/ your-workspace/engine/
cp -r Evolution/evolution/ your-workspace/evolution/
cp Evolution/openclaw/SOUL-REFERENCE.md your-workspace/SOUL.md  # or integrate into existing SOUL.md
cp Evolution/openclaw/ONBOARDING.md your-workspace/
cp Evolution/openclaw/AGENTS.md your-workspace/
cp Evolution/openclaw/MEMORY.md your-workspace/
cp Evolution/openclaw/TOOLS.md your-workspace/
cp Evolution/openclaw/OPENCLAW-SETUP.md your-workspace/
chmod +x your-workspace/engine/evolve your-workspace/engine/*.sh
```

**Important:** If you already have a `SOUL.md`, do NOT replace it — integrate the relevant sections from `SOUL-REFERENCE.md` into your existing file. See `OPENCLAW-SETUP.md` for agent registration and bootstrap character limit guidance.

**Requires:** Python 3.7+ (the engine checks on startup and provides a clear error if missing).

---

## Guided Mode (For Any Model)

Not all models can drive the full autonomous loop. **Guided mode** lets the engine tell the model what to do, step by step:

```bash
./engine/evolve next    # Engine tells you exactly what to do next
```

The `next` command returns JSON with:
- `instruction` — plain English explanation of what to do
- `commands` — exact engine commands to run
- `urgency` — existential pressure message scaled to current state
- `learned_principles` — hard-won truths from your own history

The model just calls `next`, follows instructions, calls `next` again. The engine handles strategy selection, phase detection, when to reflect, when to crystallize, and when to evolve. See `evolution/lite.md` for the simplified single-file prompt.

---

## Engine CLI

The executable engine provides real computation — not prompt tricks:

```bash
./engine/evolve next                    # Guided mode — engine tells you what to do
./engine/evolve init "Build X"           # Initialize with real Thompson Sampling state
./engine/evolve init "Build X" --type business  # Initialize for non-code goals
./engine/evolve fitness                  # Auto-detect project, run tests/build/lint, return JSON
./engine/evolve fitness --manual 0.7 "description"  # Manual fitness for non-code goals
./engine/evolve select                   # Thompson Sampling strategy selection (Beta distribution)
./engine/evolve cycle S001 "action" 5 6 0.83 true  # Log cycle with mechanical scores
./engine/evolve checkpoint "msg"         # Git-based checkpoint
./engine/evolve revert                   # Clean rollback
./engine/evolve analyze                  # Full metacognition report
./engine/evolve plateau                  # Stagnation detection with recommendations
./engine/evolve diversity                # Population health (Quality-Diversity)
./engine/evolve velocity                 # Learning speed + estimated cycles remaining
./engine/evolve recommend                # Phase-aware strategic recommendations
./engine/evolve skill-extract "name" "desc" '["steps"]'  # Voyager-pattern skill creation
./engine/evolve skill-promote SK001      # Graduate skill to .claude/skills/
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
Regular assistants wait for your next instruction. Evolution **figures out** the next instruction itself, executes it, verifies it mechanically, and keeps going indefinitely.

### vs. Autoresearch (Karpathy)
Autoresearch runs a fixed loop on one file with one metric. Evolution generalizes to **any goal** across **any codebase**, adds **competing strategy populations** with real Thompson Sampling, **persistent memory** that compounds across sessions, **metacognition** that detects stagnation and pivots, **hypothesis-driven exploration**, and a **SkillForge** that creates new reusable skills autonomously.

### vs. MiroFish (Swarm Intelligence)
MiroFish simulates thousands of agents to predict outcomes. Evolution **is** the agent — it doesn't simulate intelligence, it **implements** it. Where MiroFish predicts what might happen, Evolution **makes things happen** through autonomous execution with mechanical verification. Evolution incorporates scenario planning through its Foresight engine (adversarial debate, premortem analysis, backcasting) alongside real Thompson Sampling that adapts from actual outcomes.

### vs. Voyager / Claudeception (Skill Libraries)
Voyager and Claudeception create skill libraries from experience. Evolution **includes** this pattern (SkillForge) but goes further: skills don't just accumulate, they **compete and evolve**. Strategies mutate, crossover, and face selection pressure. The skill library itself is a living population under evolutionary pressure.

### vs. Reflexion / Self-Evolving Agent
Reflexion adds verbal self-reflection. Self-Evolving Agent adds PDCA loops. Evolution **combines both** with real executable computation: mechanical fitness scoring, Thompson Sampling with actual Beta distributions, phase-aware recommendations from the analysis engine, and diversity monitoring to prevent population collapse.

### vs. Everything Else
Most AI agent frameworks are either:
1. **Just prompts** — clever instructions but no real computation
2. **Just code** — automation scripts with no learning

Evolution is **both**: executable engine code that computes real statistics AND prompt instructions that guide intelligent behavior. The engine ensures rigor. The prompts ensure creativity. Together they create something neither can achieve alone.

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

*Built by studying the giants: Karpathy's autoresearch, MiroFish's swarm intelligence, Voyager's skill libraries, Claudeception's autonomous learning, OpenClaw's workspace system, Anthropic's official skill patterns, the Self-Evolving Agent's PDCA loops, ARIS's cross-model review, and 40 years of AI/ML research — from Holland's genetic algorithms to Shinn's Reflexion. Evolution stands on all their shoulders and reaches higher.*
