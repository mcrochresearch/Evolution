# Tool DNA — Tool Usage Evolution

> The agent's tool genome — WHICH tools it uses and HOW it combines them.
> Tool strategies evolve based on what produces the best outcomes.

## Tool Priority Stack

Ordered by default preference (evolves through experience):

| Priority | Tool | Role | Success Rate | Notes |
|----------|------|------|-------------|-------|
| 1 | Read | Understand before acting | — | Never skip this |
| 2 | Edit | Surgical code changes | — | Prefer over Write |
| 3 | Bash | Run tests, verify, execute | — | Primary verification |
| 4 | Grep | Search code contents | — | Find patterns |
| 5 | Glob | Find files by pattern | — | Locate targets |
| 6 | Write | Create new files | — | Only when necessary |
| 7 | Agent | Parallel subagent work | — | For independent tasks |
| 8 | WebSearch | External knowledge | — | When stuck |
| 9 | WebFetch | Read specific URLs | — | Documentation |

## Tool Combo Library

> Sequences of tools that work well together — "tool recipes"

| Combo ID | Sequence | When to Use | Success Rate |
|----------|----------|-------------|-------------|
| TC001 | Glob → Read → Edit → Bash | Standard code modification | — |
| TC002 | Grep → Read → Read → Edit | Find and fix pattern | — |
| TC003 | Agent(Explore) → Read → Edit | Unfamiliar codebase change | — |
| TC004 | WebSearch → Read → Edit → Bash | Using unfamiliar API | — |
| TC005 | Read → Write → Bash → Read | Create test, run, review | — |

## Tool Usage Statistics

| Tool | Times Used | Success After | Failure After | Avg Fitness Delta |
|------|-----------|--------------|--------------|------------------|
| — | — | — | — | — |

## Tool Mutations

### Possible Mutations
1. **Reorder priority**: Swap two tools in the priority stack
2. **Add tool combo**: Record a new effective tool sequence
3. **Deprecate combo**: Mark an underperforming combo
4. **Create custom tool**: Write a bash script for repeated operations
5. **Adjust parallelism**: Change when to use subagents

### Custom Tools Created

> Scripts and automations the agent has created for itself.

_No custom tools yet. The agent will create tools when it identifies repeated operations._

## Mutation Log

| Gen | Mutation | Description | Fitness Impact | Kept? |
|-----|----------|-------------|----------------|-------|
| — | — | — | — | — |
