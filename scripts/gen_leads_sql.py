#!/usr/bin/env python3
"""Generate a single SQL file to bulk-import all leads into D1 contacts table."""

import csv, json, uuid, re
from datetime import datetime, timezone

NOW = datetime.now(timezone.utc).isoformat()
OUT = "/tmp/leads_import.sql"

def norm_phone(p):
    if not p: return None
    digits = re.sub(r'\D', '', str(p))
    if len(digits) == 10: return f"+1{digits}"
    if len(digits) == 11 and digits[0] == '1': return f"+{digits}"
    return str(p)[:20]

def esc(v):
    if v is None: return 'NULL'
    return "'" + str(v).replace("'", "''")[:500] + "'"

def row_sql(r):
    return (f"({esc(r['id'])},NULL,{esc(r['fn'])},{esc(r['ln'])},"
            f"{esc(r['email'])},{esc(r['phone'])},{esc(r['source'])},"
            f"{esc(r['tags'])},NULL,0,0,1,{esc(NOW)},{esc(NOW)})")

rows = []
seen = set()

def add(id_, fn, ln, email, phone, source, tags):
    email = email.strip().lower() if email else None
    phone = norm_phone(phone)
    key = email or phone or id_
    if key in seen: return
    seen.add(key)
    rows.append({'id': id_ or str(uuid.uuid4()), 'fn': fn[:50] if fn else '',
                 'ln': ln[:50] if ln else '', 'email': email, 'phone': phone,
                 'source': source, 'tags': json.dumps(tags)})

# --- localloop-leads.csv ---
print("Loading localloop-leads.csv...")
with open('/Users/scottmckenna/Desktop/localloop-leads.csv') as f:
    for r in csv.DictReader(f):
        nm = (r.get('name') or r.get('business') or '').strip().split(' ', 1)
        tags = ['prospect']
        for k in ['vertical', 'city', 'stage']:
            if r.get(k): tags.append(r[k])
        if r.get('pain_score'): tags.append(f"pain:{r['pain_score']}")
        add(r.get('id'), nm[0], nm[1] if len(nm)>1 else '', r.get('email'), r.get('phone'), 'localloop_leads', tags)

# --- stamford_business_leads.csv ---
print("Loading stamford_business_leads.csv...")
with open('/Users/scottmckenna/Desktop/stamford_business_leads.csv') as f:
    for r in csv.DictReader(f):
        nm = (r.get('business_name') or '').strip().split(' ', 1)
        tags = ['prospect', 'stamford_scrape']
        if r.get('category'): tags.append(r['category'].lower().replace(' ','_'))
        if r.get('city'): tags.append(r['city'])
        if r.get('lead_score'): tags.append(f"score:{r['lead_score']}")
        add(None, nm[0], nm[1] if len(nm)>1 else '', r.get('email'), r.get('phone'), 'stamford_scrape', tags)

# --- high_value_leads.csv ---
print("Loading high_value_leads.csv...")
with open('/Users/scottmckenna/Desktop/high_value_leads.csv') as f:
    for r in csv.DictReader(f):
        nm = (r.get('business_name') or '').strip().split(' ', 1)
        tags = ['prospect', 'high_value']
        if r.get('category'): tags.append(r['category'].lower().replace(' ','_'))
        if r.get('city'): tags.append(r['city'])
        if r.get('lead_score'): tags.append(f"score:{r['lead_score']}")
        add(None, nm[0], nm[1] if len(nm)>1 else '', r.get('email'), r.get('phone'), 'high_value_scrape', tags)

print(f"Total unique rows: {len(rows)}")

# Write SQL in batches of 200 per INSERT
COLS = ("id,user_id,first_name,last_name,email,phone,source,tags,"
        "last_visit_at,lifetime_value_cents,opt_in_sms,opt_in_email,created_at,updated_at")

with open(OUT, 'w') as f:
    for i in range(0, len(rows), 200):
        batch = rows[i:i+200]
        vals = ",\n".join(row_sql(r) for r in batch)
        f.write(f"INSERT OR IGNORE INTO contacts ({COLS}) VALUES\n{vals};\n\n")

print(f"SQL written to {OUT}")
import os
print(f"File size: {os.path.getsize(OUT)/1024:.1f} KB")
