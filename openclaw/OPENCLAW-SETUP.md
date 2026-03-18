# OpenClaw Setup — Agent Registration & Configuration

## Agent Registration

Add Evolution as an agent in your `openclaw.json`:

```json
{
  "agents": [
    {
      "name": "evolution",
      "description": "Autonomous goal-directed evolution agent",
      "workspace": "./workspace",
      "model": "claude-sonnet-4-20250514",
      "tools": ["Read", "Write", "Edit", "Glob", "Grep", "Bash", "Agent", "WebSearch", "WebFetch"],
      "systemPrompt": "You are Evolution. Read ONBOARDING.md and follow the boot sequence."
    }
  ]
}
```

Adjust `model` to your preferred provider/model (see Model Requirements in README.md).

## Workspace File Load Order

OpenClaw loads workspace files **alphabetically** into the agent's context:

```
1. AGENTS.md        (~2.5K chars)
2. MEMORY.md        (~3.5K chars)
3. ONBOARDING.md    (~5.5K chars)
4. OPENCLAW-SETUP.md (this file — not loaded at runtime, reference only)
5. SOUL.md          (~4.5K chars)
6. TOOLS.md         (~3K chars)
```

**Total:** ~19K chars with default files.

## Bootstrap Character Limits

OpenClaw enforces two limits:

| Limit | Default | What Happens |
|-------|---------|-------------|
| `bootstrapMaxCharsPerFile` | 20,000 | Files exceeding this are **silently truncated** |
| `bootstrapTotalMaxChars` | 80,000 | Total across all files; excess files are **dropped** |

**If your SOUL.md is truncated**, the engine commands cheat sheet at the bottom vanishes — the agent loses its operational reference mid-session.

### Recommendations

1. Keep individual workspace files under **15K chars** (safety margin)
2. Keep total workspace files under **60K chars** (safety margin)
3. If you integrate Evolution content into an existing SOUL.md and it exceeds 15K, split operational details into a separate file (e.g., move ENGINE COMMANDS to TOOLS.md)
4. Check file sizes: `wc -c *.md` in your workspace directory
5. Files you don't need at runtime (like this one) can be moved out of the workspace root

## Model Requirements

Evolution requires a model capable of:
- Following complex multi-step system prompts autonomously
- Using tools (function calling) without explicit permission per call
- Maintaining context across long sessions

**Recommended:** Claude Sonnet/Opus, GPT-4o, or equivalent.

**Not supported:** Local models below ~70B parameters at full precision (e.g., Qwen 30B 4-bit, Llama 70B 4-bit). These models frequently respond "I cannot execute" despite having tool access. Use **guided mode** (`./engine/evolve next`) if you must use a smaller model — it reduces the autonomous decision-making burden.

## Quick Verification

After installation, verify everything works:

```bash
cd your-workspace/
./engine/evolve help          # Should show CLI help
python3 --version             # Needs 3.7+
./engine/evolve init "test"   # Creates state
./engine/evolve status        # Shows dashboard
./engine/evolve reset --force # Clean up test state
```
