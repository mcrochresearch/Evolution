#!/usr/bin/env python3
"""
GEO Audit — Full AI search visibility audit for SMB websites.
Runs: page fetch, AI crawler check, citability scoring, llms.txt check, schema analysis.

Usage:
    python3 geo_audit.py https://example.com
    python3 geo_audit.py https://example.com --json
    python3 geo_audit.py https://example.com --pitch   # condensed pitch format

Output: GEO Score (0-100) + prioritized action list
"""

import sys
import json
import argparse
from pathlib import Path

# Make sure sibling scripts are importable
sys.path.insert(0, str(Path(__file__).parent))

from fetch_page import fetch_page, fetch_robots_txt
from citability_scorer import analyze_page_citability
from llmstxt_generator import validate_llmstxt, generate_llmstxt


def run_geo_audit(url: str) -> dict:
    """Run a full GEO audit on a URL. Returns structured results."""

    print(f"[GEO] Auditing {url}...", file=sys.stderr)

    # 1. Fetch page
    print("[GEO] 1/4 Fetching page...", file=sys.stderr)
    page = fetch_page(url)

    # 2. Check robots.txt for AI crawler access
    print("[GEO] 2/4 Checking AI crawler access...", file=sys.stderr)
    robots = fetch_robots_txt(url)

    # 3. Score content citability
    print("[GEO] 3/4 Scoring content citability...", file=sys.stderr)
    citability = analyze_page_citability(url)

    # 4. Check llms.txt
    print("[GEO] 4/4 Checking llms.txt...", file=sys.stderr)
    llms = validate_llmstxt(url)

    # === Score Calculation ===
    scores = {}

    # AI Citability (25%)
    scores["citability"] = {
        "weight": 0.25,
        "raw": citability.get("overall_score", 0),
        "score": round(citability.get("overall_score", 0) * 0.25),
        "grade": citability.get("overall_grade", "F"),
    }

    # AI Crawler Access (20%) — blocked crawlers = big penalty
    blocked = len(robots.get("blocked_crawlers", []))
    total_crawlers = 14
    crawler_score = max(0, 100 - (blocked / total_crawlers * 100))
    scores["crawler_access"] = {
        "weight": 0.20,
        "raw": round(crawler_score),
        "score": round(crawler_score * 0.20),
        "blocked": blocked,
        "blocked_list": robots.get("blocked_crawlers", []),
    }

    # Structured Data / Schema (20%)
    has_schema = len(page.get("structured_data", [])) > 0
    schema_types = [s.get("@type", "") for s in page.get("structured_data", [])]
    has_local_business = any("LocalBusiness" in str(t) for t in schema_types)
    has_org = any("Organization" in str(t) for t in schema_types)
    schema_score = 0
    if has_schema:
        schema_score += 40
    if has_local_business:
        schema_score += 40
    if has_org:
        schema_score += 20
    scores["schema"] = {
        "weight": 0.20,
        "raw": schema_score,
        "score": round(schema_score * 0.20),
        "has_schema": has_schema,
        "schema_types": schema_types,
    }

    # llms.txt (15%)
    llms_score = 0
    if llms.get("exists"):
        llms_score += 60
        if llms.get("format_valid"):
            llms_score += 40
    scores["llmstxt"] = {
        "weight": 0.15,
        "raw": llms_score,
        "score": round(llms_score * 0.15),
        "exists": llms.get("exists", False),
        "valid": llms.get("format_valid", False),
    }

    # Technical Foundation (10%) — title, description, H1, SSR
    tech_score = 0
    if page.get("title"):
        tech_score += 25
    if page.get("description"):
        tech_score += 25
    if page.get("h1_tags"):
        tech_score += 25
    if page.get("has_ssr_content"):
        tech_score += 25
    scores["technical"] = {
        "weight": 0.10,
        "raw": tech_score,
        "score": round(tech_score * 0.10),
        "has_title": bool(page.get("title")),
        "has_description": bool(page.get("description")),
        "has_h1": bool(page.get("h1_tags")),
        "has_ssr": page.get("has_ssr_content", True),
    }

    # Content Volume (10%)
    word_count = page.get("word_count", 0)
    content_score = min(100, (word_count / 500) * 100)
    scores["content_volume"] = {
        "weight": 0.10,
        "raw": round(content_score),
        "score": round(content_score * 0.10),
        "word_count": word_count,
    }

    total_score = sum(v["score"] for v in scores.values())

    if total_score >= 80:
        overall_grade = "A"
    elif total_score >= 65:
        overall_grade = "B"
    elif total_score >= 50:
        overall_grade = "C"
    elif total_score >= 35:
        overall_grade = "D"
    else:
        overall_grade = "F"

    # === Action Plan ===
    actions = []

    if not llms.get("exists"):
        actions.append({
            "priority": 1,
            "impact": "HIGH",
            "effort": "LOW",
            "action": "Create llms.txt file",
            "detail": "Zero competitors have this. Takes 30 minutes. Tells AI crawlers exactly what your site offers.",
        })

    if blocked > 0:
        actions.append({
            "priority": 2,
            "impact": "HIGH",
            "effort": "LOW",
            "action": f"Unblock {blocked} AI crawlers in robots.txt",
            "detail": f"Blocked: {', '.join(robots.get('blocked_crawlers', [])[:5])}. ChatGPT and Claude can't read your site.",
        })

    if not has_local_business:
        actions.append({
            "priority": 3,
            "impact": "HIGH",
            "effort": "MEDIUM",
            "action": "Add LocalBusiness JSON-LD schema markup",
            "detail": "AI models use structured data to understand and recommend local businesses. You have none.",
        })

    if citability.get("overall_score", 0) < 50:
        actions.append({
            "priority": 4,
            "impact": "MEDIUM",
            "effort": "MEDIUM",
            "action": f"Improve content citability (current: {citability.get('overall_score', 0)}/100)",
            "detail": "Content is too thin/vague for AI models to cite. Add stats, specific services with descriptions, and answer common questions directly.",
        })

    if not page.get("description"):
        actions.append({
            "priority": 5,
            "impact": "MEDIUM",
            "effort": "LOW",
            "action": "Add meta description",
            "detail": "Missing meta description — AI models and search engines use this to understand your page.",
        })

    return {
        "url": url,
        "geo_score": total_score,
        "overall_grade": overall_grade,
        "scores": scores,
        "actions": actions,
        "page": {
            "title": page.get("title"),
            "description": page.get("description"),
            "word_count": page.get("word_count", 0),
            "h1_tags": page.get("h1_tags", []),
            "structured_data_count": len(page.get("structured_data", [])),
        },
        "citability": {
            "overall_score": citability.get("overall_score", 0),
            "overall_grade": citability.get("overall_grade", "F"),
            "passages_scored": citability.get("passages_scored", 0),
            "top_passages": citability.get("top_passages", [])[:2],
            "recommendations": citability.get("recommendations", []),
        },
        "robots": {
            "blocked_crawlers": robots.get("blocked_crawlers", []),
            "allowed_crawlers": robots.get("allowed_crawlers", []),
        },
        "llmstxt": llms,
    }


