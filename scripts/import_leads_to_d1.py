#!/usr/bin/env python3
"""
Import Stamford leads CSVs into LocalCRM (Cloudflare D1 remote).
Maps to the `contacts` table schema.
Deduplicates by email + phone.
"""

import csv
import json
import subprocess
import uuid
import sys
from datetime import datetime

D1_DB = "localcomm"
BATCH_SIZE = 50  # D1 remote has limits per request

CSVS = [
    ("/Users/scottmckenna/Desktop/localloop-leads.csv", "localloop_leads"),
    ("/Users/scottmckenna/Desktop/stamford_business_leads.csv", "stamford_scrape"),
    ("/Users/scottmckenna/Desktop/high_value_leads.csv", "high_value_scrape"),
]

def normalize_phone(p):
    if not p:
        return None
    import re
    digits = re.sub(r'\D', '', str(p))
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+{digits}"
    return str(p)[:20] if p else None

def load_csv_localloop(path, source):
    """localloop-leads.csv format"""
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            # Split name into first/last
            name_parts = (row.get('name') or row.get('business') or '').strip().split(' ', 1)
            first = name_parts[0][:50] if name_parts else ''
            last = name_parts[1][:50] if len(name_parts) > 1 else ''
            email = (row.get('email') or '').strip().lower()
            phone = normalize_phone(row.get('phone'))
            
            # Build tags from vertical, city, stage
            tags = []
            if row.get('vertical'):
                tags.append(row['vertical'])
            if row.get('city'):
                tags.append(row['city'])
            if row.get('stage'):
                tags.append(f"stage:{row['stage']}")
            tags.append('prospect')
            
            pain = row.get('pain_score', '')
            tags.append(f"pain:{pain}" if pain else 'pain:unknown')
            
            rows.append({
                'id': row.get('id') or str(uuid.uuid4()),
                'first_name': first,
                'last_name': last,
                'email': email if email else None,
                'phone': phone,
                'source': source,
                'tags': json.dumps(tags),
                'opt_in_email': 1,
                'opt_in_sms': 0,
                'created_at': row.get('created_at') or datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
            })
    return rows

def load_csv_stamford(path, source):
    """stamford_business_leads.csv / high_value_leads.csv format"""
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            name = (row.get('business_name') or '').strip()
            name_parts = name.split(' ', 1)
            first = name_parts[0][:50] if name_parts else ''
            last = name_parts[1][:50] if len(name_parts) > 1 else ''
            email = (row.get('email') or '').strip().lower()
            phone = normalize_phone(row.get('phone'))
            
            tags = []
            cat = row.get('category', '').strip()
            city = row.get('city', '').strip()
            if cat:
                tags.append(cat.lower().replace(' ', '_'))
            if city:
                tags.append(city)
            tags.append('prospect')
            score = row.get('lead_score', '')
            if score:
                tags.append(f"score:{score}")
            
            rows.append({
                'id': str(uuid.uuid4()),
                'first_name': first,
                'last_name': last,
                'email': email if email else None,
                'phone': phone,
                'source': source,
                'tags': json.dumps(tags),
                'opt_in_email': 1,
                'opt_in_sms': 0,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
            })
    return rows

def run_d1(sql):
    result = subprocess.run(
        ['npx', 'wrangler', 'd1', 'execute', D1_DB, '--remote', '--command', sql],
        capture_output=True, text=True, cwd='/Users/scottmckenna/shellcorp/localcomm'
    )
    if result.returncode != 0:
        print(f"ERROR: {result.stderr[-500:]}", file=sys.stderr)
        return False
    return True

def insert_batch(rows):
    if not rows:
        return True
    
    values = []
    for r in rows:
        def esc(v):
            if v is None:
                return 'NULL'
            return "'" + str(v).replace("'", "''") + "'"
        
        values.append(
            f"({esc(r['id'])}, NULL, {esc(r['first_name'])}, {esc(r['last_name'])}, "
            f"{esc(r['email'])}, {esc(r['phone'])}, {esc(r['source'])}, "
            f"{esc(r['tags'])}, NULL, 0, {r['opt_in_sms']}, {r['opt_in_email']}, "
            f"{esc(r['created_at'])}, {esc(r['updated_at'])})"
        )
    
    sql = ("INSERT OR IGNORE INTO contacts "
           "(id, user_id, first_name, last_name, email, phone, source, tags, "
           "last_visit_at, lifetime_value_cents, opt_in_sms, opt_in_email, created_at, updated_at) "
           "VALUES " + ",".join(values) + ";")
    
    return run_d1(sql)

def main():
    all_rows = []
    
    # Load all CSVs
    print("Loading localloop-leads.csv...")
    r1 = load_csv_localloop(CSVS[0][0], CSVS[0][1])
    print(f"  {len(r1)} rows")
    all_rows.extend(r1)
    
    print("Loading stamford_business_leads.csv...")
    r2 = load_csv_stamford(CSVS[1][0], CSVS[1][1])
    print(f"  {len(r2)} rows")
    all_rows.extend(r2)
    
    print("Loading high_value_leads.csv...")
    r3 = load_csv_stamford(CSVS[2][0], CSVS[2][1])
    print(f"  {len(r3)} rows")
    all_rows.extend(r3)
    
    print(f"\nTotal rows to import: {len(all_rows)}")
    
    # Deduplicate by email (keep first occurrence)
    seen_emails = set()
    seen_phones = set()
    deduped = []
    for r in all_rows:
        email = r.get('email')
        phone = r.get('phone')
        key = email if email else (phone if phone else None)
        if key and key in seen_emails:
            continue
        if key:
            seen_emails.add(key)
        deduped.append(r)
    
    print(f"After dedup: {len(deduped)} rows")
    
    # Batch insert
    inserted = 0
    errors = 0
    for i in range(0, len(deduped), BATCH_SIZE):
        batch = deduped[i:i+BATCH_SIZE]
        if insert_batch(batch):
            inserted += len(batch)
            print(f"  Inserted {inserted}/{len(deduped)}...", end='\r')
        else:
            errors += 1
            if errors > 5:
                print("\nToo many errors, aborting.")
                break
    
    print(f"\n\nDone. Inserted ~{inserted} contacts. Errors: {errors}")

if __name__ == '__main__':
    main()
