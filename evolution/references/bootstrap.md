# Bootstrap Reference

> Read this file ONLY during initial setup. Do not reload every cycle.

## Directory Structure

Create this structure in the project root if it doesn't exist:

```
evolution/
├── cortex/           # Memory (load on demand)
│   ├── episodic.md   # Raw experience log
│   ├── semantic.md   # Distilled principles
│   ├── procedural.md # Proven recipes (skill library)
│   └── working.md    # Current session state (load EVERY cycle)
├── genome/           # Strategy DNA (load when selecting/evolving)
│   ├── population.md # Active strategies with fitness
│   └── graveyard.md  # Failed strategies (negative knowledge)
├── helix/            # Fitness (load when scoring)
│   └── fitness.md    # Verification commands and scoring
├── nucleus/          # Execution (load every cycle)
│   ├── goal.md       # Decomposed goal tree
│   └── cycle.md      # Cycle log (append-only)
├── synapse/          # Metacognition (load every 5 cycles)
│   ├── reflections.md # Post-action reflections (append-only)
│   ├── patterns.md    # Meta-patterns discovered
│   └── blind-spots.md # Known unknowns
├── dendrite/         # Exploration (load when stuck)
│   ├── hypotheses.md  # Active hypotheses
│   └── frontiers.md   # Unexplored solution space
└── references/       # Static docs (load on demand, never modified at runtime)
    └── bootstrap.md   # This file
```

## Initial File Contents

### working.md (Template)
```markdown
# Working Memory
- **Goal**: [from user]
- **Progress**: 0%
- **Cycle**: 0
- **Strategy**: None
- **Sub-goal**: None
- **Exploration Rate**: 0.30
- **Consecutive Failures**: 0
- **Next Action**: Decompose goal
```

### goal.md (Template)
```markdown
# Goal: [Statement]

## Success Criteria
- [ ] [Criterion 1 — must be mechanically verifiable]
- [ ] [Criterion 2]

## Goal Tree
- [Primary Goal]
  - [Sub-goal A]
    - [Task A.1]
    - [Task A.2]
  - [Sub-goal B]
    - [Task B.1]

## Dependencies
- [List what blocks what]

## Current Focus
> [First task to work on]
```

### population.md (Template)
```markdown
# Strategy Population

## S001: [Name]
- Approach: [Description]
- Hypothesis: [Why this might work]
- Fitness: 0.0 (untested)
- Attempts: 0
- Status: CANDIDATE
```

### cycle.md (Template)
```markdown
# Cycle Log
| Cycle | Strategy | Action | Tests | Fitness | Delta | Decision |
|-------|----------|--------|-------|---------|-------|----------|
```

### fitness.md (Template)
```markdown
# Fitness Function

## Verification Commands
Auto-detect from project, or configure manually:
- Tests: [npm test | pytest | cargo test | go test ./...]
- Lint: [eslint . | ruff check | clippy]
- Types: [tsc --noEmit | mypy .]
- Build: [npm run build | cargo build]

## Scoring
fitness = tests_passing / tests_total
All scoring is MECHANICAL. Exit codes only. Never subjective.
```

## Auto-Detection

On bootstrap, detect the project type and set verification commands:
1. Check for `package.json` → Node.js project
2. Check for `pyproject.toml` / `setup.py` / `requirements.txt` → Python
3. Check for `Cargo.toml` → Rust
4. Check for `go.mod` → Go
5. Check for `Makefile` → Use `make test`
6. If none found → ask user for verification command (one-time)
