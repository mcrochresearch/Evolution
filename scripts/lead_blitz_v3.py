#!/usr/bin/env python3
"""
Lead Blitz v3 — Fast SearXNG scraper with concurrent URL verification.
Target: Add ~1,300+ new leads to hit 5,000 total in CRM.
Then auditor daemon handles the audit scoring.
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
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = "/Users/scottmckenna/.localcrm/database.db"
SEARXNG = "http://127.0.0.1:8888/search"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

SKIP_DOMAINS = {
    "yelp.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "youtube.com", "tiktok.com", "bbb.org",
    "yellowpages.com", "mapquest.com", "foursquare.com",
    "tripadvisor.com", "angi.com", "homeadvisor.com", "thumbtack.com",
    "nextdoor.com", "manta.com", "chamberofcommerce.com",
    "google.com", "apple.com", "amazon.com", "wikipedia.org",
    "reddit.com", "pinterest.com", "patch.com", "indeed.com",
    "glassdoor.com", "ziprecruiter.com", "niche.com", "houzz.com",
    "superpages.com", "whitepages.com", "citysearch.com",
    "merchantcircle.com", "expertise.com", "bark.com",
}

VERTICALS = [
    ("restaurant", "restaurant"), ("cafe coffee shop", "cafe"),
    ("dentist dental office", "dental"), ("orthodontist", "orthodontist"),
    ("gym fitness center", "gym"), ("yoga pilates studio", "fitness_studio"),
    ("med spa medspa", "medspa"), ("massage spa", "spa"),
    ("law firm lawyer attorney", "law"),
    ("auto repair mechanic", "auto_repair"), ("auto body shop", "auto_body"),
    ("plumber plumbing", "plumbing"), ("electrician", "electrical"),
    ("accountant CPA", "accounting"), ("tax preparer", "tax"),
    ("HVAC heating cooling", "hvac"),
    ("roofing roofer", "roofing"), ("painting contractor", "painting"),
    ("landscaping lawn care", "landscaping"),
    ("real estate agent realtor", "real_estate"),
    ("chiropractor", "chiropractor"), ("physical therapy", "physical_therapy"),
    ("insurance agency", "insurance"),
    ("pet grooming dog groomer", "pet_services"), ("veterinarian", "veterinary"),
    ("cleaning service house cleaning", "cleaning"),
    ("moving company movers", "moving"),
    ("hair salon barber", "salon"), ("nail salon", "nail_salon"),
    ("florist flower shop", "florist"), ("bakery", "bakery"),
    ("daycare childcare", "childcare"),
    ("pest control exterminator", "pest_control"),
    ("construction contractor", "construction"),
    ("optometrist eye doctor", "optometry"),
    ("pharmacy", "pharmacy"), ("dry cleaner", "dry_cleaning"),
    ("jewelry store", "jewelry"), ("tutoring learning center", "tutoring"),
    ("martial arts karate", "martial_arts"), ("dance studio", "dance_studio"),
    ("wine shop liquor store", "liquor"),
    ("printing shop", "printing"), ("photography studio", "photography"),
    ("IT support computer repair", "it_services"),
    ("wedding planner event venue", "events"),
    ("catering", "catering"), ("food truck", "food_truck"),
    ("pizza restaurant", "pizza"), ("sushi restaurant", "sushi"),
    ("thai restaurant", "thai"), ("mexican restaurant", "mexican"),
    ("italian restaurant", "italian"), ("indian restaurant", "indian"),
    ("deli sandwich shop", "deli"),
]

CITIES = [
    "Stamford CT", "Greenwich CT", "Norwalk CT", "Darien CT",
    "New Canaan CT", "Westport CT", "Fairfield CT", "Bridgeport CT",
    "Danbury CT", "White Plains NY", "Rye NY", "Port Chester NY",
    "Mamaroneck NY", "New Rochelle NY", "Ridgefield CT", "Trumbull CT",
    "Shelton CT", "Milford CT", "Stratford CT", "Wilton CT",
    "Cos Cob CT", "Old Greenwich CT", "Riverside CT",
    "Larchmont NY", "Scarsdale NY", "Bronxville NY",
    "Bethel CT", "Monroe CT", "Weston CT",
]


def search(query, page=1):
    params = urllib.parse.urlencode({"q": query, "format": "json", "categories": "general", "pageno": page})
    try:
        req = urllib.request.Request(f"{SEARXNG}?{params}", headers={"User-Agent": "LeadBlitz/3.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()).get("results", [])
    except:
        return []


def verify_url(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "LeadBlitz/3.0"})
        with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as resp:
            return resp.status < 400
    except:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LeadBlitz/3.0"})
            with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as resp:
                return resp.status < 400
        except:
            return False


def domain(url):
    try:
        d = urllib.parse.urlparse(url).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except:
        return ""


def main():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")

    existing_biz = {r[0] for r in conn.execute("SELECT LOWER(business) FROM contacts")}
    existing_dom = {r[0] for r in conn.execute("SELECT LOWER(website) FROM contacts WHERE website IS NOT NULL AND website != ''")}
    # Also track domains
    existing_domains = set()
    for site in existing_dom:
        d = domain(site)
        if d:
            existing_domains.add(d)

    initial = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    target = 5000
    need = max(0, target - initial)
    print(f"📊 Start: {initial} | Target: {target} | Need: {need}")
    print(f"🔍 {len(VERTICALS)} verticals × {len(CITIES)} cities = {len(VERTICALS)*len(CITIES)} queries")
    print(flush=True)

    added = 0
    dupes = 0
    bad_url = 0
    queries = 0

    # Collect candidates first, then batch verify
    candidates = []

    for vi, (term, vtag) in enumerate(VERTICALS):
        if added >= need + 200:  # overshoot buffer
            break
        for ci, city in enumerate(CITIES):
            if added >= need + 200:
                break
            q = f"{term} {city}"
            queries += 1
            if queries % 25 == 0:
                pct = queries / (len(VERTICALS)*len(CITIES)) * 100
                print(f"[{pct:5.1f}%] Q#{queries} | candidates: {len(candidates)} | added: {added} | dupes: {dupes}", flush=True)

            results = search(q)
            for r in results[:8]:
                title = r.get("title", "").strip()
                url = r.get("url", "").strip()
                snippet = r.get("content", r.get("snippet", "")).strip()
                if not title or not url:
                    continue
                dom = domain(url)
                if any(s in dom for s in SKIP_DOMAINS):
                    continue
                biz = title.split(" - ")[0].split(" | ")[0].split(" — ")[0].strip()
                if len(biz) < 3 or len(biz) > 100:
                    continue
                if biz.lower() in existing_biz:
                    dupes += 1
                    continue
                if dom in existing_domains:
                    dupes += 1
                    continue

                # Extract phone
                phone = None
                pm = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', snippet)
                if pm:
                    phone = pm.group(0)

                candidates.append({
                    "biz": biz, "url": url, "dom": dom,
                    "phone": phone, "vertical": vtag, "city": city,
                    "snippet": snippet[:200],
                })
                existing_biz.add(biz.lower())
                if dom:
                    existing_domains.add(dom)

            time.sleep(0.4)  # Rate limit SearXNG

    print(f"\n📋 {len(candidates)} candidates found. Verifying URLs with 20 threads...", flush=True)

    # Batch verify URLs with thread pool
    verified = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        future_map = {pool.submit(verify_url, c["url"]): c for c in candidates}
        done_count = 0
        for future in as_completed(future_map):
            done_count += 1
            c = future_map[future]
            try:
                if future.result():
                    verified.append(c)
                else:
                    bad_url += 1
            except:
                bad_url += 1
            if done_count % 100 == 0:
                print(f"  Verified {done_count}/{len(candidates)} ({len(verified)} good, {bad_url} bad)", flush=True)

    print(f"\n✅ {len(verified)} verified leads. Inserting into CRM...", flush=True)

    # Insert all verified
    for c in verified:
        now = datetime.now().isoformat()
        lid = str(uuid.uuid4())[:8]
        for attempt in range(5):
            try:
                conn.execute(
                    """INSERT INTO contacts (id, name, business, email, phone, website, vertical, city, painScore, stage, source, notes, createdAt, updatedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 'new', 'blitz-v3', ?, ?, ?)""",
                    (lid, c["biz"], c["biz"], None, c["phone"], c["url"], c["vertical"], c["city"], c["snippet"], now, now)
                )
                added += 1
                break
            except sqlite3.IntegrityError:
                dupes += 1
                break
            except sqlite3.OperationalError:
                if attempt < 4:
                    time.sleep(2 ** attempt)
                else:
                    raise

    conn.commit()
    final = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    conn.close()

    print(f"\n{'='*60}")
    print(f"✅ LEAD BLITZ v3 COMPLETE")
    print(f"{'='*60}")
    print(f"📊 Start: {initial} → Final: {final} (+{added})")
    print(f"🔍 Queries: {queries}")
    print(f"📋 Candidates: {len(candidates)}")
    print(f"✅ Verified: {len(verified)}")
    print(f"❌ Bad URL: {bad_url}")
    print(f"🔄 Dupes: {dupes}")
    if final >= target:
        print(f"\n🎉 TARGET HIT: {final} leads in CRM!")
    else:
        print(f"\n⚠️  Gap: {target - final} more needed. Run again or expand cities.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
