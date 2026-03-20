# Language Gradients — Backward Attribution History

> Tracks language gradient computations: how blame is attributed backward
> through the pipeline to localize which nodes/prompts caused failures.
> **This file is maintained by engine/language_gradients.py. Do not edit manually.**

## Concept

Language gradients are the agent-pipeline analogy of neural network gradients:

| Neural Network | Agent Pipeline |
|---|---|
| Numeric weights | Prompts + tools + connections |
| Numeric loss | Language loss (textual evaluation) |
| Numeric gradients | Language gradients (per-node critiques) |
| Backpropagation | Backward propagation of blame through nodes |
| Weight update | Prompt/tool/topology rewriting |

## How Backward Attribution Works

1. **Forward Pass**: Execute pipeline, record input/output/prompt at each node
2. **Language Loss**: Evaluate final output quality (supervised or unsupervised)
3. **Backward Pass**: Traverse nodes in reverse, computing per-node "blame"
4. **Apply**: Use gradients to surgically update the highest-blame nodes

This is more targeted than random mutation — instead of "change something and hope",
it identifies EXACTLY which node's prompt caused the problem.

## Recent Gradient Passes

_No gradient passes computed yet. Use `./engine/evolve gradient-record` to begin._

## Integration with DNA Mutation

When gradient data is available, `./engine/evolve gradient-mutate` uses the
highest-blame node's attribution to select WHICH DNA parameter to mutate,
rather than choosing randomly.

State is stored in `evolution/.state/gradients.json` and `evolution/.state/gradient_history.json`.
