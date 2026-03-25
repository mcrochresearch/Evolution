# MEMORY — Stamford AI Agency

**Last updated:** 2026-03-13

---

## The Business

**Agency:** Full-service AI consulting + marketing automation for SMBs in Stamford CT and surrounding areas.
**Model:** Done-for-you AI — social content, email, lead gen, Google presence, AI workflows.
**Target:** SMBs with $500K–$5M revenue, no in-house marketing team.
**Year 1 goal:** $1M ARR (~83K MRR / ~30 clients).
**First goal:** 3 paying clients.
**Lead gen:** Direct mail (QR postcard) + LinkedIn + cold email + outbound scraping.

---

## Positioning

- Not a generic "AI agency" — CT/Westchester-focused, regionally dominant
- Pitch: "We run your marketing and operations on autopilot. You focus on the business."
- Differentiator: AI does the work at a fraction of agency cost; faster + more consistent than a freelancer
- Price anchor: $997–$6,997/month retainer (vs $3K–$8K for traditional agency)

---

## Service Catalog

### AI Consulting
- AI workflow automation
- AI customer support agents
- AI lead qualification
- Internal productivity automation
- Document automation + AI knowledge bases
- AI sales assistants

### Marketing Services
- Local SEO + Google Business Profile
- Paid ads (Google, Meta, Google Local Services)
- Website optimization + landing pages
- Content marketing (blog, social, video)
- Social media automation + reputation management
- Email marketing + CRM automation

### Productized Packages

| Package | Price | Includes |
|---------|-------|---------|
| **AI Starter Pack** | $997/mo | Chatbot + lead capture + CRM integration |
| **AI Marketing Engine** | $1,997/mo | Automated content + lead funnels + ad campaigns |
| **Local Growth System** | $2,497/mo | SEO + reviews + Google Business + ads |
| **Growth** | $3,997/mo | Full marketing + 2 Reels + reputation |
| **Dominate** | $6,997/mo | Everything + Google Ads + 6 Reels + full SEO |

---

## Target Market

### Geographic Markets (priority order)
1. Stamford, CT
2. Greenwich, CT
3. Norwalk, CT
4. Bridgeport, CT
5. White Plains, NY

### Priority Verticals
1. Home services (HVAC, plumbing, roofing, landscaping, appliance repair)
2. Dental practices
3. Law firms
4. Med spas / salons / wellness
5. Real estate
6. Gyms / fitness
7. Restaurants / cafes
8. Contractors
9. Accountants
10. Local retail

### Ideal Prospect Profile
- 3+ years in business
- 20+ Google reviews
- No current agency, minimal digital presence
- Clear pain: low leads, weak online presence, manual processes, slow response times

---

## Sales System

### Lead Sources
- Local business scraping (Google Maps, Yelp, directories)
- LinkedIn prospecting
- Referrals
- Cold email (personalized audit)

### Outreach Sequence (3-touch)
1. Cold email with free mini-audit finding
2. Follow-up with specific ROI example from their vertical
3. LinkedIn message or video audit

### CLOSER Agent (Port 8052)
```bash
curl -s -X POST http://localhost:8052/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"task":{"id":"prospect-1","type":"prospect_research",
    "business_name":"[NAME]","location":"[CITY, STATE]","vertical":"hvac",
    "audit_findings":"{\"pain_points\":[\"low_online_presence\",\"weak_google_presence\",\"no_social_media\"],\"competitor_analysis\":[\"local_competitor_1\",\"local_competitor_2\"]}',
    "skills":"","budget_remaining":0}' | python3 -m json.tool
```

---

## Infrastructure

### Services
| Service | Port | What It Does |
|---------|------|--------------|
| OpenClaw gateway | 18789 | Agent orchestration |
| Paperclip | 3100 | AI company orchestrator |
| OLMx primary (30B) | 8080 | Strategy / heavy tasks |
| OLMx fast (0.8B) | 8081 | Fast / classification |
| Ollama | 11434 | Fallback inference |
| SearXNG | 8888 | Self-hosted search |
| Approval UI | 8060 | Review content before publish |
| Agency Dashboard | 8061 | Client metrics |
| LocalLoop agents | 8040–8054 | 15-agent operational system |

### LocalLoop 15-Agent System
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

### Ad Factory (Marketing Asset Engine)
Path: `~/shellcorp/ad-factory/`
Run: `cd ~/shellcorp/ad-factory && python3 run.py demo`
Autoresearch baseline: 6.94 → self-improving genome at `autoresearch/agency_genome.py`

### Key Paths
| What | Path |
|------|------|
| LocalLoop DB | `~/shellcorp/.claude/worktrees/thirsty-dewdney/data/agency_state.db` |
| LocalLoop config | `~/shellcorp/.claude/worktrees/thirsty-dewdney/config/agency-config.json` |
| LocalClaw guides | `~/shellcorp/localclaw/` (206 industry guides) |
| Ad Factory | `~/shellcorp/ad-factory/` |
| Agency artifacts | `~/shellcorp/agency/` |
| OpenClaw config | `~/.openclaw/openclaw.json` |

### Control
```bash
claw status                       # full system view
claw restart localloop            # restart LocalLoop agents
claw logs localloop               # agent output
claw logs olmx                    # inference logs
```

---

## Delivery Pipelines

### SEO Delivery
1. Website audit → keyword research → on-page optimization → content generation → backlink strategy

### AI Automation Deployment
1. Process mapping → workflow design → tool integration → testing → training

### Marketing Asset Production
```bash
cd ~/shellcorp/ad-factory
python3 run.py pipeline --industry [vertical] --client [id]
```

### Content Pipeline
COPYCAT generates → QA scores (threshold 80+) → Approval (http://localhost:8060) → POSTER publishes

---

## Current Pipeline

### Prospects
- **Prisco Appliance** — 247 Tarrytown Rd, White Plains NY. Nick Prisco, (914) 949-6464.
  57-year family business, $3M rev, 4.9★ (206 reviews), zero ads, 57 Instagram followers.
  DB: `prisco-001`. Pitch built. **NOT YET SIGNED.**

### Clients
_(None yet — first 3 is the goal)_

---

## Setup Status

### Done
- [x] Mac Studio running all services (OLMx, Paperclip, OpenClaw, Telegram)
- [x] LocalLoop 15-agent system operational (ports 8040–8054)
- [x] SearXNG self-hosted search (:8888)
- [x] Ad Factory (63 modules, images/video/SEO/websites/campaigns)
- [x] Autoresearch genome (self-improving creative engine)
- [x] LocalClaw 206 industry guides
- [x] Stamford AI Consulting website live (stamfordaiconsulting.com)
- [x] Agency artifact repo structure (~/shellcorp/agency/)

### To Do — Agency Launch
- [ ] Close Prisco Appliance (first client)
- [ ] Build 50-target lead list (Stamford/Greenwich HVAC + Dental + Law)
- [ ] Launch CLOSER agent outreach campaign
- [ ] Agency landing page (stamfordaiagency.com)
- [ ] Google Business Profile
- [ ] Direct mail postcard (QR → landing page)
- [ ] Fill API keys: META_ACCESS_TOKEN, GBP_REFRESH_TOKEN, TWILIO

---

## Research Log

_(Add findings here as you research the market)_

---

## Lessons Learned

_(Document what works and what doesn't as you run outreach)_
