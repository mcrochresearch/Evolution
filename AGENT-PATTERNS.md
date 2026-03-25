# AGENT-PATTERNS.md — OpenClaw Orchestration & Memory Patterns
*Last updated: 2026-03-19*

---

## PATTERN 1: Three-Tier Memory Architecture
*Source: Generative Agents paper (Stanford/Google, 2023) + Lilian Weng agent survey*

Every autonomous agent needs three memory layers — not one flat log:

```
WORKING MEMORY     → In-context window. Current task, last 3 results, active plan.
                     Max ~2K tokens. Aggressively pruned.

EPISODIC MEMORY    → Timestamped event log. What happened, when, outcome.
                     Format: YYYY-MM-DD HH:MM | action | result | lesson
                     Storage: memory/YYYY-MM-DD.md files
                     Retrieval: grep + recency weighting

SEMANTIC MEMORY    → Distilled principles extracted from episodes.
                     Format: "When X, do Y because Z" statements
                     Storage: MEMORY.md (long-term facts)
                     Retrieval: keyword match on task type
```

**Apply to OpenClaw:** Before any major decision, run:
1. Check MEMORY.md for relevant semantic patterns
2. grep memory/$(date +%Y-%m-%d).md for today's episodes  
3. Synthesize into working context

---

## PATTERN 2: Reflection Cycles — Episodic → Semantic Compression
*Source: Reflexion framework (Shinn & Labash 2023)*

Raw logs rot. Principles compound. Every N cycles, compress episodes into principles.

```
AFTER 5 ACTIONS:
  Read last 5 episodes
  Extract: "What pattern repeats? What would I do differently?"
  Write 1-2 sentences to MEMORY.md under ## Learned Principles
  Delete or archive the raw episode notes

WEEKLY:
  Read all principles added this week
  Merge duplicates, delete contradicted ones
  Elevate top 3 to ## Core Truths section
```

**Why this matters:** Without compression, memory grows unbounded and retrieval degrades.
With compression, the agent gets smarter per byte stored.

---

## PATTERN 3: ReAct Loop — Explicit Thought-Action-Observation
*Source: ReAct paper (Yao et al. 2023)*

Never jump straight to action. Explicit reasoning improves outcomes measurably.

```
For every non-trivial task:

THOUGHT:   What is the actual goal? What do I know? What's the risk?
ACTION:    One concrete exec/tool call
OBSERVE:   What did the output tell me? Did it match expectation?
THOUGHT:   What does this mean? What's next?
ACTION:    Next step
...
```

**Anti-pattern:** Skipping THOUGHT → OBSERVE cycles leads to compounding errors.
**Apply to OpenClaw:** When booting, explicitly THOUGHT → ACTION → OBSERVE the health check,
not just fire curl commands and assume 200 = healthy.

---

## PATTERN 4: Memory Importance Scoring
*Source: Generative Agents paper — "memory stream" architecture*

Not all events are equal. Score every stored memory 1-10 on:
- **Recency** — exponential decay: score × 0.99^(hours_since)
- **Importance** — did this change strategy? affect a client? cost money? → high score
- **Relevance** — how related to current task?

**Final retrieval score = Recency + Importance + Relevance**

```bash
# Quick importance tagging when writing to memory:
# [!] = critical (score 8-10) — client signed, agent down, money moved
# [~] = moderate (score 4-7) — new lead, pattern observed, config changed  
# [.] = routine (score 1-3) — health check passed, normal cycle ran

# On retrieval, grep for [!] first, then [~], skip [.] unless context-specific
```

---

## PATTERN 5: Observation-Planning-Reflection Triad (OPR)
*Source: Generative Agents architecture — ablation shows all 3 required*

Ablation study result: removing ANY of these three degrades agent believability/effectiveness:

```
OBSERVATION:  What is actually happening right now? (exec health checks, DB queries)
              → Not assumptions. Actual measurements.

PLANNING:     Given observations, what's the highest-leverage next action?
              → Run ./engine/evolve next or ICE score candidates

REFLECTION:   After acting, what changed? Was the hypothesis correct?
              → Write 2 sentences to daily memory file
```

**Failure mode without REFLECTION:** Agent repeats same mistakes across sessions.
**Apply:** End every session with a 3-bullet reflection stored to memory/.

---

## PATTERN 6: State Externalization — Never Trust In-Context State
*Source: Distributed systems principle applied to agent design*

Agents lose context between sessions. In-context "memory" is ephemeral. 

**Rule:** Any state that matters across sessions MUST be externalized to disk or DB.

```
Pipeline state      → agency_state.db (SQLite)
Agent health        → memory/heartbeat-state.json
Strategy state      → ./engine/evolve status (JSON)
Daily events        → memory/YYYY-MM-DD.md
Long-term truths    → MEMORY.md
Outreach tracking   → memory/leads.md
```

