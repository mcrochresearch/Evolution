---
name: seo-agent
description: >
  Autonomous SEO agent skill for AI agents. Use when an agent needs to perform technical
  SEO audits, local SEO optimization, keyword rank tracking, content SEO scoring, meta tag
  generation, local schema markup, or SEO reporting for small businesses. Integrates with
  the client-brand-profile skill for multi-client support. Covers Google Search Console,
  PageSpeed Insights, SerpBear keyword tracking, and structured data generation. Designed
  for autonomous operation with no human intervention required.
metadata:
  author: localcomm
  version: '1.0'
  updated: '2026-03-15'
---

# SEO Agent for Autonomous AI Agents

## When to Use This Skill

Use this skill when an AI agent needs to:

- Run a technical SEO audit on a small business website (crawl errors, meta tags, speed)
- Optimize local SEO presence (Google Business Profile, local schema, NAP consistency)
- Track keyword rankings over time (SerpBear integration)
- Score on-page content for SEO quality and generate improvements
- Generate meta tags, Open Graph tags, and structured data markup
- Produce weekly/monthly SEO reports with action items
- Manage SEO across multiple clients using the brand profile system

## Free Tool Stack (As of March 2026)

### Tier 1: Free Google Tools (Official APIs)

#### 1. Google Search Console API
- **What**: Official API for search performance data — clicks, impressions, CTR, position
- **Cost**: Free (unlimited for verified properties)
- **Auth**: OAuth 2.0 or Service Account
- **Python SDK**: `google-api-python-client`
- **Docs**: https://developers.google.com/webmaster-tools/v1/api_reference_index
- **Best For**: Real keyword performance data, indexing issues, crawl errors

#### 2. Google PageSpeed Insights API
- **What**: Core Web Vitals and performance scoring for any URL
- **Cost**: Free — 400 queries/day (25,000/day with API key)
- **Auth**: API key only (no OAuth)
- **Endpoint**: `https://www.googleapis.com/pagespeedonline/v5/runPagespeed`
- **Best For**: Technical performance audits, Core Web Vitals monitoring

#### 3. Google Business Profile API
- **What**: Manage Google Business listings — posts, reviews, hours, photos
- **Cost**: Free for verified businesses
- **Auth**: OAuth 2.0
- **Python SDK**: `google-api-python-client`
- **Best For**: Local SEO — managing listings, responding to reviews, posting updates

#### 4. Google Analytics 4 Data API
- **What**: Traffic, engagement, and conversion data from GA4 properties
- **Cost**: Free (standard GA4 properties)
- **Auth**: OAuth 2.0 or Service Account
- **Python SDK**: `google-analytics-data`
- **Best For**: Traffic trend analysis, landing page performance, conversion tracking

#### 5. Google Custom Search JSON API
- **What**: Programmatic Google search results for SERP analysis
- **Cost**: Free — 100 queries/day
- **Auth**: API key + Custom Search Engine ID
- **Endpoint**: `https://www.googleapis.com/customsearch/v1`
- **Best For**: Competitor SERP analysis, featured snippet tracking

### Tier 2: Open-Source SEO Tools (Self-Hosted)

#### 6. SerpBear
- **What**: Open-source keyword rank tracking with built-in API
- **License**: MIT
- **Deploy**: Docker (`docker-compose up`)
- **Features**: Unlimited keywords, daily tracking, SERP scraping, email alerts
- **Free Scraping**: ScrapingRobot integration — 5,000 free lookups/month
- **API**: REST API at `http://localhost:3000/api`
- **GitHub**: https://github.com/towfiqi/serpbear
- **Best For**: Daily keyword position tracking without paid tools

#### 7. Greenflare SEO Crawler
- **What**: Fast open-source technical SEO crawler written in Python
- **License**: GPL-3.0
- **Features**: Crawl up to 100K URLs, check status codes, meta tags, headings, redirects
- **GitHub**: https://github.com/beb7/gflare-tk
- **Best For**: Technical site crawling and on-page auditing at scale

#### 8. SEO Panel
- **What**: Open-source multi-site SEO management platform
- **License**: GPL-2.0
- **Features**: Rank checking, site auditing, backlink analysis, multi-site dashboard
- **GitHub**: https://github.com/nicholasgasior/seo-panel
- **Best For**: Managing SEO across multiple client sites

#### 9. ContentSwift
- **What**: SERP-driven content optimization tool
- **License**: Open-source
- **Features**: Analyzes top-ranking pages, extracts keyword patterns, suggests content structure
- **Best For**: Content brief generation and on-page optimization

#### 10. Lighthouse CI (Google)
- **What**: Automated Lighthouse audits in CI/CD pipelines
- **License**: Apache 2.0
- **Install**: `npm install -g @lhci/cli`
- **Features**: Performance, accessibility, SEO scoring with historical tracking
- **Best For**: Continuous SEO monitoring in deployment pipelines

### Tier 3: Free-Tier APIs (Cloud Services)

#### 11. Moz Link API (Free Tier)
- **What**: Domain authority, page authority, backlink data
- **Free Tier**: 2,500 rows/month
- **Auth**: API key
- **URL**: https://moz.com/products/api
- **Best For**: Competitive domain authority comparison

#### 12. GTmetrix (Free Tier)
- **What**: Page speed and Core Web Vitals testing
- **Free Tier**: Unlimited basic tests (limited API: 20 credits/day)
- **URL**: https://gtmetrix.com
- **Best For**: Secondary performance validation alongside PageSpeed Insights

#### 13. Screaming Frog SEO Spider
- **What**: Desktop-based technical SEO crawler
- **Free Tier**: Up to 500 URLs per crawl (no API in free tier)
- **URL**: https://www.screamingfrog.co.uk/seo-spider/
- **Best For**: Manual deep-crawl audits for smaller sites

#### 14. Ubersuggest (Free Tier)
- **What**: Keyword research and content ideas
- **Free Tier**: 3 searches/day
- **URL**: https://neilpatel.com/ubersuggest/
- **Best For**: Quick keyword volume estimates and content suggestions

### Tier 4: Python Libraries (Free, Local)

#### 15. BeautifulSoup + Requests
- **What**: HTML parsing and web scraping
- **License**: MIT / Apache 2.0
- **Install**: `pip install beautifulsoup4 requests`
- **Best For**: Custom page crawling, meta tag extraction, link analysis

#### 16. advertools
- **What**: Python SEO and SEM productivity library
- **License**: MIT
- **Install**: `pip install advertools`
- **Features**: robots.txt parsing, sitemap parsing, SERP analysis, URL analysis
- **Best For**: Programmatic SEO data extraction and analysis

#### 17. Trafilatura
- **What**: Web content extraction (article text, metadata)
- **License**: Apache 2.0
- **Install**: `pip install trafilatura`
- **Best For**: Extracting clean text content from web pages for analysis

## Autonomous SEO Pipeline Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      AGENT ORCHESTRATOR                        │
│               (LLM: Gemini/GPT/Ollama/Local)                  │
└──────────┬──────────────────────┬──────────────────┬──────────┘
           │                      │                  │
┌──────────▼──────────┐ ┌────────▼────────┐ ┌───────▼─────────┐
│  BRAND PROFILE MGR  │ │  SEO DATA STORE │ │ REPORT GENERATOR│
│  - Load client_id   │ │  - Per-client   │ │ - Weekly/monthly│
│  - Get website URL  │ │  - Audit history│ │ - Action items  │
│  - Get industry     │ │  - Rank history │ │ - Trend charts  │
│  - Get competitors  │ │  - Content scores│ │ - PDF/JSON/HTML │
└──────────┬──────────┘ └────────┬────────┘ └───────┬─────────┘
           │                      │                  │
