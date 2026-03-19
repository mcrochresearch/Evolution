#!/usr/bin/env python3
"""
Citability Scorer — Analyzes content blocks for AI citation readiness.
Scores passages based on how likely AI models are to cite them.

Based on research showing optimal AI-cited passages are:
- 134-167 words long
- Self-contained (extractable without context)
- Fact-rich with specific statistics
- Structured with clear answer patterns

Adapted from geo-seo-claude (zubair-trabzada/geo-seo-claude).
"""

import sys
import json
import re
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install requests beautifulsoup4 lxml")
    sys.exit(1)


def score_passage(text: str, heading: Optional[str] = None) -> dict:
    """Score a single passage for AI citability (0-100)."""
    words = text.split()
    word_count = len(words)

    scores = {
        "answer_block_quality": 0,
        "self_containment": 0,
        "structural_readability": 0,
        "statistical_density": 0,
        "uniqueness_signals": 0,
    }

    # === 1. Answer Block Quality (30%) ===
    abq_score = 0
    definition_patterns = [
        r"\b\w+\s+is\s+(?:a|an|the)\s",
        r"\b\w+\s+refers?\s+to\s",
        r"\b\w+\s+means?\s",
        r"\b\w+\s+(?:can be |are )?defined\s+as\s",
        r"\bin\s+(?:simple|other)\s+(?:terms|words)\s*,",
    ]
    for pattern in definition_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            abq_score += 15
            break

    first_60_words = " ".join(words[:60])
    if any(
        re.search(p, first_60_words, re.IGNORECASE)
        for p in [r"\b(?:is|are|was|were|means?|refers?)\b", r"\d+%", r"\$[\d,]+", r"\d+\s+(?:million|billion|thousand)"]
    ):
        abq_score += 15

    if heading and heading.endswith("?"):
        abq_score += 10

    sentences = re.split(r"[.!?]+", text)
    short_clear_sentences = sum(1 for s in sentences if 5 <= len(s.split()) <= 25)
    if sentences:
        clarity_ratio = short_clear_sentences / len(sentences)
        abq_score += int(clarity_ratio * 10)

    if re.search(
        r"(?:according to|research shows|studies? (?:show|indicate|suggest|found)|data (?:shows|indicates|suggests))",
        text, re.IGNORECASE,
    ):
        abq_score += 10

    scores["answer_block_quality"] = min(abq_score, 30)

    # === 2. Self-Containment (25%) ===
    sc_score = 0
    if 134 <= word_count <= 167:
        sc_score += 10
    elif 100 <= word_count <= 200:
        sc_score += 7
    elif 80 <= word_count <= 250:
        sc_score += 4
    elif word_count < 30 or word_count > 400:
        sc_score += 0
    else:
        sc_score += 2

    pronoun_count = len(re.findall(
        r"\b(?:it|they|them|their|this|that|these|those|he|she|his|her)\b",
        text, re.IGNORECASE,
    ))
    if word_count > 0:
        pronoun_ratio = pronoun_count / word_count
        if pronoun_ratio < 0.02:
            sc_score += 8
        elif pronoun_ratio < 0.04:
            sc_score += 5
        elif pronoun_ratio < 0.06:
            sc_score += 3

    proper_nouns = len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text))
    if proper_nouns >= 3:
        sc_score += 7
    elif proper_nouns >= 1:
        sc_score += 4

    scores["self_containment"] = min(sc_score, 25)

    # === 3. Structural Readability (20%) ===
    sr_score = 0
    if sentences:
        avg_sentence_length = word_count / len(sentences)
        if 10 <= avg_sentence_length <= 20:
            sr_score += 8
        elif 8 <= avg_sentence_length <= 25:
            sr_score += 5
        else:
            sr_score += 2

    if re.search(r"(?:first|second|third|finally|additionally|moreover|furthermore)", text, re.IGNORECASE):
        sr_score += 4
    if re.search(r"(?:\d+[\.]\s|\b(?:step|tip|point)\s+\d+)", text, re.IGNORECASE):
        sr_score += 4
    if "\n" in text:
        sr_score += 4

    scores["structural_readability"] = min(sr_score, 20)

    # === 4. Statistical Density (15%) ===
    sd_score = 0
    pct_count = len(re.findall(r"\d+(?:\.\d+)?%", text))
    sd_score += min(pct_count * 3, 6)
    dollar_count = len(re.findall(r"\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|M|B|K))?", text))
    sd_score += min(dollar_count * 3, 5)
    number_count = len(re.findall(
        r"\b\d+(?:,\d{3})*(?:\.\d+)?\s+(?:users|customers|pages|sites|companies|businesses|people|percent|times|x\b)",
        text, re.IGNORECASE,
    ))
    sd_score += min(number_count * 2, 4)
    year_count = len(re.findall(r"\b20(?:2[3-6]|1\d)\b", text))
    if year_count > 0:
        sd_score += 2
    source_patterns = [
        r"(?:according to|per|from|by)\s+[A-Z]",
        r"(?:Gartner|Forrester|McKinsey|Harvard|Stanford|MIT|Google|Microsoft|OpenAI|Anthropic)",
        r"\([A-Z][a-z]+(?:\s+\d{4})?\)",
    ]
    for pattern in source_patterns:
        if re.search(pattern, text):
            sd_score += 2
            break

    scores["statistical_density"] = min(sd_score, 15)

    # === 5. Uniqueness Signals (10%) ===
    us_score = 0
    if re.search(
        r"(?:our (?:research|study|data|analysis|survey|findings)|we (?:found|discovered|analyzed|surveyed|measured))",
        text, re.IGNORECASE,
    ):
        us_score += 5
    if re.search(r"(?:case study|for example|for instance|in practice|real-world|hands-on)", text, re.IGNORECASE):
        us_score += 3
    if re.search(r"(?:using|with|via|through)\s+[A-Z][a-z]+", text):
        us_score += 2

    scores["uniqueness_signals"] = min(us_score, 10)

    total = sum(scores.values())

    if total >= 80:
        grade, label = "A", "Highly Citable"
    elif total >= 65:
        grade, label = "B", "Good Citability"
    elif total >= 50:
        grade, label = "C", "Moderate Citability"
    elif total >= 35:
        grade, label = "D", "Low Citability"
    else:
        grade, label = "F", "Poor Citability"

    return {
        "heading": heading,
        "word_count": word_count,
        "total_score": total,
        "grade": grade,
        "label": label,
        "breakdown": scores,
        "preview": " ".join(words[:30]) + ("..." if word_count > 30 else ""),
    }


