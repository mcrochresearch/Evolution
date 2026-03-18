# Fitness Function

> The soul of natural selection — how the agent measures progress.
> Without a fitness signal, evolution is random walk. With one, it's directed search.
> This file defines WHAT constitutes improvement and HOW to measure it.

## Fitness Dimensions

The overall fitness score is a weighted combination of multiple dimensions:

```
Fitness = Σ (weight_i * score_i) for each dimension i
```

### Default Dimensions

| Dimension | Weight | Measurement | Score Range |
|-----------|--------|-------------|-------------|
| **Correctness** | 0.35 | Tests passing / Total tests | 0.0 - 1.0 |
| **Completeness** | 0.25 | Success criteria met / Total criteria | 0.0 - 1.0 |
| **Quality** | 0.15 | Linter warnings (inverse), type safety | 0.0 - 1.0 |
| **Performance** | 0.10 | Build time, runtime benchmarks | 0.0 - 1.0 |
| **Simplicity** | 0.10 | Lines of code (less = better for same function) | 0.0 - 1.0 |
| **Robustness** | 0.05 | Edge cases handled, error recovery | 0.0 - 1.0 |

### Custom Dimensions
> Add goal-specific fitness dimensions here during initialization.

_None defined yet._

## Verification Commands

> These commands are run every cycle to compute fitness scores.
> Auto-detected from the project, or manually configured.

```bash
# Tests (auto-detect from project)
# npm test | pytest | cargo test | go test ./... | make test

# Linting (auto-detect)
# eslint . | ruff check | clippy | golangci-lint

# Type checking (auto-detect)
# tsc --noEmit | mypy . | cargo check

# Build (auto-detect)
# npm run build | cargo build | go build ./...

# Custom verification
# [User-defined commands]
```

## Fitness History

| Cycle | Correctness | Completeness | Quality | Performance | Simplicity | Robustness | **Total** |
|-------|-------------|-------------|---------|-------------|------------|------------|-----------|
| — | — | — | — | — | — | — | — |

## Fitness Trends

```
Fitness over time:
[No data yet — graph will be ASCII-rendered as data accumulates]
```

## Adaptive Fitness

The fitness function itself can evolve:
1. If a dimension is always maxed out, reduce its weight (it's no longer differentiating)
2. If a dimension is always zero, investigate if the measurement is broken
3. After goal decomposition, add custom dimensions specific to the sub-goals
4. Every 10 cycles, review if the weights still reflect what matters
