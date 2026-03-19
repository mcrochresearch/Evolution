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