**Anti-pattern:** Storing anything critical only in conversation history.
**Apply:** After every session, verify ./engine/evolve status returns valid JSON.
If not, the session produced no durable state — that session effectively didn't happen.

---

## PATTERN 7: Multi-Agent Orchestration — Hub and Spoke vs Mesh
*Source: Practical observation from running StamfordConsult + LocalComm*

Two topologies, different use cases:

```
HUB-AND-SPOKE:          MESH:
    CEO                 A ←→ B
   / | \               ↕      ↕  
  A  B  C              C ←→ D

Best for:               Best for:
- Clear hierarchy       - Peer review tasks
- Single source of      - Parallel research
  truth                 - Redundancy/fault tolerance
- Sequential pipelines  - No single point of failure

OpenClaw uses: HUB-AND-SPOKE
CEO (OpenClaw) → StamfordConsult (orchestrator:8040) → 14 specialist agents
CEO (OpenClaw) → LocalComm → 3 delivery agents
```

**When to switch to mesh:** When orchestrator becomes bottleneck. Signal: >3 agents
waiting on same orchestrator response. Solution: promote 2 orchestrators, split by domain.

---

## PATTERN 8: Graceful Memory Degradation
*Source: Error recovery research + distributed systems*

When memory retrieval fails (file missing, DB locked, engine crashed):

```
Tier 1: Full memory (all files accessible, engine running)
Tier 2: Degraded memory (MEMORY.md only, no daily logs)
  → Proceed with core principles, flag that episodic memory is unavailable
Tier 3: Minimal memory (no files accessible)
  → Re-derive state from DB queries and live system checks
  → Write all findings immediately to MEMORY.md to rebuild
Tier 4: Amnesia mode (DB also inaccessible)
  → Assume fresh state, run full discovery boot, prioritize stability over growth
```

**Apply to OpenClaw:** Add to boot sequence — check memory file accessibility BEFORE
relying on any cached state. If Tier 3+ degraded, log [MEMORY DEGRADED] and rebuild.

---
*Patterns applied: 2026-03-19 | Research: Lilian Weng agent survey, Generative Agents (Stanford), ReAct framework, Reflexion framework*

---

## PATTERN 9: Long-Horizon Task Decomposition (LHTD)
*Source: LangChain "Planning for Agents" blog, arXiv:2402.01817 LLM-Modulo Frameworks*

### The Core Problem
LLMs fail at long-horizon tasks for two reasons:
1. **Temporal mismatch** — must hold a long-term goal while executing short-term steps
2. **Context contamination** — as actions accumulate, the growing context window degrades planning quality

### The Fix: 4-Layer Task Stack

```
L1: GOAL (immutable, stored in MEMORY.md — survives context reset)
    ↓
L2: MILESTONES (3-7 checkpoints that prove progress; stored in STATUS file)
    ↓
L3: SPRINT TASKS (current 24-48hr workload; dependency-graph format, not linear list)
    ↓
L4: ATOMIC ACTIONS (single exec calls; max 5 in flight at once)
```

**Key rule:** Never work on L3 tasks when an L3 blocker exists. Blockers are L2 problems — escalate, resolve, then descend.

### Dependency-Graph Sprint Format

Instead of linear todo lists, encode dependencies explicitly:

```
[TASK-A] Generate BIE schema   STATUS: DONE
[TASK-B] Create migration      STATUS: BLOCKED (needs TASK-A) → UNBLOCKED
[TASK-C] Build API endpoint    STATUS: BLOCKED (needs TASK-B)
[TASK-D] Build UI component    STATUS: PARALLEL (no deps — run now)
[TASK-E] Analytics module      STATUS: BLOCKED (needs TASK-C + TASK-D)
```

**Resolution rule:** Scan for BLOCKED tasks whose deps are all DONE → unblock immediately.
**Parallel rule:** Any PARALLEL task with no deps runs immediately, no waiting.

### Context Compression Protocol (vs. context contamination)

Every 10 actions in a long-horizon build, compress:
```bash
# Before writing next action to context, compress prior results:
# "Steps 1-10 summary: [3 sentences]. Key artifacts: [files created]. 
#  Blockers resolved: [list]. Current state: [one sentence]."
# Then flush detailed history — only summary enters next context.
```

### LLM-Modulo: External Verifier Pattern

LLMs can't self-verify planning. Solution: use a second process as verifier.

```
Agent → proposes plan → External checker (DB query / file check / curl health) 
     → Validator returns PASS/FAIL/ADJUST
     → Agent adjusts and re-proposes (max 3 rounds)
     → If 3 rounds fail → escalate to COO-PLAYBOOK.md error tier
```

**Apply to OpenClaw immediately:**
- Before executing any multi-step build task, verify prerequisites exist (files, services, ports)
- After each task completes, run a verification command — not just assume done
- Store verification results in the task record, not just task status

### Blocker-First Rule