def analyze_page_citability(url: str) -> dict:
    """Fetch a page and score all content blocks for AI citability."""
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    result = {
        "url": url,
        "overall_score": 0,
        "overall_grade": "F",
        "passages_scored": 0,
        "top_passages": [],
        "all_scores": [],
        "recommendations": [],
    }

    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        soup = BeautifulSoup(response.text, "lxml")

        # Remove boilerplate
        for el in soup.find_all(["script", "style", "nav", "footer", "header"]):
            el.decompose()

        # Score each content section
        headings = soup.find_all(["h1", "h2", "h3"])
        scored_passages = []

        for heading in headings:
            heading_text = heading.get_text(strip=True)
            # Collect text after heading until next heading
            content_parts = []
            for sibling in heading.next_siblings:
                if sibling.name in ["h1", "h2", "h3"]:
                    break
                if hasattr(sibling, "get_text"):
                    t = sibling.get_text(strip=True)
                    if t:
                        content_parts.append(t)

            combined = " ".join(content_parts)
            if len(combined.split()) >= 20:
                score = score_passage(combined, heading_text)
                scored_passages.append(score)

        # Also score paragraphs not under headings
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text.split()) >= 50:
                score = score_passage(text)
                scored_passages.append(score)

        if scored_passages:
            result["passages_scored"] = len(scored_passages)
            result["all_scores"] = scored_passages
            avg_score = sum(p["total_score"] for p in scored_passages) / len(scored_passages)
            result["overall_score"] = round(avg_score)

            if avg_score >= 80:
                result["overall_grade"] = "A"
            elif avg_score >= 65:
                result["overall_grade"] = "B"
            elif avg_score >= 50:
                result["overall_grade"] = "C"
            elif avg_score >= 35:
                result["overall_grade"] = "D"
            else:
                result["overall_grade"] = "F"

            # Top 3 best passages
            top = sorted(scored_passages, key=lambda x: x["total_score"], reverse=True)[:3]
            result["top_passages"] = top

            # Recommendations based on common weaknesses
            low_stat = [p for p in scored_passages if p["breakdown"]["statistical_density"] < 5]
            if len(low_stat) > len(scored_passages) * 0.6:
                result["recommendations"].append("Add specific statistics, dollar amounts, and percentages to content — AI models prioritize fact-dense passages")

            short_passages = [p for p in scored_passages if p["word_count"] < 80]
            if len(short_passages) > len(scored_passages) * 0.4:
                result["recommendations"].append("Expand thin content sections to 134-167 words — optimal length for AI citation")

            low_sc = [p for p in scored_passages if p["breakdown"]["self_containment"] < 10]
            if len(low_sc) > len(scored_passages) * 0.5:
                result["recommendations"].append("Make sections more self-contained — avoid pronouns like 'it', 'they', 'this' that require context to understand")

    except Exception as e:
        result["error"] = str(e)

    return result


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"

    if url.startswith("http"):
        print(json.dumps(analyze_page_citability(url), indent=2))
    else:
        # Score a text string directly
        text = " ".join(sys.argv[1:])
        print(json.dumps(score_passage(text), indent=2))
