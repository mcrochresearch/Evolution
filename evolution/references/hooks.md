# Evolution Hooks — Enforcement Layer

> Hooks enforce Evolution's rules mechanically. Install these in your
> Claude Code settings or agent platform configuration.

## Recommended Hooks

### 1. Post-Edit Hook: Verify Before Proceeding
Ensures no code change goes unverified.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hook": {
          "type": "prompt",
          "prompt": "A code file was just modified. Remind the agent: Evolution Rule 3 requires running mechanical verification (tests/build/lint) before proceeding to the next cycle. Has verification been run since this edit? If not, the agent must run it now."
        }
      }
    ]
  }
}
```

### 2. Pre-Bash Hook: Checkpoint Guard
Prevents destructive operations without a checkpoint.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hook": {
          "type": "prompt",
          "prompt": "Check if this bash command could modify or delete files (rm, git reset, git checkout, etc.). If so, verify that a checkpoint has been recorded in evolution/nucleus/cycle.md for the current cycle. Block if no checkpoint exists."
        }
      }
    ]
  }
}
```

### 3. Session Start Hook: Resume Evolution
Automatically resumes Evolution if state exists.

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hook": {
          "type": "command",
          "command": "test -f evolution/cortex/working.md && echo 'Evolution state detected. Read evolution/cortex/working.md and evolution/nucleus/goal.md to resume.' || echo 'No Evolution state found.'"
        }
      }
    ]
  }
}
```

## Installation

Add to `.claude/settings.json` in your project:

```json
{
  "hooks": {
    // paste hooks from above
  }
}
```

Or add to your agent platform's equivalent configuration file.
