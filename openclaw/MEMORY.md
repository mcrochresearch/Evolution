# MEMORY — Cortex Persistent Memory System

> Evolution's brain. Persists across sessions, searchable, structured, and temporal.
> Powered by `engine/memory.py` — hybrid retrieval with zero external dependencies.

## Architecture

```
┌─────────────────────────────────────────────┐
│              CORE MEMORY (RAM)              │
│  Top 20 memories by importance × confidence  │
│  Always loaded at session start              │
│  Auto-generated: evolution/cortex/core-memory.md │
├─────────────────────────────────────────────┤
│            RECALL MEMORY (Search)            │
│  Hybrid retrieval: FTS5 + TF-IDF + Graph     │
│  All active memories, queryable by content   │
│  ./engine/evolve mem-recall "query"          │
├─────────────────────────────────────────────┤
│           ARCHIVAL MEMORY (Disk)             │
│  All memories including expired/invalidated  │
│  Temporal validity: valid_from → valid_until  │
│  SQLite database: evolution/.state/cortex.db │
└─────────────────────────────────────────────┘
```

## Memory Types

| Type | What to Store | Importance |
|------|--------------|------------|
| `decision` | Architectural/technical choices with rationale | 0.8-0.9 |
| `bug-fix` | What broke, why, and the fix | 0.6-0.8 |
| `pattern` | Recurring successful approaches | 0.7-0.9 |
| `architecture` | Structural knowledge about the codebase | 0.8-0.9 |
| `preference` | User/project conventions | 0.5-0.7 |
| `debug` | Debugging insights, error resolutions | 0.5-0.7 |
| `insight` | General learnings | 0.4-0.6 |
| `warning` | Things to AVOID, known failure modes | 0.8-1.0 |
| `procedure` | Step-by-step recipes that work | 0.7-0.9 |
| `goal-outcome` | How goals ended, what worked/didn't | 0.8-0.9 |

## Quick Reference

```bash
# Store a memory
./engine/evolve mem-store decision "Use X because Y" --importance 0.8 --tags "topic"

# Search memories (hybrid: keyword + semantic + graph + time decay)
./engine/evolve mem-recall "database performance" --limit 5

# Load core memories (do this every session start)
./engine/evolve mem-core

# Save session state for resume
./engine/evolve mem-checkpoint --goal "..." --strategy "S001" --cycle 10 --fitness 0.75

# Resume from last checkpoint
./engine/evolve mem-resume

# Maintenance (every 10 cycles)
./engine/evolve mem-consolidate
./engine/evolve mem-core --refresh

# Mark old fact as superseded
./engine/evolve memory invalidate M12345 --superseded-by M67890

# Create relationship between memories
./engine/evolve memory relate M12345 M67890 fixes
```

## How It Works

### Hybrid Retrieval (5 signals merged)
1. **FTS5 keyword search** (35%) — fast exact matching with BM25 ranking
2. **TF-IDF cosine similarity** (35%) — semantic fuzzy matching, zero external models
3. **Graph traversal boost** — connected memories score higher
4. **Time decay** — older unused memories score lower (30-day half-life)
5. **Importance × access frequency** — frequently useful memories rank higher

### Deduplication
- Exact hash match → boost confidence of existing memory
- TF-IDF similarity > 0.85 → merge instead of creating duplicate

### Conflict Detection
- For decision/architecture/preference types: automatically finds potentially contradicting memories
- Creates `contradicts` relationships for review

### Temporal Validity (from Zep)
- Memories have `valid_from` and `valid_until` timestamps
- Invalidated memories aren't deleted — they're marked with `valid_until`
- `supersedes` relationships track fact evolution over time
- Old facts can be queried with `--include-expired` for historical context

### Relationship Graph
- `supersedes` — new fact replaces old one
- `contradicts` — facts conflict (needs resolution)
- `supports` — evidence reinforcing another memory
- `related` — topical connection
- `depends-on` — X only applies if Y is true
- `caused-by` — X happened because of Y
- `fixes` — X is the solution for problem Y
