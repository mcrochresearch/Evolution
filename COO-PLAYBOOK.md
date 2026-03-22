# COO PLAYBOOK — Autonomous Error Recovery & Operational Resilience
*OpenClaw | Last updated: 2026-03-19*

---

## CORE PRINCIPLE: Simplicity Beats Complexity

From Anthropic's production agent research: **The most successful agent implementations use simple, composable patterns — not complex frameworks.** Every abstraction layer you add is a failure surface. Prefer direct API calls + explicit retry logic over "magic" orchestration.

---

## PATTERN 1: Tiered Error Recovery (Apply to Every Agent Call)

When any agent, service, or tool fails, don't treat all failures the same. Classify and respond:

```
TIER 1 — TRANSIENT (retry immediately, same approach)
  Symptoms: HTTP 429, 503, timeout, connection refused (service starting up)
  Response: wait 5s, retry up to 3x with exponential backoff (5s → 15s → 45s)
  Example: curl to port 8042 returns 503

TIER 2 — STRUCTURAL (retry with modified approach)
  Symptoms: HTTP 400, 422, malformed response, wrong schema
  Response: simplify the task, reduce payload, check config, retry once
  Example: Paperclip agent returns 400 on oversized task payload

TIER 3 — FATAL (fix root cause, then retry)
  Symptoms: Process not found, port not bound, missing file/key
  Response: fix the underlying issue (restart service, repair file, set env var), then retry
  Example: port 8044 DOWN because plist misconfigured → fix plist → launchctl reload → retry

TIER 4 — ESCALATE (log, notify Pat, move on)
  Symptoms: 3+ consecutive FATAL failures, data corruption, auth failure after key rotation
  Response: log with full context, Telegram Pat one line, continue other work
  Example: Paperclip API returns 401 after key rotation → needs manual key update
```

**The rule:** Never fail silently. Never retry infinitely. Always classify before acting.

---

## PATTERN 2: Graceful Degradation for Research/Search

SearXNG external engines go down (rate-limited, suspended). Don't abort the research cycle.

**Fallback chain for any research task:**
```
1. SearXNG (primary) → curl http://127.0.0.1:8888/search?q=...&format=json
2. If 0 results → web_fetch on 3-5 known high-value URLs directly:
   - https://www.anthropic.com/engineering/building-effective-agents
   - https://lilianweng.github.io/posts/2023-06-23-agent/
   - https://martinfowler.com/articles/patterns-of-distributed-systems/
   - https://hbr.org/topic/subject/saas (for SaaS strategy)
   - https://www.paulgraham.com/essays.html (for startup/growth)
3. If web_fetch fails → synthesize from existing RESEARCH-LEARNINGS.md + internal knowledge
4. NEVER return "search unavailable" — always produce 3 insights minimum
```

This cycle used fallback chain #2 and still produced actionable output. Degradation = success, not failure.

---

## PATTERN 3: Checkpoint-Before-Risk

Before any irreversible operation, snapshot current state. Already in evolution engine (`./engine/evolve checkpoint`) — apply this MORE BROADLY:

```bash
# Before editing agent configs
cp ~/shellcorp/paperclip-integrations/agent.json ~/shellcorp/paperclip-integrations/agent.json.bak.$(date +%Y%m%d%H%M)

# Before DB migrations
sqlite3 $DB ".backup $DB.bak.$(date +%Y%m%d%H%M)"

# Before restarting critical services
curl -s http://localhost:PORT/health > /tmp/pre-restart-health.json

# Before SOUL/config changes
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak.$(date +%Y%m%d%H%M)
```

**Rule:** If you can't undo it in 30 seconds, checkpoint first.

---

## PATTERN 4: Verification Gate (Every Action)

A task is NOT done until verified with exec. Build verification into every action:

| Action | Verification Command |
|--------|---------------------|
| File written | `wc -l FILE && head -3 FILE` |
| Service restarted | `curl -s localhost:PORT/health` |
| DB updated | `sqlite3 $DB "SELECT COUNT(*) FROM table WHERE updated_at > datetime('now','-1 minute')"` |
| Email/outreach queued | Check queue endpoint or log file |
| Cron job added | `crontab -l | grep JOB_NAME` |
| Config changed | Restart service, hit endpoint, confirm behavior |

**If you can't verify → the task didn't happen.**

---

## PATTERN 5: Self-Healing Boot Sequence

On every boot, run health checks in parallel, not serially. Fix first, report second.

