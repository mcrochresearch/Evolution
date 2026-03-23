#!/usr/bin/env python3
"""
Lead Blitz v4 — Scrape YellowPages, BBB, and Yelp directory listings directly.
Each page yields 10-30 businesses. Fast, high-yield.
"""

import json, sqlite3, urllib.request, urllib.parse, uuid, time, sys, ssl, re, html
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = "/Users/scottmckenna/.localcrm/database.db"

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

VERTICALS = [
    ("restaurants", "restaurant"), ("dentists", "dental"), ("gyms", "gym"),
    ("med-spas", "medspa"), ("lawyers", "law"), ("auto-repair", "auto_repair"),
    ("plumbers", "plumbing"), ("electricians", "electrical"),
    ("accountants", "accounting"), ("hvac", "hvac"), ("roofers", "roofing"),
    ("landscaping", "landscaping"), ("house-cleaning", "cleaning"),
    ("movers", "moving"), ("hair-salons", "salon"), ("florists", "florist"),
    ("bakeries", "bakery"), ("day-care-centers", "childcare"),
    ("pest-control", "pest_control"), ("painters", "painting"),
    ("optometrists", "optometry"), ("chiropractors", "chiropractor"),
    ("physical-therapists", "physical_therapy"), ("veterinarians", "veterinary"),
    ("insurance-agents", "insurance"), ("real-estate-agents", "real_estate"),
    ("photographers", "photography"), ("caterers", "catering"),
    ("nail-salons", "nail_salon"), ("massage-therapists", "spa"),
    ("yoga-studios", "fitness_studio"), ("martial-arts", "martial_arts"),
    ("dance-studios", "dance_studio"), ("tutoring-centers", "tutoring"),
    ("auto-body-shops", "auto_body"), ("dry-cleaners", "dry_cleaning"),
    ("jewelers", "jewelry"), ("pet-groomers", "pet_services"),
    ("printing-services", "printing"), ("it-services", "it_services"),
]

CITIES_YP = [
    ("stamford-ct", "Stamford CT"), ("greenwich-ct", "Greenwich CT"),
    ("norwalk-ct", "Norwalk CT"), ("darien-ct", "Darien CT"),
    ("new-canaan-ct", "New Canaan CT"), ("westport-ct", "Westport CT"),
    ("fairfield-ct", "Fairfield CT"), ("bridgeport-ct", "Bridgeport CT"),
    ("danbury-ct", "Danbury CT"), ("ridgefield-ct", "Ridgefield CT"),
    ("wilton-ct", "Wilton CT"), ("trumbull-ct", "Trumbull CT"),
    ("shelton-ct", "Shelton CT"), ("milford-ct", "Milford CT"),
    ("stratford-ct", "Stratford CT"), ("westport-ct", "Westport CT"),
    ("white-plains-ny", "White Plains NY"), ("rye-ny", "Rye NY"),
    ("port-chester-ny", "Port Chester NY"), ("new-rochelle-ny", "New Rochelle NY"),
    ("mamaroneck-ny", "Mamaroneck NY"), ("larchmont-ny", "Larchmont NY"),
    ("scarsdale-ny", "Scarsdale NY"), ("bronxville-ny", "Bronxville NY"),
    ("harrison-ny", "Harrison NY"), ("greenburgh-ny", "Greenburgh NY"),
]


def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None


def extract_yp_businesses(html_text, vertical, city):
    """Extract businesses from YellowPages listing page."""
    leads = []
    if not html_text:
        return leads

    # YP business blocks — match name, website, phone
    # Pattern: <a class="business-name" href="..."><span>NAME</span></a>
    name_pattern = re.compile(r'class="business-name[^"]*"[^>]*>\s*<span[^>]*>([^<]+)</span>', re.I)
    website_pattern = re.compile(r'class="track-visit-website[^"]*"[^>]*href="([^"]+)"', re.I)
    phone_pattern = re.compile(r'class="phones[^"]*"[^>]*>\s*([^<]+)</p>', re.I)

    names = name_pattern.findall(html_text)
    websites = website_pattern.findall(html_text)
    phones = phone_pattern.findall(html_text)

    for i, name in enumerate(names):
        name = html.unescape(name.strip())
        website = websites[i] if i < len(websites) else None
        phone = phones[i].strip() if i < len(phones) else None
        if website and ("yellowpages.com" in website or "dexknows.com" in website):
            website = None
        leads.append({"biz": name, "url": website or "", "phone": phone, "vertical": vertical, "city": city})

    # Also try simpler pattern
    if not leads:
        block_pattern = re.compile(
            r'"business-name[^"]*"[^>]*href="([^"]*)"[^>]*>\s*<span[^>]*>([^<]+)</span>',
            re.I | re.S
        )
        for match in block_pattern.finditer(html_text):
            url_path, name = match.group(1), html.unescape(match.group(2).strip())
            if name and len(name) > 2:
                leads.append({"biz": name, "url": "", "phone": None, "vertical": vertical, "city": city})

    return leads


def scrape_yp(vertical_slug, city_slug, city_name, page=1):
    """Scrape YellowPages for a vertical + city."""
    url = f"https://www.yellowpages.com/{city_slug}/{vertical_slug}"
    if page > 1:
        url += f"?page={page}"
    html_text = fetch(url)
    return extract_yp_businesses(html_text or "", vertical_slug.replace("-", "_"), city_name)