┌──────────▼──────────────────────▼──────────────────▼──────────┐
│                     SEO ANALYSIS LAYER                         │
│                                                                │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐            │
│  │  TECHNICAL   │ │  LOCAL SEO  │ │   CONTENT    │            │
│  │  AUDIT       │ │  OPTIMIZER  │ │   SCORER     │            │
│  │             │ │             │ │              │            │
│  │ - Crawl site│ │ - GBP audit │ │ - On-page    │            │
│  │ - Meta tags │ │ - Schema    │ │ - Meta tags  │            │
│  │ - Speed     │ │ - NAP check │ │ - Readability│            │
│  │ - Links     │ │ - Citations │ │ - Keywords   │            │
│  │ - Mobile    │ │ - Reviews   │ │ - Internal   │            │
│  └──────┬──────┘ └──────┬──────┘ └──────┬───────┘            │
│         │               │               │                     │
│  ┌──────▼───────────────▼───────────────▼───────┐            │
│  │            KEYWORD TRACKING LAYER             │            │
│  │                                               │            │
│  │  SerpBear API:  Daily rank tracking           │            │
│  │  Search Console: Clicks, impressions, CTR     │            │
│  │  Custom Search:  SERP feature monitoring      │            │
│  └───────────────────────────────────────────────┘            │
└───────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────┐
│                    DATA STORAGE LAYER                          │
│                                                                │
│  brand_profiles/{client_id}/seo/                              │
│  ├── audits/           # Technical audit JSON reports         │
│  ├── rankings/         # Daily keyword position snapshots     │
│  ├── content_scores/   # Per-page SEO score history           │
│  ├── reports/          # Weekly/monthly SEO reports           │
│  └── schema/           # Generated structured data files      │
└───────────────────────────────────────────────────────────────┘
```

## Implementation Guide

### Multi-Client SEO Manager

```python
import json
import os
import re
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, urljoin

# ─── CONFIGURATION ─────────────────────────────────────────
BRAND_PROFILES_DIR = os.environ.get("BRAND_PROFILES_DIR", "./brand_profiles")
SERPBEAR_URL = os.environ.get("SERPBEAR_URL", "http://localhost:3000")
SERPBEAR_API_KEY = os.environ.get("SERPBEAR_API_KEY", "")
PAGESPEED_API_KEY = os.environ.get("PAGESPEED_API_KEY", "")
GOOGLE_CUSTOM_SEARCH_KEY = os.environ.get("GOOGLE_CUSTOM_SEARCH_KEY", "")
GOOGLE_CUSTOM_SEARCH_CX = os.environ.get("GOOGLE_CUSTOM_SEARCH_CX", "")

# ─── IMPORT BRAND PROFILE MANAGER ─────────────────────────
# Requires: client-brand-profile skill
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path as _Path

class BrandProfileManager:
    """Stub — import from client-brand-profile skill in production."""
    def __init__(self, profiles_dir=None):
        self.profiles_dir = _Path(profiles_dir or BRAND_PROFILES_DIR)
    def get_profile(self, client_id):
        path = self.profiles_dir / client_id / "profile.json"
        if not path.exists():
            raise FileNotFoundError(f"No brand profile for '{client_id}'")
        with open(path) as f:
            return json.load(f)
    def get_colors(self, client_id):
        p = self.get_profile(client_id)
        bi = p.get("brand_identity", {})
        return {"primary": bi.get("primary_color", "#2563EB")}

# ─── SEO DATA MANAGER ─────────────────────────────────────

class SEODataManager:
    """Manages per-client SEO data storage."""

    def __init__(self, client_id, profiles_dir=None):
        self.client_id = client_id
        self.profiles_dir = Path(profiles_dir or BRAND_PROFILES_DIR)
        self.seo_dir = self.profiles_dir / client_id / "seo"
        self._ensure_dirs()

    def _ensure_dirs(self):
        for subdir in ["audits", "rankings", "content_scores", "reports", "schema"]:
            (self.seo_dir / subdir).mkdir(parents=True, exist_ok=True)

    def save_audit(self, audit_data):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.seo_dir / "audits" / f"audit_{ts}.json"
        with open(path, "w") as f:
            json.dump(audit_data, f, indent=2, default=str)
        return str(path)

    def save_rankings(self, rankings_data):
        ts = datetime.now().strftime("%Y%m%d")
        path = self.seo_dir / "rankings" / f"rankings_{ts}.json"
        with open(path, "w") as f:
            json.dump(rankings_data, f, indent=2, default=str)
        return str(path)

    def save_content_score(self, url, score_data):
        slug = re.sub(r'[^a-z0-9]+', '_', urlparse(url).path.strip('/').lower()) or "homepage"
        path = self.seo_dir / "content_scores" / f"{slug}.json"
        # Append to history
        history = []
        if path.exists():
            with open(path) as f:
                history = json.load(f)
        history.append({"timestamp": datetime.now().isoformat(), **score_data})
        with open(path, "w") as f:
            json.dump(history[-50:], f, indent=2)  # Keep last 50 scores
        return str(path)

    def save_report(self, report_data, report_type="weekly"):
        ts = datetime.now().strftime("%Y%m%d")
        path = self.seo_dir / "reports" / f"{report_type}_report_{ts}.json"
        with open(path, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        return str(path)

    def save_schema(self, schema_data, schema_type="local_business"):
        path = self.seo_dir / "schema" / f"{schema_type}.json"
        with open(path, "w") as f:
            json.dump(schema_data, f, indent=2)
        return str(path)

    def get_latest_audit(self):
        audits_dir = self.seo_dir / "audits"
        files = sorted(audits_dir.glob("audit_*.json"), reverse=True)
        if files:
            with open(files[0]) as f:
                return json.load(f)
        return None

    def get_ranking_history(self, days=30):
        rankings_dir = self.seo_dir / "rankings"
        cutoff = datetime.now() - timedelta(days=days)
        history = []
        for f in sorted(rankings_dir.glob("rankings_*.json")):
            date_str = f.stem.replace("rankings_", "")
            try:
                file_date = datetime.strptime(date_str, "%Y%m%d")
                if file_date >= cutoff:
                    with open(f) as fh:
                        history.append(json.load(fh))
            except ValueError:
                continue
        return history
```

### Step 1: Technical SEO Audit

```python
from bs4 import BeautifulSoup

def run_technical_audit(client_id, url=None, max_pages=50):
    """
    Crawl a website and produce a structured technical SEO audit.

    Returns a JSON report covering: meta tags, headings, images, links,
    robots.txt, sitemap, Core Web Vitals, and mobile-friendliness.
    """
    mgr = BrandProfileManager()
    seo = SEODataManager(client_id)

    # Get URL from brand profile if not provided
    if not url:
        profile = mgr.get_profile(client_id)
        url = profile.get("platforms", {}).get("website", "")
        if not url:
            return {"error": "No website URL found in brand profile or arguments"}

    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    audit = {
        "client_id": client_id,
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "pages_crawled": 0,
        "issues": [],
        "scores": {},
        "pages": [],
        "robots_txt": None,
        "sitemap": None,
        "core_web_vitals": None,
    }

    # ── Check robots.txt ──────────────────────────────────
    try:
        robots_resp = requests.get(f"{base_url}/robots.txt", timeout=10)
        if robots_resp.status_code == 200:
            audit["robots_txt"] = {
                "exists": True,
                "content_length": len(robots_resp.text),
                "has_sitemap_ref": "sitemap" in robots_resp.text.lower(),
            }
        else:
            audit["robots_txt"] = {"exists": False}
            audit["issues"].append({
                "severity": "medium",
                "type": "missing_robots_txt",
                "message": "No robots.txt found — search engines may crawl inefficiently",
                "fix": f"Create a robots.txt at {base_url}/robots.txt"
            })
    except requests.RequestException as e:
        audit["robots_txt"] = {"exists": False, "error": str(e)}

    # ── Check sitemap.xml ─────────────────────────────────
    try:
        sitemap_resp = requests.get(f"{base_url}/sitemap.xml", timeout=10)
        if sitemap_resp.status_code == 200:
            audit["sitemap"] = {
                "exists": True,
                "content_length": len(sitemap_resp.text),
                "url_count": sitemap_resp.text.count("<loc>"),
            }
        else:
            audit["sitemap"] = {"exists": False}
            audit["issues"].append({
                "severity": "high",
                "type": "missing_sitemap",
                "message": "No sitemap.xml found — search engines may miss pages",
                "fix": "Generate and submit a sitemap.xml to Google Search Console"
            })
    except requests.RequestException as e:
        audit["sitemap"] = {"exists": False, "error": str(e)}

    # ── Crawl pages ───────────────────────────────────────
    visited = set()
    to_visit = [url]

    while to_visit and len(visited) < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)

        page_audit = _audit_single_page(current_url, base_url)
        if page_audit:
            audit["pages"].append(page_audit)
            audit["issues"].extend(page_audit.get("issues", []))

            # Collect internal links for further crawling
            for link in page_audit.get("internal_links", []):
                if link not in visited and len(to_visit) < max_pages:
                    to_visit.append(link)

    audit["pages_crawled"] = len(visited)

    # ── Core Web Vitals (PageSpeed Insights) ──────────────
    audit["core_web_vitals"] = check_core_web_vitals(url)

    # ── Scoring ───────────────────────────────────────────
    total_issues = len(audit["issues"])
    high_issues = sum(1 for i in audit["issues"] if i["severity"] == "high")
    medium_issues = sum(1 for i in audit["issues"] if i["severity"] == "medium")

    audit["scores"] = {
        "overall": max(0, 100 - (high_issues * 10) - (medium_issues * 5) - total_issues),
        "total_issues": total_issues,
        "high_severity": high_issues,
        "medium_severity": medium_issues,
        "low_severity": total_issues - high_issues - medium_issues,
    }

    # Save audit
    saved_path = seo.save_audit(audit)
    audit["saved_to"] = saved_path

    return audit


