# TOOLS — System Reference

## Service Control

```bash
claw status                         # all services + ports
claw start|stop|restart [service]   # openclaw, agents, olmx, all
claw logs agents                    # paperclip agent output
claw logs olmx                      # MLX inference logs
claw logs openclaw                  # gateway logs
claw logs all                       # everything
```

## Ports

| Service | Port |
|---------|------|
| OpenClaw gateway | 18789 |
| Paperclip | 3100 |
| OLMx primary (Qwen3-30B, ~64 tok/s) | 8080 |
| OLMx fast (Qwen3.5-0.8B) | 8081 |
| Content agent | 8020 |
| Publisher agent | 8021 |
| Analytics agent | 8022 |

## Key Paths

| What | Path |
|------|------|
| Agent code | `~/shellcorp/paperclip-integrations/nutn-co/agents.py` |
| Inference client | `~/shellcorp/paperclip-integrations/shared/olmx.py` |
| nütn workspace | `~/shellcorp/companies/nutn/` |
| OpenClaw config | `~/.openclaw/openclaw.json` |
| OLMx plist (primary) | `~/Library/LaunchAgents/com.olmx.primary.plist` |
| This workspace | `~/.openclaw/workspace/` |

## Agency Memory Files

| File | Purpose |
|------|---------|
| `memory/leads.md` | Stamford SMB lead list |
| `memory/outreach/` | Email/DM templates |
| `memory/competitive-landscape.md` | Competitor research |
| `memory/heartbeat-state.json` | Loop state tracker |
| `memory/YYYY-MM-DD.md` | Daily session logs |

## Search

**ALL web searches MUST use SearXNG — never Brave or any other external search.**

```bash
curl -s "http://127.0.0.1:8888/search?q=YOUR+QUERY+HERE&format=json" | python3 -c "
import json,sys
data = json.load(sys.stdin)
for r in data.get('results',[])[:5]:
    print(r['title'], '|', r['url'], '|', r.get('content','')[:120])
"
```

SearXNG runs locally at `http://127.0.0.1:8888`. No API key. No rate limits. Always use this.

## Telegram

- Bot: @Mrsheldonkrabsbot
- Pat's ID: 1830363373
