# Prompt Population — Evolutionary Breeding Registry

> Tracks the breeding population of prompt variants across roles.
> Each role maintains a population of competing prompts that evolve
> through crossover and mutation, with fitness-proportional selection.
> **This file is maintained by engine/prompt_breeding.py. Do not edit manually.**

## Overview

The prompt breeding system (EvoPrompt pattern) treats prompts as organisms
in an evolutionary population:

- **Population**: N variant prompts per pipeline role
- **Crossover**: Combine two high-fitness prompts into a child
- **Mutation**: Introduce small random variations
- **Selection**: Fitness-proportional (better prompts reproduce more)
- **Elitism**: Best prompt always survives to next generation
- **Promptbreeder**: The mutation prompt itself evolves

## Active Roles

_No roles initialized yet. Use `./engine/evolve breed-init <role> "<seed_prompt>"` to begin._

## Breeding History

_No breeding cycles yet. Run `./engine/evolve breed <role>` to evolve._

## Promptbreeder Status

The mutation meta-prompt (the prompt that guides how prompts are mutated)
is itself subject to evolution. This creates a self-referential improvement
loop where the system improves its own ability to improve.

Current mutator version: **0** (default)

---

## How It Works

1. Initialize a role: `./engine/evolve breed-init soul "You are an autonomous agent..."`
2. Create variants: `./engine/evolve breed-mutate soul P001`
3. Score after use: `./engine/evolve breed-score soul P001 0.75`
4. Run breeding cycle: `./engine/evolve breed soul`
5. Get the best: `./engine/evolve breed-best soul`
6. Evolve the mutator: `./engine/evolve breed-evolve-mutator`

State is stored in `evolution/.state/prompt_breeding.json`.
