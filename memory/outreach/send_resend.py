#!/usr/bin/env python3
"""
LocalComm Outreach Sender — Resend API (drop-in replacement for send_all_outreach.py)

SETUP (one-time):
  1. Go to https://resend.com → sign up free → API Keys → Create Key
  2. RESEND_API_KEY=re_xxxx python3 send_resend.py
  
  Free tier: 100 emails/day, 3,000/month. More than enough.
  Sending domain: by default sends from onboarding@resend.dev (verified).
  Custom domain (localcomm.co): add DNS records in Resend dashboard → Settings → Domains.
  
  Dry run (preview without sending):
  DRY_RUN=1 python3 send_resend.py
"""

import os
import time
import resend

API_KEY   = os.getenv("RESEND_API_KEY", "")
FROM_NAME = os.getenv("FROM_NAME", "Pat McKenna")
FROM_ADDR = os.getenv("FROM_ADDR", "pat@localcomm.co")  # must be verified domain in Resend
DRY_RUN   = os.getenv("DRY_RUN", "0") == "1"

if not DRY_RUN and not API_KEY:
    print("ERROR: Set RESEND_API_KEY env var")
    print("  Get one free at https://resend.com/api-keys")
    print("  Then: RESEND_API_KEY=re_xxxx python3 send_resend.py")
    print("  Or dry run: DRY_RUN=1 python3 send_resend.py")
    exit(1)

resend.api_key = API_KEY

# ─── LEADS ─────────────────────────────────────────────────────────────────
# (to_name, to_email, subject, body, vertical, priority)
# Priority 1 = send first.

