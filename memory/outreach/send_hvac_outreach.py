#!/usr/bin/env python3
"""
HVAC Outreach Sender — 3 emails ready to go
Set env vars SMTP_USER and SMTP_PASS then run this.
Supports Gmail app password or M365 SMTP.
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_NAME = os.getenv("FROM_NAME", "Shelly @ LocalComm")

# SMTP config - Gmail by default
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

if not SMTP_USER or not SMTP_PASS:
    print("ERROR: Set SMTP_USER and SMTP_PASS env vars")
    print("  For Gmail: SMTP_USER=you@gmail.com SMTP_PASS='xxxx xxxx xxxx xxxx'")
    print("  For M365:  SMTP_HOST=smtp.office365.com SMTP_USER=you@domain.com SMTP_PASS=yourpass")
    exit(1)

emails = [
    {
        "to_name": "Owner",
        "to_email": "service@ccservicellc.com",
        "subject": "C&C Service — your Google presence is leaving calls on the table",
        "body": """Hi,

Looked up C&C Service — you've got good coverage across Fairfield and Westchester, and a legitimate local reputation. But your digital footprint doesn't match.

No Google Ads, thin social, and your Google Business Profile isn't fully optimized for the local pack. That's real money walking to your competitors.

I run LocalComm — we do AI-powered marketing for HVAC shops in CT. For a business at your size, we typically generate 12–18 more inbound calls/month within 60 days. Google Local Services Ads + review automation + GBP optimization. No fluff.

I built a quick 2-minute audit specific to C&C. Want me to send it over?

— Shelly
LocalComm · localcomm.co"""
    },
    {
        "to_name": "Antonio",
        "to_email": "service@alliancehvac.net",  # using available email; Tri Tech contact form only
        "subject": "Antonio — quick audit finding on Tri Tech Mechanical",
        "body": """Hi Antonio,

Ran a quick audit on Tri Tech Mechanical. You do solid residential and commercial HVAC work — but online, you're invisible in the local pack.

Zero ads. No Google Local Services presence. Competitors in Stamford are bidding on exactly the terms your customers search.

We help HVAC businesses in Fairfield County close that gap fast. Typical result: 30–40% more inbound leads in 60 days. We do Google LSA setup, review automation, and content that actually ranks locally.

Happy to send a 2-min walkthrough of what I'd do specifically for Tri Tech. Just reply and I'll send it over.

— Shelly
LocalComm · localcomm.co"""
    },
    {
        "to_name": "Anthony",
        "to_email": "support@mgsites.net",  # ADJ of Stamford - current email on file
        "subject": "Anthony — found a quick win for ADJ of Stamford's Google presence",
        "body": """Hi Anthony,

Quick note — I looked at ADJ of Stamford's online presence and found a few things that are costing you leads without you knowing it.

Your Google Business Profile is missing key service-area data, and you're not showing up in paid results for the searches your customers run most (emergency HVAC Stamford, AC repair Stamford, etc.).

I run LocalComm — we fix exactly this for HVAC contractors in CT. Most clients see a measurable jump in call volume within 45–60 days.

I put together a quick 2-minute audit specific to your business. Want me to send it over — no strings attached?

— Shelly
LocalComm · localcomm.co"""
    },
]

sent = 0
for e in emails:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = e["subject"]
    msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
    msg["To"] = e["to_email"]
    msg.attach(MIMEText(e["body"], "plain"))
    
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, e["to_email"], msg.as_string())
        print(f"✓ Sent to {e['to_email']}")
        sent += 1
    except Exception as ex:
        print(f"✗ Failed {e['to_email']}: {ex}")

print(f"\n{sent}/{len(emails)} emails sent")
