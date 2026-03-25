#!/usr/bin/env python3
"""
Fetch and parse web pages for GEO analysis.
Extracts HTML, text content, meta tags, headers, and structured data.
Adapted from geo-seo-claude (zubair-trabzada/geo-seo-claude).
"""

import sys
import json
import re
from urllib.parse import urljoin, urlparse
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install requests beautifulsoup4 lxml")
    sys.exit(1)

AI_CRAWLERS = {
    "GPTBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)",
    "ClaudeBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +https://www.anthropic.com/claude-bot)",
    "PerplexityBot": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
    "GoogleBot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "BingBot": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
}

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}

ALL_AI_CRAWLERS = [
    "GPTBot", "OAI-SearchBot", "ChatGPT-User",
    "ClaudeBot", "anthropic-ai",
    "PerplexityBot",
    "CCBot", "Bytespider", "cohere-ai",
    "Google-Extended", "GoogleOther",
    "Applebot-Extended", "FacebookBot", "Amazonbot",
]


def fetch_page(url: str, timeout: int = 30) -> dict:
    result = {
        "url": url,
        "status_code": None,
        "redirect_chain": [],
        "headers": {},
        "meta_tags": {},
        "title": None,
        "description": None,
        "canonical": None,
        "h1_tags": [],
        "heading_structure": [],
        "word_count": 0,
        "text_content": "",
        "internal_links": [],
        "external_links": [],
        "images": [],
        "structured_data": [],
        "has_ssr_content": True,
        "security_headers": {},
        "errors": [],
    }

    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)

        if response.history:
            result["redirect_chain"] = [{"url": r.url, "status": r.status_code} for r in response.history]

        result["status_code"] = response.status_code
        result["headers"] = dict(response.headers)

        security_headers = [
            "Strict-Transport-Security", "Content-Security-Policy",
            "X-Frame-Options", "X-Content-Type-Options",
            "Referrer-Policy", "Permissions-Policy",
        ]
        for header in security_headers:
            result["security_headers"][header] = response.headers.get(header, None)

        soup = BeautifulSoup(response.text, "lxml")

        title_tag = soup.find("title")
        result["title"] = title_tag.get_text(strip=True) if title_tag else None

        for meta in soup.find_all("meta"):
            name = meta.get("name", meta.get("property", ""))
            content = meta.get("content", "")
            if name and content:
                result["meta_tags"][name.lower()] = content
                if name.lower() == "description":
                    result["description"] = content

        canonical = soup.find("link", rel="canonical")
        result["canonical"] = canonical.get("href") if canonical else None

        for level in range(1, 7):
            for heading in soup.find_all(f"h{level}"):
                text = heading.get_text(strip=True)
                result["heading_structure"].append({"level": level, "text": text})
                if level == 1:
                    result["h1_tags"].append(text)

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                result["structured_data"].append(data)
            except (json.JSONDecodeError, TypeError):
                result["errors"].append("Invalid JSON-LD detected")

        js_app_roots = soup.find_all(id=re.compile(r"(app|root|__next|__nuxt)", re.I))

        for element in soup.find_all(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        text = soup.get_text(separator=" ", strip=True)
        result["text_content"] = text
        result["word_count"] = len(text.split())

        parsed_url = urlparse(url)
        base_domain = parsed_url.netloc
        for link in soup.find_all("a", href=True):
            href = urljoin(url, link["href"])
            link_text = link.get_text(strip=True)
            parsed_href = urlparse(href)
            if parsed_href.netloc == base_domain:
                result["internal_links"].append({"url": href, "text": link_text})
            elif parsed_href.scheme in ("http", "https"):
                result["external_links"].append({"url": href, "text": link_text})

        for img in soup.find_all("img"):
            result["images"].append({
                "src": img.get("src", ""),
                "alt": img.get("alt", ""),
                "width": img.get("width"),
                "height": img.get("height"),
                "loading": img.get("loading"),
            })

        if js_app_roots:
            for root in js_app_roots:
                inner_text = root.get_text(strip=True)
                if len(inner_text) < 50:
                    result["has_ssr_content"] = False
                    result["errors"].append(
                        f"Possible client-side only rendering: #{root.get('id', 'unknown')} has minimal server-rendered content"
                    )

    except requests.exceptions.Timeout:
        result["errors"].append(f"Timeout after {timeout} seconds")
    except requests.exceptions.ConnectionError as e:
        result["errors"].append(f"Connection error: {str(e)}")
    except Exception as e:
        result["errors"].append(f"Unexpected error: {str(e)}")

    return result


def fetch_robots_txt(url: str, timeout: int = 15) -> dict:
    """Fetch and parse robots.txt — check which AI crawlers are allowed/blocked."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    result = {
        "url": robots_url,
        "exists": False,
        "content": "",
        "ai_crawler_status": {},
        "blocked_crawlers": [],
        "allowed_crawlers": [],
        "issues": [],
        "recommendations": [],
    }

    try:
        response = requests.get(robots_url, headers=DEFAULT_HEADERS, timeout=timeout)
        if response.status_code == 200:
            result["exists"] = True
            content = response.text
            result["content"] = content

            lines = content.lower().split("\n")
            current_agent = None
            rules = {}

            for line in lines:
                line = line.strip()
                if line.startswith("user-agent:"):
                    current_agent = line.split(":", 1)[1].strip()
                    if current_agent not in rules:
                        rules[current_agent] = {"disallow": [], "allow": []}
                elif line.startswith("disallow:") and current_agent:
                    path = line.split(":", 1)[1].strip()
                    rules[current_agent]["disallow"].append(path)
                elif line.startswith("allow:") and current_agent:
                    path = line.split(":", 1)[1].strip()
                    rules[current_agent]["allow"].append(path)

            # Check each AI crawler
            for crawler in ALL_AI_CRAWLERS:
                crawler_lower = crawler.lower()
                status = "unknown"

                if crawler_lower in rules:
                    disallowed = rules[crawler_lower]["disallow"]
                    if "/" in disallowed or "/*" in disallowed:
                        status = "blocked"
                        result["blocked_crawlers"].append(crawler)
                    elif disallowed:
                        status = "partial"
                    else:
                        status = "allowed"
                        result["allowed_crawlers"].append(crawler)
                elif "*" in rules:
                    star_disallowed = rules["*"]["disallow"]
                    if "/" in star_disallowed or "/*" in star_disallowed:
                        status = "blocked_by_wildcard"
                        result["blocked_crawlers"].append(crawler)
                    else:
                        status = "allowed_by_wildcard"
                        result["allowed_crawlers"].append(crawler)
                else:
                    status = "allowed"
                    result["allowed_crawlers"].append(crawler)

                result["ai_crawler_status"][crawler] = status

            if result["blocked_crawlers"]:
                result["issues"].append(
                    f"{len(result['blocked_crawlers'])} AI crawlers blocked: {', '.join(result['blocked_crawlers'][:5])}"
                )
                result["recommendations"].append(
                    "Add explicit Allow rules for AI crawlers (GPTBot, ClaudeBot, PerplexityBot, Google-Extended)"
                )
        else:
            result["recommendations"].append("No robots.txt found — create one with explicit AI crawler permissions")
    except Exception as e:
        result["issues"].append(f"Error fetching robots.txt: {str(e)}")

    return result


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    mode = sys.argv[2] if len(sys.argv) > 2 else "full"

    if mode == "robots":
        print(json.dumps(fetch_robots_txt(url), indent=2))
    else:
        print(json.dumps(fetch_page(url), indent=2))
