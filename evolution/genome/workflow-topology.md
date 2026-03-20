# Workflow Topology — Pipeline DAG Registry

> Represents the agent pipeline as a directed acyclic graph (DAG) where
> nodes are pipeline stages and edges are data dependencies.
> The topology itself evolves through SEW (Self-Evolving Workflow) and
> AFlow (Alternative Flow decomposition) optimization.
> **This file is maintained by engine/workflow_evolution.py. Do not edit manually.**

## DAG Concept

```
[analyze] → [plan] → [execute] → [verify]
                  ↘                  ↗
              [risk_check] ─────────┘
```

Each node has:
- **Role**: What function this stage serves (analyzer, planner, executor, etc.)
- **Prompt**: The instructions for this stage
- **Tools**: Available tools for this stage
- **Dependencies**: Which nodes must complete before this one runs
- **Fitness**: How well this node performs (tracked independently)

## Optimization Strategies

### SEW (Self-Evolving Workflow)
Analyzes node fitness data and recommends structural changes:
1. **Remove** consistently low-performing nodes
2. **Split** overloaded nodes (middling fitness → doing too much)
3. **Merge** redundant nodes (same role, both performing well)
4. **Parallelize** independent nodes that currently run sequentially

### AFlow (Alternative Flow Decomposition)
Generates multiple ways to decompose a task into pipeline steps:
1. **Sequential**: Simple linear chain (analyze → plan → execute → verify)
2. **Parallel Analysis**: Multiple analysis angles, then converge
3. **Iterative Refinement**: Quick draft → critique → refine → validate

## Current Topology

_No workflow initialized yet. Use `./engine/evolve workflow-init "name" "description"` to begin._

## Commands

- Init: `./engine/evolve workflow-init "pipeline" "description"`
- Add node: `./engine/evolve workflow-add-node <id> <role> "<prompt>" [deps_json]`
- Add edge: `./engine/evolve workflow-add-edge <from> <to>`
- View: `./engine/evolve workflow-topology`
- Validate: `./engine/evolve workflow-validate`
- Optimize (SEW): `./engine/evolve workflow-optimize`
- Decompose (AFlow): `./engine/evolve workflow-aflow "task description"`
- Parallel groups: `./engine/evolve workflow-parallel`

State is stored in `evolution/.state/workflow.json`.