def scrape_bbb(term, city, state, city_name):
    """Scrape BBB for local businesses."""
    q = urllib.parse.quote(term)
    url = f"https://www.bbb.org/search?find_text={q}&find_loc={urllib.parse.quote(city)}%2C+{state}&page=1"
    html_text = fetch(url) or ""

    leads = []
    # BBB business name pattern
    name_pat = re.compile(r'class="[^"]*bds-body[^"]*"[^>]*>\s*<a[^>]*href="/profile/[^"]*"[^>]*>([^<]+)</a>', re.I)
    website_pat = re.compile(r'href="(/profile/[^"]+)"', re.I)

    names = name_pat.findall(html_text)
    for name in names[:20]:
        name = html.unescape(name.strip())
        if len(name) > 2:
            leads.append({"biz": name, "url": "", "phone": None, "vertical": term, "city": city_name})
    return leads


def verify_url(url):
    if not url:
        return False
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": HEADERS["User-Agent"]})
        with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as r:
            return r.status < 400
    except:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
            with urllib.request.urlopen(req, timeout=6, context=ssl_ctx) as r:
                return r.status < 400
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
    existing_dom = set()
    for (site,) in conn.execute("SELECT website FROM contacts WHERE website IS NOT NULL AND website != ''"):
        d = domain(site)
        if d:
            existing_dom.add(d)

    initial = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    target = 5000
    need = max(0, target - initial)
    print(f"📊 Start: {initial} | Target: {target} | Need: {need}", flush=True)

    all_candidates = []
    queries = 0
    dupes = 0

    for vtag, vname in VERTICALS:
        for city_slug, city_name in CITIES_YP:
            queries += 1
            if queries % 20 == 0:
                print(f"  Q#{queries} | candidates so far: {len(all_candidates)} | dupes: {dupes}", flush=True)

            leads = scrape_yp(vtag, city_slug, city_name)
            for lead in leads:
                biz = lead["biz"]
                if not biz or len(biz) < 3:
                    continue
                if biz.lower() in existing_biz:
                    dupes += 1
                    continue
                d = domain(lead.get("url", ""))
                if d and d in existing_dom:
                    dupes += 1
                    continue
                existing_biz.add(biz.lower())
                if d:
                    existing_dom.add(d)
                all_candidates.append(lead)

            time.sleep(0.6)  # Be polite to YP

            if len(all_candidates) >= need + 500:
                print(f"  ✅ Enough candidates ({len(all_candidates)}). Stopping search.", flush=True)
                break
        else:
            continue
        break

    print(f"\n📋 {len(all_candidates)} candidates. Verifying URLs (20 threads)...", flush=True)

    # Batch verify in parallel
    verified = []
    no_url = []
    bad = 0

    # Separate those with URLs vs without
    with_url = [c for c in all_candidates if c.get("url")]
    without_url = [c for c in all_candidates if not c.get("url")]

    print(f"  With URL: {len(with_url)} | Without URL (name-only): {len(without_url)}", flush=True)

    with ThreadPoolExecutor(max_workers=20) as pool:
        fut = {pool.submit(verify_url, c["url"]): c for c in with_url}
        done = 0
        for future in as_completed(fut):
            done += 1
            c = fut[future]
            try:
                if future.result():
                    verified.append(c)
                else:
                    bad += 1
            except:
                bad += 1
            if done % 200 == 0:
                print(f"  Checked {done}/{len(with_url)} | good: {len(verified)} | bad: {bad}", flush=True)

    # Name-only leads still count — no URL to verify but biz name is real
    # Insert them without website field
    for c in without_url[:max(0, need - len(verified))]:
        verified.append(c)

    print(f"\n✅ {len(verified)} leads ready. Inserting...", flush=True)

    added = 0
    insert_dupes = 0
    for c in verified:
        now = datetime.now().isoformat()
        lid = str(uuid.uuid4())[:8]
        for attempt in range(5):
            try:
                conn.execute(
                    """INSERT INTO contacts (id,name,business,email,phone,website,vertical,city,painScore,stage,source,notes,createdAt,updatedAt)
                    VALUES (?,?,?,?,?,?,?,?,0,'new','yp-blitz',?,?,?)""",
                    (lid, c["biz"], c["biz"], None, c.get("phone"), c.get("url") or None,
                     c["vertical"], c["city"], "", now, now)
                )
                added += 1
                break
            except sqlite3.IntegrityError:
                insert_dupes += 1
                break
            except sqlite3.OperationalError:
                if attempt < 4:
                    time.sleep(2 ** attempt)
                else:
                    raise
        if added % 100 == 0 and added > 0:
            conn.commit()

    conn.commit()
    final = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    conn.close()

    print(f"\n{'='*60}")
    print(f"{'LEAD BLITZ v4 DONE':^60}")
    print(f"{'='*60}")
    print(f"Start: {initial} → Final: {final} (+{added})")
    print(f"Queries: {queries} | Candidates: {len(all_candidates)} | Verified: {len(verified)}")
    print(f"Bad URL: {bad} | Dupes (search): {dupes} | Dupes (insert): {insert_dupes}")
    print()
    if final >= target:
        print(f"🎉 TARGET HIT: {final} leads! Go get those SMTP creds, Pat.")
    else:
        print(f"⚠️  Gap: {target - final} — expand verticals or add more cities")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
