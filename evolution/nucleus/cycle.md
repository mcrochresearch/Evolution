# Cycle State

> The heartbeat of Evolution — tracking the current and historical execution cycles.
> Each cycle is one complete pass through the Evolution Loop:
> SELECT → EXECUTE → VERIFY → SCORE → KEEP/REVERT → REFLECT → EVOLVE → UPDATE

## Current Cycle

- **Cycle Number**: 0
- **Phase**: NOT_STARTED
- **Strategy**: —
- **Action**: —
- **Started At**: —
- **Status**: IDLE

## Cycle History

### Format
```
## Cycle [N] — [Timestamp]
- **Strategy**: S[NNN] — [Name]
- **Phase Durations**: SELECT:[Xs] EXECUTE:[Xs] VERIFY:[Xs] SCORE:[Xs] REFLECT:[Xs]
- **Action**: [What was done]
- **Verification**: PASS / FAIL — [Details]
- **Fitness Delta**: [+/- X.XX]
- **Decision**: KEEP / REVERT
- **Mutation Triggered**: [Yes/No — what mutation]
- **Key Insight**: [One-line learning]
```

_No cycles completed yet._

## Cycle Statistics

| Metric | Value |
|--------|-------|
| Total Cycles | 0 |
| Successful Cycles | 0 |
| Failed Cycles | 0 |
| Average Cycle Duration | — |
| Longest Cycle | — |
| Shortest Cycle | — |
| Current Streak (success) | 0 |
| Current Streak (failure) | 0 |