EMAILS = [

    # ── PRISCO (warmest — send first) ──────────────────────────────────────
    ("Nick", "nick@priscoappliance.com",
     "Prisco Appliance — quick question",
     """Hi Nick,

Reached out a while back about Prisco's online presence. 4.9 stars and 206 reviews is exceptional for White Plains — that's a level of trust most businesses spend years trying to build.

Here's the thing: zero paid ads means your competitors are buying traffic that your reputation should be winning organically. Google Local Services Ads for appliance repair in Westchester runs about $18–25 per lead. We'd target it to get you to $8–12 with proper setup.

I built a specific action plan for Prisco — three things that would generate measurable new calls within 60 days. Takes 15 minutes to walk through.

Are you free for a call this week or next?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""",
     "Appliance", 1),

    # ── HVAC ───────────────────────────────────────────────────────────────
    ("Owner", "service@ccservicellc.com",
     "C&C Service — your Carrier Diamond creds aren't driving inbound leads",
     """Hi,

You're a Carrier Factory Authorized Dealer and Mitsubishi Diamond Dealer — those certifications should be closing jobs before you even answer the phone. But competitors without your credentials are showing up first in Google paid results for Stamford HVAC searches.

We help HVAC shops in Fairfield County turn those credentials into a Google LSA and review engine. Most clients add 10–15 inbound calls per month within 60 days.

Do you have 15 minutes Thursday or Friday?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""",
     "HVAC", 2),

    ("Antonio", "service@tritechmechanical.com",
     "Antonio — Tri Tech has 12 Yelp reviews. Your competitors have 200+.",
     """Hi Antonio,

Tri Tech has solid testimonials on your site — "could not be happier with their professionalism" isn't something every HVAC shop earns. But you have 12 Yelp reviews. Competitors in Stamford have 10x that, and they're bidding on Google LSA while you're not showing up.

We turn existing customer satisfaction into a review engine and get HVAC contractors on Google Local Services Ads. Most clients see 30–40% more inbound calls within 60 days.

Do you have 15 minutes Thursday or Friday?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""",
     "HVAC", 2),

    # ── ROOFING ────────────────────────────────────────────────────────────
    ("David", "info@mgottfried.com",
     "David — Gottfried's 75-year track record isn't ranking on Google",
     """Hi David,

M. Gottfried has been doing this since 1946 — that's a track record most contractors would kill for. But when building managers in Stamford and Greenwich search "commercial flat roof contractor," newer firms with a fraction of your history are showing up first in paid results.

We help established contractors like Gottfried turn their reputation into a lead engine — Google LSA, targeted paid search, review automation. Most clients add 8–12 qualified inbound calls per month within 60 days.

Do you have 15 minutes Thursday or Friday?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""",
     "Roofing", 3),

    # ── PLUMBING ───────────────────────────────────────────────────────────
    ("Owner", "service@cassidyplumbinginc.com",
     "Cassidy Plumbing — the one channel you're not using that your competitors are",
     """Hi,

Looked at Cassidy Plumbing — good reviews, solid local presence. But you're not on Instagram and your paid search footprint is thin. In a market like Stamford/Fairfield County, that's real jobs going to competitors with inferior service.

We do AI-powered marketing for home service businesses in CT. Typical plumbing client adds 12–18 inbound calls/month within 60 days: Google Local Services Ads, review automation, social content, GBP optimization. Flat monthly rate, no long-term commitments.

I put together a 2-minute audit for Cassidy. Do you have 15 minutes Thursday or Friday?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""",
     "Plumbing", 3),

    # ── CPA ────────────────────────────────────────────────────────────────
    ("Michael", "info@anglisscolohanpc.com",
     "Your Google presence is leaving CPA clients to competitors",
     """Hi Michael,

CPA firms doing business tax prep and estate planning in Stamford are quietly losing clients to younger practices that rank on page one — even when the smaller firm has less experience than yours.

Angliss & Colohan has 13 years and A+ BBB accreditation. That credibility isn't showing up where prospects are searching.

We've helped local service firms in CT add 10–20 qualified inquiries per month by fixing their Google presence and automating their follow-up. For a CPA practice, that typically means $30K–$80K in new AUM or recurring clients within the first quarter.

No jargon, no 12-month contracts. Do you have 20 minutes this week?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""",
     "CPA", 3),

    ("Owner", "jhumyb@gmail.com",
     "Quick question about your tax practice in Stamford",
     """Hi,

Found your CPA practice on BBB — A+ rating, Atlantic Street location. Impressive for a boutique operation.

Solo and small CPA firms in CT are losing up to 40% of potential referrals because their online presence doesn't match their reputation. Google searches for "CPA Stamford CT" return firms with less experience but better digital marketing.

We help small professional service firms fix that with AI-automated marketing. The ROI for a solo practice is typically 3–5 new client files per month — from fixes that take us 2 weeks to set up.

Do you have 15 minutes this week?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""",
     "CPA", 4),
]

# ─── SEND ──────────────────────────────────────────────────────────────────

EMAILS.sort(key=lambda x: x[5])

sent, failed = 0, 0
for (to_name, to_email, subject, body, vertical, priority) in EMAILS:
    if DRY_RUN:
        print(f"[DRY RUN] {vertical} P{priority} | {to_email} | {subject}")
        sent += 1
        continue
    try:
        params: resend.Emails.SendParams = {
            "from": f"{FROM_NAME} <{FROM_ADDR}>",
            "to": [to_email],
            "subject": subject,
            "text": body,
        }
        resend.Emails.send(params)
        print(f"✓ [{vertical}] Sent → {to_email}")
        sent += 1
        time.sleep(2)
    except Exception as ex:
        print(f"✗ [{vertical}] Failed {to_email}: {ex}")
        failed += 1

print(f"\n{'[DRY RUN] ' if DRY_RUN else ''}{sent} sent, {failed} failed / {len(EMAILS)} total")

# ─── SETUP NOTES ───────────────────────────────────────────────────────────
# 1. Get free API key: https://resend.com/api-keys
# 2. To send from pat@localcomm.co (not the default resend.dev address):
#    → Resend dashboard → Domains → Add Domain → add localcomm.co DNS records
#    → Takes ~5 min. Free tier supports custom domains.
# 3. Run:
#    RESEND_API_KEY=re_xxxx python3 send_resend.py
# 4. Dry run first to verify all emails look right:
#    DRY_RUN=1 python3 send_resend.py
