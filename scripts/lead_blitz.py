#!/usr/bin/env python3
"""
Lead Blitz — Scrape SearXNG for SMB leads across target verticals and cities.
Verify URLs resolve. Deduplicate against existing CRM. Insert into localcrm.

Target: 5,000 audited leads total (need ~1,300 more).
"""

import json
import sqlite3
import urllib.request
import urllib.parse
import uuid
import time
import sys
import ssl
from datetime import datetime

DB_PATH = "/Users/scottmckenna/.localcrm/database.db"
SEARXNG = "http://127.0.0.1:8888/search"

# Target verticals × cities — systematic coverage
VERTICALS = [
    # (search_term, vertical_tag)
    ("restaurant", "restaurant"),
    ("dental office dentist", "dental"),
    ("gym fitness center", "gym"),
    ("med spa medspa", "medspa"),
    ("law firm lawyer attorney", "law"),
    ("auto repair mechanic", "auto_repair"),
    ("plumber plumbing", "plumbing"),
    ("accountant CPA accounting", "accounting"),
    ("HVAC heating cooling", "hvac"),
    ("roofing roofer", "roofing"),
    ("electrician electrical contractor", "electrical"),
    ("hair salon barber", "salon"),
    ("veterinarian vet clinic", "veterinary"),
    ("landscaping lawn care", "landscaping"),
    ("real estate agent realtor", "real_estate"),
    ("chiropractor", "chiropractor"),
    ("physical therapy", "physical_therapy"),
    ("insurance agency", "insurance"),
    ("pet grooming", "pet_services"),
    ("cleaning service house cleaning", "cleaning"),
    ("moving company movers", "moving"),
    ("photographer photography studio", "photography"),
    ("florist flower shop", "florist"),
    ("bakery", "bakery"),
    ("daycare childcare preschool", "childcare"),
    ("auto body collision repair", "auto_body"),
    ("pest control exterminator", "pest_control"),
    ("painting contractor painter", "painting"),
    ("construction contractor builder", "construction"),
    ("yoga pilates studio", "fitness_studio"),
    ("spa massage therapy", "spa"),
    ("optometrist eye doctor", "optometry"),
    ("orthodontist", "orthodontist"),
    ("pharmacy", "pharmacy"),
    ("dry cleaner laundry", "dry_cleaning"),
    ("jewelry store jeweler", "jewelry"),
    ("tattoo shop tattoo parlor", "tattoo"),
    ("tailor alterations", "tailor"),
    ("tutoring learning center", "tutoring"),
    ("music lessons school", "music_school"),
    ("martial arts karate", "martial_arts"),
    ("dance studio", "dance_studio"),
    ("wine shop liquor store", "liquor"),
    ("printing shop print services", "printing"),
]

CITIES = [
    "Stamford CT",
    "Greenwich CT",
    "Norwalk CT",
    "Darien CT",
    "New Canaan CT",
    "Westport CT",
    "Fairfield CT",
    "Bridgeport CT",
    "Danbury CT",
    "White Plains NY",
    "Rye NY",
    "Port Chester NY",
    "Mamaroneck NY",
    "Larchmont NY",
    "Scarsdale NY",
    "Bronxville NY",
    "New Rochelle NY",
    "Ridgefield CT",
    "Trumbull CT",
    "Shelton CT",
    "Milford CT",
    "Stratford CT",
    "Monroe CT",
    "Bethel CT",
    "Wilton CT",
    "Weston CT",
    "Redding CT",
    "Easton CT",
    "Cos Cob CT",
    "Old Greenwich CT",
    "Riverside CT",
    "Byram CT",
]

# SSL context that doesn't verify (for quick URL checks)
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def get_existing_businesses(conn):
    """Get set of existing business names (lowercased) for dedup."""
    cursor = conn.execute("SELECT LOWER(business) FROM contacts")
    return {row[0] for row in cursor.fetchall()}


def get_existing_websites(conn):
    """Get set of existing websites for dedup."""
    cursor = conn.execute("SELECT LOWER(website) FROM contacts WHERE website IS NOT NULL AND website != ''")
    return {row[0] for row in cursor.fetchall()}


def search_searxng(query, page=1):
    """Search SearXNG and return results."""
    params = urllib.parse.urlencode({
        "q": query,
        "format": "json",
        "categories": "general",
        "pageno": page,
    })
    url = f"{SEARXNG}?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LeadBlitz/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("results", [])
    except Exception as e:
        print(f"  ⚠ Search failed: {e}", file=sys.stderr)
        return []