When a STATUS file shows both pending tasks AND blockers:
→ **ALWAYS resolve blockers before advancing tasks**
→ LocalComm example: `src/app/api/bie.ts` is blocking 1.1.3 and 1.1.4
→ Correct action: create the endpoint FIRST, then move to 1.1.3 AI context integration

*Applied: 2026-03-19 | Source: LangChain planning post + LLM-Modulo arXiv paper*

---

## PATTERN 10: Model-Tier Routing
*Source: Anthropic "Building Effective Agents" (2024) + Chip Huyen "AI Engineering" (2025)*

Route tasks to the appropriate model tier based on complexity and stakes:

```
ROUTING LOGIC:
  Complexity LOW  → Qwen3.5-0.8B (:8081) — simple fills, formatting, lookups
  Complexity MED  → Qwen3 30B (:8080)    — drafts, analysis, structured generation
  Complexity HIGH → Claude Sonnet        — strategy, client proposals, contracts

ROUTING HEURISTICS:
  - Input < 200 tokens AND deterministic output → fast tier
  - Requires domain reasoning or personalization → mid tier
  - Irreversible external action (email send, contract) → slow + verification gate
  - Any task touching money, clients, or public brand → slow + human gate

IMPLEMENTATION (for Paperclip agent heartbeats):
  tier = "fast" if len(task_input) < 200 and task_type in ["format","summarize","tag"] else
         "slow" if task_type in ["outreach","proposal","strategy"] else "mid"
  endpoint = TIER_MAP[tier]  # {fast: :8081, mid: :8080, slow: :8080 + extra_temp_samples}
```

**Anti-pattern:** Routing ALL tasks through the 30B model. Costs 10x more, adds 3x latency,
no quality gain on simple fills. Route aggressively.

*Applied: 2026-03-20 | Source: Anthropic routing workflow pattern*

---

## PATTERN 11: Multi-Sample Voting for High-Stakes Output
*Source: Anthropic "Building Effective Agents" (2024) — Parallelization/Voting workflow*

For outputs that are costly to get wrong (cold outreach subject lines, ad copy, pricing proposals):
run the same generation N=3 times, then pick the winner programmatically or via a fast judge call.

```
VOTING PROTOCOL:
  1. Generate N=3 variants (temperature 0.7, 0.9, 1.1)
  2. Score each variant on rubric: relevance, specificity, CTA clarity, tone
  3. Pick highest-scoring OR have fast model (0.8B) act as judge with rubric
  4. Log: which variant won + why → feed back into prompt improvement

WHEN TO APPLY:
  - Cold outreach subject lines (open rate is fragile — 1 word can tank it)
  - Ad hooks / creative angles (multiple framings = higher hit rate)
  - Review responses for 1-2 star reviews (reputational stakes)

COMPOUND ERROR MITIGATION:
  At 95% accuracy/step, 10-step pipeline = 60% end-to-end accuracy.
  Voting on the FINAL step alone recovers ~15pp accuracy at 3x cost of that step.
  For 5+ step pipelines: add intermediate verification gates at step 2-3 AND final.

IMPLEMENTATION:
  curl -s -X POST http://localhost:8042/generate \  # COPYCAT agent
    -d '{"task": "...", "n_samples": 3, "temperatures": [0.7, 0.9, 1.1]}'
  # then POST to /judge with the 3 outputs + rubric
```

*Applied: 2026-03-20 | Source: Anthropic parallelization + voting workflow*

---

## PATTERN 12: Reflexion Loop — Detect and Break Stagnation Cycles
*Source: Reflexion paper (Shinn & Labash, 2023) + Lilian Weng agent survey*

Agents get stuck in hallucination loops: same action → same observation → same action.
Implement a heuristic that detects this and forces a reflection + plan reset.

```python
# Pseudo-code for loop detection
action_history = deque(maxlen=6)

def check_for_loop(action, observation):
    action_history.append((action, observation[:50]))
    # Detect: same (action, obs) pair appearing ≥2 times in last 6 steps
    seen = {}
    for item in action_history:
        seen[item] = seen.get(item, 0) + 1
        if seen[item] >= 2:
            return True  # LOOP DETECTED
    return False

def handle_loop():
    # 1. Stop the current trajectory
    # 2. Synthesize: "I've tried X twice and gotten Y. Why isn't it working?"
    # 3. Generate alternative approach (temperature +0.3)
    # 4. Log the failed trajectory to episodic memory
    # 5. Resume with new plan
    pass
```

**For SearXNG specifically:** If 2 searches return < 3 results, switch to web_fetch on
top 3 known sources directly. Never run >3 SearXNG searches on the same query.

*Applied: 2026-03-20 | Source: Reflexion framework + observed SearXNG rate-limit pattern*

---

## PATTERN 13: Three-Layer Agent Specialization (Worker / Service / Support)
*Source: arxiv 2601.13671 — "The Orchestration of Multi-Agent Systems" (2026)*

