# Checkpoints

> Reversibility safety net — snapshots of state before risky operations.
> Every cycle creates a lightweight checkpoint before executing changes.
> If verification fails, the checkpoint enables clean reversion.

## Checkpoint Protocol

### Before Each Cycle:
1. Record which files will be modified
2. Note the git state (branch, HEAD commit)
3. Store any critical state values

### On Revert:
1. Use `git checkout -- [files]` to restore modified files
2. If new files were created, delete them
3. If dependencies changed, restore lockfile
4. Verify the revert brought fitness back to pre-cycle level

## Active Checkpoints

_No active checkpoints. Evolution has not started._

### Checkpoint Format

```
## Checkpoint CP[NNN] — Cycle [N]
- **Created**: [Timestamp]
- **Git HEAD**: [commit hash]
- **Files to Modify**: [list of files]
- **Pre-change State**:
  - Fitness: [X.XX]
  - Tests Passing: [X/Y]
  - Build: PASS/FAIL
- **Revert Command**: `git checkout [hash] -- [files]`
- **Status**: ACTIVE / USED / EXPIRED
```

## Checkpoint History

_No checkpoints created yet._

## Rules

1. Keep only the last 10 checkpoints (older ones expire)
2. Never delete a checkpoint for the current cycle
3. If a revert fails, escalate to user immediately
4. Checkpoints are cheap — always create them, never skip