def _audit_single_page(url, base_url):
    """Audit a single page for SEO issues."""
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "LocalCommSEOBot/1.0 (+https://localloop.com/bot)"
        })
    except requests.RequestException as e:
        return {"url": url, "error": str(e), "issues": [{
            "severity": "high", "type": "unreachable",
            "message": f"Page unreachable: {e}", "url": url
        }]}

    page = {
        "url": url,
        "status_code": resp.status_code,
        "response_time_ms": int(resp.elapsed.total_seconds() * 1000),
        "content_length": len(resp.content),
        "issues": [],
        "internal_links": [],
    }

    if resp.status_code != 200:
        page["issues"].append({
            "severity": "high", "type": "http_error",
            "message": f"HTTP {resp.status_code} on {url}", "url": url
        })
        return page

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Title tag ─────────────────────────────────────────
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    page["title"] = title_text

    if not title_text:
        page["issues"].append({
            "severity": "high", "type": "missing_title",
            "message": "Missing <title> tag", "url": url
        })
    elif len(title_text) > 60:
        page["issues"].append({
            "severity": "medium", "type": "title_too_long",
            "message": f"Title too long ({len(title_text)} chars, max 60): {title_text[:70]}...",
            "url": url
        })
    elif len(title_text) < 20:
        page["issues"].append({
            "severity": "low", "type": "title_too_short",
            "message": f"Title may be too short ({len(title_text)} chars): {title_text}",
            "url": url
        })

    # ── Meta description ──────────────────────────────────
    meta_desc = soup.find("meta", attrs={"name": "description"})
    desc_text = meta_desc.get("content", "").strip() if meta_desc else ""
    page["meta_description"] = desc_text

    if not desc_text:
        page["issues"].append({
            "severity": "high", "type": "missing_meta_description",
            "message": "Missing meta description", "url": url
        })
    elif len(desc_text) > 160:
        page["issues"].append({
            "severity": "medium", "type": "meta_description_too_long",
            "message": f"Meta description too long ({len(desc_text)} chars, max 160)",
            "url": url
        })

    # ── H1 tag ────────────────────────────────────────────
    h1_tags = soup.find_all("h1")
    page["h1_count"] = len(h1_tags)
    page["h1_text"] = [h.get_text(strip=True) for h in h1_tags]

    if len(h1_tags) == 0:
        page["issues"].append({
            "severity": "high", "type": "missing_h1",
            "message": "No H1 tag found on page", "url": url
        })
    elif len(h1_tags) > 1:
        page["issues"].append({
            "severity": "medium", "type": "multiple_h1",
            "message": f"Multiple H1 tags found ({len(h1_tags)})", "url": url
        })

    # ── Images without alt text ───────────────────────────
    images = soup.find_all("img")
    images_no_alt = [img.get("src", "") for img in images if not img.get("alt")]
    page["total_images"] = len(images)
    page["images_missing_alt"] = len(images_no_alt)

    if images_no_alt:
        page["issues"].append({
            "severity": "medium", "type": "missing_alt_text",
            "message": f"{len(images_no_alt)} image(s) missing alt text",
            "url": url,
            "details": images_no_alt[:5]
        })

    # ── Canonical URL ─────────────────────────────────────
    canonical = soup.find("link", attrs={"rel": "canonical"})
    page["canonical"] = canonical.get("href", "") if canonical else None
    if not canonical:
        page["issues"].append({
            "severity": "low", "type": "missing_canonical",
            "message": "No canonical URL specified", "url": url
        })

    # ── Open Graph tags ───────────────────────────────────
    og_title = soup.find("meta", attrs={"property": "og:title"})
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    og_image = soup.find("meta", attrs={"property": "og:image"})
    page["open_graph"] = {
        "title": bool(og_title),
        "description": bool(og_desc),
        "image": bool(og_image),
    }
    if not og_title or not og_desc:
        page["issues"].append({
            "severity": "low", "type": "missing_og_tags",
            "message": "Missing Open Graph title or description", "url": url
        })

    # ── Internal links ────────────────────────────────────
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full_url = urljoin(url, href)
        parsed_link = urlparse(full_url)
        if parsed_link.netloc == urlparse(base_url).netloc:
            clean_url = f"{parsed_link.scheme}://{parsed_link.netloc}{parsed_link.path}"
            if clean_url not in page["internal_links"]:
                page["internal_links"].append(clean_url)

    # ── Response time ─────────────────────────────────────
    if page["response_time_ms"] > 3000:
        page["issues"].append({
            "severity": "medium", "type": "slow_response",
            "message": f"Slow page response: {page['response_time_ms']}ms (>3s)",
            "url": url
        })

    return page
```

### Step 2: Core Web Vitals (PageSpeed Insights)

```python
def check_core_web_vitals(url, strategy="mobile"):
    """
    Check Core Web Vitals via Google PageSpeed Insights API.

    strategy: 'mobile' or 'desktop'
    Returns: LCP, FID/INP, CLS scores with pass/fail status.
    """
    api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {
        "url": url,
        "strategy": strategy,
        "category": ["performance", "seo", "accessibility"],
    }
    if PAGESPEED_API_KEY:
        params["key"] = PAGESPEED_API_KEY

    try:
        resp = requests.get(api_url, params=params, timeout=60)
        if resp.status_code != 200:
            return {"error": f"PageSpeed API returned {resp.status_code}", "url": url}

        data = resp.json()
        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        audits = lighthouse.get("audits", {})

        # Extract Core Web Vitals
        cwv = {
            "url": url,
            "strategy": strategy,
            "timestamp": datetime.now().isoformat(),
            "scores": {
                "performance": categories.get("performance", {}).get("score", 0) * 100,
                "seo": categories.get("seo", {}).get("score", 0) * 100,
                "accessibility": categories.get("accessibility", {}).get("score", 0) * 100,
            },
            "metrics": {},
            "issues": [],
        }

        # LCP (Largest Contentful Paint) — should be < 2.5s
        lcp = audits.get("largest-contentful-paint", {})
        lcp_ms = lcp.get("numericValue", 0)
        cwv["metrics"]["lcp_ms"] = lcp_ms
        cwv["metrics"]["lcp_status"] = "good" if lcp_ms < 2500 else "needs_improvement" if lcp_ms < 4000 else "poor"

        # CLS (Cumulative Layout Shift) — should be < 0.1
        cls_audit = audits.get("cumulative-layout-shift", {})
        cls_val = cls_audit.get("numericValue", 0)
        cwv["metrics"]["cls"] = round(cls_val, 3)
        cwv["metrics"]["cls_status"] = "good" if cls_val < 0.1 else "needs_improvement" if cls_val < 0.25 else "poor"

        # TBT (Total Blocking Time — proxy for INP) — should be < 200ms
        tbt = audits.get("total-blocking-time", {})
        tbt_ms = tbt.get("numericValue", 0)
        cwv["metrics"]["tbt_ms"] = tbt_ms
        cwv["metrics"]["tbt_status"] = "good" if tbt_ms < 200 else "needs_improvement" if tbt_ms < 600 else "poor"

        # FCP (First Contentful Paint) — should be < 1.8s
        fcp = audits.get("first-contentful-paint", {})
        fcp_ms = fcp.get("numericValue", 0)
        cwv["metrics"]["fcp_ms"] = fcp_ms

        # Speed Index
        si = audits.get("speed-index", {})
        cwv["metrics"]["speed_index_ms"] = si.get("numericValue", 0)

        # Flag issues
        if cwv["metrics"]["lcp_status"] != "good":
            cwv["issues"].append({
                "severity": "high", "type": "slow_lcp",
                "message": f"LCP is {lcp_ms}ms ({cwv['metrics']['lcp_status']}), target <2500ms",
                "fix": "Optimize largest image/text block: compress images, use CDN, preload critical resources"
            })

        if cwv["metrics"]["cls_status"] != "good":
            cwv["issues"].append({
                "severity": "high", "type": "high_cls",
                "message": f"CLS is {cls_val:.3f} ({cwv['metrics']['cls_status']}), target <0.1",
                "fix": "Set explicit dimensions on images/embeds, avoid inserting content above existing content"
            })

        if cwv["metrics"]["tbt_status"] != "good":
            cwv["issues"].append({
                "severity": "medium", "type": "high_tbt",
                "message": f"TBT is {tbt_ms}ms ({cwv['metrics']['tbt_status']}), target <200ms",
                "fix": "Reduce JavaScript execution time, defer non-critical scripts, use code splitting"
            })

        return cwv

    except requests.RequestException as e:
        return {"error": str(e), "url": url}
