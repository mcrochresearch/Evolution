#!/usr/bin/env python3
"""
llms.txt Generator — Creates and validates llms.txt files for AI crawler guidance.

The llms.txt standard helps AI crawlers understand your site structure.
Location: /llms.txt (root of domain)

Adapted from geo-seo-claude (zubair-trabzada/geo-seo-claude).
"""

import sys
import json
import re
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install requests beautifulsoup4 lxml")
    sys.exit(1)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def validate_llmstxt(url: str) -> dict:
    """Check if llms.txt exists and validate its format."""
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    llms_url = f"{base_url}/llms.txt"
    llms_full_url = f"{base_url}/llms-full.txt"

    result = {
        "url": llms_url,
        "exists": False,
        "format_valid": False,
        "has_title": False,
        "has_description": False,
        "has_sections": False,
        "has_links": False,
        "section_count": 0,
        "link_count": 0,
        "content": "",
        "issues": [],
        "suggestions": [],
        "full_version": {"url": llms_full_url, "exists": False},
    }

    try:
        response = requests.get(llms_url, headers=DEFAULT_HEADERS, timeout=15)
        if response.status_code == 200:
            result["exists"] = True
            content = response.text
            result["content"] = content
            lines = content.strip().split("\n")

            if lines and lines[0].startswith("# "):
                result["has_title"] = True
            else:
                result["issues"].append("Missing title (should start with '# Site Name')")

            for line in lines:
                if line.startswith("> "):
                    result["has_description"] = True
                    break
            if not result["has_description"]:
                result["issues"].append("Missing description (use '> Brief description')")

            sections = [l for l in lines if l.startswith("## ")]
            result["section_count"] = len(sections)
            result["has_sections"] = len(sections) > 0
            if not result["has_sections"]:
                result["issues"].append("No sections found (use '## Section Name')")

            links = re.findall(r"- \[.+\]\(.+\)", content)
            result["link_count"] = len(links)
            result["has_links"] = len(links) > 0
            if not result["has_links"]:
                result["issues"].append("No page links found (use '- [Page Title](url): Description')")

            result["format_valid"] = (
                result["has_title"] and result["has_description"]
                and result["has_sections"] and result["has_links"]
            )

            if result["link_count"] < 5:
                result["suggestions"].append("Add more key pages (aim for 10-20)")
            if result["section_count"] < 2:
                result["suggestions"].append("Add more sections to organize content types")
            if "contact" not in content.lower():
                result["suggestions"].append("Add a Contact section with address and phone")

        else:
            result["issues"].append(f"llms.txt not found (status {response.status_code})")
    except Exception as e:
        result["issues"].append(f"Error checking llms.txt: {str(e)}")

    try:
        r2 = requests.get(llms_full_url, headers=DEFAULT_HEADERS, timeout=10)
        result["full_version"]["exists"] = r2.status_code == 200
    except Exception:
        pass

    return result


def generate_llmstxt(url: str, business_info: dict = None) -> dict:
    """
    Generate an llms.txt file by crawling the site.
    
    business_info: optional dict with keys like:
        name, description, phone, address, city, state,
        services (list), hours, founded_year
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    result = {
        "generated_llmstxt": "",
        "pages_analyzed": 0,
        "sections": {},
        "error": None,
    }

    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        soup = BeautifulSoup(response.text, "lxml")
    except Exception as e:
        result["error"] = f"Failed to fetch homepage: {str(e)}"
        return result

    title = soup.find("title")
    site_name = title.get_text(strip=True).split("|")[0].split("-")[0].strip() if title else parsed.netloc
    meta_desc = soup.find("meta", attrs={"name": "description"})
    site_description = meta_desc.get("content", "") if meta_desc else f"Official website of {site_name}"

    if business_info:
        if business_info.get("name"):
            site_name = business_info["name"]
        if business_info.get("description"):
            site_description = business_info["description"]

    pages = {
        "Main Pages": [],
        "Services": [],
        "Resources": [],
        "Company": [],
        "Contact": [],
    }

    seen_urls = set()
    for link in soup.find_all("a", href=True):
        href = urljoin(base_url, link["href"])
        link_text = link.get_text(strip=True)

        if not link_text or len(link_text) < 2:
            continue
        parsed_href = urlparse(href)
        if parsed_href.netloc != parsed.netloc:
            continue
        if href in seen_urls:
            continue
        if any(ext in href for ext in [".pdf", ".jpg", ".png", ".gif", ".css", ".js"]):
            continue

        seen_urls.add(href)
        path = parsed_href.path.lower()
        page_entry = {"url": href, "title": link_text}

        if any(kw in path for kw in ["/service", "/pricing", "/product", "/solution", "/what-we-do"]):
            pages["Services"].append(page_entry)
        elif any(kw in path for kw in ["/blog", "/article", "/resource", "/guide", "/learn", "/faq"]):
            pages["Resources"].append(page_entry)
        elif any(kw in path for kw in ["/about", "/team", "/our-story", "/history"]):
            pages["Company"].append(page_entry)
        elif any(kw in path for kw in ["/contact", "/location", "/directions", "/hours"]):
            pages["Contact"].append(page_entry)
        elif path not in ["/", ""]:
            pages["Main Pages"].append(page_entry)

    result["sections"] = pages
    result["pages_analyzed"] = len(seen_urls)

    # Build llms.txt content
    lines = [f"# {site_name}", ""]
    lines.append(f"> {site_description}")
    lines.append("")

    # Business facts if provided
    if business_info:
        lines.append("## Key Facts")
        lines.append("")
        if business_info.get("founded_year"):
            lines.append(f"- Founded: {business_info['founded_year']}")
        if business_info.get("address") and business_info.get("city"):
            lines.append(f"- Location: {business_info['address']}, {business_info['city']}, {business_info.get('state', '')}")
        if business_info.get("phone"):
            lines.append(f"- Phone: {business_info['phone']}")
        if business_info.get("services"):
            lines.append(f"- Services: {', '.join(business_info['services'])}")
        lines.append("")

    # Add page sections
    for section_name, section_pages in pages.items():
        if section_pages:
            lines.append(f"## {section_name}")
            lines.append("")
            for page in section_pages[:10]:
                lines.append(f"- [{page['title']}]({page['url']})")
            lines.append("")

    # Homepage always included
    lines.append("## Homepage")
    lines.append("")
    lines.append(f"- [{site_name} Home]({base_url}): {site_description[:100]}")
    lines.append("")

    result["generated_llmstxt"] = "\n".join(lines)

    return result


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    mode = sys.argv[2] if len(sys.argv) > 2 else "generate"

    if mode == "validate":
        print(json.dumps(validate_llmstxt(url), indent=2))
    else:
        result = generate_llmstxt(url)
        print(json.dumps(result, indent=2))
        if result.get("generated_llmstxt"):
            print("\n--- GENERATED llms.txt ---")
            print(result["generated_llmstxt"])