def verify_url(url):
    """Quick HEAD check — returns True if URL resolves."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "LeadBlitz/1.0"})
        with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as resp:
            return resp.status < 400
    except Exception:
        # Try GET as fallback (some servers reject HEAD)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "LeadBlitz/1.0"})
            with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as resp:
                return resp.status < 400
        except Exception:
            return False


def extract_domain(url):
    """Extract clean domain from URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def extract_lead_from_result(result, vertical, city):
    """Try to extract a lead from a search result."""
    title = result.get("title", "").strip()
    url = result.get("url", "").strip()
    content = result.get("content", "").strip()

    if not title or not url:
        return None

    # Skip non-business results
    skip_domains = [
        "yelp.com", "facebook.com", "instagram.com", "twitter.com",
        "linkedin.com", "youtube.com", "tiktok.com", "bbb.org",
        "yellowpages.com", "mapquest.com", "foursquare.com",
        "tripadvisor.com", "angi.com", "homeadvisor.com", "thumbtack.com",
        "nextdoor.com", "manta.com", "chamberofcommerce.com",
        "google.com", "apple.com", "amazon.com", "wikipedia.org",
        "reddit.com", "pinterest.com", "patch.com", "indeed.com",
        "glassdoor.com", "ziprecruiter.com", "niche.com",
    ]
    domain = extract_domain(url)
    for skip in skip_domains:
        if skip in domain:
            return None

    # Clean up business name from title
    # Often format is "Business Name - City" or "Business Name | Service"
    biz_name = title.split(" - ")[0].split(" | ")[0].split(" — ")[0].strip()
    # Remove trailing location info
    for suffix in [f" {city}", " CT", " NY", " Connecticut", " New York"]:
        if biz_name.lower().endswith(suffix.lower()):
            biz_name = biz_name[:-len(suffix)].strip()

    if len(biz_name) < 3 or len(biz_name) > 100:
        return None

    # Extract phone from content if present
    import re
    phone = None
    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', content)
    if phone_match:
        phone = phone_match.group(0)

    website = url
    # If it's a business directory page, try to find actual website
    # Otherwise use the URL as-is (it's likely their site)

    return {
        "name": biz_name,
        "business": biz_name,
        "website": website,
        "domain": domain,
        "phone": phone,
        "vertical": vertical,
        "city": city,
        "content": content[:200],
    }


def insert_lead(conn, lead):
    """Insert lead into CRM database."""
    now = datetime.now().isoformat()
    lead_id = str(uuid.uuid4())[:8]
    for attempt in range(5):
        try:
            conn.execute(
                """INSERT INTO contacts (id, name, business, email, phone, website, vertical, city, painScore, stage, source, notes, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    lead_id,
                    lead["name"],
                    lead["business"],
                    None,  # email - need enrichment later
                    lead.get("phone"),
                    lead.get("website"),
                    lead["vertical"],
                    lead["city"],
                    0,  # painScore - will audit later
                    "new",
                    "searxng-blitz",
                    lead.get("content", ""),
                    now,
                    now,
                ),
            )
            return True
        except sqlite3.IntegrityError:
            return False
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise
    return False


def main():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    existing_biz = get_existing_businesses(conn)
    existing_sites = get_existing_websites(conn)
    
    initial_count = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    print(f"📊 Starting count: {initial_count} contacts")
    print(f"🎯 Target: 5,000 contacts")
    print(f"📈 Need: {max(0, 5000 - initial_count)} more leads")
    print(f"🔍 Searching {len(VERTICALS)} verticals × {len(CITIES)} cities = {len(VERTICALS) * len(CITIES)} queries")
    print()

    added = 0
    skipped_dup = 0
    skipped_bad = 0
    verified = 0
    failed_verify = 0
    queries_run = 0
    target_remaining = 5000 - initial_count

    for vi, (search_term, vertical_tag) in enumerate(VERTICALS):
        if added >= target_remaining:
            print(f"\n🎉 Target reached! Added {added} leads.")
            break

        for ci, city in enumerate(CITIES):
            if added >= target_remaining:
                break

            query = f"{search_term} {city}"
            queries_run += 1

            # Progress
            pct = (queries_run / (len(VERTICALS) * len(CITIES))) * 100
            print(f"[{pct:5.1f}%] Q#{queries_run}: {query} (added: {added}, dup: {skipped_dup})", flush=True)

            results = search_searxng(query)
            if not results:
                time.sleep(0.3)
                continue

            batch_added = 0
            for r in results[:10]:  # Top 10 results per query
                lead = extract_lead_from_result(r, vertical_tag, city)
                if not lead:
                    skipped_bad += 1
                    continue

                # Dedup by business name
                if lead["business"].lower() in existing_biz:
                    skipped_dup += 1
                    continue

                # Dedup by domain
                if lead["domain"] and lead["domain"].lower() in existing_sites:
                    skipped_dup += 1
                    continue

                # Verify URL resolves (audit step)
                if lead.get("website"):
                    if verify_url(lead["website"]):
                        verified += 1
                    else:
                        failed_verify += 1
                        continue  # Skip unverifiable leads

                # Insert
                if insert_lead(conn, lead):
                    added += 1
                    batch_added += 1
                    existing_biz.add(lead["business"].lower())
                    if lead.get("domain"):
                        existing_sites.add(lead["domain"].lower())
                else:
                    skipped_dup += 1

            if batch_added > 0:
                conn.commit()

            # Rate limit SearXNG gently
            time.sleep(0.5)

    # Final commit
    conn.commit()
    final_count = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]

    print(f"\n{'='*60}")
    print(f"✅ LEAD BLITZ COMPLETE")
    print(f"{'='*60}")
    print(f"📊 Starting count:  {initial_count}")
    print(f"📊 Final count:     {final_count}")
    print(f"➕ Added:           {added}")
    print(f"🔗 URL verified:    {verified}")
    print(f"❌ URL failed:      {failed_verify}")
    print(f"🔄 Skipped (dup):   {skipped_dup}")
    print(f"🚫 Skipped (bad):   {skipped_bad}")
    print(f"🔍 Queries run:     {queries_run}")
    print(f"{'='*60}")

    if final_count >= 5000:
        print(f"\n🎉 TARGET HIT: {final_count} leads in CRM!")
    else:
        print(f"\n⚠️  Gap remaining: {5000 - final_count} more leads needed")

    conn.close()


if __name__ == "__main__":
    main()
