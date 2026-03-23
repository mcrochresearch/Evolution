#!/usr/bin/env python3
"""
LocalComm Outreach Sender — all verticals
Usage:
  SMTP_USER=pat@gmail.com SMTP_PASS='xxxx xxxx xxxx xxxx' python3 send_all_outreach.py

  For Gmail: create App Password at https://myaccount.google.com/apppasswords
  For M365:  SMTP_HOST=smtp.office365.com SMTP_USER=pat@localcomm.co SMTP_PASS=yourpass
  For dry run (no send): DRY_RUN=1 python3 send_all_outreach.py
"""
import smtplib
import os
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_NAME = os.getenv("FROM_NAME", "Pat McKenna")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
DRY_RUN   = os.getenv("DRY_RUN", "0") == "1"

if not DRY_RUN and (not SMTP_USER or not SMTP_PASS):
    print("ERROR: Set SMTP_USER and SMTP_PASS env vars")
    print("  Gmail:  SMTP_USER=you@gmail.com SMTP_PASS='xxxx xxxx xxxx xxxx'")
    print("  M365:   SMTP_HOST=smtp.office365.com SMTP_USER=you@domain.com SMTP_PASS=yourpass")
    print("  Dry run: DRY_RUN=1 python3 send_all_outreach.py")
    exit(1)

# ─── LEADS ────────────────────────────────────────────────────────────────────
# Format: (to_name, to_email, subject, body, vertical, priority)
# Priority 1 = send first. Only direct emails included — no contact form addresses.

EMAILS = [

    # ── HVAC ──────────────────────────────────────────────────────────────────
    ("Owner", "service@ccservicellc.com", "C&C Service — your Carrier Diamond creds aren't driving inbound leads", """Hi,

You're a Carrier Factory Authorized Dealer and Mitsubishi Diamond Dealer — those certifications should be closing jobs before you even answer the phone. But competitors without your credentials are showing up first in Google paid results for Stamford HVAC searches.

We help HVAC shops in Fairfield County turn those credentials into a Google LSA and review engine. Most clients add 10–15 inbound calls per month within 60 days.

Do you have 15 minutes Thursday or Friday?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""", "HVAC", 1),

    ("Antonio", "service@tritechmechanical.com", "Antonio — Tri Tech has 12 Yelp reviews. Your competitors have 200+.", """Hi Antonio,

Tri Tech has solid testimonials on your site — "could not be happier with their professionalism" isn't something every HVAC shop earns. But you have 12 Yelp reviews. Competitors in Stamford have 10x that, and they're bidding on Google LSA while you're not showing up.

We turn existing customer satisfaction into a review engine and get HVAC contractors on Google Local Services Ads. Most clients see 30–40% more inbound calls within 60 days.

Do you have 15 minutes Thursday or Friday?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""", "HVAC", 1),

    # ── ROOFING ───────────────────────────────────────────────────────────────
    ("David", "info@mgottfried.com", "David — Gottfried's 75-year track record isn't ranking on Google", """Hi David,

M. Gottfried has been doing this since 1946 — that's a track record most contractors would kill for. But when building managers in Stamford and Greenwich search "commercial flat roof contractor," newer firms with a fraction of your history are showing up first in paid results.

We help established contractors like Gottfried turn their reputation into a lead engine — Google LSA, targeted paid search, review automation. Most clients add 8–12 qualified inbound calls per month within 60 days.

Do you have 15 minutes Thursday or Friday?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""", "Roofing", 1),

    # ── PLUMBING ──────────────────────────────────────────────────────────────
    ("Owner", "service@cassidyplumbinginc.com", "Cassidy Plumbing — the one channel you're not using that your competitors are", """Hi,

Looked at Cassidy Plumbing — good reviews, solid local presence. But you're not on Instagram and your paid search footprint is thin. In a market like Stamford/Fairfield County, that's real jobs going to competitors with inferior service.

We do AI-powered marketing for home service businesses in CT. Typical plumbing client adds 12–18 inbound calls/month within 60 days: Google Local Services Ads, review automation, social content, GBP optimization. Flat monthly rate, no long-term commitments.

I put together a 2-minute audit for Cassidy. Happy to send it over — no pitch, just the gaps.

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""", "Plumbing", 2),

    # ── CPA ───────────────────────────────────────────────────────────────────
    ("Michael", "info@anglisscolohanpc.com", "Your Google presence is leaving CPA clients to competitors", """Hi Michael,

CPA firms doing business tax prep and estate planning in Stamford are quietly losing clients to younger practices that rank on page one — even when the smaller firm has less experience than yours.

Angliss & Colohan has 13 years and A+ BBB accreditation. That credibility isn't showing up where prospects are searching.

We've helped local service firms in CT add 10–20 qualified inquiries per month by fixing their Google presence and automating their follow-up. For a CPA practice, that typically means $30K–$80K in new AUM or recurring clients within the first quarter.

No jargon, no 12-month contracts. One call to see if it makes sense for your firm.

Can we connect for 20 minutes this week?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""", "CPA", 1),

    ("Owner", "jhumyb@gmail.com", "Quick question about your tax practice in Stamford", """Hi,

Found your CPA practice on BBB — A+ rating, Atlantic Street location. Impressive for a boutique operation.

Solo and small CPA firms in CT are losing up to 40% of potential referrals because their online presence doesn't match their reputation. Google searches for "CPA Stamford CT" return firms with less experience but better digital marketing.

We help small professional service firms fix that with AI-automated marketing. The ROI for a solo practice is typically 3–5 new client files per month ($6K–$15K in annual fees) — from fixes that take us 2 weeks to set up.

Worth a 15-minute call?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""", "CPA", 2),

    # ── PRISCO (follow-up) ────────────────────────────────────────────────────
    ("Nick", "nick@priscoappliance.com", "Prisco Appliance — quick question", """Hi Nick,

Reached out a while back about Prisco's online presence. 4.9 stars and 206 reviews is exceptional for White Plains — that's a level of trust most businesses spend years trying to build.

Here's the thing: zero paid ads means your competitors are buying traffic that your reputation should be winning organically. Google Local Services Ads for appliance repair in Westchester runs about $18–25 per lead. We'd target it to get you to $8–12 with proper setup.

I built a specific action plan for Prisco — three things that would generate measurable new calls within 60 days. Takes 15 minutes to walk through.

Are you free for a call this week or next?

— Pat McKenna
LocalComm · localcomm.co · (203) 555-0100""", "Appliance", 1),

]

