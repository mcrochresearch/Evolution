# LocalLoop Agent Skills Index

Agents MUST read the relevant skill file before executing skill-related tasks.
Load skills as additional system context when the task matches.

## Available Skills

| File | When to Use |
|------|-------------|
| `performance-analytics.md` | Analyzing campaign results, channel ROI, reporting (weekly/monthly/QBR), attribution, trend analysis, dashboards |
| `contract-review.md` | Reviewing vendor agreements, client MSAs, SaaS contracts — GREEN/YELLOW/RED risk classification, redlines |
| `client-brand-profile.md` | REQUIRED before generating any marketing asset — load client's brand colors, voice, logo, audience |
| `image-generation-agent.md` | Generating marketing images, social graphics, ad creatives, thumbnails using ComfyUI/Stable Diffusion |
| `video-ad-generation.md` | Creating video ads, social clips, animated content using open-source video tools |
| `pitch-deck-generation.md` | Building investor/sales pitch decks and presentations as PPTX |
| `seo-agent.md` | SEO audits, local SEO, keyword tracking, meta tags, schema markup, SEO reports |
| `website-builder-agent.md` | Generating full static websites from brand profile — multi-page, Tailwind CSS, Cloudflare Pages deploy |
| `reputation-management-agent.md` | Monitoring reviews, sentiment analysis, generating review responses, reputation scores, campaigns |

## Usage Pattern

```python
# Load skill as context before calling OLMx:
skill_path = f"{WORKSPACE}/skills/{skill_name}.md"
skill_context = open(skill_path).read()

prompt = f"/no_think\n\n[SKILL CONTEXT]\n{skill_context}\n\n[TASK]\n{task_description}"
response = call_olmx(prompt)
```

## Skill-to-Agent Mapping

| Agent | Primary Skills |
|-------|---------------|
| localcomm-co / review_monitor | reputation-management-agent, performance-analytics |
| localcomm-co / social_publisher | image-generation-agent, video-ad-generation, client-brand-profile |
| localcomm-co / site_monitor | seo-agent, website-builder-agent |
| localclaw | performance-analytics, competitive-analysis, seo-agent |
| main / openclaw-coo | performance-analytics, contract-review |
| main / localcomm-builder | client-brand-profile, pitch-deck-generation, website-builder-agent |