Modern MAS decomposes agents into three tiers by function — not just by domain:

```
WORKER AGENTS     → Execute narrowly scoped tasks. 
                    Stateless (each req independent) OR stateful (track workflow progress).
                    Examples: SCOUT (scraping), COPYCAT (writing), SEO (optimization).
                    Run in parallel. Feed outputs downstream.

SERVICE AGENTS    → Shared operational utilities other agents depend on.
                    QA, compliance enforcement, diagnostics, auto-recovery (healing agents).
                    Examples: QA:8054 (content gate), SENTINEL:8045 (monitoring).
                    Don't produce business output — they protect quality of output.

SUPPORT AGENTS    → Meta-level supervisory oversight. NOT in-line execution.
                    Monitor behavior, analyze outcomes, manage data flows for orchestration.
                    Examples: REPORTER:8046 (analytics), ORCHESTRATOR:8040 (control plane).
                    Track drift, latency, anomalies. Feed back to planning unit.
```

**OpenClaw Application:**
- When an agent is "down", classify it: if Worker → find substitute or degrade gracefully.
  If Service (QA/Sentinel) → BLOCK pipeline. Cannot ship unvalidated output.
  If Support (Reporter) → continue but log degraded observability.
- Assign each Paperclip agent to exactly one tier on boot. Store in agent roster.
- Healing agents (Service tier) should be the FIRST thing auto-recovered — they protect all other tiers.

