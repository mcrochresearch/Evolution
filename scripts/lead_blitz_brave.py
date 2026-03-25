#!/usr/bin/env python3
"""
Lead Blitz v2 — Read search results from a JSONL file and insert into CRM.
Results are pre-gathered via web_search tool, dumped to a file, then this script
deduplicates, verifies URLs, and inserts.

Usage:
  1. Dump search results to data/search_results.jsonl (one JSON per line)
  2. python3 scripts/lead_blitz_brave.py
"""

import json
import sqlite3
import urllib.request
import urllib.parse
import uuid
import time
import sys
import ssl
import re
from datetime import datetime

DB_PATH = "/Users/scottmckenna/.localcrm/database.db"
RESULTS_FILE = "/Users/scottmckenna/.openclaw/workspace/data/search_results.jsonl"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

SKIP_DOMAINS = {
    "yelp.com", "facebook.com", "instagram.com", "twitter.com",
    "linkedin.com", "youtube.com", "tiktok.com", "bbb.org",
    "yellowpages.com", "mapquest.com", "foursquare.com",
    "tripadvisor.com", "angi.com", "homeadvisor.com", "thumbtack.com",
    "nextdoor.com", "manta.com", "chamberofcommerce.com",
    "google.com", "apple.com", "amazon.com", "wikipedia.org",
    "reddit.com", "pinterest.com", "patch.com", "indeed.com",
    "glassdoor.com", "ziprecruiter.com", "niche.com", "x.com",
}


def get_existing(conn):
    biz = {r[0] for r in conn.execute("SELECT LOWER(business) FROM contacts").fetchall()}
    sites = {r[0] for r in conn.execute("SELECT LOWER(website) FROM contacts WHERE website IS NOT NULL AND website != ''").fetchall()}
    return biz, sites


def extract_domain(url):
    try:
        d = urllib.parse.urlparse(url).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except:
        return ""


def verify_url(url):
    for method in ["HEAD", "GET"]:
        try:
            req = urllib.request.Request(url, method=method if method == "HEAD" else None,
                                        headers={"User-Agent": "LeadBlitz/2.0"})
            if method == "GET":
                req = urllib.request.Request(url, headers={"User-Agent": "LeadBlitz/2.0"})
            with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as resp:
                if resp.status < 400:
                    return True
        except:
            if method == "HEAD":
                continue
            return False
    return False


def main():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")

    existing_biz, existing_sites = get_existing(conn)
    initial = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    print(f"📊 CRM: {initial} contacts | Target: 5,000 | Need: {max(0,5000-initial)}")

    try:
        with open(RESULTS_FILE) as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"❌ No results file at {RESULTS_FILE}")
        print("Run the search gathering step first.")
        return

    added = 0
    skipped = 0
    verified = 0
    failed_verify = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except:
            continue

        title = entry.get("title", "").strip()
        url = entry.get("url", "").strip()
        snippet = entry.get("snippet", "").strip()
        vertical = entry.get("vertical", "unknown")
        city = entry.get("city", "unknown")

        if not title or not url:
            continue

        domain = extract_domain(url)
        if any(skip in domain for skip in SKIP_DOMAINS):
            skipped += 1
            continue

        # Clean business name
        biz = title.split(" - ")[0].split(" | ")[0].split(" — ")[0].strip()
        if len(biz) < 3 or len(biz) > 100:
            skipped += 1
            continue

        if biz.lower() in existing_biz or (domain and domain in existing_sites):
            skipped += 1
            continue

        # Verify URL
        if verify_url(url):
            verified += 1
        else:
            failed_verify += 1
            continue

        # Extract phone
        phone = None
        pm = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', snippet)
        if pm:
            phone = pm.group(0)

        # Insert
        now = datetime.now().isoformat()
        lid = str(uuid.uuid4())[:8]
        for attempt in range(5):
            try:
                conn.execute(
                    """INSERT INTO contacts (id, name, business, email, phone, website, vertical, city, painScore, stage, source, notes, createdAt, updatedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'new', 'brave-blitz', ?, ?, ?)""",
                    (lid, biz, biz, None, phone, url, vertical, city, snippet[:200], now, now)
                )
                added += 1
                existing_biz.add(biz.lower())
                if domain:
                    existing_sites.add(domain)
                break
            except sqlite3.IntegrityError:
                skipped += 1
                break
            except sqlite3.OperationalError:
                if attempt < 4:
                    time.sleep(2 ** attempt)
                    continue
                raise

        if added % 50 == 0 and added > 0:
            conn.commit()
            print(f"  ✅ {added} added, {skipped} skipped, {verified} verified, {failed_verify} bad URLs")

    conn.commit()
    final = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]

    print(f"\n{'='*50}")
    print(f"✅ IMPORT COMPLETE")
    print(f"Start: {initial} → Final: {final} (+{added})")
    print(f"Verified: {verified} | Bad URL: {failed_verify} | Skipped: {skipped}")
    if final >= 5000:
        print(f"🎉 TARGET HIT: {final} leads!")
    else:
        print(f"⚠️  Gap: {5000 - final} more needed")
    print(f"{'='*50}")
    conn.close()


if __name__ == "__main__":
    main()