def format_pitch_report(audit: dict) -> str:
    """Format a concise pitch-friendly report."""
    score = audit["geo_score"]
    grade = audit["overall_grade"]
    url = audit["url"]
    blocked = len(audit["robots"]["blocked_crawlers"])
    has_schema = audit["scores"]["schema"]["has_schema"]
    has_llms = audit["llmstxt"]["exists"]
    citability_score = audit["citability"]["overall_score"]
    citability_grade = audit["citability"]["overall_grade"]

    lines = [
        f"🔍 GEO AUDIT — {url}",
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"",
        f"AI Search Visibility Score: {score}/100 (Grade {grade})",
        f"",
        f"📊 BREAKDOWN:",
        f"  Content Citability:  {citability_score}/100 ({citability_grade}) — {'✓' if citability_score >= 60 else '✗'} AI models {'can' if citability_score >= 60 else 'cannot'} easily quote your content",
        f"  AI Crawler Access:   " + ("✓ All bots allowed" if blocked == 0 else f"✗ {blocked} AI bots blocked (ChatGPT, Claude, etc. cannot crawl you)"),
        f"  Schema Markup:       {'✓ Present' if has_schema else '✗ Missing — AI has no structured business data'}",
        f"  llms.txt:            {'✓ Present' if has_llms else '✗ Missing — AI crawlers have no site guide'}",
        f"",
        f"🚨 TOP FIXES (fastest ROI first):",
    ]

    for i, action in enumerate(audit["actions"][:4], 1):
        lines.append(f"  {i}. [{action['impact']} impact / {action['effort']} effort] {action['action']}")
        lines.append(f"     → {action['detail']}")

    lines += [
        f"",
        f"💡 WHY THIS MATTERS:",
        f"  AI-referred traffic converts 4.4x better than organic search.",
        f"  AI search traffic is up 527% YoY. Traditional search dropping 50% by 2028.",
        f"  With a score of {score}/100, you're invisible to AI. We can fix that.",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GEO Audit — AI search visibility scorer")
    parser.add_argument("url", help="URL to audit")
    parser.add_argument("--json", action="store_true", help="Output full JSON")
    parser.add_argument("--pitch", action="store_true", help="Output pitch-format report")
    args = parser.parse_args()

    audit = run_geo_audit(args.url)

    if args.json:
        print(json.dumps(audit, indent=2))
    elif args.pitch:
        print(format_pitch_report(audit))
    else:
        # Default: score + actions
        print(f"\n{'='*50}")
        print(f"GEO Score: {audit['geo_score']}/100 (Grade {audit['overall_grade']})")
        print(f"{'='*50}")
        print(f"\nPage: {audit['page']['title']}")
        print(f"Words: {audit['page']['word_count']} | Schema: {audit['scores']['schema']['raw']}/100 | Citability: {audit['citability']['overall_score']}/100")
        print(f"AI Crawlers Blocked: {len(audit['robots']['blocked_crawlers'])} | llms.txt: {'YES' if audit['llmstxt']['exists'] else 'NO'}")
        print(f"\nTOP ACTIONS:")
        for action in audit["actions"]:
            print(f"  [{action['impact']}] {action['action']}")
