# Workflow DNA — Execution Pattern Evolution

> The agent's procedural genome — HOW it approaches work.
> Different workflows suit different types of problems.
> The agent evolves its workflow to match the challenge.

## Active Workflow

```
RESEARCH → PLAN → EXECUTE → VERIFY → REFLECT
```

## Workflow Population

### W001: Standard (Default)
```
Research → Plan → Execute → Verify → Reflect
```
- **Best for**: Well-understood problems with clear solutions
- **Fitness**: 0.00 (untested)
- **Attempts**: 0

### W002: Scientific
```
Observe → Hypothesize → Predict → Test → Analyze → Conclude
```
- **Best for**: Debugging, unknown root causes, exploration
- **Fitness**: 0.00 (untested)
- **Attempts**: 0

### W003: Rapid Prototype
```
Prototype → Test → Iterate → Refine → Verify
```
- **Best for**: UI work, API design, when direction is unclear
- **Fitness**: 0.00 (untested)
- **Attempts**: 0

### W004: Parallel Decompose
```
Decompose → [Parallel Execute A, B, C] → Integrate → Verify
```
- **Best for**: Independent sub-tasks, large scope work
- **Fitness**: 0.00 (untested)
- **Attempts**: 0

### W005: Deep Understand
```
Explore → Map → Understand → Plan → Execute → Verify
```
- **Best for**: Unfamiliar codebases, legacy code, complex systems
- **Fitness**: 0.00 (untested)
- **Attempts**: 0

## Workflow Selection

Choose workflow based on problem characteristics:

| Characteristic | Recommended Workflow |
|---------------|---------------------|
| Clear requirements, known solution | W001: Standard |
| Unknown root cause, mysterious behavior | W002: Scientific |
| Unclear direction, need to experiment | W003: Rapid Prototype |
| Multiple independent pieces | W004: Parallel Decompose |
| Complex unfamiliar system | W005: Deep Understand |

## Workflow Mutation Operations

1. **Step Insertion**: Add a new step to an existing workflow
2. **Step Removal**: Remove a step that doesn't contribute to fitness
3. **Step Swap**: Reorder steps in the workflow
4. **Step Merge**: Combine two workflows into a hybrid
5. **Step Fork**: Add a conditional branch (if X, do Y; else do Z)

## Mutation Log

| Gen | Workflow | Mutation | Fitness Impact | Kept? |
|-----|----------|----------|----------------|-------|
| — | — | — | — | — |