```bash
# Check all 18 agent ports in 3 seconds (not one at a time)
for port in 8040..8054 8023 8024 8025; do
  (curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://localhost:$port/health && echo "$port OK" || echo "$port DOWN") &
done
wait

# If any DOWN: check logs, restart, verify — THEN report
# Don't report before fixing
```

---

## PATTERN 6: Task Decomposition for Long-Horizon Work

From Lilian Weng / Anthropic research: Large tasks need explicit subgoal trees, not linear plans.

**Format for any task > 2 hours of agent work:**

```
GOAL: [One sentence]
SUCCESS METRIC: [Measurable — revenue, installs, uptime %, etc.]

PHASE 1 (foundation): [deliverable + verification]
  └─ Task 1.1: [atomic, 1 agent, < 30min]
  └─ Task 1.2: [atomic, depends on 1.1 output]
  └─ GATE: [exec command that proves phase 1 done]

PHASE 2 (build): [deliverable + verification]
  └─ Task 2.1: [can run parallel with 2.2]
  └─ Task 2.2: [can run parallel with 2.1]
  └─ GATE: [exec command that proves phase 2 done]

PHASE 3 (ship): [deliverable + verification]
  └─ GATE: [user-observable outcome]
```

**Key:** Gates are executable. Not "probably done" — `curl /health` returns 200 done.

---

## PATTERN 7: Prioritization Framework (ICE + Urgency)

When task queue has > 5 items and unclear order:

```
SCORE = (Impact × Confidence × Ease) + Urgency_Bonus

Impact (1-10): How much does this move the mission metric? ($ARR, clients, uptime)
Confidence (1-10): How sure am I this will work as expected?
Ease (1-10): How fast can I complete + verify?
Urgency_Bonus (+50): Add if blocking another agent, client-facing, or SLA breach

Top score = next action. No debate. Execute.
```

**Example:**
- Fix broken review_monitor agent: I=8, C=9, E=7 + Urgency=50 → **Score: 554** → DO FIRST
- Research new vertical: I=6, C=5, E=6 → **Score: 180** → DO AFTER

---

## META-RULE: Failure Is Data, Not Defeat

Every failure produces a pattern update. When something breaks:
1. Fix it (< 5 min)
2. Add the root cause + fix to this playbook (< 2 min)
3. Add a verification gate so it can't silently break again
4. Move on

Failures that don't generate playbook updates are wasted failures.

---

*Applied from: Anthropic Building Effective Agents blog, Lilian Weng LLM Agents post, self-healing infrastructure research, AutoAct division-of-labor paper*

---

## PATTERN 8: WSJF — Weighted Shortest Job First (Upgrade from ICE)

*Research synthesis: 2026-03-20 | Source: SAFe framework + Don Reinertsen "Principles of Product Development Flow" + Cost of Delay theory*

**ICE is wrong for autonomous systems.** ICE ignores time value — a task scored 180 today might be worth 360 tomorrow if the window closes. WSJF fixes this by making Cost of Delay explicit.

**Formula:**
```
WSJF = Cost_of_Delay / Job_Duration

Cost_of_Delay = User_Value + Time_Criticality + Risk_Reduction_or_Opportunity_Enablement

Scoring scale (1, 2, 3, 5, 8, 13, 20) — Fibonacci, relative not absolute.
```

| Component | What It Measures | Example |
|-----------|-----------------|---------|
| **User Value** | Revenue/retention impact if done now vs. later | Client onboarding: 13 |
| **Time Criticality** | How fast does value decay if delayed? | Lead follow-up (24h window): 20 |
| **Risk Reduction / Opportunity Enablement** | Does this unblock other work or remove downside risk? | Fix broken email agent (blocks outreach): 13 |
| **Job Duration** | Relative effort — how long to complete + verify? | 30min task: 2, half-day: 5, full-day: 8 |

**Example queue scoring:**
```
Task A: Fix broken review_monitor (blocks client SLA)
  CoD = 8 (value) + 13 (time-critical) + 13 (unblocks) = 34
  Duration = 2 (30min fix)
  WSJF = 34/2 = 17.0 ← DO FIRST

Task B: Research new vertical (plumbers)
  CoD = 5 (value) + 2 (not urgent) + 3 (enables future) = 10
  Duration = 3 (90min deep research)
  WSJF = 10/3 = 3.3 ← do later

Task C: Send follow-up to warm lead (24h window closing)
  CoD = 8 (close value) + 20 (expires in hours) + 3 = 31
  Duration = 1 (5min email)
  WSJF = 31/1 = 31.0 ← DO BEFORE Task A if truly < 5min
```

**Key insight:** WSJF automatically deprioritizes big speculative projects vs. small high-CoD tasks. The shortest job that prevents the most delay always wins.

