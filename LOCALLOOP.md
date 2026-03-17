## LocalLoop 15-Agent System

| Agent | Port | Role |
|-------|------|------|
| ORCHESTRATOR | 8040 | Health + dispatch |
| SCOUT | 8041 | Competitor intel |
| COPYCAT | 8042 | Content generation |
| AD OPTIMIZER | 8043 | Ad performance |
| GROWTH | 8044 | Creative testing |
| SENTINEL | 8045 | Review monitoring |
| REPORTER | 8046 | Monthly reports |
| POSTER | 8047 | Content publishing |
| CREATIVE | 8048 | Visual assets |
| SEO | 8049 | SEO + GBP |
| EMAIL | 8050 | Email marketing |
| VIDEO | 8051 | Reels/TikTok |
| CLOSER | 8052 | Sales pipeline |
| INTAKE | 8053 | Client onboarding |
| QA | 8054 | Content quality gate |

## LocalLoop Configuration

```json
{
  "agents": {
    "ORCHESTRATOR": {
      "port": 8040,
      "role": "Health + dispatch"
    },
    "SCOUT": {
      "port": 8041,
      "role": "Competitor intel"
    },
    "COPYCAT": {
      "port": 8042,
      "role": "Content generation"
    },
    "AD OPTIMIZER": {
      "port": 8043,
      "role": "Ad performance"
    },
    "GROWTH": {
      "port": 8044,
      "role": "Creative testing"
    },
    "SENTINEL": {
      "port": 8045,
      "role": "Review monitoring"
    },
    "REPORTER": {
      "port": 8046,
      "role": "Monthly reports"
    },
    "POSTER": {
      "port": 8047,
      "role": "Content publishing"
    },
    "CREATIVE": {
      "port": 8048,
      "role": "Visual assets"
    },
    "SEO": {
      "port": 8049,
      "role": "SEO + GBP"
    },
    "EMAIL": {
      "port": 8050,
      "role": "Email marketing"
    },
    "VIDEO": {
      "port": 8051,
      "role": "Reels/TikTok"
    },
    "CLOSER": {
      "port": 8052,
      "role": "Sales pipeline"
    },
    "INTAKE": {
      "port": 8053,
      "role": "Client onboarding"
    },
    "QA": {
      "port": 8054,
      "role": "Content quality gate"
    }
  }
}
```