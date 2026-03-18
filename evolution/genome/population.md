# Strategy Population

> The living genome — a population of competing strategies that evolve through
> selection, mutation, and crossover. Inspired by genetic algorithms (Holland, 1975)
> and Quality-Diversity methods (MAP-Elites, Mouret & Clune, 2015).

## Population Parameters
- **Max Population Size**: 12 (carrying capacity)
- **Min Population Size**: 3 (extinction prevention)
- **Mutation Rate**: 0.2 (probability of mutating a selected strategy)
- **Crossover Rate**: 0.1 (probability of combining two strategies)
- **Selection Method**: Thompson Sampling with UCB1 tiebreaking
- **Diversity Pressure**: Maintain at least 3 distinct "species" (approach categories)

## Fitness Ranking

| Rank | ID | Name | Fitness | Gen | Tries | Wins | Species |
|------|----|------|---------|-----|-------|------|---------|
| — | — | _No strategies yet_ | — | — | — | — | — |

## Active Strategies

_No strategies in population. Goal decomposition will seed the initial population._

## Species Map (Quality-Diversity)

> Strategies are grouped into species by approach type.
> This ensures diversity — we don't want all strategies to converge on one approach.

_No species yet._

## Selection Log

> Records which strategy was selected each cycle and why.

_No selections yet._

---

## Genetic Operators Reference

### Mutation Types
1. **Parameter Tweak**: Change a parameter within the same approach
2. **Step Swap**: Reorder steps in a procedure
3. **Tool Substitution**: Try a different tool for the same purpose
4. **Scope Change**: Widen or narrow the scope of the change
5. **Inversion**: Try the opposite of what's been tried

### Crossover Rules
- Only cross strategies with fitness > 0.3
- Child inherits the best-performing elements from each parent
- Child gets a new ID and Generation = max(parent_gens) + 1

### Selection Pressure
- Bottom 20% fitness: eligible for extinction (moved to graveyard)
- Top strategy: preserved in hall-of-fame (elitism)
- New strategies enter with fitness = 0.0 and high uncertainty bonus