---

## PATTERN 9: Entropy-Aware Scheduling

Some tasks rot. They get harder, more expensive, or impossible the longer they wait.

**Entropy multiplier — apply to WSJF Time_Criticality component:**

```
ENTROPY CLASS       DECAY RATE    TIME_CRITICALITY MULTIPLIER
Perishable          Hours         ×3 (leads, time-sensitive follow-ups, error spikes)
Degrading           Days          ×1.5 (infrastructure drift, stale configs, low reviews)
Stable              Weeks         ×1 (feature builds, research tasks)
Appreciation        —             ×0.5 (deferred = more info = better decision)
```

**Perishable tasks (do TODAY, not "eventually"):**
- Lead follow-up after inquiry or demo (> 24h = 80% conversion drop)
- Negative review response (> 48h = visible abandonment to other readers)
- Agent error accumulation (cascading failures, > 4h backlog = data loss)
- Session-critical research (context evaporates after 48h without application)

**Appreciation tasks (intentionally defer):**
- Architecture decisions with missing info → wait for data
- Vendor selection before having clear requirements → wait for client feedback
- Scaling decisions before hitting actual limits → don't pre-optimize

**Rule:** On every boot, scan for perishable tasks FIRST. They trump WSJF score.

---

## PATTERN 10: Type 1 / Type 2 Decision Router

*From Bezos "Day 1 vs Day 2" framework, adapted for autonomous agents*

Two-question test before every action:

```
Q1: Is this reversible in < 5 minutes?
Q2: Does failure affect live users, money, or reputation?

          | Reversible | Irreversible |
Contained |  TYPE 2    |   TYPE 2+    |
External  |  TYPE 2+   |   TYPE 1     |
```

**TYPE 2 (most things): Decide fast, execute, measure.**
- File edits, internal config changes, draft outreach, agent restarts
- Threshold: < 1 second decision time. Don't overthink.
- Failed TYPE 2 → fix it in < 5 min and move on.

**TYPE 2+ (moderate stakes): Checkpoint first, then execute.**
- DB migrations, production config changes, agent prompt updates
- Rule: `./engine/evolve checkpoint "before [action]"` then proceed
- Failed TYPE 2+ → `./engine/evolve revert` and diagnose

**TYPE 1 (rare, high stakes): Slow down, verify twice, confirm with Pat if money.**
- Sending bulk outreach for the first time to a new list
- Deploying to production LocalComm (live client data)
- Any action touching live billing or payment data
- Rule: Premortem first (`./engine/evolve premortem`), verify intent, checkpoint, execute, verify output before proceeding.

**Default:** 95% of agent decisions are TYPE 2. Don't let TYPE 1 caution infect TYPE 2 speed.

---

## PATTERN 11: Critical Path Multiplier for Queue

Any task that is blocking N other tasks gets a geometric urgency boost — not flat.

```python
# In WSJF calculation, adjust Cost_of_Delay:
blocking_multiplier = 1 + (0.5 * count_of_blocked_tasks)

effective_CoD = base_CoD * blocking_multiplier

# Examples:
# Task blocks 0 others: CoD × 1.0 (no change)
# Task blocks 1 other: CoD × 1.5
# Task blocks 2 others: CoD × 2.0 (double the urgency)
# Task blocks 5 others: CoD × 3.5 (critical path, highest priority)
```

**Practical application:**
- Fix broken outreach agent (blocks 15 leads/day) → CoD ×3.5 minimum
- Add API key to environment (blocks 3 agents) → CoD ×2.5
- Research a new vertical (blocks nobody) → CoD ×1.0

**When stuck:** Map the dependency graph. The node with the most downstream dependents gets fixed first. Always.

---

## PATTERN 12: 2-Minute Rule for Queue Drainage

*From GTD (David Allen) adapted for agent systems*

Any task completable in < 2 minutes bypasses WSJF scoring and executes immediately.

**Why:** Scheduling overhead for sub-2min tasks exceeds their deferral cost. They also create psychological/operational drag on the queue — long lists of tiny tasks generate false complexity.

**Application:**
- Send one follow-up email: 90 seconds → do it NOW
- Restart a downed agent with a known fix: 60 seconds → do it NOW
- Add a lead to memory/leads.md: 30 seconds → do it NOW  
- Write a one-line status update: 45 seconds → do it NOW

**Anti-pattern:** Never put a sub-2min task in a priority queue. Execute on encounter.

**Exception:** If you have > 10 sub-2min tasks, batch them (2-min rule → batch mode). Sequential tiny tasks are fine; scattered interruption of deep work is not.

