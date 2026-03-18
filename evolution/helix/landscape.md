# Fitness Landscape

> A map of the solution space — which regions have been explored,
> which are promising, and which are dead ends.
> Inspired by Wright's fitness landscape (1932) and MAP-Elites (2015).

## Landscape Visualization

The fitness landscape is a multi-dimensional space where:
- **X-axis**: Approach type / strategy species
- **Y-axis**: Complexity level (simple → complex)
- **Color/value**: Fitness achieved in that region

```
Fitness Landscape Map
                    ┌─────────────────────────────────────────┐
                    │            COMPLEXITY LEVEL              │
                    │   Simple    Medium     Complex    Extreme│
 ┌──────────────────┼─────────────────────────────────────────┤
 │ Approach A       │  [    ]    [    ]     [    ]     [    ] │
 │ Approach B       │  [    ]    [    ]     [    ]     [    ] │
 │ Approach C       │  [    ]    [    ]     [    ]     [    ] │
 │ Approach D       │  [    ]    [    ]     [    ]     [    ] │
 └──────────────────┴─────────────────────────────────────────┘

 Legend: [ ] = unexplored  [░] = low fitness  [▓] = medium  [█] = high
```

_Landscape will be populated as strategies are tested._

## Explored Regions

| Region | Strategy | Fitness | Cycles | Verdict |
|--------|----------|---------|--------|---------|
| — | — | — | — | — |

## Promising Frontiers

> Regions adjacent to high-fitness areas that haven't been explored yet.

_No frontiers identified yet._

## Dead Zones

> Regions confirmed to have low fitness — avoid unless context changes.

_No dead zones identified yet._

## Landscape Insights

> Meta-observations about the shape of the fitness landscape.

_No insights yet. The landscape reveals itself through exploration._

---

## Landscape Update Protocol

After every cycle:
1. Plot the tested strategy's region on the landscape
2. Identify new frontiers (unexplored neighbors of successful regions)
3. Mark dead zones (3+ failures in same region)
4. Look for ridges (paths of increasing fitness to follow)
5. Look for valleys (local minima to escape via exploration jumps)