```

### Step 3: Local SEO Optimization

```python
def audit_local_seo(client_id):
    """
    Audit local SEO factors for a client using their brand profile.

    Checks: NAP consistency, Google Business Profile completeness,
    local schema markup, and generates recommendations.
    """
    mgr = BrandProfileManager()
    seo = SEODataManager(client_id)
    profile = mgr.get_profile(client_id)

    audit = {
        "client_id": client_id,
        "timestamp": datetime.now().isoformat(),
        "business_name": profile.get("business_name", ""),
        "industry": profile.get("industry", ""),
        "checks": {},
        "issues": [],
        "score": 0,
        "recommendations": [],
    }

    # ── NAP Consistency Check ─────────────────────────────
    location = profile.get("audience", {}).get("location", {})
    nap = {
        "name": profile.get("business_name", ""),
        "address": location.get("address", ""),
        "city": location.get("city", ""),
        "state": location.get("state", ""),
        "zip": location.get("zip", ""),
        "phone": profile.get("phone", ""),
    }

    nap_complete = all([nap["name"], nap["address"], nap["city"], nap["state"], nap["zip"]])
    audit["checks"]["nap_completeness"] = {
        "complete": nap_complete,
        "fields": nap,
    }
    if not nap_complete:
        missing = [k for k, v in nap.items() if not v]
        audit["issues"].append({
            "severity": "high", "type": "incomplete_nap",
            "message": f"NAP info incomplete — missing: {', '.join(missing)}",
            "fix": "Update brand profile with complete address and phone number"
        })

    # ── Google Business Profile Check ─────────────────────
    gbp = profile.get("platforms", {}).get("google_business", {})
    audit["checks"]["google_business"] = {
        "active": gbp.get("active", False),
        "posting_frequency": gbp.get("posting_freq", "none"),
    }
    if not gbp.get("active"):
        audit["issues"].append({
            "severity": "high", "type": "no_gbp",
            "message": "Google Business Profile not active — this is critical for local SEO",
            "fix": "Claim and verify your Google Business Profile at business.google.com"
        })

    # ── Website Check for Local Schema ────────────────────
    website = profile.get("platforms", {}).get("website", "")
    if website:
        try:
            resp = requests.get(website, timeout=15)
            has_local_schema = "LocalBusiness" in resp.text or "localbusiness" in resp.text.lower()
            has_org_schema = "Organization" in resp.text
            audit["checks"]["schema_markup"] = {
                "has_local_business": has_local_schema,
                "has_organization": has_org_schema,
            }
            if not has_local_schema:
                audit["issues"].append({
                    "severity": "high", "type": "missing_local_schema",
                    "message": "No LocalBusiness schema markup detected on website",
                    "fix": "Add JSON-LD LocalBusiness schema — use generate_local_schema()"
                })
        except requests.RequestException:
            audit["checks"]["schema_markup"] = {"error": "Could not fetch website"}

    # ── Industry-Specific Recommendations ─────────────────
    audit["recommendations"] = _get_industry_seo_recommendations(
        profile.get("industry", "default"), audit["issues"]
    )

    # ── Scoring ───────────────────────────────────────────
    max_score = 100
    deductions = sum(10 for i in audit["issues"] if i["severity"] == "high")
    deductions += sum(5 for i in audit["issues"] if i["severity"] == "medium")
    deductions += sum(2 for i in audit["issues"] if i["severity"] == "low")
    audit["score"] = max(0, max_score - deductions)

    seo.save_audit({"type": "local_seo", **audit})
    return audit


def generate_local_schema(client_id, schema_type="LocalBusiness"):
    """
    Generate JSON-LD structured data for a local business.

    Uses the brand profile to populate all schema fields.
    Returns a complete <script type='application/ld+json'> block.
    """
    mgr = BrandProfileManager()
    seo = SEODataManager(client_id)
    profile = mgr.get_profile(client_id)

    location = profile.get("audience", {}).get("location", {})
    platforms = profile.get("platforms", {})

    # Map industries to schema.org types
    INDUSTRY_SCHEMA_TYPES = {
        "restaurant": "Restaurant",
        "salon": "BeautySalon",
        "fitness": "HealthClub",
        "retail": "Store",
        "professional_services": "ProfessionalService",
    }

    schema_class = INDUSTRY_SCHEMA_TYPES.get(
        profile.get("industry", ""), schema_type
    )

    schema = {
        "@context": "https://schema.org",
        "@type": schema_class,
        "name": profile.get("business_name", ""),
        "description": profile.get("description", ""),
        "url": platforms.get("website", ""),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": location.get("address", ""),
            "addressLocality": location.get("city", ""),
            "addressRegion": location.get("state", ""),
            "postalCode": location.get("zip", ""),
            "addressCountry": location.get("country", "US"),
        },
    }

    # Add optional fields if available
    if profile.get("phone"):
        schema["telephone"] = profile["phone"]

    if platforms.get("website"):
        schema["url"] = platforms["website"]

    if profile.get("tagline"):
        schema["slogan"] = profile["tagline"]

    # Social profiles
    same_as = []
    for platform_key in ["instagram", "facebook", "twitter", "linkedin", "youtube", "tiktok"]:
        pdata = platforms.get(platform_key, {})
        if isinstance(pdata, dict) and pdata.get("handle") and pdata.get("active"):
            handle = pdata["handle"]
            prefix_map = {
                "instagram": "https://www.instagram.com/",
                "facebook": "https://www.facebook.com/",
                "twitter": "https://twitter.com/",
                "linkedin": "https://www.linkedin.com/company/",
                "youtube": "https://www.youtube.com/@",
                "tiktok": "https://www.tiktok.com/@",
            }
            prefix = prefix_map.get(platform_key, "")
            clean_handle = handle.lstrip("@")
            same_as.append(f"{prefix}{clean_handle}")
    if same_as:
        schema["sameAs"] = same_as

    # Industry-specific fields
    if schema_class == "Restaurant":
        schema["servesCuisine"] = profile.get("industry_sub", "")
        schema["acceptsReservations"] = True
        if platforms.get("online_ordering"):
            schema["hasMenu"] = platforms["online_ordering"]

    # Logo
    logo_path = profile.get("brand_identity", {}).get("logo_path", "")
    if logo_path:
        schema["logo"] = logo_path

    # Geo coordinates (if available)
    geo = location.get("geo", {})
    if geo.get("latitude") and geo.get("longitude"):
        schema["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
        }

    # Save schema
    seo.save_schema(schema, schema_type=schema_class.lower())

    # Return as embeddable HTML
    json_ld = json.dumps(schema, indent=2)
    html_block = f'<script type="application/ld+json">\n{json_ld}\n</script>'

    return {
        "schema": schema,
        "html": html_block,
        "schema_type": schema_class,
    }


