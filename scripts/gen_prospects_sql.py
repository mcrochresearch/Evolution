#!/usr/bin/env python3
"""Generate SQL to import all leads into agency_prospects table."""

import csv, json, uuid, re
from datetime import datetime, timezone

NOW = datetime.now(timezone.utc).isoformat()
OUT = "/tmp/prospects_import.sql"

def norm_phone(p):
    if not p: return None
    digits = re.sub(r'\D', '', str(p))
    if len(digits) == 10: return f"+1{digits}"
    if len(digits) == 11 and digits[0] == '1': return f"+{digits}"
    return str(p)[:30]

def esc(v):
    if v is None: return 'NULL'
    return "'" + str(v).replace("'", "''")[:1000] + "'"

rows = []
seen = set()

def add(id_, name, category, city, address, phone, email, website,
        lead_score, pain_score, source, tags, stage,
        facebook=None, instagram=None, linkedin=None, tiktok=None,
        fb_followers=None, ig_followers=None,
        no_meta=0, no_social=0, no_blog=0, no_https=0, notes=None):
    email = email.strip().lower() if email else None
    phone = norm_phone(phone)
    # Dedup by email > phone > (name+city)
    key = email or phone or f"{name}|{city}"
    if key in seen: return
    seen.add(key)
    rows.append({
        'id': id_ or str(uuid.uuid4()),
        'name': (name or '')[:200],
        'category': (category or '')[:100],
        'city': (city or '')[:100],
        'address': (address or '')[:300],
        'phone': phone,
        'email': email,
        'website': (website or '')[:300],
        'lead_score': lead_score or 0,
        'pain_score': pain_score or 0,
        'source': source,
        'tags': json.dumps(tags),
        'stage': stage or 'lead',
        'facebook': facebook,
        'instagram': instagram,
        'linkedin': linkedin,
        'tiktok': tiktok,
        'fb_followers': fb_followers,
        'ig_followers': ig_followers,
        'no_meta': no_meta,
        'no_social': no_social,
        'no_blog': no_blog,
        'no_https': no_https,
        'notes': notes,
    })

# --- localloop-leads.csv ---
print("Loading localloop-leads.csv...")
with open('/Users/scottmckenna/Desktop/localloop-leads.csv') as f:
    for r in csv.DictReader(f):
        tags = ['prospect']
        if r.get('vertical'): tags.append(r['vertical'])
        add(r.get('id'),
            r.get('business') or r.get('name'),
            r.get('vertical'), r.get('city'), None,
            r.get('phone'), r.get('email'), r.get('website'),
            None, int(r.get('pain_score') or 0),
            'localloop_leads', tags, r.get('stage') or 'lead',
            notes=r.get('notes') or r.get('audit_data'))

# --- stamford_business_leads.csv ---
print("Loading stamford_business_leads.csv...")
with open('/Users/scottmckenna/Desktop/stamford_business_leads.csv') as f:
    for r in csv.DictReader(f):
        tags = ['prospect', 'stamford_scrape']
        if r.get('category'): tags.append(r['category'].lower().replace(' ','_'))
        try: score = int(float(r.get('lead_score') or 0))
        except: score = 0
        add(None,
            r.get('business_name'), r.get('category'), r.get('city'), r.get('address'),
            r.get('phone'), r.get('email'), r.get('website'),
            score, 0, 'stamford_scrape', tags, 'lead',
            facebook=r.get('facebook'), instagram=r.get('instagram'),
            linkedin=r.get('linkedin'), tiktok=r.get('tiktok'),
            fb_followers=r.get('facebook_followers') or None,
            ig_followers=r.get('instagram_followers') or None,
            no_meta=1 if r.get('no_meta_description')=='True' else 0,
            no_social=1 if r.get('no_social_media')=='True' else 0,
            no_blog=1 if r.get('no_blog')=='True' else 0,
            no_https=1 if r.get('no_https')=='True' else 0)

# --- high_value_leads.csv ---
print("Loading high_value_leads.csv...")
with open('/Users/scottmckenna/Desktop/high_value_leads.csv') as f:
    for r in csv.DictReader(f):
        tags = ['prospect', 'high_value']
        if r.get('category'): tags.append(r['category'].lower().replace(' ','_'))
        try: score = int(float(r.get('lead_score') or 0))
        except: score = 0
        add(None,
            r.get('business_name'), r.get('category'), r.get('city'), r.get('address'),
            r.get('phone'), r.get('email'), r.get('website'),
            score, 0, 'high_value_scrape', tags, 'lead',
            facebook=r.get('facebook'), instagram=r.get('instagram'),
            linkedin=r.get('linkedin'), tiktok=r.get('tiktok'),
            fb_followers=r.get('facebook_followers') or None,
            ig_followers=r.get('instagram_followers') or None,
            no_meta=1 if r.get('no_meta_description')=='True' else 0,
            no_social=1 if r.get('no_social_media')=='True' else 0,
            no_blog=1 if r.get('no_blog')=='True' else 0,
            no_https=1 if r.get('no_https')=='True' else 0)

print(f"Total unique rows: {len(rows)}")

COLS = ("id,business_name,category,city,address,phone,email,website,"
        "lead_score,pain_score,source,tags,stage,"
        "facebook,instagram,linkedin,tiktok,"
        "facebook_followers,instagram_followers,"
        "no_meta_description,no_social_media,no_blog,no_https,notes,"
        "created_at,updated_at")

def row_sql(r):
    return (f"({esc(r['id'])},{esc(r['name'])},{esc(r['category'])},{esc(r['city'])},"
            f"{esc(r['address'])},{esc(r['phone'])},{esc(r['email'])},{esc(r['website'])},"
            f"{r['lead_score']},{r['pain_score']},{esc(r['source'])},{esc(r['tags'])},{esc(r['stage'])},"
            f"{esc(r['facebook'])},{esc(r['instagram'])},{esc(r['linkedin'])},{esc(r['tiktok'])},"
            f"{esc(r['fb_followers'])},{esc(r['ig_followers'])},"
            f"{r['no_meta']},{r['no_social']},{r['no_blog']},{r['no_https']},{esc(r['notes'])},"
            f"{esc(NOW)},{esc(NOW)})")

with open(OUT, 'w') as f:
    for i in range(0, len(rows), 200):
        batch = rows[i:i+200]
        vals = ",\n".join(row_sql(r) for r in batch)
        f.write(f"INSERT OR IGNORE INTO agency_prospects ({COLS}) VALUES\n{vals};\n\n")

import os
print(f"SQL written to {OUT} ({os.path.getsize(OUT)/1024:.1f} KB)")
