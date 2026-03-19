# GEO Audit Skill

**Purpose:** Full AI search visibility audit for SMB websites. Scores how visible a site is to ChatGPT, Perplexity, Claude, Google AI Overviews.

## Quick Start

```bash
cd ~/.openclaw/workspace/skills/geo-audit/scripts

# Full pitch-format report (best for lead outreach)
python3 geo_audit.py https://CLIENTSITE.com --pitch

# JSON output (for integrations)
python3 geo_audit.py https://CLIENTSITE.com --json

# Individual tools
python3 fetch_page.py https://CLIENTSITE.com robots      # AI crawler check
python3 citability_scorer.py https://CLIENTSITE.com       # Content citability
python3 llmstxt_generator.py https://CLIENTSITE.com       # Generate llms.txt
```

## What It Scores (GEO Score 0-100)

| Category | Weight | What It Measures |
|----------|--------|-----------------|
| AI Citability | 25% | How quote-worthy is the content to AI models |
| AI Crawler Access | 20% | Are GPTBot, ClaudeBot, PerplexityBot allowed in robots.txt |
| Schema Markup | 20% | LocalBusiness / Organization JSON-LD present |
| llms.txt | 15% | AI navigation file exists + is valid |
| Technical Foundation | 10% | Title, meta description, H1, SSR |
| Content Volume | 10% | Word count adequacy |

## Schema Templates

`schema/local-business.json` — for HVAC, appliance, dental, any local service business
`schema/organization.json` — for agencies, practices with multiple locations

## Sales Pitch Integration

Run `--pitch` on any lead's site to get a ready-to-send audit snippet.
Prisco Appliance scored **22/100** with zero schema, no llms.txt, no meta description.
That's your opening line.

## Dependencies

```
requests, beautifulsoup4, lxml (all pre-installed)
```