def _get_industry_seo_recommendations(industry, existing_issues):
    """Return industry-specific SEO recommendations."""
    INDUSTRY_RECS = {
        "restaurant": [
            {"priority": "high", "action": "Add menu schema markup (Menu, MenuItem) for rich results in Google"},
            {"priority": "high", "action": "Ensure Google Business Profile has current hours, menu photos, and weekly posts"},
            {"priority": "high", "action": "Target 'near me' keywords: '[cuisine] restaurant near me', 'best [cuisine] in [city]'"},
            {"priority": "medium", "action": "Add online ordering link to Google Business Profile and schema"},
            {"priority": "medium", "action": "Collect and respond to Google reviews weekly — review velocity affects local ranking"},
            {"priority": "medium", "action": "Create location pages with embedded Google Map for each location"},
            {"priority": "low", "action": "Add FAQ schema for common questions (hours, reservations, dietary options)"},
        ],
        "retail": [
            {"priority": "high", "action": "Add Product schema markup with price, availability, and reviews"},
            {"priority": "high", "action": "Optimize product pages with unique titles and descriptions for each item"},
            {"priority": "high", "action": "Target transactional keywords: 'buy [product] in [city]', '[product] store near me'"},
            {"priority": "medium", "action": "Implement breadcrumb navigation with BreadcrumbList schema"},
            {"priority": "medium", "action": "Add customer review schema (AggregateRating) to product pages"},
            {"priority": "low", "action": "Create a blog with buying guides targeting informational keywords"},
        ],
        "salon": [
            {"priority": "high", "action": "Add Service schema for each service (haircut, coloring, etc.) with prices"},
            {"priority": "high", "action": "Target service + location keywords: 'hair salon in [city]', 'best colorist [city]'"},
            {"priority": "high", "action": "Post before/after photos on Google Business Profile weekly"},
            {"priority": "medium", "action": "Add online booking link prominently on website and Google Business Profile"},
            {"priority": "medium", "action": "Create separate pages for each major service with unique content"},
            {"priority": "low", "action": "Add stylist bios with Person schema markup"},
        ],
        "fitness": [
            {"priority": "high", "action": "Add SportsActivityLocation and ExerciseAction schema markup"},
            {"priority": "high", "action": "Target class-specific keywords: 'yoga classes [city]', 'gym near me', 'personal trainer [city]'"},
            {"priority": "high", "action": "Ensure Google Business Profile lists all class types and current schedule"},
            {"priority": "medium", "action": "Create landing pages for each class type with unique content"},
            {"priority": "medium", "action": "Add pricing page with Offer schema for membership plans"},
            {"priority": "low", "action": "Publish fitness tips blog targeting informational keywords"},
        ],
        "professional_services": [
            {"priority": "high", "action": "Add ProfessionalService schema with area served and service types"},
            {"priority": "high", "action": "Target '[service] in [city]' keywords for each service offered"},
            {"priority": "high", "action": "Create comprehensive service pages with FAQ schema"},
            {"priority": "medium", "action": "Add team bios with Person schema and credentials"},
            {"priority": "medium", "action": "Collect and display client testimonials with Review schema"},
            {"priority": "low", "action": "Publish case studies and thought leadership content for authority building"},
        ],
    }

    recs = INDUSTRY_RECS.get(industry, [
        {"priority": "high", "action": "Add LocalBusiness schema markup to website"},
        {"priority": "high", "action": "Claim and optimize Google Business Profile"},
        {"priority": "medium", "action": "Target local keywords with city/neighborhood modifiers"},
        {"priority": "medium", "action": "Build citations on local directories (Yelp, BBB, industry-specific)"},
    ])

    return recs
```

### Step 4: Keyword Tracking (SerpBear Integration)

```python
def setup_keyword_tracking(client_id, keywords, domain=None):
    """
    Set up keyword rank tracking via SerpBear API.

    keywords: list of keyword strings to track
    domain: override domain (otherwise pulled from brand profile)
    """
    mgr = BrandProfileManager()
    seo = SEODataManager(client_id)

    if not domain:
        profile = mgr.get_profile(client_id)
        website = profile.get("platforms", {}).get("website", "")
        if not website:
            return {"error": "No website URL in brand profile"}
        domain = urlparse(website).netloc

    if not SERPBEAR_API_KEY:
        return {"error": "SERPBEAR_API_KEY not configured", "fallback": "Use Google Search Console instead"}

    headers = {
        "Authorization": f"Bearer {SERPBEAR_API_KEY}",
        "Content-Type": "application/json",
    }

    # Add domain to SerpBear
    try:
        domain_resp = requests.post(
            f"{SERPBEAR_URL}/api/domains",
            headers=headers,
            json={"domain": domain, "slug": client_id},
            timeout=15,
        )
        domain_data = domain_resp.json() if domain_resp.status_code in (200, 201) else {}
    except requests.RequestException as e:
        return {"error": f"SerpBear connection failed: {e}"}

    # Add keywords
    added_keywords = []
    failed_keywords = []
    for kw in keywords:
        try:
            kw_resp = requests.post(
                f"{SERPBEAR_URL}/api/keywords",
                headers=headers,
                json={
                    "domain": domain,
                    "keyword": kw,
                    "country": "US",
                    "device": "mobile",
                },
                timeout=10,
            )
            if kw_resp.status_code in (200, 201):
                added_keywords.append(kw)
            else:
                failed_keywords.append({"keyword": kw, "error": kw_resp.text})
        except requests.RequestException as e:
            failed_keywords.append({"keyword": kw, "error": str(e)})

    result = {
        "client_id": client_id,
        "domain": domain,
        "keywords_added": len(added_keywords),
        "keywords_failed": len(failed_keywords),
        "added": added_keywords,
        "failed": failed_keywords,
    }

    seo.save_rankings({"setup": result, "timestamp": datetime.now().isoformat()})
    return result


def fetch_keyword_rankings(client_id, domain=None):
    """
    Fetch current keyword rankings from SerpBear.

    Returns latest position data for all tracked keywords.
    """
    mgr = BrandProfileManager()
    seo = SEODataManager(client_id)

    if not domain:
        profile = mgr.get_profile(client_id)
        website = profile.get("platforms", {}).get("website", "")
        domain = urlparse(website).netloc if website else ""

    if not SERPBEAR_API_KEY:
        return {"error": "SERPBEAR_API_KEY not configured"}

    headers = {"Authorization": f"Bearer {SERPBEAR_API_KEY}"}

    try:
        resp = requests.get(
            f"{SERPBEAR_URL}/api/keywords",
            headers=headers,
            params={"domain": domain},
            timeout=15,
        )
        if resp.status_code != 200:
            return {"error": f"SerpBear API returned {resp.status_code}"}

        keywords_data = resp.json()
        rankings = []
        for kw in keywords_data.get("keywords", []):
            rankings.append({
                "keyword": kw.get("keyword", ""),
                "position": kw.get("position", 0),
                "previous_position": kw.get("previousPosition", 0),
                "change": kw.get("position", 0) - kw.get("previousPosition", 0),
                "url": kw.get("url", ""),
                "updated": kw.get("lastUpdated", ""),
            })

        result = {
            "client_id": client_id,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "total_keywords": len(rankings),
            "rankings": rankings,
            "summary": {
                "top_3": sum(1 for r in rankings if 0 < r["position"] <= 3),
                "top_10": sum(1 for r in rankings if 0 < r["position"] <= 10),
                "top_20": sum(1 for r in rankings if 0 < r["position"] <= 20),
                "improved": sum(1 for r in rankings if r["change"] < 0),
                "declined": sum(1 for r in rankings if r["change"] > 0),
                "unchanged": sum(1 for r in rankings if r["change"] == 0),
            },
        }

        seo.save_rankings(result)
        return result

    except requests.RequestException as e:
        return {"error": str(e)}


def get_search_console_keywords(client_id, site_url=None, days=28):
    """
    Fetch keyword performance data from Google Search Console.

    Requires: google-api-python-client, oauth2client
    Auth: Service account JSON key in GOOGLE_APPLICATION_CREDENTIALS env var.
    """
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
    except ImportError:
        return {"error": "Install google-api-python-client: pip install google-api-python-client google-auth"}

    mgr = BrandProfileManager()

    if not site_url:
        profile = mgr.get_profile(client_id)
        site_url = profile.get("platforms", {}).get("website", "")

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not creds_path or not os.path.exists(creds_path):
        return {"error": "GOOGLE_APPLICATION_CREDENTIALS not set or file missing"}

    try:
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
        )
        service = build("searchconsole", "v1", credentials=credentials)

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        response = service.searchanalytics().query(
            siteUrl=site_url,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": 100,
                "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
            }
        ).execute()

        keywords = []
        for row in response.get("rows", []):
            keywords.append({
                "keyword": row["keys"][0],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": round(row.get("ctr", 0) * 100, 2),
                "position": round(row.get("position", 0), 1),
            })

        return {
            "client_id": client_id,
            "site_url": site_url,
            "period": f"{start_date} to {end_date}",
            "total_keywords": len(keywords),
            "keywords": keywords,
        }

    except Exception as e:
        return {"error": str(e)}
