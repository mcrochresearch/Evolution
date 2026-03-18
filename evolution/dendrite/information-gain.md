# Information Gain

> What questions, if answered, would most improve decision-making?
> This file maintains a ranked list of the most valuable things to learn.
> Inspired by Bayesian optimization acquisition functions and Active Learning.

## Information Gain Scoring

Each question is scored by:
- **Uncertainty Reduction**: How much would answering this reduce overall uncertainty?
- **Decision Impact**: How many pending decisions depend on this answer?
- **Action Enablement**: How many new strategies would this enable?
- **Cost to Answer**: How many cycles would it take to test this?

```
Info Gain = (Uncertainty_Reduction * Decision_Impact * Action_Enablement) / Cost_to_Answer
```

## Highest-Value Questions

| Rank | Question | Gain Score | Cost | Strategy to Answer | Status |
|------|----------|-----------|------|-------------------|--------|
| — | _No questions yet_ | — | — | — | — |

## Answered Questions

| Question | Answer | Cycles to Answer | Impact on Strategy |
|----------|--------|-----------------|-------------------|
| — | — | — | — |

## Question Generation Protocol

After every reflection, ask:
1. "What single piece of information would most change my approach?"
2. "What am I assuming that I could verify in one cycle?"
3. "What's the riskiest assumption in my current strategy?"
4. "If I were wrong about X, what would break?"

---

_The agent that asks the right questions evolves faster than the agent that tries random actions._