# ─── SEND ─────────────────────────────────────────────────────────────────────

def send_email(to_name, to_email, subject, body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{FROM_NAME} <{SMTP_USER}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to_email, msg.as_string())

# Sort by priority
EMAILS.sort(key=lambda x: x[5])

sent, failed = 0, 0
for (to_name, to_email, subject, body, vertical, priority) in EMAILS:
    if DRY_RUN:
        print(f"[DRY RUN] {vertical} | To: {to_email} | Subject: {subject}")
        sent += 1
        continue
    try:
        send_email(to_name, to_email, subject, body)
        print(f"✓ [{vertical}] Sent to {to_email}")
        sent += 1
        time.sleep(3)  # avoid rate limits
    except Exception as ex:
        print(f"✗ [{vertical}] Failed {to_email}: {ex}")
        failed += 1

print(f"\n{'DRY RUN — ' if DRY_RUN else ''}{sent} sent, {failed} failed / {len(EMAILS)} total")

# ─── USAGE NOTES ──────────────────────────────────────────────────────────────
# Gmail App Password setup:
#   1. Enable 2FA: https://myaccount.google.com/security
#   2. Create App Password: https://myaccount.google.com/apppasswords
#      Select "Mail" + "Mac" → generates 16-char password
#   3. SMTP_USER=you@gmail.com SMTP_PASS='abcd efgh ijkl mnop' python3 send_all_outreach.py
#
# Prisco note: confirm email before sending. (914) 949-6464 to verify.

# ─── VET LEADS (added 2026-03-23) ─────────────────────────────────────────────
# High Ridge has a phone number; call may be better first touch than email.
# Stamford Vet Center: email not found on site — use contact form.
# Add these to the queue once email addresses are confirmed via contact form or phone.

# VET OUTREACH DRAFTS (not yet in send queue — no confirmed email addresses):
#
# HIGH RIDGE ANIMAL HOSPITAL — (203) 322-0507 — highridgeanimalhosp.com
# Subject: High Ridge Animal Hospital — your Google presence isn't matching your care quality
# Body:
#   Hi,
#   High Ridge Animal Hospital has been serving Stamford for years — wellness, surgery, diagnostics,
#   PetDesk app. That's a serious operation. But pet owners searching "veterinarian Stamford CT"
#   are landing on practices with thinner track records that rank higher in Google.
#   We help veterinary practices in Fairfield County close that gap. GBP optimization, automated
#   review sequences, local SEO for high-value services (dental, surgery). Typical result: 10–20
#   more new patient inquiries/month within 60 days.
#   Do you have 15 minutes Thursday or Friday?
#   — Pat McKenna · LocalComm · localcomm.co · (203) 555-0100
#
# STAMFORD VET CENTER — stamfordvetcenter.com — use contact form
# Subject: Your "first exam free" offer — is it driving new clients?
# Body:
#   Hi,
#   Noticed Stamford Veterinary Center is running a "Free First Exam" offer — that's a smart
#   acquisition play. But if that offer isn't showing up in local search results and Google Ads,
#   you're leaving it on the table.
#   We help vet practices in CT turn acquisition offers like yours into a full funnel — Google LSA,
#   review automation, local SEO. Most clients add 10–20 new patient families/month within 60 days.
#   Worth a 15-minute call to see if it makes sense?
#   — Pat McKenna · LocalComm · localcomm.co · (203) 555-0100