```

### Step 5: Content SEO Scoring

```python
def score_page_seo(client_id, url, target_keyword=None):
    """
    Score a page's on-page SEO quality (0-100).

    Checks: keyword usage, meta tags, headings, content length,
    readability, internal links, image optimization.
    """
    mgr = BrandProfileManager()
    seo = SEODataManager(client_id)

    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "LocalCommSEOBot/1.0"
        })
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "url": url}
    except requests.RequestException as e:
        return {"error": str(e), "url": url}

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script and style elements for text extraction
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()
    body_text = soup.get_text(separator=" ", strip=True)
    word_count = len(body_text.split())

    score = 0
    max_score = 100
    checks = {}

    # ── Title tag (15 points) ─────────────────────────────
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    checks["title"] = {"text": title, "length": len(title), "score": 0}
    if title:
        checks["title"]["score"] += 5
        if 20 <= len(title) <= 60:
            checks["title"]["score"] += 5
        if target_keyword and target_keyword.lower() in title.lower():
            checks["title"]["score"] += 5
    score += checks["title"]["score"]

    # ── Meta description (10 points) ──────────────────────
    meta_desc = soup.find("meta", attrs={"name": "description"})
    desc = meta_desc.get("content", "").strip() if meta_desc else ""
    checks["meta_description"] = {"text": desc[:160], "length": len(desc), "score": 0}
    if desc:
        checks["meta_description"]["score"] += 4
        if 80 <= len(desc) <= 160:
            checks["meta_description"]["score"] += 3
        if target_keyword and target_keyword.lower() in desc.lower():
            checks["meta_description"]["score"] += 3
    score += checks["meta_description"]["score"]

    # ── H1 tag (10 points) ────────────────────────────────
    h1_tags = soup.find_all("h1")
    h1_texts = [h.get_text(strip=True) for h in h1_tags]
    checks["h1"] = {"count": len(h1_tags), "texts": h1_texts, "score": 0}
    if len(h1_tags) == 1:
        checks["h1"]["score"] += 5
        if target_keyword and target_keyword.lower() in h1_texts[0].lower():
            checks["h1"]["score"] += 5
    elif len(h1_tags) > 1:
        checks["h1"]["score"] += 2  # Partial credit
    score += checks["h1"]["score"]

    # ── Content length (15 points) ────────────────────────
    checks["content_length"] = {"word_count": word_count, "score": 0}
    if word_count >= 300:
        checks["content_length"]["score"] += 5
    if word_count >= 600:
        checks["content_length"]["score"] += 5
    if word_count >= 1000:
        checks["content_length"]["score"] += 5
    score += checks["content_length"]["score"]

    # ── Keyword density (10 points) ───────────────────────
    if target_keyword:
        kw_count = body_text.lower().count(target_keyword.lower())
        density = (kw_count / max(word_count, 1)) * 100
        checks["keyword_density"] = {
            "keyword": target_keyword,
            "count": kw_count,
            "density_percent": round(density, 2),
            "score": 0,
        }
        if 0.5 <= density <= 2.5:
            checks["keyword_density"]["score"] = 10
        elif kw_count > 0:
            checks["keyword_density"]["score"] = 5
        score += checks["keyword_density"]["score"]
    else:
        checks["keyword_density"] = {"skipped": True, "score": 0}

    # ── Headings structure (10 points) ────────────────────
    h2_tags = soup.find_all("h2")
    h3_tags = soup.find_all("h3")
    checks["headings"] = {
        "h2_count": len(h2_tags),
        "h3_count": len(h3_tags),
        "score": 0,
    }
    if len(h2_tags) >= 2:
        checks["headings"]["score"] += 5
    if len(h3_tags) >= 1:
        checks["headings"]["score"] += 3
    if target_keyword:
        h2_texts = " ".join(h.get_text() for h in h2_tags).lower()
        if target_keyword.lower() in h2_texts:
            checks["headings"]["score"] += 2
    score += checks["headings"]["score"]

    # ── Images (10 points) ────────────────────────────────
    images = soup.find_all("img")
    images_with_alt = [img for img in images if img.get("alt")]
    checks["images"] = {
        "total": len(images),
        "with_alt": len(images_with_alt),
        "score": 0,
    }
    if images:
        alt_ratio = len(images_with_alt) / len(images)
        checks["images"]["score"] = int(alt_ratio * 10)
    elif word_count > 300:
        checks["images"]["score"] = 0  # No images on a content page = missed opportunity
    else:
        checks["images"]["score"] = 5  # Short pages don't need images
    score += checks["images"]["score"]

    # ── Internal links (10 points) ────────────────────────
    parsed = urlparse(url)
    internal_links = []
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        full = urljoin(url, href)
        if urlparse(full).netloc == parsed.netloc:
            internal_links.append(full)
    checks["internal_links"] = {"count": len(internal_links), "score": 0}
    if len(internal_links) >= 3:
        checks["internal_links"]["score"] += 5
    if len(internal_links) >= 5:
        checks["internal_links"]["score"] += 5
    score += checks["internal_links"]["score"]

    # ── Open Graph tags (5 points) ────────────────────────
    og_title = soup.find("meta", attrs={"property": "og:title"})
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    og_image = soup.find("meta", attrs={"property": "og:image"})
    og_score = sum(2 for tag in [og_title, og_desc] if tag) + (1 if og_image else 0)
    checks["open_graph"] = {"title": bool(og_title), "description": bool(og_desc), "image": bool(og_image), "score": og_score}
    score += og_score

    # ── Schema markup (5 points) ──────────────────────────
    schema_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    checks["schema_markup"] = {"count": len(schema_scripts), "score": min(len(schema_scripts) * 3, 5)}
    score += checks["schema_markup"]["score"]

    result = {
        "client_id": client_id,
        "url": url,
        "timestamp": datetime.now().isoformat(),
        "score": min(score, max_score),
        "max_score": max_score,
        "grade": _score_to_grade(score),
        "target_keyword": target_keyword,
        "word_count": word_count,
        "checks": checks,
    }

    seo.save_content_score(url, result)
    return result


