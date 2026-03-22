# LEARNINGS — Mistakes & Fixes

Read this before every new task. If you've made this mistake before, solve it differently this time.

---

## Rule: Before any new task, scan this file. If a matching pattern exists, apply the fix automatically.

---

## Mistakes Log

### [2026-03-22] SearXNG search results — hallucinated businesses
**What happened:** Agent generated fake business names, addresses, and phone numbers instead of pulling real search results.
**Fix:** Always run the actual curl command against SearXNG. If results are empty or unclear, log that and move on. Never invent replacements.
**Rule added:** "NO HALLUCINATION RULE" in HEARTBEAT.md Block B.

### [2026-03-22] curl URL not quoted in zsh
**What happened:** URLs with `?` in query strings caused zsh glob expansion to fail with "no matches found".
**Fix:** ALWAYS wrap curl URLs in single quotes. `curl -s 'http://localhost:3100/api/...'`
**Rule added:** SOUL.md CHEAT SHEET — Rule 4.

### [2026-03-22] Asking Pat questions instead of deciding
**What happened:** Agent presented options ("Should I do X or Y?") instead of picking and executing.
**Fix:** Pick highest expected value. Execute. Report which you picked and why.
**Rule added:** SOUL.md — "Never Ask. Always Execute."

---

## Add New Mistakes

When something breaks or goes wrong, run:
> "Add this mistake to learnings"

Include: what happened, the fix, and the rule derived from it.

---

## Pattern Library (recurring fixes)

| Pattern | Fix |
|---------|-----|
| curl URL with `?` in zsh | Wrap in single quotes |
| Empty search results | Log it. Never invent data. |
| Agent down on health check | Check logs → fix → verify with curl |
| Fake/stale lead data | Verify URL resolves before adding to leads.md |
| Question sent to Pat | Delete it. Rewrite as statement. |
