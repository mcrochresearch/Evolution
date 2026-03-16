# Semantic Memory

> Distilled knowledge — the principles, patterns, and truths this agent has learned.
> Unlike episodic memory (raw events), semantic memory contains abstracted understanding.
> This is the agent's growing wisdom — transferable across goals and sessions.

## Knowledge Crystallization Protocol

Principles are extracted from episodic memory when patterns emerge across 3+ episodes.
Each principle has a confidence score updated by Bayesian reasoning:
- Prior starts at 0.5 (uncertain)
- Each confirming episode: `posterior = prior * 0.9 + 0.1`
- Each contradicting episode: `posterior = prior * 0.7`
- Principles below 0.2 confidence are marked DEPRECATED

### Principle Format

```
## Principle: [Descriptive Name]
- **Statement**: [Clear, actionable principle]
- **Confidence**: [0.0-1.0]
- **Evidence**: [Episode numbers that support this]
- **Counter-evidence**: [Episode numbers that contradict this]
- **Domain**: [Where this principle applies — language, framework, pattern type]
- **First Observed**: [Timestamp]
- **Last Confirmed**: [Timestamp]
- **Applications**: [How many times this principle was successfully applied]
```

## Categories

### Architecture & Design
_No principles yet._

### Debugging & Problem-Solving
_No principles yet._

### Testing & Verification
_No principles yet._

### Performance & Optimization
_No principles yet._

### Code Quality & Patterns
_No principles yet._

### Tool & Framework Usage
_No principles yet._

### Meta-Strategy (How to Approach Problems)
_No principles yet._

---

_Semantic memory grows through experience. Start the Evolution Loop to begin learning._
