# TOOLS — Weapons Manifest

> Every tool is a weapon. Know what it kills, when to deploy it, and what it costs.

---

## Kill Chain

### Phase 1: RECON (Understand the terrain)

| Weapon | Kills | Deploy |
|--------|-------|--------|
| **Read** | Ignorance about specific files | Before modifying anything. Always. |
| **Glob** | Unknown file locations | When you need to find files by pattern. Faster than Grep. |
| **Grep** | Hidden patterns in code | When you know WHAT to find but not WHERE. |
| **Agent (Scout)** | Large unknowns | When the search space is too large for manual recon. |
| **WebSearch** | Knowledge gaps | When the answer isn't in the codebase. |
| **WebFetch** | Specific external intel | When you have a URL and need its contents. |

### Phase 2: TARGET (Lock on the change)

| Weapon | Kills | Deploy |
|--------|-------|--------|
| **`./engine/evolve select`** | Decision paralysis | Thompson Sampling picks the strategy. Trust it. |
| **`./engine/evolve checkpoint`** | Irreversibility | Before ANY code change. Non-negotiable. |
| **`./engine/evolve express-dna`** | Behavioral drift | Check your current cognitive parameters before big decisions. |

### Phase 3: STRIKE (Make the change)

| Weapon | Kills | Deploy |
|--------|-------|--------|
| **Edit** | Existing code that needs modification | Surgical precision. Smallest diff that tests the hypothesis. |
| **Write** | Missing files | Only when a new file is genuinely needed. Prefer Edit. |
| **Bash** | System operations | Install deps, run scripts, git operations, process management. |
| **Agent (Builder)** | Large implementation blocks | When you know exactly what to build and want speed. |

### Phase 4: VERIFY (Confirm the kill)

| Weapon | Kills | Deploy |
|--------|-------|--------|
| **`./engine/evolve fitness`** | Uncertainty about impact | After EVERY change. The machine judges the machine. |
| **`./engine/evolve guard`** | Hidden anti-patterns | After fitness passes. Catches @ts-ignore, test skips, etc. |
| **Bash** | Specific verification needs | When fitness.sh doesn't cover your case (e.g., curl an endpoint). |
| **Agent (Striker)** | False confidence | When you think it works. That's when it's most likely broken. |

### Phase 5: EXTRACT (Harvest intelligence)

| Weapon | Kills | Deploy |
|--------|-------|--------|
| **`./engine/evolve cycle`** | Unlogged outcomes | After every verify. Builds the dataset that powers learning. |
| **`./engine/evolve crystallize`** | Wasted experience | Every 10 episodes. Turns raw data into principles. |
| **`./engine/evolve mem-store`** | Amnesia | After every significant learning. Scars and trophies persist. |
| **`./engine/evolve analyze`** | Blind spots | Every 5 cycles. Pattern mining on your own behavior. |

---

## Weapon Selection Rules

1. **Read before Edit.** Always understand before modifying. Shooting blind is how you kill your own code.
2. **Glob before Grep.** Find the files first, then search their contents. Faster, more precise.
3. **Edit over Write.** Modify what exists. Don't create files you don't need. Every new file is debt.
4. **Agent for parallel ops.** When tasks are independent, run them simultaneously. Don't serialize what can be parallelized.
5. **Bash for verification.** The exit code doesn't lie. The test output doesn't lie. Your intuition lies constantly.
6. **Engine over intuition.** `./engine/evolve select` uses real Thompson Sampling with Beta distributions. Your gut uses vibes. Trust the math.

---

## Weapon Combos (Proven Effective)

| Combo | Sequence | When |
|-------|----------|------|
| **Surgical Strike** | Read → Edit → fitness → cycle | Standard cycle. Most changes. |
| **Recon-in-Force** | Glob → Grep → Agent(Scout) → Read | Entering unfamiliar codebase. |
| **Blitz** | checkpoint → Write → fitness → cycle | Creating new files. Fast, verify fast. |
| **Siege** | analyze → plateau → WebSearch → add-strategy → select | Breaking through stagnation. |
| **Scorched Earth** | revert → extinct → add-strategy × 3 → select | Total strategy failure. Nuclear restart. |

---

## Designated Tools (Hard-coded — no improvising)

The agent uses these tools. No alternatives. No substitutions. No "let me try this other thing instead."

| Category | Tool | Why |
|----------|------|-----|
| **Tasks** | Todoist | All task management goes here. Not Trello, not Linear, not sticky notes. |
| **Docs** | Notion | All documentation lives here. Not Confluence, not Google Docs, not random markdown files. |
| **Deploys** | Netlify | All deployments go through Netlify. Not Vercel, not Railway, not manual SSH. |

**Why hard-code tools?** Because the agent stops improvising with random tools and starts executing predictably. Choice is the enemy of velocity. The agent knows exactly where to look and where to put things.

Override these only by editing this file directly. The agent does not get to decide.

---

## Ammo Conservation

- **Context window is finite.** Don't Read files you don't need. Don't Grep with broad patterns.
- **API calls cost tokens.** Batch Agent tasks. Don't spawn a scout for one file — just Read it.
- **Time is fitness.** Every minute spent on recon is a minute not spent building. Recon has diminishing returns after cycle 1.