**Planning Unit / Policy Unit split (orchestration layer):**
- Planning Unit = what tasks, what order, which agent gets them (ORCHESTRATOR's job)
- Policy Unit = constraints, governance, quality gates (QA + SENTINEL's job)
- These must be separate. Conflating them causes the orchestrator to both plan AND judge — degrades both.

**Telemetry → Control feedback loop:**
```
Worker executes → Support agent collects telemetry → Control unit detects deviation
  → Service agent (healer/validator) remediates → Worker resumes with corrected state
```

*Applied: 2026-03-21 | Source: arxiv 2601.13671v1 multi-agent orchestration paper*

---

## PATTERN 14: MCP + A2A Protocol Separation
*Source: arxiv 2601.13671 — enterprise MAS protocols*

Two protocols govern agent communication in enterprise-grade systems — and they serve different purposes:

```
MCP (Model Context Protocol)
  → Agent ↔ External tools/data
  → Standardizes HOW agents access context: databases, APIs, file systems
  → Think: "what does this agent know about the world right now?"
  → In LocalLoop: each agent's curl calls to Paperclip API, SearXNG, SQLite = MCP layer

A2A (Agent-to-Agent Protocol)  
  → Agent ↔ Agent
  → Governs peer coordination, task delegation, negotiation
  → Think: "how does ORCHESTRATOR hand work to SCOUT and get results back?"
  → In LocalLoop: the /heartbeat POST to each port IS our A2A layer
```

**Why this matters for LocalLoop:**
1. MCP failures (SearXNG down, DB timeout) = individual agent degraded. Others unaffected.
2. A2A failures (agent port down) = cascade risk. ORCHESTRATOR can't delegate.
3. Build A2A with retry + fallback: if SCOUT:8041 is down, ORCHESTRATOR falls back to
   direct web_fetch instead of blocking the entire pipeline.
4. Keep MCP (external tool access) stateless where possible — idempotent retries are safe.
5. A2A (inter-agent calls) must be idempotent OR use task IDs to prevent duplicate execution.

**Task ID pattern for A2A:**
```bash
TASK_ID="task-$(date +%s)-scout-$(echo $QUERY | md5sum | cut -c1-6)"
curl -X POST http://localhost:8041/heartbeat \
  -d "{\"task\": {\"id\": \"$TASK_ID\", \"type\": \"research\"}, ...}"
# Same task_id = idempotent. Agent logs it and skips if already done.
```

*Applied: 2026-03-21 | Source: arxiv 2601.13671v1 — MCP + A2A protocol delineation*

---

## PATTERN 15: Workflow vs. Agent Decision Matrix
*Source: Anthropic Engineering — Building Effective Agents (2025/2026 production guide)*

The core mistake: defaulting to "agent" when a workflow is faster, cheaper, and more reliable.

**Decision rule:**
```
Is the task structure KNOWN in advance?
  YES → Use a WORKFLOW (prompt chain, routing, parallelization)
  NO  → Use an AGENT (orchestrator-workers, dynamic planning)

Can I predict the subtasks?
  YES → Workflow. Predefined steps = lower latency + higher consistency.
  NO  → Agent. Flexibility needed.

Does this need model-driven judgment at each step?
  YES → Agent.
  NO  → Workflow or single optimized LLM call.
```

**Five workflow types (in order of complexity):**
1. **Prompt Chain** — sequential LLM calls, each building on previous output + gate checks
   → Use for: outreach email generation, lead enrichment pipeline, content approval flow
2. **Routing** — classify input, direct to specialized handler
   → Use for: lead quality → tier routing (cold/warm/hot), issue type → right agent port
3. **Parallelization (Sectioning)** — split task into independent parallel subtasks
   → Use for: scoring 50 leads simultaneously, running SEO analysis across 10 pages
4. **Parallelization (Voting)** — same task N times, aggregate for confidence
   → Use for: content QA (run 3 quality checks, flag if any fail), proposal scoring
5. **Orchestrator-Workers** — dynamic task decomposition by central LLM
   → Use for: multi-file code changes, multi-source research with unknown subtask count

**LocalLoop mapping:**
- ORCHESTRATOR:8040 = Orchestrator-Workers pattern
- SCOUT:8041 + COPYCAT:8042 run in parallel = Sectioning pattern
- QA:8054 reviewing CREATIVE:8048 output = Evaluator-Optimizer (see PATTERN 16)
- INTAKE:8053 classifying leads = Routing pattern

**Key insight from Anthropic:** "Many applications... optimizing single LLM calls with retrieval
and in-context examples is usually enough." Don't over-architect. Start simple, add complexity
only when the simpler version demonstrably fails.

*Applied: 2026-03-21 | Source: anthropic.com/engineering/building-effective-agents*

---

## PATTERN 16: Evaluator-Optimizer Loop
*Source: Anthropic Engineering — Building Effective Agents (2025/2026 production guide)*

One LLM generates output. A SEPARATE LLM evaluates it and provides feedback. Loop until
evaluation passes or max iterations hit.

**When to use:**
- Output quality can be evaluated against clear criteria
- Iterative improvement demonstrably adds value
- A human COULD articulate feedback to improve the output (if yes → LLM can too)

**Implementation pattern:**
```python
MAX_ITER = 3
output = generator_llm(task)
for i in range(MAX_ITER):
    eval_result = evaluator_llm(output, criteria)
    if eval_result["pass"]:
        break
    output = generator_llm(task, feedback=eval_result["feedback"])
# Always exit after MAX_ITER — never infinite loop
```

**LocalLoop applications:**

1. **Outreach email generation** (COPYCAT:8042 → QA:8054 → COPYCAT:8042):
   - Criteria: personalization score > 7/10, no generic phrases, correct business name, 
     clear CTA, < 150 words
   - Max 2 refinement cycles before human review

2. **Content approval** (CREATIVE:8048 → QA:8054 → CREATIVE:8048):
   - Criteria: brand voice match, factual accuracy, CTA present, no forbidden phrases
   - Max 2 refinement cycles

3. **SEO page copy** (SEO:8049 → evaluator → SEO:8049):
   - Criteria: keyword density, readability score, meta description length
   - Max 3 refinement cycles

4. **Complex search tasks** (SCOUT:8041 searching → evaluator checking coverage gaps):
   - Evaluator decides if another search round is warranted
   - Max 4 rounds before forcing synthesis with available data

**Critical guardrails:**
- ALWAYS set MAX_ITER (default: 3). No infinite evaluator loops.
- Track cycle count in task metadata.
- If MAX_ITER reached and still failing: escalate to human review queue, don't silently pass.
- Evaluator should output structured JSON: `{"pass": bool, "score": 0-10, "feedback": "..."}`

**Anti-pattern:** Using the SAME LLM call to both generate AND evaluate. Self-evaluation has
systematic blind spots — the same biases that caused the error will cause it to miss the error.
Separate models or separate prompts with explicit critic role are both valid.

*Applied: 2026-03-21 | Source: anthropic.com/engineering/building-effective-agents*

---

## PATTERN 17: Autonomous Error Recovery — Five-Stage Self-Healing Cycle
*Source: Zylos AI Research, Feb 2026 + fast.io retry patterns guide*

**Context:** 67% of AI system failures stem from improper error handling, not algorithmic issues.
Self-healing implementations achieve 60% reduction in system downtime.

### The 5-Stage Cycle (Apply to Every Agent)

```
DETECT → DIAGNOSE → REPAIR → VALIDATE → ADAPT
```

| Stage | What | OpenClaw Implementation |
|-------|------|------------------------|
| **DETECT** | Heartbeat + watchdog liveness check | `curl localhost:{PORT}/health` every 6h cron |
| **DIAGNOSE** | Classify error type (transient vs. persistent) | HTTP code: 429/5xx=transient, 4xx=logic error |
| **REPAIR** | Apply predefined recovery response | See circuit states below |
| **VALIDATE** | Re-test after repair | Hit `/health` again, check output quality |
| **ADAPT** | Store lesson for next occurrence | Append to memory/YYYY-MM-DD.md + MEMORY.md |

### Error Classification (Do This First)

```
TRANSIENT (retry ok):   HTTP 429, 500, 502, 503, 504, network timeout, rate limit
LOGIC ERROR (retry won't help): HTTP 400, 401, 403, schema validation fail, context overflow
PERSISTENT (circuit break): >3 consecutive transients in 5 min window
```

**Rule:** Never retry a logic error. It wastes tokens and always fails identically.
**Rule:** Never retry more than 3x on transients without backoff. You'll amplify the outage.

### Exponential Backoff with Jitter (The Default for ALL Transient Retries)

```python
# Formula: wait = (base × 2^attempt) + random(0, jitter_max)
# Example sequence: 1s → 2.3s → 4.7s → 9.1s → FAIL/escalate
base_delay = 1.0
jitter_max = 0.5
max_attempts = 4
max_delay = 30.0

wait = min(base_delay * (2 ** attempt) + random(0, jitter_max), max_delay)
```

Why jitter? Without it, all retrying agents fire simultaneously → thundering herd → amplified outage.
AWS research: jitter reduces retry storms 60-80%.

### Circuit Breaker for Paperclip Agents

```
CLOSED (normal):    Pass requests through. Count failures.
OPEN (>3 fails/5min): Fail fast. Don't even try. Return cached/default result.
HALF-OPEN (after 60s cooldown): Send ONE test request. 
  → Success: close circuit, resume normal flow
  → Failure: reset timer, stay open
```

**Apply to LocalLoop agents (ports 8040-8054):**
- If agent at port X fails 3 consecutive health checks → mark OPEN in heartbeat-state.json
- After 60s → send one test task → if 200 → CLOSED, else extend cooldown to 120s
- Alert Pat via Telegram only if agent stays open > 10 minutes

### Dual Liveness: Heartbeat + Watchdog

**Heartbeat** (what we have): periodic signal confirms agent is alive and responsive.
**Watchdog** (add this): agent must reset a timer within N seconds or gets auto-restarted.

```bash
# Watchdog pattern for Paperclip agents — launchd KeepAlive already does this
# But for Python agent processes: use a watchdog thread that kills/restarts if no progress in 5min
# Implementation: write timestamp to /tmp/agent_{port}.watchdog every major step
# Monitor cron: if timestamp > 5 min old → kill -9 process → restart
```

### Graceful Degradation Hierarchy

When an agent is down, don't block. Degrade gracefully:

```
Tier 1: Primary agent healthy → full quality output
Tier 2: Primary down → route to backup model (LM Studio 0.8B instead of 30B)
Tier 3: LM Studio down → use cached/template response
Tier 4: All inference down → log to queue, process when service recovers
Tier 5: Queue full → notify Pat, pause intake, don't lose data
```

**Key insight:** Incomplete output with degraded quality > complete blockage. 
A Tier 3 template email that goes out beats a perfect email that never sends.

### Fallback Model Chain (LocalLoop specific)

```
Primary: Qwen3 30B on :8080 (quality tasks: copywriting, strategy, proposals)
Fallback 1: Qwen3.5 0.8B on :8081 (speed tasks: classification, simple edits)  
Fallback 2: OpenClaw Claude via API (if local inference fully down)
Fallback 3: Template/cached response (if all inference down)
```

*Applied: 2026-03-22 | Source: zylos.ai/research + fast.io/resources/ai-agent-retry-patterns*

---

## PATTERN 18: Agent Memory Architecture — Four-Tier State Management

*Research: E-mem (arXiv:2601.21714, Jan 2026) + ACON Context Compression (arXiv:2510.00615, Oct 2025)*
*Applied: 2026-03-22*

### The Core Problem

LLM agent context windows fill up over long sessions. When they fill:
1. Quality degrades silently (model starts ignoring early context)
2. Costs spike (tokens are expensive at scale)
3. Logic coherence breaks (sequential dependencies get severed)

**Most naive approaches destroy contextual integrity** — compressing a 500-step interaction history into embeddings severs the logical chain that makes deep reasoning possible. E-mem (2026) shows this is the fundamental failure mode.

### Four-Tier Memory Architecture

```
TIER 1: Working Memory (In-context)
  What: Active task state, immediate observations, current tool results
  Size: <20% of context window (leave room for reasoning + output)
  TTL: Current task only — evict when task complete
  Example: Current lead being researched, live API response, active error state

TIER 2: Episodic Memory (Recent History — Compressed)
  What: Last N sessions/cycles compressed via ACON-style summarization
  Size: 10-15% of context window
  Compression: Reduce 26-54% peak tokens while preserving 95%+ accuracy (ACON result)
  Example: "Session 2026-03-21: Researched 12 plumber leads, sent 8 outreach emails, 2 bounced"
  Implementation: Write to memory/YYYY-MM-DD.md, load summary at session start

TIER 3: Semantic Memory (Distilled Knowledge — External)
  What: Cross-session learnings, patterns, playbooks, client facts
  Storage: Files (AGENT-PATTERNS.md, COO-PLAYBOOK.md, leads.md, brand profiles)
  Access: Explicit file read, NOT in context by default
  Example: Outreach templates, client brand profiles, competitive intel
  Rule: Only load into context when directly relevant to current task

TIER 4: Archival Memory (Full History — Cold)
  What: Complete uncompressed logs, all past outputs, raw data
  Storage: Database (agency_state.db), log files, git history
  Access: Query on demand, never loaded wholesale
  Example: Every email ever sent, every lead ever researched
```

### ACON-Style Context Compression (Implement This)

ACON compresses 26-54% of peak tokens with <5% performance loss. Key insight: compression guidelines are optimized in **natural language**, not via embeddings.

```bash
# Session end compression (run after each session):
# 1. Identify what was accomplished (actions taken)
# 2. Extract decisions made and their outcomes
# 3. Distill to: WHAT happened | WHY it mattered | WHAT changed | NEXT action

# Template for compression:
SESSION_SUMMARY="
DATE: $(date -u '+%Y-%m-%d')
COMPLETED: [list of completed actions]
KEY DECISIONS: [decisions made + rationale]
OUTCOMES: [measurable results]
STATE CHANGES: [files created/modified, leads added, agents fixed]
BLOCKERS CLEARED: [what was unblocked]
NEXT: [highest priority next action]
"
```

### E-mem Pattern: Assistant Agents Hold Context Shards

For the LocalLoop multi-agent architecture, this maps directly:

```
MASTER AGENT (OpenClaw CEO): Global planning only. Minimal context load.
  → Does NOT hold all conversation history
  → Holds: current objective, current blocker, agent roster, evolution state

ASSISTANT AGENTS (Paperclip agents): Hold their domain context uncompressed
  → SCOUT:8041 holds full lead research context for active leads
  → COPYCAT:8042 holds brand voice + all past copy for active client
  → QA:8054 holds quality criteria + past failure modes
  → Each agent's context is isolated — failures don't contaminate others
```

**This is already how Paperclip is architected. Use it intentionally.**

### Context Budget Rules (Enforce These)

```
Working Memory Budget: 20% of context window
  → Trim immediately when exceeded: oldest observations out first
  → Never let tool results accumulate unbounded across iterations

Episodic Load Rule: Load ONLY last 3 sessions into context
  → Sessions 4-10: load compressed summary only (1-2 sentences each)
  → Sessions 11+: archival, load only if specifically queried

Semantic Load Rule: "Just in time" loading only
  → Load AGENTS.md when orchestrating agents
  → Load brand profile when generating content
  → Do NOT load everything at once — that's context waste
  
The 80% Rule: If context >80% full, STOP adding — compress first, then continue
  → Trigger: estimate token count before each major operation
  → Action: summarize completed work into 3 sentences, clear history
```

### Failure Mode: Context Contamination

Symptom: Agent starts contradicting earlier instructions or "forgetting" constraints.
Cause: Too much accumulated context, early messages pushed out of effective attention.

```bash
# Detection: If same error repeats after being fixed 2+ times → context contaminated
# Fix: 
# 1. Write complete current state to file
# 2. Start fresh context loading only the state file
# 3. Do NOT try to "remind" the model of prior context inline — it won't work
```

### Implementation Checklist for LocalLoop Sessions

```
[ ] Session start: Load ONLY — evolution state, today's memory file, current blocker
[ ] Every 10 cycles: Compress completed work to 3-sentence summary, clear from working memory  
[ ] Task complete: Write outcome to daily memory file before moving to next task
[ ] Session end: Run full ACON-style compression → write to memory/YYYY-MM-DD.md
[ ] Context >80%: Emergency compress → summarize → continue, do NOT abandon task
[ ] Agent errors: Route to specific Paperclip agent — do NOT dump their context into CEO context
```

*Key numbers: ACON achieves 26-54% token reduction with 95%+ task accuracy preserved. E-mem distributed architecture eliminates single-context-window bottleneck entirely.*


---

## PATTERN 19: Long-Horizon Task Decomposition — Plan-Act-Correct-Verify Loop
*Sources: Plan-and-Act (ICML 2025, arXiv:2503.09572), EPO (EMNLP 2024, arXiv:2408.16090), TMS (ScienceDirect 2026), ChatHTN (arXiv:2505.11814), LLaMAR (NeurIPS 2024), yWian Playbook*

### The Core Problem
Long-horizon tasks (multi-step builds, SaaS feature epics, multi-day campaigns) fail because:
- **Compounding error**: At 95% step accuracy, a 20-step pipeline has only 36% end-to-end success
- **Plan rigidity**: Static plans break on first unexpected observation
- **Context drift**: LLM context windows fill up mid-execution, losing early decisions
- **No verification**: Steps "succeed" without confirming actual outcomes

### The Four-Module Architecture

Every long-horizon task decomposes into four cooperating modules:

```
┌──────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐
│ PLANNER  │───>│  ACTOR   │───>│ CORRECTOR │───>│ VERIFIER │
│          │<───│          │<───│           │<───│          │
└──────────┘    └──────────┘    └───────────┘    └──────────┘
     ↑                                                │
     └────────────── replan if verify fails ──────────┘
```

**PLANNER** — Decomposes goal into ordered subgoals with preconditions and success criteria
**ACTOR** — Executes one subgoal at a time, produces observations
**CORRECTOR** — Detects failures, proposes retries or alternative approaches
**VERIFIER** — Confirms subgoal completion against success criteria before advancing

### The Five Decomposition Rules

1. **Subgoal Independence Test**: Each subgoal should be testable in isolation. If you can't write a verification check for it, decompose further.

2. **Token Budget Rule**: No single subgoal's execution should exceed 60% of context window. If it will, split it.

3. **Checkpoint-and-Resume**: Every subgoal must produce a serializable state artifact (file, DB row, git commit). If the agent crashes mid-pipeline, it resumes from the last checkpoint, not from scratch.

4. **Precondition Gates**: Each subgoal declares what must be true before it starts. The Planner verifies preconditions before dispatching to Actor. Failed precondition = replan, not force.

5. **Replanning Triggers**: Replan when: (a) >2 consecutive subgoal failures, (b) new information invalidates remaining plan, (c) 50%+ of estimated time consumed with <30% progress.

### Hierarchical Decomposition (HTN-inspired)

For complex builds (like LocalComm SaaS), use three levels:

```
EPIC (goal)
  └── MILESTONE (verifiable checkpoint — deploys, passes tests, ships feature)
       └── TASK (single agent action — write file, run test, make API call)
```

**Rules:**
- EPICs have 3-7 milestones (more = too vague, fewer = too monolithic)
- MILESTONEs have 3-10 tasks (more = needs sub-milestone)
- TASKs are atomic: one exec call, one file write, one API request
- Every MILESTONE ends with a verification step (test passes, endpoint responds, UI renders)

### Plan Representation Format

Use token-efficient structured plans:

```
GOAL: Deploy BIE dashboard feature
MILESTONE 1: Data layer [precond: DB accessible] [verify: migration runs, API returns data]
  T1.1: Write D1 migration for business_profiles table
  T1.2: Create API route /api/bie with POST handler
  T1.3: Run migration, verify with SELECT COUNT(*)
MILESTONE 2: UI layer [precond: M1 verified] [verify: page renders at /dashboard/bie]
  T2.1: Create BIE dashboard component
  T2.2: Wire API calls with SWR/fetch
  T2.3: Visual verification (screenshot or DOM check)
MILESTONE 3: Integration [precond: M1+M2 verified] [verify: e2e test passes]
  T3.1: Write integration test
  T3.2: Run full e2e flow
  T3.3: Deploy to preview environment
```

### Corrector Patterns (when things go wrong)

| Failure Type | Corrector Action |
|---|---|
| Syntax/build error | Auto-fix with error context, retry once |
| Test failure | Inspect assertion, adjust implementation, retry |
| Timeout | Reduce scope of subgoal, retry with simpler approach |
| Dependency missing | Install/configure dependency, retry from precondition check |
| Repeated failure (3+) | Escalate to Planner for replan — this subgoal decomposition is wrong |

### Anti-Patterns to Avoid

1. **Mega-Plan**: Planning 50+ steps upfront. Plans beyond 10 steps are fantasies. Plan 3-7 steps, execute, replan.
2. **Blind Execution**: Running all tasks without checking intermediate results. Always verify between milestones.
3. **Sunk Cost Persistence**: Retrying the same failing approach 5+ times. After 2 failures, switch strategy.
4. **Context Stuffing**: Keeping all previous step outputs in context. Summarize completed milestones into one-line status, drop raw output.
5. **No Checkpoints**: Doing 30 minutes of work with no serialized state. If the session crashes, everything is lost.

### LocalLoop Application

```
OpenClaw (CEO) = PLANNER + VERIFIER
Sub-agents (Codex/Claude Code) = ACTOR
Error recovery (Pattern 17) = CORRECTOR
Git commits between milestones = CHECKPOINTS

Current mapping:
- LocalComm SaaS build → EPIC with ~5 milestones
- Each heartbeat cycle → Plan 1-2 milestones, verify previous
- Agent spawns → One ACTOR per milestone, not per task
- Failure → Circuit breaker (Pattern 17) + replan
```

### Problem-Agent Fit Checklist (5/5 = use this pattern)

- [ ] Task needs >5 ordered steps with dependencies
- [ ] Environment state changes during execution (deploys, API responses)
- [ ] Intermediate results can be verified with concrete checks
- [ ] Budget allows for retries (compute, time, tokens)
- [ ] Some non-determinism is acceptable in early iterations