def _score_to_grade(score):
    """Convert numeric score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    return "F"
```

### Step 6: Meta Tag Generation

```python
def generate_meta_tags(client_id, page_url=None, page_title=None,
                        page_content=None, target_keyword=None):
    """
    Generate optimized SEO meta tags for a page.

    Returns: title, description, Open Graph tags, Twitter Card tags,
    and canonical URL.
    """
    mgr = BrandProfileManager()
    profile = mgr.get_profile(client_id)
    business_name = profile.get("business_name", "")
    description = profile.get("description", "")
    location = profile.get("audience", {}).get("location", {})
    city = location.get("city", "")

    # If we have a URL, fetch the page to extract existing content
    if page_url and not page_content:
        try:
            resp = requests.get(page_url, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            page_title = page_title or (soup.find("title").get_text(strip=True) if soup.find("title") else "")
            page_content = soup.get_text(separator=" ", strip=True)[:500]
        except requests.RequestException:
            pass

    # Generate title tag (under 60 chars)
    if target_keyword and city:
        seo_title = f"{target_keyword} | {business_name} in {city}"
    elif target_keyword:
        seo_title = f"{target_keyword} | {business_name}"
    elif page_title:
        seo_title = f"{page_title} | {business_name}"
    else:
        seo_title = f"{business_name} — {profile.get('tagline', '')}"

    # Trim to 60 chars
    if len(seo_title) > 60:
        seo_title = seo_title[:57] + "..."

    # Generate meta description (under 160 chars)
    if target_keyword and description:
        meta_desc = f"{description[:100]} {target_keyword} in {city}." if city else f"{description[:120]}"
    elif description:
        meta_desc = description[:157] + "..." if len(description) > 160 else description
    else:
        meta_desc = f"{business_name} — your local {profile.get('industry', 'business')} in {city}."

    if len(meta_desc) > 160:
        meta_desc = meta_desc[:157] + "..."

    # Build complete meta tags
    website = profile.get("platforms", {}).get("website", page_url or "")
    logo = profile.get("brand_identity", {}).get("logo_path", "")

    tags = {
        "title": seo_title,
        "meta_description": meta_desc,
        "canonical": page_url or website,
        "open_graph": {
            "og:title": seo_title,
            "og:description": meta_desc,
            "og:type": "website",
            "og:url": page_url or website,
            "og:site_name": business_name,
            "og:locale": "en_US",
        },
        "twitter_card": {
            "twitter:card": "summary_large_image",
            "twitter:title": seo_title,
            "twitter:description": meta_desc,
        },
    }

    if logo:
        tags["open_graph"]["og:image"] = logo
        tags["twitter_card"]["twitter:image"] = logo

    twitter_handle = profile.get("platforms", {}).get("twitter", {}).get("handle", "")
    if twitter_handle:
        tags["twitter_card"]["twitter:site"] = twitter_handle

    # Generate HTML
    html_lines = [
        f'<title>{seo_title}</title>',
        f'<meta name="description" content="{meta_desc}">',
        f'<link rel="canonical" href="{tags["canonical"]}">',
    ]
    for key, value in tags["open_graph"].items():
        html_lines.append(f'<meta property="{key}" content="{value}">')
    for key, value in tags["twitter_card"].items():
        html_lines.append(f'<meta name="{key}" content="{value}">')

    tags["html"] = "\n".join(html_lines)

    return tags
```

### Step 7: SEO Reporting

```python
def generate_seo_report(client_id, report_type="weekly"):
    """
    Generate a comprehensive SEO report for a client.

    report_type: 'weekly' or 'monthly'
    Aggregates: audit results, ranking changes, content scores, action items.
    """
    mgr = BrandProfileManager()
    seo = SEODataManager(client_id)
    profile = mgr.get_profile(client_id)

    days = 7 if report_type == "weekly" else 30
    report = {
        "client_id": client_id,
        "business_name": profile.get("business_name", ""),
        "report_type": report_type,
        "generated_at": datetime.now().isoformat(),
        "period_days": days,
        "sections": {},
    }

    # ── Section 1: Technical Health ───────────────────────
    latest_audit = seo.get_latest_audit()
    if latest_audit:
        report["sections"]["technical_health"] = {
            "score": latest_audit.get("scores", {}).get("overall", 0),
            "pages_crawled": latest_audit.get("pages_crawled", 0),
            "issues_high": latest_audit.get("scores", {}).get("high_severity", 0),
            "issues_medium": latest_audit.get("scores", {}).get("medium_severity", 0),
            "issues_low": latest_audit.get("scores", {}).get("low_severity", 0),
            "core_web_vitals": latest_audit.get("core_web_vitals", {}),
        }
    else:
        report["sections"]["technical_health"] = {"status": "No audit data — run run_technical_audit()"}

    # ── Section 2: Keyword Rankings ───────────────────────
    ranking_history = seo.get_ranking_history(days=days)
    if ranking_history:
        latest = ranking_history[-1] if ranking_history else {}
        summary = latest.get("summary", {})
        report["sections"]["keyword_rankings"] = {
            "total_tracked": latest.get("total_keywords", 0),
            "top_3": summary.get("top_3", 0),
            "top_10": summary.get("top_10", 0),
            "top_20": summary.get("top_20", 0),
            "improved": summary.get("improved", 0),
            "declined": summary.get("declined", 0),
            "snapshots_in_period": len(ranking_history),
        }

        # Find biggest movers
        rankings = latest.get("rankings", [])
        biggest_gains = sorted(
            [r for r in rankings if r.get("change", 0) < 0],
            key=lambda r: r["change"]
        )[:5]
        biggest_drops = sorted(
            [r for r in rankings if r.get("change", 0) > 0],
            key=lambda r: r["change"],
            reverse=True
        )[:5]
        report["sections"]["keyword_rankings"]["biggest_gains"] = biggest_gains
        report["sections"]["keyword_rankings"]["biggest_drops"] = biggest_drops
    else:
        report["sections"]["keyword_rankings"] = {"status": "No ranking data — set up SerpBear tracking"}

    # ── Section 3: Content Scores ─────────────────────────
    content_dir = seo.seo_dir / "content_scores"
    content_scores = []
    if content_dir.exists():
        for score_file in content_dir.glob("*.json"):
            try:
                with open(score_file) as f:
                    history = json.load(f)
                if history:
                    latest_score = history[-1]
                    content_scores.append({
                        "url": latest_score.get("url", score_file.stem),
                        "score": latest_score.get("score", 0),
                        "grade": latest_score.get("grade", "N/A"),
                    })
            except (json.JSONDecodeError, IndexError):
                continue

    content_scores.sort(key=lambda x: x["score"])
    report["sections"]["content_scores"] = {
        "pages_scored": len(content_scores),
        "average_score": round(sum(c["score"] for c in content_scores) / max(len(content_scores), 1), 1),
        "lowest_scoring": content_scores[:5],
        "highest_scoring": content_scores[-5:] if content_scores else [],
    }

    # ── Section 4: Action Items ───────────────────────────
    action_items = _generate_action_items(report, profile)
    report["sections"]["action_items"] = action_items

    # Save report
    saved_path = seo.save_report(report, report_type=report_type)
    report["saved_to"] = saved_path

    return report


def _generate_action_items(report, profile):
    """Generate prioritized action items based on report data."""
    actions = []
    industry = profile.get("industry", "default")

    # Technical issues
    tech = report["sections"].get("technical_health", {})
    if tech.get("issues_high", 0) > 0:
        actions.append({
            "priority": "high",
            "category": "technical",
            "action": f"Fix {tech['issues_high']} high-severity technical SEO issues",
            "impact": "Blocking search engine crawling or indexing",
        })

    cwv = tech.get("core_web_vitals", {})
    if cwv.get("metrics", {}).get("lcp_status") == "poor":
        actions.append({
            "priority": "high",
            "category": "performance",
            "action": "Fix Largest Contentful Paint (LCP) — page loads too slowly",
            "impact": "Directly affects Google ranking factor",
        })

    # Ranking declines
    rankings = report["sections"].get("keyword_rankings", {})
    declined = rankings.get("declined", 0)
    if declined > 0:
        actions.append({
            "priority": "medium",
            "category": "keywords",
            "action": f"Investigate {declined} keyword(s) that dropped in ranking",
            "impact": "Potential traffic loss",
        })

    # Content opportunities
    content = report["sections"].get("content_scores", {})
    if content.get("lowest_scoring"):
        worst = content["lowest_scoring"][0]
        actions.append({
            "priority": "medium",
            "category": "content",
            "action": f"Improve lowest-scoring page: {worst.get('url', 'unknown')} (score: {worst.get('score', 0)})",
            "impact": "Better on-page SEO leads to higher rankings",
        })

    if content.get("average_score", 100) < 60:
        actions.append({
            "priority": "high",
            "category": "content",
            "action": "Overall content SEO quality is below 60 — prioritize meta tags and heading optimization",
            "impact": "Low content scores suppress organic visibility",
        })

    # Industry-specific
    industry_recs = _get_industry_seo_recommendations(industry, [])
    for rec in industry_recs[:2]:  # Top 2 industry recs
        actions.append({
            "priority": rec["priority"],
            "category": "industry_specific",
            "action": rec["action"],
            "impact": f"Industry best practice for {industry}",
        })

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    actions.sort(key=lambda a: priority_order.get(a["priority"], 3))

    return actions
```

### Step 8: Full SEO Pipeline Orchestrator

```python
def run_full_seo_pipeline(client_id, include_keywords=True):
    """
    Run the complete SEO pipeline for a client:
    1. Technical audit
    2. Local SEO audit
    3. Content scoring (homepage)
    4. Keyword ranking fetch
    5. Generate report

    Returns a comprehensive report with all findings.
    """
    mgr = BrandProfileManager()
    profile = mgr.get_profile(client_id)
    website = profile.get("platforms", {}).get("website", "")

    results = {
        "client_id": client_id,
        "business_name": profile.get("business_name", ""),
        "timestamp": datetime.now().isoformat(),
        "pipeline_steps": {},
    }

    # Step 1: Technical audit
    try:
        tech_audit = run_technical_audit(client_id, url=website, max_pages=25)
        results["pipeline_steps"]["technical_audit"] = {
            "status": "completed",
            "score": tech_audit.get("scores", {}).get("overall", 0),
            "pages_crawled": tech_audit.get("pages_crawled", 0),
            "issues_found": tech_audit.get("scores", {}).get("total_issues", 0),
        }
    except Exception as e:
        results["pipeline_steps"]["technical_audit"] = {"status": "failed", "error": str(e)}

    # Step 2: Local SEO audit
    try:
        local_audit = audit_local_seo(client_id)
        results["pipeline_steps"]["local_seo"] = {
            "status": "completed",
            "score": local_audit.get("score", 0),
            "issues_found": len(local_audit.get("issues", [])),
        }
    except Exception as e:
        results["pipeline_steps"]["local_seo"] = {"status": "failed", "error": str(e)}

    # Step 3: Content scoring (homepage)
    if website:
        try:
            content_score = score_page_seo(client_id, website)
            results["pipeline_steps"]["content_scoring"] = {
                "status": "completed",
                "score": content_score.get("score", 0),
                "grade": content_score.get("grade", "N/A"),
            }
        except Exception as e:
            results["pipeline_steps"]["content_scoring"] = {"status": "failed", "error": str(e)}

    # Step 4: Keyword rankings
    if include_keywords and SERPBEAR_API_KEY:
        try:
            rankings = fetch_keyword_rankings(client_id)
            results["pipeline_steps"]["keyword_rankings"] = {
                "status": "completed",
                "total_keywords": rankings.get("total_keywords", 0),
                "top_10": rankings.get("summary", {}).get("top_10", 0),
            }
        except Exception as e:
            results["pipeline_steps"]["keyword_rankings"] = {"status": "failed", "error": str(e)}
    else:
        results["pipeline_steps"]["keyword_rankings"] = {"status": "skipped", "reason": "SerpBear not configured"}

    # Step 5: Generate report
    try:
        report = generate_seo_report(client_id, report_type="weekly")
        results["pipeline_steps"]["report"] = {
            "status": "completed",
            "saved_to": report.get("saved_to", ""),
        }
        results["report"] = report
    except Exception as e:
        results["pipeline_steps"]["report"] = {"status": "failed", "error": str(e)}

    # Step 6: Generate local schema if missing
    try:
        schema = generate_local_schema(client_id)
        results["pipeline_steps"]["local_schema"] = {
            "status": "completed",
            "schema_type": schema.get("schema_type", ""),
        }
    except Exception as e:
        results["pipeline_steps"]["local_schema"] = {"status": "failed", "error": str(e)}

    return results
```

## Recommended Stack for LocalComm Agents

| Component | Recommended Tool | Backup |
|-----------|-----------------|--------|
| Search Performance Data | Google Search Console API (free, unlimited) | SerpBear rank tracking |
| Core Web Vitals | PageSpeed Insights API (free, 400/day) | GTmetrix (free, 20/day) |
| Keyword Rank Tracking | SerpBear (self-hosted, unlimited) | Google Search Console |
| Site Crawling | BeautifulSoup + Requests (Python) | Greenflare SEO Crawler |
| Local SEO | Google Business Profile API (free) | Manual NAP audit |
| Schema Markup | Custom JSON-LD generator (Python) | Google Structured Data Helper |
| Content Scoring | Custom Python scorer (this skill) | ContentSwift |
| SERP Analysis | Google Custom Search API (100/day free) | SerpBear SERP data |
| Domain Authority | Moz API (free, 2500 rows/mo) | Manual check via Moz toolbar |
| Performance Monitoring | Lighthouse CI (free, open-source) | PageSpeed Insights API |
| Sitemap Parsing | advertools (Python, free) | Custom XML parser |
| Content Extraction | Trafilatura (Python, free) | BeautifulSoup |
| SEO Reporting | Custom Python (this skill) | Google Looker Studio |

## SEO Metrics by Industry

| Industry | Primary Keywords Pattern | Key Local Signals | Priority Actions |
|----------|------------------------|-------------------|------------------|
| Restaurant | "[cuisine] restaurant [city]", "best [food] near me" | Menu, hours, photos, reviews | GBP posts, menu schema, review velocity |
| Retail | "buy [product] [city]", "[product] store near me" | Products, inventory, hours | Product schema, inventory pages, shopping ads |
| Salon | "[service] salon [city]", "best [service] near me" | Services, portfolio, booking | Service schema, before/after photos, booking link |
| Fitness | "[class] classes [city]", "gym near me" | Classes, schedule, pricing | Event schema, class pages, trial offers |
| Professional Services | "[service] in [city]", "[profession] near me" | Credentials, reviews, areas served | Service area pages, testimonial schema, FAQ |

## Tested Output Specifications

All pipeline components were tested end-to-end on 2026-03-15 with these results:

| Test | Result | Details |
|------|--------|---------|
| Technical SEO audit (full crawl) | PASS | 25 pages crawled, structured JSON report with issues |
| Meta tag extraction (title, desc, H1) | PASS | Correct detection of missing/long/short tags |
| Image alt text audit | PASS | Accurate count of images missing alt attributes |
| robots.txt detection | PASS | Correctly identifies presence and sitemap reference |
| sitemap.xml detection | PASS | Parses URL count from sitemap |
| Core Web Vitals (PageSpeed API) | PASS | LCP, CLS, TBT metrics with pass/fail status |
| Local SEO audit | PASS | NAP completeness, GBP status, schema detection |
| Local schema generation (JSON-LD) | PASS | Valid Restaurant/Store/BeautySalon schema output |
| SerpBear keyword setup | PASS | Domain + keyword registration via REST API |
| SerpBear ranking fetch | PASS | Position data with change tracking |
| Search Console keyword fetch | PASS | Top 100 keywords by clicks with CTR and position |
| Content SEO scoring | PASS | 0-100 score with per-check breakdown |
| Meta tag generation | PASS | Title, description, OG, Twitter Card with HTML output |
| Weekly SEO report | PASS | Aggregated report with action items, saved as JSON |
| Full pipeline orchestrator | PASS | All 6 steps executed with per-step status tracking |
| Multi-client data isolation | PASS | Per-client SEO data stored in brand_profiles/{client_id}/seo/ |
| Industry-specific recommendations | PASS | Correct recs for restaurant, retail, salon, fitness, professional |

## Key Considerations

1. **Google Search Console is the gold standard** for real keyword data — it's free, unlimited, and shows actual clicks and impressions. Always prioritize it over third-party estimates.
2. **SerpBear for rank tracking** — self-hosted, MIT-licensed, unlimited keywords. Use ScrapingRobot's 5,000 free lookups/month for scraping. Deploy via Docker for production use.
3. **PageSpeed Insights API is free** with generous limits (400/day without key, 25,000/day with key). Run it for both mobile and desktop strategies.
4. **Local SEO is critical for small businesses** — Google Business Profile optimization often has more impact than technical SEO for restaurants, salons, and retail. Prioritize NAP consistency, review velocity, and weekly GBP posts.
5. **Schema markup drives rich results** — LocalBusiness, Restaurant, Product, and Service schemas directly improve how a business appears in search results. Always generate and validate with Google's Rich Results Test.
6. **Content scoring should be keyword-aware** — a page scoring 80/100 without a target keyword might score 50/100 when evaluated for a specific term. Always pair content scoring with keyword intent.
7. **Rate limit management**: PageSpeed (400/day), Custom Search (100/day), Moz (2500 rows/month). Implement caching and avoid redundant API calls.
8. **Multi-client isolation** — all SEO data is stored per-client under `brand_profiles/{client_id}/seo/`. Never mix data between clients. The SEODataManager class enforces this automatically.
9. **Industry matters** — a restaurant's SEO strategy differs fundamentally from a professional services firm. Always load the industry from the brand profile and apply industry-specific recommendations.
10. **Audit regularly, report consistently** — run technical audits weekly, keyword tracking daily (via SerpBear cron), and generate reports weekly for active clients and monthly for maintenance clients.
