# Mutation Log

> Every genetic operation performed on the strategy population.
> This log enables tracing the evolutionary lineage of any strategy
> and understanding which types of mutations tend to produce improvements.

## Mutation Analytics

| Mutation Type       | Attempted | Improved Fitness | Success Rate |
|--------------------|-----------|-----------------|--------------|
| Parameter Tweak    | 0         | 0               | —            |
| Step Swap          | 0         | 0               | —            |
| Tool Substitution  | 0         | 0               | —            |
| Scope Change       | 0         | 0               | —            |
| Inversion          | 0         | 0               | —            |
| Crossover          | 0         | 0               | —            |
| Random Genesis     | 0         | 0               | —            |

## Mutation History

### Format
```
## Mutation M[NNN] — Cycle [N]
- **Type**: [Mutation type]
- **Parent(s)**: [Strategy ID(s)]
- **Child**: [New strategy ID]
- **Change**: [What was mutated]
- **Rationale**: [Why this mutation was chosen]
- **Outcome**: [Did the child outperform the parent?]
```

_No mutations yet._
