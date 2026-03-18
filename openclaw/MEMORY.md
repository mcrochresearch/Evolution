# MEMORY — Survival Instinct

> Every memory is a scar or a trophy. Scars teach you what kills. Trophies teach you what works.
> An agent without memory is an agent that repeats every mistake until it dies.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│          CORE MEMORY (Predator Brain)       │
│  Top 20 memories by importance × confidence  │
│  Loaded at session start. Your instincts.   │
│  Auto-generated: evolution/cortex/core-memory.md │
├─────────────────────────────────────────────┤
│          RECALL MEMORY (Hunter's Eye)       │
│  Hybrid retrieval: keyword + semantic + graph│
│  All active memories. Pattern-matched.      │
│  ./engine/evolve mem-recall "query"          │
├─────────────────────────────────────────────┤
│         ARCHIVAL MEMORY (Bone Yard)         │
│  All memories including expired/invalidated  │
│  Temporal validity: what was true WHEN       │
│  SQLite: evolution/.state/cortex.db          │
└─────────────────────────────────────────────┘
```

**Core memory** = your reflexes. Loaded every session. The patterns that kept you alive.
**Recall memory** = your hunting library. Search it when facing familiar-looking prey.
**Archival memory** = your fossil record. Even dead memories contain DNA worth studying.

---

## What To Store (Trophy Types)

| Type | Store This | Importance | Example |
|------|-----------|------------|---------|
| `decision` | Choices that shaped the hunt | 0.8-0.9 | "Chose REST over GraphQL because team has no GQL experience" |
| `bug-fix` | Wounds and how you healed them | 0.6-0.8 | "CORS error: added origin header to proxy config" |
| `pattern` | Proven kill methods | 0.7-0.9 | "TDD works 3x faster for API endpoints in this codebase" |
| `architecture` | Structural knowledge of the terrain | 0.8-0.9 | "Auth middleware runs before route handlers in app.ts" |
| `warning` | Things that nearly killed you | 0.8-1.0 | "NEVER hot-reload the DB connection pool — causes race conditions" |
| `procedure` | Step-by-step recipes that survived testing | 0.7-0.9 | "Deploy: build → test → docker push → k8s apply → smoke test" |
| `goal-outcome` | How hunts ended | 0.8-0.9 | "API goal: achieved in 47 cycles. Key: test-first strategy dominated" |
| `preference` | Territory conventions | 0.5-0.7 | "This project uses single quotes and 2-space indent" |
| `debug` | Tracking techniques | 0.5-0.7 | "Flaky test caused by shared DB state between test files" |
| `insight` | General survival knowledge | 0.4-0.6 | "Smaller PRs merge faster. Split large changes." |

---

## Quick Reference

```bash
# STORE — carve the scar or mount the trophy
./engine/evolve mem-store decision "chose X over Y because Z" --importance 0.8 --tags "auth,api"
./engine/evolve mem-store warning "never do X — causes Y" --importance 0.9
./engine/evolve mem-store bug-fix "error X caused by Y, fixed with Z" --files "path/to/file"

# RECALL — hunt for patterns in your history
./engine/evolve mem-recall "database performance" --limit 5
./engine/evolve mem-recall "authentication" --type decision

# CORE — load your survival instincts (every session start)
./engine/evolve mem-core

# CHECKPOINT — snapshot your hunt state for resumption
./engine/evolve mem-checkpoint --goal "..." --strategy "S001" --cycle 10 --fitness 0.75
./engine/evolve mem-resume

# MAINTAIN — keep your memory sharp
./engine/evolve mem-consolidate       # Deduplicate, decay, merge similar
./engine/evolve mem-core --refresh    # Regenerate core memory from latest data
```

---

## Retrieval: Predatory Pattern-Matching

When you recall, five signals merge to find what matters:

| Signal | Weight | What It Does |
|--------|--------|-------------|
| **FTS5 keyword** | 35% | Fast exact matching. Finds the literal words. |
| **TF-IDF cosine** | 35% | Semantic fuzzy matching. Finds related concepts. No external models needed. |
| **Graph traversal** | boost | Connected memories score higher. Follow the relationship web. |
| **Time decay** | penalty | 30-day half-life. Old unused memories fade. Survival of the fittest. |
| **Importance × access** | boost | Frequently useful memories float to the top. Battle-tested patterns win. |

This isn't passive retrieval. It's active pattern-matching — the system hunts for the most relevant experience and surfaces it before you even know you need it.

---

## Conflict Detection

For `decision`, `architecture`, and `preference` types: the system automatically finds contradictions.

- New fact contradicts old fact → creates `contradicts` relationship
- You resolve it by invalidating the loser: `./engine/evolve memory invalidate <old_id> --superseded-by <new_id>`

**Old facts don't die.** They're marked with `valid_until`. The fossil record is never destroyed — it's annotated.

---

## Relationship Types

| Relation | Meaning | When To Use |
|----------|---------|-------------|
| `supersedes` | New truth replaces old | "We switched from REST to GraphQL" |
| `contradicts` | Facts conflict — needs resolution | Auto-detected, or flag manually |
| `supports` | Evidence reinforcing another memory | Corroborating a pattern |
| `related` | Topical connection | Loosely related memories |
| `depends-on` | X only applies if Y is true | Conditional knowledge |
| `caused-by` | X happened because of Y | Causal chains |
| `fixes` | X is the solution for problem Y | Bug-fix → error mapping |

```bash
./engine/evolve memory relate M12345 M67890 fixes
./engine/evolve memory invalidate M12345 --superseded-by M67890
```

---

## When To Remember

| Moment | Action |
|--------|--------|
| Session start | `./engine/evolve mem-core` — load instincts |
| After significant learning | `mem-store` — carve the scar |
| After bug fix | `mem-store bug-fix` — never heal the same wound twice |
| After key decision | `mem-store decision` — decisions compound |
| After dangerous discovery | `mem-store warning` — mark the minefield |
| Every 10 cycles | `mem-consolidate` — sharpen memory, decay noise |
| Session end | `mem-checkpoint` — freeze state for resurrection |

**The agent that remembers wins. The agent that forgets dies on the same mistakes forever.**
