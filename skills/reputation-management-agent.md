---
name: reputation-management-agent
description: >
  Autonomous reputation management skill for AI agents. Use when an agent needs to monitor
  online reviews, analyze customer sentiment, generate on-brand review responses, calculate
  reputation scores, run review request campaigns, benchmark against competitors, or produce
  monthly reputation reports. Integrates with the client-brand-profile skill for multi-client
  brand-aware operation. Covers Google Places, Yelp Fusion, VADER sentiment analysis, LLM
  response generation with brand voice injection, QR code campaigns, and alerting. Designed
  for autonomous operation with no human intervention required.
metadata:
  author: localcomm
  version: '1.0'
  updated: '2026-03-15'
---

# Reputation Management for Autonomous AI Agents

## When to Use This Skill

Use this skill when an AI agent needs to:

- Monitor and fetch new reviews from Google, Yelp, or Facebook
- Analyze customer sentiment across all review platforms
- Generate on-brand responses to positive, negative, and neutral reviews
- Calculate and track a client's overall reputation score
- Run review request campaigns (email, SMS, QR code)
- Benchmark a client's reputation against local competitors
- Produce monthly reputation reports with trends and recommendations
- Alert on negative reviews or sudden reputation drops

## Free Tool Stack (As of March 2026)

### Tier 1: Review Monitoring APIs

#### 1. Google Places API (Reviews + Ratings)
- **What**: Official Google API for place details including reviews and ratings
- **Cost**: Free $200/month credit (~$17/1K requests for Place Details)
- **Data**: Star rating, review text, author, time, profile photo
- **Limit**: 5 most recent reviews per API call; use Outscraper for full history
- **URL**: https://developers.google.com/maps/documentation/places/web-service
- **Best For**: Real-time review monitoring for Google Business profiles

#### 2. Outscraper Google Maps Reviews API
- **What**: Third-party API for bulk Google Maps review extraction
- **Cost**: Free tier — 25 requests/month
- **Data**: Full review history, review responses, photo URLs, reviewer profiles
- **URL**: https://outscraper.com/google-maps-reviews-api/
- **Best For**: Historical review collection and bulk analysis

#### 3. Yelp Fusion API (Reviews + Ratings)
- **What**: Official Yelp API for business reviews and ratings
- **Cost**: Free — 5,000 API calls/day
- **Data**: Star rating, review text, time, user info, up to 3 review excerpts per business
- **URL**: https://docs.developer.yelp.com/docs/fusion-intro
- **Best For**: Restaurant and local service review monitoring

#### 4. Facebook Graph API (Page Reviews)
- **What**: Access Facebook Page recommendations and reviews
- **Cost**: Free with Facebook App credentials
- **Data**: Recommendation (yes/no), review text, reviewer name
- **URL**: https://developers.facebook.com/docs/graph-api/
- **Best For**: Businesses with active Facebook presence

### Tier 2: Sentiment Analysis (Free / Open Source)

#### 5. VADER Sentiment (vaderSentiment)
- **What**: Rule-based sentiment analysis tuned for social media and reviews
- **License**: MIT — fully free
- **Output**: Compound score (-1.0 to +1.0), positive/negative/neutral breakdowns
- **Strengths**: Handles emojis, slang, punctuation emphasis, capitalization
- **Install**: `pip install vaderSentiment`
- **Best For**: Fast, accurate sentiment scoring of customer reviews

#### 6. TextBlob
- **What**: Simple NLP library with sentiment analysis
- **License**: MIT — fully free
- **Output**: Polarity (-1.0 to +1.0) and subjectivity (0.0 to 1.0)
- **Install**: `pip install textblob`
- **Best For**: Quick polarity checks and subjectivity filtering

#### 7. spaCy + spacytextblob
- **What**: Industrial-strength NLP with sentiment extension
- **License**: MIT — fully free
- **Strengths**: Named entity recognition, topic extraction, dependency parsing
- **Install**: `pip install spacy spacytextblob`
- **Best For**: Advanced theme extraction and entity-level sentiment

#### 8. MeaningCloud Sentiment API
- **What**: Cloud sentiment analysis with aspect-based opinions
- **Cost**: Free tier — 20K credits/month (~1K analyses)
- **URL**: https://www.meaningcloud.com/developer/sentiment-analysis
- **Best For**: Aspect-based sentiment (food, service, ambiance separately)

### Tier 3: Response Generation (Free LLMs)

#### 9. Google Gemini API (Free Tier)
- **What**: Google's multimodal LLM with generous free tier
- **Cost**: Free — 15 RPM, 1M tokens/day
- **Models**: gemini-2.0-flash (fast), gemini-2.5-pro (quality)
- **URL**: https://ai.google.dev/
- **Best For**: High-quality review response generation with brand voice

#### 10. Ollama (Local LLMs)
- **What**: Run open-source LLMs locally — Llama 3, Mistral, Gemma
- **Cost**: Completely free (requires local GPU or CPU)
- **Models**: llama3.1:8b (fast), mistral:7b, gemma2:9b
- **URL**: https://ollama.ai
- **Best For**: Unlimited, private response generation with no API limits

### Tier 4: Social Listening & Alerts

#### 11. Google Alerts
- **What**: Free email alerts for brand mentions across the web
- **Cost**: Completely free
- **Setup**: Create alerts for business name, owner name, product names
- **URL**: https://www.google.com/alerts
- **Best For**: Passive monitoring of web mentions and news

#### 12. Social Searcher
- **What**: Free real-time social media search engine
- **Cost**: Free — 100 searches/day
- **Platforms**: Twitter/X, Facebook, Instagram, YouTube, Reddit, Tumblr
- **URL**: https://www.social-searcher.com
- **Best For**: Real-time social media mention monitoring

#### 13. Brand24
- **What**: Social media monitoring and analytics platform
- **Cost**: Free trial — 25M+ sources monitored
- **URL**: https://brand24.com
- **Best For**: Comprehensive social listening with sentiment trends

### Tier 5: Campaign & Reporting Tools

#### 14. qrcode (Python Library)
- **What**: QR code generator for Python
- **License**: BSD — fully free
- **Install**: `pip install qrcode[pil]`
- **Best For**: Generating review request QR codes for physical locations

#### 15. matplotlib + Pillow (Reporting)
- **What**: Chart generation and image composition for reports
- **License**: PSF (matplotlib), PIL (Pillow) — fully free
- **Install**: `pip install matplotlib Pillow`
- **Best For**: Reputation trend charts, sentiment breakdowns, monthly reports

#### 16. Jinja2 (Email/SMS Templates)
- **What**: Python templating engine for campaign messages
- **License**: BSD — fully free
- **Install**: `pip install Jinja2`
- **Best For**: Generating personalized review request emails and SMS messages

## Autonomous Reputation Management Pipeline Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATOR                           │
│              (LLM: Gemini / Ollama / Local)                    │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │             BrandProfileManager (client_id)              │  │
│  │    brand_profiles/{client_id}/profile.json → voice,      │  │
│  │    colors, competitors, platforms, vocabulary             │  │
│  └──────────────────────┬───────────────────────────────────┘  │
└─────────────────────────┼──────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌─────────────────┐ ┌──────────┐ ┌────────────────┐
│ REVIEW SOURCES  │ │ SOCIAL   │ │ COMPETITOR     │
│                 │ │ LISTENING│ │ MONITORING     │
│ Google Places   │ │          │ │                │
│ Yelp Fusion     │ │ Google   │ │ Google Places  │
│ Facebook Graph  │ │ Alerts   │ │ Yelp Fusion    │
│ Outscraper      │ │ Social   │ │ Same APIs,     │
│                 │ │ Searcher │ │ competitor IDs │
└────────┬────────┘ └────┬─────┘ └───────┬────────┘
         │               │               │
         ▼               ▼               ▼
┌────────────────────────────────────────────────────┐
│              REVIEW DATA STORE                      │
│    brand_profiles/{client_id}/reviews/              │
│                                                     │
│  reviews.jsonl  — All reviews with metadata         │
│  sentiment.jsonl — Sentiment scores per review      │
│  responses.jsonl — Generated/sent responses         │
│  competitors.jsonl — Competitor review snapshots     │
└───────────────────────┬─────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────────┐
│ SENTIMENT   │ │ RESPONSE     │ │ REPUTATION       │
│ ANALYSIS    │ │ GENERATION   │ │ SCORING          │
│             │ │              │ │                  │
│ VADER       │ │ LLM + Brand  │ │ Weighted formula │
│ compound    │ │ voice inject │ │ stars + volume + │
│ scoring     │ │ pos/neg/neu  │ │ recency + rate + │
│             │ │ templates    │ │ sentiment        │
└──────┬──────┘ └──────┬───────┘ └────────┬─────────┘
       │               │                  │
       ▼               ▼                  ▼
┌────────────────────────────────────────────────────┐
│                 ALERT SYSTEM                        │
│                                                     │
│  Negative review (< 3 stars) → Immediate alert     │
│  Reputation drop (> 5pts/week) → Trend alert       │
│  No response (> 24hrs) → Response reminder          │
│  Competitor surge → Competitive alert               │
└───────────────────────┬─────────────────────────────┘
                        │
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────────┐
│ REVIEW      │ │ MONTHLY      │ │ CAMPAIGN         │
│ RESPONSE    │ │ REPORT       │ │ GENERATION       │
│ QUEUE       │ │              │ │                  │
│             │ │ Score trend  │ │ Email templates  │
│ Draft →     │ │ Sentiment    │ │ SMS templates    │
│ Review →    │ │ breakdown    │ │ QR codes for     │
│ Post        │ │ Competitor   │ │ physical review  │
│             │ │ comparison   │ │ request cards    │
└─────────────┘ └──────────────┘ └──────────────────┘
```

## Implementation Guide

### Step 1: Review Data Model & Storage

```python
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# ─── CONFIGURATION ─────────────────────────────────────────
BRAND_PROFILES_DIR = os.environ.get("BRAND_PROFILES_DIR", "./brand_profiles")

# ─── REVIEW DATA STRUCTURES ───────────────────────────────

def get_reviews_dir(client_id):
    """Get or create the reviews directory for a client."""
    reviews_dir = Path(BRAND_PROFILES_DIR) / client_id / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    return reviews_dir

def store_review(client_id, review):
    """
    Store a single review to the client's review database.

    review dict keys:
      - platform: "google" | "yelp" | "facebook"
      - review_id: unique ID from the platform
      - author: reviewer name
      - rating: float (1-5)
      - text: review text
      - date: ISO date string
      - url: link to original review (if available)
    """
    reviews_dir = get_reviews_dir(client_id)
    reviews_path = reviews_dir / "reviews.jsonl"

    # Deduplicate by review_id + platform
    existing_ids = set()
    if reviews_path.exists():
        with open(reviews_path, "r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    existing_ids.add(f"{entry['platform']}:{entry['review_id']}")

    key = f"{review['platform']}:{review['review_id']}"
    if key in existing_ids:
        return False  # Already stored

    review["stored_at"] = datetime.now().isoformat()
    review.setdefault("responded", False)
    review.setdefault("response_text", "")

    with open(reviews_path, "a") as f:
        f.write(json.dumps(review) + "\n")
    return True

def load_reviews(client_id, platform=None, since_days=None, min_rating=None, max_rating=None):
    """Load reviews for a client with optional filters."""
    reviews_dir = get_reviews_dir(client_id)
    reviews_path = reviews_dir / "reviews.jsonl"
    if not reviews_path.exists():
        return []

    reviews = []
    cutoff = None
    if since_days:
        cutoff = (datetime.now() - timedelta(days=since_days)).isoformat()

    with open(reviews_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            review = json.loads(line)
            if platform and review.get("platform") != platform:
                continue
            if cutoff and review.get("date", "") < cutoff:
                continue
            if min_rating is not None and review.get("rating", 0) < min_rating:
                continue
            if max_rating is not None and review.get("rating", 5) > max_rating:
                continue
            reviews.append(review)
    return reviews

def get_unresponded_reviews(client_id):
    """Get reviews that haven't been responded to yet."""
    all_reviews = load_reviews(client_id)
    return [r for r in all_reviews if not r.get("responded", False)]
```

### Step 2: Review Collection from APIs

```python
import requests
import os

# ─── GOOGLE PLACES API ────────────────────────────────────

def fetch_google_reviews(client_id, place_id, api_key=None):
    """
    Fetch reviews from Google Places API for a business.

    place_id: Google Place ID (e.g., 'ChIJ...')
    api_key: Google API key (falls back to GOOGLE_API_KEY env var)
    """
    api_key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY required. Get one at https://console.cloud.google.com")

    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,rating,user_ratings_total,reviews",
        "key": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"[Google API error] {e}")
        return {"reviews": [], "rating": 0, "total_ratings": 0}

    result = data.get("result", {})
    reviews = []
    for r in result.get("reviews", []):
        review = {
            "platform": "google",
            "review_id": f"google_{r.get('time', '')}_{hash(r.get('author_name', ''))}",
            "author": r.get("author_name", "Anonymous"),
            "rating": r.get("rating", 0),
            "text": r.get("text", ""),
            "date": datetime.fromtimestamp(r.get("time", 0)).isoformat(),
            "url": r.get("author_url", ""),
            "language": r.get("language", "en"),
        }
        stored = store_review(client_id, review)
        reviews.append(review)

    return {
        "reviews": reviews,
        "rating": result.get("rating", 0),
        "total_ratings": result.get("user_ratings_total", 0),
    }

# ─── YELP FUSION API ──────────────────────────────────────

def fetch_yelp_reviews(client_id, business_id, api_key=None):
    """
    Fetch reviews from Yelp Fusion API.

    business_id: Yelp business ID or alias (e.g., 'marios-bistro-springfield')
    api_key: Yelp API key (falls back to YELP_API_KEY env var)
    """
    api_key = api_key or os.environ.get("YELP_API_KEY")
    if not api_key:
        raise ValueError("YELP_API_KEY required. Get one at https://www.yelp.com/developers")

    headers = {"Authorization": f"Bearer {api_key}"}

    # Get business details (rating + review count)
    try:
        biz_resp = requests.get(
            f"https://api.yelp.com/v3/businesses/{business_id}",
            headers=headers, timeout=15
        )
        biz_resp.raise_for_status()
        biz_data = biz_resp.json()
    except requests.RequestException as e:
        print(f"[Yelp Business API error] {e}")
        biz_data = {}

    # Get reviews (up to 3 per call on free tier)
    try:
        rev_resp = requests.get(
            f"https://api.yelp.com/v3/businesses/{business_id}/reviews",
            headers=headers,
            params={"limit": 50, "sort_by": "newest"},
            timeout=15
        )
        rev_resp.raise_for_status()
        rev_data = rev_resp.json()
    except requests.RequestException as e:
        print(f"[Yelp Reviews API error] {e}")
        rev_data = {"reviews": []}

    reviews = []
    for r in rev_data.get("reviews", []):
        review = {
            "platform": "yelp",
            "review_id": r.get("id", ""),
            "author": r.get("user", {}).get("name", "Anonymous"),
            "rating": r.get("rating", 0),
            "text": r.get("text", ""),
            "date": r.get("time_created", ""),
            "url": r.get("url", ""),
        }
        stored = store_review(client_id, review)
        reviews.append(review)

    return {
        "reviews": reviews,
        "rating": biz_data.get("rating", 0),
        "total_ratings": biz_data.get("review_count", 0),
    }

# ─── UNIFIED REVIEW FETCHER ───────────────────────────────

def fetch_all_reviews(client_id, google_place_id=None, yelp_business_id=None):
    """
    Fetch reviews from all configured platforms for a client.
    Returns a summary dict with per-platform results.
    """
    results = {}

    if google_place_id:
        try:
            results["google"] = fetch_google_reviews(client_id, google_place_id)
        except Exception as e:
            results["google"] = {"error": str(e), "reviews": []}

    if yelp_business_id:
        try:
            results["yelp"] = fetch_yelp_reviews(client_id, yelp_business_id)
        except Exception as e:
            results["yelp"] = {"error": str(e), "reviews": []}

    # Summary
    all_reviews = []
    for platform_data in results.values():
        all_reviews.extend(platform_data.get("reviews", []))

    results["summary"] = {
        "total_new_reviews": len(all_reviews),
        "platforms_checked": list(results.keys()),
        "fetched_at": datetime.now().isoformat(),
    }

    return results
```

### Step 3: Sentiment Analysis Pipeline

```python
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ─── VADER SENTIMENT ANALYSIS ─────────────────────────────

_vader = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    """
    Analyze sentiment of a review using VADER.

    Returns:
      {
        "compound": float (-1.0 to 1.0),
        "positive": float,
        "negative": float,
        "neutral": float,
        "label": "positive" | "negative" | "neutral",
        "urgent": bool
      }
    """
    if not text or not text.strip():
        return {
            "compound": 0.0, "positive": 0.0, "negative": 0.0,
            "neutral": 1.0, "label": "neutral", "urgent": False
        }

    scores = _vader.polarity_scores(text)
    compound = scores["compound"]

    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    # Urgent if strongly negative
    urgent = compound <= -0.5

    return {
        "compound": compound,
        "positive": scores["pos"],
        "negative": scores["neg"],
        "neutral": scores["neu"],
        "label": label,
        "urgent": urgent,
    }

def analyze_reviews_batch(client_id, reviews=None):
    """
    Run sentiment analysis on all reviews (or a provided list).
    Stores results in brand_profiles/{client_id}/reviews/sentiment.jsonl
    """
    if reviews is None:
        reviews = load_reviews(client_id)

    reviews_dir = get_reviews_dir(client_id)
    sentiment_path = reviews_dir / "sentiment.jsonl"

    results = []
    for review in reviews:
        sentiment = analyze_sentiment(review.get("text", ""))
        entry = {
            "review_id": review.get("review_id"),
            "platform": review.get("platform"),
            "rating": review.get("rating"),
            "sentiment": sentiment,
            "analyzed_at": datetime.now().isoformat(),
        }
        results.append(entry)

    # Write all results (overwrite for full re-analysis)
    with open(sentiment_path, "w") as f:
        for entry in results:
            f.write(json.dumps(entry) + "\n")

    # Aggregate stats
    compounds = [r["sentiment"]["compound"] for r in results]
    avg_sentiment = sum(compounds) / len(compounds) if compounds else 0.0
    urgent_count = sum(1 for r in results if r["sentiment"]["urgent"])

    return {
        "total_analyzed": len(results),
        "avg_sentiment": round(avg_sentiment, 3),
        "positive_count": sum(1 for r in results if r["sentiment"]["label"] == "positive"),
        "negative_count": sum(1 for r in results if r["sentiment"]["label"] == "negative"),
        "neutral_count": sum(1 for r in results if r["sentiment"]["label"] == "neutral"),
        "urgent_count": urgent_count,
    }

def get_sentiment_trends(client_id, periods=6, period_days=30):
    """
    Calculate sentiment trends over multiple time periods.
    Returns a list of {period, avg_sentiment, review_count} dicts.
    """
    trends = []
    now = datetime.now()

    for i in range(periods):
        period_end = now - timedelta(days=i * period_days)
        period_start = period_end - timedelta(days=period_days)

        reviews = load_reviews(client_id)
        period_reviews = [
            r for r in reviews
            if period_start.isoformat() <= r.get("date", "") <= period_end.isoformat()
        ]

        if period_reviews:
            sentiments = [analyze_sentiment(r.get("text", ""))["compound"] for r in period_reviews]
            avg = sum(sentiments) / len(sentiments)
        else:
            avg = None

        trends.append({
            "period_start": period_start.strftime("%Y-%m-%d"),
            "period_end": period_end.strftime("%Y-%m-%d"),
            "avg_sentiment": round(avg, 3) if avg is not None else None,
            "review_count": len(period_reviews),
        })

    trends.reverse()
    return trends
```

### Step 4: AI Review Response Generation with Brand Voice

```python
import requests
import json
import os
import sys

# Add parent path for brand profile import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path

# ─── BRAND PROFILE INTEGRATION ────────────────────────────

BRAND_PROFILES_DIR = os.environ.get("BRAND_PROFILES_DIR", "./brand_profiles")

def _load_brand_voice(client_id):
    """Load the client's voice profile from brand profile."""
    profile_path = Path(BRAND_PROFILES_DIR) / client_id / "profile.json"
    if not profile_path.exists():
        return {
            "tone": "friendly",
            "formality": "casual",
            "personality": ["professional", "caring"],
            "vocabulary_include": [],
            "vocabulary_avoid": [],
            "business_name": client_id,
        }
    with open(profile_path, "r") as f:
        profile = json.load(f)
    voice = profile.get("voice", {})
    voice["business_name"] = profile.get("business_name", client_id)
    voice["description"] = profile.get("description", "")
    voice["tagline"] = profile.get("tagline", "")
    return voice

# ─── RESPONSE TEMPLATES ───────────────────────────────────

RESPONSE_TEMPLATES = {
    "positive": {
        "structure": [
            "Express genuine gratitude for the kind words",
            "Reference a specific detail from their review",
            "Reinforce the positive experience they mentioned",
            "Include a warm invitation to return",
        ],
        "tone_guide": "warm, grateful, personal",
        "template": (
            "Thank you so much for your wonderful review, {author}! "
            "We're thrilled to hear {specific_detail}. "
            "{brand_reinforcement} "
            "We'd love to welcome you back — {cta}!"
        ),
    },
    "negative": {
        "structure": [
            "Open with empathy and acknowledgment — never be defensive",
            "Apologize sincerely for their experience",
            "Offer a specific resolution or next step",
            "Invite them to continue the conversation offline",
        ],
        "tone_guide": "empathetic, solution-oriented, humble",
        "template": (
            "Thank you for sharing your feedback, {author}. "
            "We're sorry to hear that {specific_issue}. "
            "This is not the experience we strive for. "
            "{resolution_offer} "
            "Please reach out to us directly at {contact} so we can make this right."
        ),
    },
    "neutral": {
        "structure": [
            "Thank them for taking the time to share",
            "Acknowledge what they liked",
            "Gently highlight a strength they may not have experienced",
            "Include a soft invitation to visit again",
        ],
        "tone_guide": "appreciative, informative, inviting",
        "template": (
            "Thanks for your review, {author}! "
            "We appreciate your feedback. "
            "{highlight_strength} "
            "We hope to see you again soon — {cta}!"
        ),
    },
}

# ─── LLM-BASED RESPONSE GENERATION ────────────────────────

def generate_review_response(client_id, review, method="gemini"):
    """
    Generate an on-brand response to a customer review.

    client_id: brand profile ID
    review: dict with keys {author, rating, text, platform}
    method: "gemini" (API), "ollama" (local), or "template" (no LLM)

    Returns: response text string
    """
    voice = _load_brand_voice(client_id)
    sentiment = analyze_sentiment(review.get("text", ""))

    # Determine response category
    rating = review.get("rating", 3)
    if rating >= 4 or sentiment["label"] == "positive":
        category = "positive"
    elif rating <= 2 or sentiment["label"] == "negative":
        category = "negative"
    else:
        category = "neutral"

    if method == "template":
        return _generate_template_response(review, voice, category)
    elif method == "ollama":
        return _generate_llm_response(review, voice, category, provider="ollama")
    else:
        return _generate_llm_response(review, voice, category, provider="gemini")

def _generate_llm_response(review, voice, category, provider="gemini"):
    """Generate response using an LLM with brand voice injection."""
    template_info = RESPONSE_TEMPLATES[category]

    prompt = f"""You are a reputation manager for {voice.get('business_name', 'our business')}.
{voice.get('description', '')}

Generate a review response with these STRICT rules:

BRAND VOICE:
- Tone: {voice.get('tone', 'friendly')}
- Formality: {voice.get('formality', 'casual')}
- Personality: {', '.join(voice.get('personality', ['professional']))}
- Words to USE naturally: {', '.join(voice.get('vocabulary_include', []))}
- Words to NEVER use: {', '.join(voice.get('vocabulary_avoid', []))}

RESPONSE STRUCTURE ({category} review):
{chr(10).join(f'- {s}' for s in template_info['structure'])}

RULES:
- Never mention competitors by name
- Never be defensive or argumentative
- Never offer discounts or free items in public responses
- Keep response under 100 words
- Be genuine, not generic
- Reference specific details from the review text

REVIEW TO RESPOND TO:
Author: {review.get('author', 'Customer')}
Rating: {review.get('rating', 'N/A')} stars
Platform: {review.get('platform', 'online')}
Text: {review.get('text', '')}

Write ONLY the response text, nothing else."""

    if provider == "gemini":
        return _call_gemini(prompt)
    elif provider == "ollama":
        return _call_ollama(prompt)
    else:
        return _generate_template_response(review, voice, category)

def _call_gemini(prompt):
    """Call Google Gemini API for response generation."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY required. Get one at https://ai.google.dev/")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    try:
        response = requests.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 300}
        }, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except requests.RequestException as e:
        print(f"[Gemini API error] {e}")
        return None
    except (KeyError, IndexError):
        print("[Gemini API error] Unexpected response format")
        return None

def _call_ollama(prompt, model="llama3.1:8b"):
    """Call local Ollama instance for response generation."""
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    try:
        response = requests.post(f"{url}/api/generate", json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 300}
        }, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.RequestException as e:
        print(f"[Ollama error] {e}")
        return None

def _generate_template_response(review, voice, category):
    """Fallback: generate response from templates without LLM."""
    template = RESPONSE_TEMPLATES[category]["template"]
    business = voice.get("business_name", "our business")
    author = review.get("author", "there")

    if category == "positive":
        return template.format(
            author=author,
            specific_detail="you enjoyed your experience with us",
            brand_reinforcement=f"At {business}, that's exactly what we aim for.",
            cta="we always have something new to share",
        )
    elif category == "negative":
        return template.format(
            author=author,
            specific_issue="your experience didn't meet expectations",
            resolution_offer=f"We'd love the chance to make it up to you.",
            contact=f"our team at {business}",
        )
    else:
        return template.format(
            author=author,
            highlight_strength=f"At {business}, we're always working to make every visit special.",
            cta="there's always something great waiting for you",
        )

# ─── BATCH RESPONSE GENERATION ─────────────────────────────

def generate_responses_batch(client_id, method="gemini"):
    """
    Generate responses for all unresponded reviews.
    Stores responses in brand_profiles/{client_id}/reviews/responses.jsonl
    """
    unresponded = get_unresponded_reviews(client_id)
    reviews_dir = get_reviews_dir(client_id)
    responses_path = reviews_dir / "responses.jsonl"

    generated = []
    for review in unresponded:
        response_text = generate_review_response(client_id, review, method=method)
        if response_text:
            entry = {
                "review_id": review.get("review_id"),
                "platform": review.get("platform"),
                "author": review.get("author"),
                "rating": review.get("rating"),
                "review_text": review.get("text", "")[:200],
                "response_text": response_text,
                "category": (
                    "positive" if review.get("rating", 3) >= 4
                    else "negative" if review.get("rating", 3) <= 2
                    else "neutral"
                ),
                "generated_at": datetime.now().isoformat(),
                "status": "draft",  # draft → approved → posted
            }
            with open(responses_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            generated.append(entry)

    return {
        "total_unresponded": len(unresponded),
        "responses_generated": len(generated),
        "output_path": str(responses_path),
    }
```

### Step 5: Reputation Score Calculation

```python
from datetime import datetime, timedelta

# ─── REPUTATION SCORE FORMULA ──────────────────────────────
#
# reputation_score = (
#     star_weight   * normalized_stars   +   (0.35)
#     volume_weight * normalized_volume  +   (0.15)
#     recency_weight * recency_score     +   (0.15)
#     response_weight * response_rate    +   (0.15)
#     sentiment_weight * avg_sentiment       (0.20)
# ) * 100
#
# Result: 0–100 scale

SCORE_WEIGHTS = {
    "star_rating": 0.35,
    "volume": 0.15,
    "recency": 0.15,
    "response_rate": 0.15,
    "sentiment": 0.20,
}

def calculate_reputation_score(client_id, benchmark_volume=50):
    """
    Calculate a weighted reputation score (0-100) for a client.

    benchmark_volume: number of reviews considered "good" volume (for normalization)
    """
    reviews = load_reviews(client_id)
    if not reviews:
        return {"score": 0.0, "components": {}, "grade": "N/A", "review_count": 0}

    # 1. Star rating component (normalize 1-5 → 0-1)
    ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    normalized_stars = max(0, (avg_rating - 1) / 4)  # 1-star=0, 5-star=1

    # 2. Volume component (normalize against benchmark)
    normalized_volume = min(1.0, len(reviews) / benchmark_volume)

    # 3. Recency component (proportion of reviews in last 90 days)
    cutoff_90d = (datetime.now() - timedelta(days=90)).isoformat()
    recent_reviews = [r for r in reviews if r.get("date", "") >= cutoff_90d]
    recency_score = min(1.0, len(recent_reviews) / max(1, len(reviews) * 0.25))

    # 4. Response rate component
    responded = [r for r in reviews if r.get("responded", False)]
    response_rate = len(responded) / len(reviews) if reviews else 0

    # 5. Sentiment component (normalize compound -1..+1 → 0..1)
    sentiments = [analyze_sentiment(r.get("text", ""))["compound"] for r in reviews]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
    normalized_sentiment = (avg_sentiment + 1) / 2  # -1..+1 → 0..1

    # Weighted sum
    score = (
        SCORE_WEIGHTS["star_rating"] * normalized_stars +
        SCORE_WEIGHTS["volume"] * normalized_volume +
        SCORE_WEIGHTS["recency"] * recency_score +
        SCORE_WEIGHTS["response_rate"] * response_rate +
        SCORE_WEIGHTS["sentiment"] * normalized_sentiment
    ) * 100

    score = round(min(100, max(0, score)), 1)

    # Letter grade
    if score >= 90:
        grade = "A+"
    elif score >= 80:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 60:
        grade = "C"
    elif score >= 50:
        grade = "D"
    else:
        grade = "F"

    return {
        "score": score,
        "grade": grade,
        "review_count": len(reviews),
        "avg_rating": round(avg_rating, 2),
        "components": {
            "star_rating": {"value": round(avg_rating, 2), "normalized": round(normalized_stars, 3), "weight": SCORE_WEIGHTS["star_rating"]},
            "volume": {"value": len(reviews), "normalized": round(normalized_volume, 3), "weight": SCORE_WEIGHTS["volume"]},
            "recency": {"value": len(recent_reviews), "normalized": round(recency_score, 3), "weight": SCORE_WEIGHTS["recency"]},
            "response_rate": {"value": round(response_rate * 100, 1), "normalized": round(response_rate, 3), "weight": SCORE_WEIGHTS["response_rate"]},
            "sentiment": {"value": round(avg_sentiment, 3), "normalized": round(normalized_sentiment, 3), "weight": SCORE_WEIGHTS["sentiment"]},
        },
        "calculated_at": datetime.now().isoformat(),
    }

def store_reputation_snapshot(client_id):
    """Store a point-in-time reputation score for trend tracking."""
    score_data = calculate_reputation_score(client_id)
    reviews_dir = get_reviews_dir(client_id)
    history_path = reviews_dir / "reputation_history.jsonl"

    with open(history_path, "a") as f:
        f.write(json.dumps(score_data) + "\n")

    return score_data

def get_reputation_trend(client_id, limit=12):
    """Load reputation score history for trend analysis."""
    reviews_dir = get_reviews_dir(client_id)
    history_path = reviews_dir / "reputation_history.jsonl"

    if not history_path.exists():
        return []

    entries = []
    with open(history_path, "r") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries[-limit:]
```

### Step 6: Competitor Reputation Benchmarking

```python
def fetch_competitor_reputation(client_id, competitor_place_id, competitor_name,
                                 platform="google", api_key=None):
    """
    Fetch a competitor's reviews and calculate their reputation score.
    Stores results for comparison in the client's review directory.
    """
    # Use a temp client_id prefix for competitor data
    comp_client_id = f"_comp_{client_id}_{competitor_name.lower().replace(' ', '-')}"

    if platform == "google":
        data = fetch_google_reviews(comp_client_id, competitor_place_id, api_key=api_key)
    elif platform == "yelp":
        data = fetch_yelp_reviews(comp_client_id, competitor_place_id, api_key=api_key)
    else:
        data = {"reviews": [], "rating": 0, "total_ratings": 0}

    # Calculate competitor's score
    comp_reviews = load_reviews(comp_client_id)
    if comp_reviews:
        sentiments = [analyze_sentiment(r.get("text", ""))["compound"] for r in comp_reviews]
        avg_sentiment = sum(sentiments) / len(sentiments)
    else:
        avg_sentiment = 0.0

    result = {
        "competitor_name": competitor_name,
        "platform": platform,
        "rating": data.get("rating", 0),
        "total_ratings": data.get("total_ratings", 0),
        "avg_sentiment": round(avg_sentiment, 3),
        "recent_reviews": len(data.get("reviews", [])),
        "fetched_at": datetime.now().isoformat(),
    }

    # Store in client's competitor data
    reviews_dir = get_reviews_dir(client_id)
    comp_path = reviews_dir / "competitors.jsonl"
    with open(comp_path, "a") as f:
        f.write(json.dumps(result) + "\n")

    return result

def benchmark_against_competitors(client_id, competitors_config):
    """
    Compare client reputation against all configured competitors.

    competitors_config: list of dicts with keys:
      - name: competitor business name
      - google_place_id: (optional) Google Place ID
      - yelp_business_id: (optional) Yelp business ID

    Returns comparison table data.
    """
    client_score = calculate_reputation_score(client_id)
    benchmarks = [{
        "name": "(You)",
        "rating": client_score["avg_rating"],
        "review_count": client_score["review_count"],
        "sentiment": client_score["components"]["sentiment"]["value"],
        "score": client_score["score"],
    }]

    for comp in competitors_config:
        comp_name = comp.get("name", "Unknown")
        comp_data = {"name": comp_name, "rating": 0, "review_count": 0, "sentiment": 0, "score": 0}

        if comp.get("google_place_id"):
            try:
                result = fetch_competitor_reputation(
                    client_id, comp["google_place_id"], comp_name, platform="google"
                )
                comp_data["rating"] = result.get("rating", 0)
                comp_data["review_count"] = result.get("total_ratings", 0)
                comp_data["sentiment"] = result.get("avg_sentiment", 0)
            except Exception as e:
                print(f"[Competitor fetch error: {comp_name}] {e}")

        benchmarks.append(comp_data)

    return {
        "client_score": client_score["score"],
        "client_grade": client_score["grade"],
        "benchmarks": benchmarks,
        "generated_at": datetime.now().isoformat(),
    }
```

### Step 7: Review Request Campaign Generation

```python
import qrcode
from io import BytesIO
from PIL import Image

# ─── QR CODE GENERATION ────────────────────────────────────

def generate_review_qr_code(review_url, output_path, size=300):
    """
    Generate a QR code that links to the business's review page.

    review_url: e.g., "https://g.page/r/YOUR_PLACE_ID/review"
    output_path: path to save the QR code PNG
    size: pixel size of the output image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(review_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((size, size), Image.LANCZOS)
    img.save(output_path)
    return output_path

# ─── CAMPAIGN TEMPLATES ────────────────────────────────────

def generate_review_request_templates(client_id):
    """
    Generate email and SMS templates for requesting reviews.
    Uses the client's brand voice from their profile.
    """
    voice = _load_brand_voice(client_id)
    business_name = voice.get("business_name", "our business")
    tone = voice.get("tone", "friendly")
    formality = voice.get("formality", "casual")

    # Adapt language to formality level
    if formality == "formal":
        greeting = "Dear {customer_name}"
        thanks = "We sincerely appreciate your recent visit"
        closing = "With gratitude"
    else:
        greeting = "Hi {customer_name}"
        thanks = "Thanks for visiting us"
        closing = "Cheers"

    templates = {
        "email_initial": {
            "subject": f"How was your experience at {business_name}?",
            "body": f"""{greeting},

{thanks} to {business_name}! We hope you had a wonderful time.

Your feedback means the world to us and helps other customers discover what makes us special. Would you take a moment to share your experience?

{{{{review_link}}}}

Thank you for being part of the {business_name} family!

{closing},
The {business_name} Team""",
        },
        "email_followup": {
            "subject": f"Quick reminder — we'd love your feedback, {'{customer_name}'}!",
            "body": f"""{greeting},

Just a friendly follow-up! We noticed you visited {business_name} recently and we'd love to hear how it went.

It only takes 30 seconds and helps us keep doing what we do best:

{{{{review_link}}}}

Thanks so much!

{closing},
The {business_name} Team""",
        },
        "sms_initial": {
            "body": (
                f"Hi {{{{customer_name}}}}! Thanks for visiting {business_name}. "
                f"We'd love to hear your feedback — it only takes 30 seconds! "
                f"{{{{review_link}}}}"
            ),
        },
        "sms_followup": {
            "body": (
                f"Hey {{{{customer_name}}}}, just a quick reminder from {business_name}! "
                f"If you have a moment, we'd really appreciate a review: "
                f"{{{{review_link}}}}"
            ),
        },
    }

    # Store templates for the client
    reviews_dir = get_reviews_dir(client_id)
    templates_path = reviews_dir / "campaign_templates.json"
    with open(templates_path, "w") as f:
        json.dump(templates, f, indent=2)

    return templates

# ─── CAMPAIGN TIMING RECOMMENDATIONS ──────────────────────

OPTIMAL_TIMING = {
    "restaurant": {
        "send_delay_hours": 2,     # Hours after visit to send request
        "followup_days": 3,        # Days before follow-up
        "best_days": ["Tuesday", "Wednesday", "Thursday"],
        "best_hours": (10, 14),    # 10am-2pm
    },
    "salon": {
        "send_delay_hours": 1,
        "followup_days": 2,
        "best_days": ["Tuesday", "Wednesday", "Thursday", "Friday"],
        "best_hours": (11, 15),
    },
    "fitness": {
        "send_delay_hours": 1,
        "followup_days": 2,
        "best_days": ["Monday", "Tuesday", "Wednesday"],
        "best_hours": (9, 12),
    },
    "retail": {
        "send_delay_hours": 24,
        "followup_days": 5,
        "best_days": ["Tuesday", "Wednesday", "Thursday"],
        "best_hours": (10, 14),
    },
    "default": {
        "send_delay_hours": 4,
        "followup_days": 3,
        "best_days": ["Tuesday", "Wednesday", "Thursday"],
        "best_hours": (10, 14),
    },
}

def get_campaign_timing(client_id):
    """Get optimal review request timing for the client's industry."""
    profile_path = Path(BRAND_PROFILES_DIR) / client_id / "profile.json"
    industry = "default"
    if profile_path.exists():
        with open(profile_path, "r") as f:
            profile = json.load(f)
        industry = profile.get("industry", "default")
    return OPTIMAL_TIMING.get(industry, OPTIMAL_TIMING["default"])
```

### Step 8: Alert System

```python
import json
from datetime import datetime, timedelta
from pathlib import Path

# ─── ALERT TYPES ───────────────────────────────────────────

ALERT_TYPES = {
    "negative_review": {
        "severity": "high",
        "description": "New review with rating <= 2 stars",
    },
    "reputation_drop": {
        "severity": "high",
        "description": "Reputation score dropped > 5 points in 7 days",
    },
    "no_response_24h": {
        "severity": "medium",
        "description": "Review has not been responded to within 24 hours",
    },
    "competitor_surge": {
        "severity": "low",
        "description": "Competitor rating increased significantly",
    },
    "volume_drop": {
        "severity": "medium",
        "description": "Review volume dropped significantly vs prior period",
    },
}

def check_alerts(client_id):
    """
    Run all alert checks for a client. Returns a list of active alerts.
    """
    alerts = []

    # 1. Check for new negative reviews (< 3 stars, last 24h)
    recent = load_reviews(client_id, since_days=1)
    for review in recent:
        if review.get("rating", 5) <= 2:
            alerts.append({
                "type": "negative_review",
                "severity": "high",
                "message": (
                    f"Negative {review.get('rating')}-star review on {review.get('platform')} "
                    f"from {review.get('author', 'Unknown')}: "
                    f"\"{review.get('text', '')[:100]}...\""
                ),
                "review_id": review.get("review_id"),
                "action": "Generate response immediately",
                "timestamp": datetime.now().isoformat(),
            })

    # 2. Check for reputation score drop
    trend = get_reputation_trend(client_id, limit=2)
    if len(trend) >= 2:
        current_score = trend[-1].get("score", 0)
        prev_score = trend[-2].get("score", 0)
        if prev_score - current_score > 5:
            alerts.append({
                "type": "reputation_drop",
                "severity": "high",
                "message": (
                    f"Reputation score dropped from {prev_score} to {current_score} "
                    f"({round(prev_score - current_score, 1)} point decline)"
                ),
                "action": "Investigate recent negative reviews and accelerate response",
                "timestamp": datetime.now().isoformat(),
            })

    # 3. Check for unresponded reviews > 24h old
    unresponded = get_unresponded_reviews(client_id)
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    stale = [r for r in unresponded if r.get("stored_at", "") < cutoff]
    if stale:
        alerts.append({
            "type": "no_response_24h",
            "severity": "medium",
            "message": f"{len(stale)} review(s) unresponded for over 24 hours",
            "review_ids": [r.get("review_id") for r in stale],
            "action": "Generate and post responses",
            "timestamp": datetime.now().isoformat(),
        })

    # 4. Check for review volume drop (compare last 30d vs prior 30d)
    recent_30d = load_reviews(client_id, since_days=30)
    prior_reviews = load_reviews(client_id, since_days=60)
    prior_30d = [r for r in prior_reviews if r not in recent_30d]
    if len(prior_30d) > 0 and len(recent_30d) < len(prior_30d) * 0.5:
        alerts.append({
            "type": "volume_drop",
            "severity": "medium",
            "message": (
                f"Review volume dropped: {len(recent_30d)} reviews in last 30 days "
                f"vs {len(prior_30d)} in prior period"
            ),
            "action": "Consider launching a review request campaign",
            "timestamp": datetime.now().isoformat(),
        })

    # Store alerts
    reviews_dir = get_reviews_dir(client_id)
    alerts_path = reviews_dir / "alerts.jsonl"
    with open(alerts_path, "a") as f:
        for alert in alerts:
            f.write(json.dumps(alert) + "\n")

    return alerts

def get_alert_summary(client_id, since_days=7):
    """Get recent alerts for a client."""
    reviews_dir = get_reviews_dir(client_id)
    alerts_path = reviews_dir / "alerts.jsonl"

    if not alerts_path.exists():
        return {"alerts": [], "high": 0, "medium": 0, "low": 0}

    cutoff = (datetime.now() - timedelta(days=since_days)).isoformat()
    alerts = []
    with open(alerts_path, "r") as f:
        for line in f:
            if line.strip():
                alert = json.loads(line)
                if alert.get("timestamp", "") >= cutoff:
                    alerts.append(alert)

    return {
        "alerts": alerts,
        "high": sum(1 for a in alerts if a.get("severity") == "high"),
        "medium": sum(1 for a in alerts if a.get("severity") == "medium"),
        "low": sum(1 for a in alerts if a.get("severity") == "low"),
    }
```

### Step 9: Monthly Reputation Report

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path
import json

def generate_monthly_report(client_id, output_dir=None):
    """
    Generate a comprehensive monthly reputation report.

    Returns a dict with report data and paths to generated chart images.
    """
    if output_dir is None:
        output_dir = get_reviews_dir(client_id) / "reports"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    month_str = now.strftime("%Y-%m")

    # ── Gather data ──────────────────────────────────────
    all_reviews = load_reviews(client_id)
    recent_reviews = load_reviews(client_id, since_days=30)
    score_data = calculate_reputation_score(client_id)
    sentiment_stats = analyze_reviews_batch(client_id, recent_reviews)
    trends = get_sentiment_trends(client_id, periods=6, period_days=30)
    alert_summary = get_alert_summary(client_id, since_days=30)

    # ── Generate score trend chart ───────────────────────
    score_trend = get_reputation_trend(client_id, limit=6)
    if score_trend:
        fig, ax = plt.subplots(figsize=(8, 4))
        dates = [s.get("calculated_at", "")[:10] for s in score_trend]
        scores = [s.get("score", 0) for s in score_trend]
        ax.plot(dates, scores, marker="o", color="#2563EB", linewidth=2)
        ax.fill_between(range(len(scores)), scores, alpha=0.15, color="#2563EB")
        ax.set_title("Reputation Score Trend", fontsize=14, fontweight="bold")
        ax.set_ylabel("Score (0-100)")
        ax.set_ylim(0, 100)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        score_chart_path = output_dir / f"score_trend_{month_str}.png"
        plt.savefig(score_chart_path, dpi=150, bbox_inches="tight")
        plt.close()
    else:
        score_chart_path = None

    # ── Generate sentiment breakdown chart ───────────────
    if sentiment_stats["total_analyzed"] > 0:
        fig, ax = plt.subplots(figsize=(6, 4))
        labels = ["Positive", "Neutral", "Negative"]
        counts = [
            sentiment_stats["positive_count"],
            sentiment_stats["neutral_count"],
            sentiment_stats["negative_count"],
        ]
        colors = ["#22C55E", "#94A3B8", "#EF4444"]
        ax.pie(counts, labels=labels, colors=colors, autopct="%1.0f%%", startangle=90)
        ax.set_title("Sentiment Breakdown (Last 30 Days)", fontsize=14, fontweight="bold")
        plt.tight_layout()
        sentiment_chart_path = output_dir / f"sentiment_{month_str}.png"
        plt.savefig(sentiment_chart_path, dpi=150, bbox_inches="tight")
        plt.close()
    else:
        sentiment_chart_path = None

    # ── Generate rating distribution chart ───────────────
    if recent_reviews:
        fig, ax = plt.subplots(figsize=(6, 4))
        rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in recent_reviews:
            star = int(r.get("rating", 0))
            if 1 <= star <= 5:
                rating_counts[star] += 1
        bars = ax.bar(
            [str(k) for k in rating_counts.keys()],
            rating_counts.values(),
            color=["#EF4444", "#F97316", "#EAB308", "#84CC16", "#22C55E"]
        )
        ax.set_title("Rating Distribution (Last 30 Days)", fontsize=14, fontweight="bold")
        ax.set_xlabel("Stars")
        ax.set_ylabel("Count")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout()
        rating_chart_path = output_dir / f"ratings_{month_str}.png"
        plt.savefig(rating_chart_path, dpi=150, bbox_inches="tight")
        plt.close()
    else:
        rating_chart_path = None

    # ── Calculate response rate ──────────────────────────
    responded = [r for r in recent_reviews if r.get("responded", False)]
    response_rate = len(responded) / len(recent_reviews) * 100 if recent_reviews else 0

    # ── Build report ─────────────────────────────────────
    report = {
        "client_id": client_id,
        "report_period": month_str,
        "generated_at": now.isoformat(),
        "reputation_score": score_data["score"],
        "reputation_grade": score_data["grade"],
        "score_components": score_data["components"],
        "review_stats": {
            "total_reviews": len(all_reviews),
            "new_reviews_30d": len(recent_reviews),
            "avg_rating_30d": round(
                sum(r.get("rating", 0) for r in recent_reviews) / len(recent_reviews), 2
            ) if recent_reviews else 0,
            "response_rate_30d": round(response_rate, 1),
        },
        "sentiment": {
            "avg_sentiment_30d": sentiment_stats["avg_sentiment"],
            "positive_pct": round(
                sentiment_stats["positive_count"] / max(1, sentiment_stats["total_analyzed"]) * 100, 1
            ),
            "negative_pct": round(
                sentiment_stats["negative_count"] / max(1, sentiment_stats["total_analyzed"]) * 100, 1
            ),
        },
        "alerts": {
            "total_30d": len(alert_summary["alerts"]),
            "high_severity": alert_summary["high"],
            "medium_severity": alert_summary["medium"],
        },
        "charts": {
            "score_trend": str(score_chart_path) if score_chart_path else None,
            "sentiment_breakdown": str(sentiment_chart_path) if sentiment_chart_path else None,
            "rating_distribution": str(rating_chart_path) if rating_chart_path else None,
        },
        "recommendations": _generate_recommendations(score_data, sentiment_stats, response_rate, recent_reviews),
    }

    # Save report JSON
    report_path = output_dir / f"report_{month_str}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report

def _generate_recommendations(score_data, sentiment_stats, response_rate, recent_reviews):
    """Generate actionable recommendations based on current metrics."""
    recs = []

    if score_data["score"] < 70:
        recs.append("Reputation score is below 70 — prioritize responding to all negative reviews within 4 hours.")

    if response_rate < 50:
        recs.append(f"Response rate is only {response_rate:.0f}%. Aim for 90%+ by responding to every review within 24 hours.")

    if sentiment_stats["negative_count"] > sentiment_stats["positive_count"] * 0.3:
        recs.append("Negative review ratio is high. Investigate recurring complaints and address root causes operationally.")

    if len(recent_reviews) < 5:
        recs.append("Review volume is low. Launch a review request campaign to active customers.")

    avg_rating = score_data.get("avg_rating", 0)
    if avg_rating < 4.0:
        recs.append(f"Average rating is {avg_rating}. Focus on service quality and follow up with unsatisfied customers.")

    if sentiment_stats.get("urgent_count", 0) > 0:
        recs.append(f"{sentiment_stats['urgent_count']} review(s) flagged as urgent — respond immediately with empathy and resolution.")

    if not recs:
        recs.append("Strong performance! Maintain momentum with consistent review requests and timely responses.")

    return recs
```

### Step 10: Full Pipeline Orchestrator

```python
def run_reputation_pipeline(client_id, google_place_id=None, yelp_business_id=None,
                             competitors_config=None, response_method="gemini"):
    """
    Run the full reputation management pipeline for a client.

    Steps:
    1. Fetch new reviews from all platforms
    2. Run sentiment analysis on all reviews
    3. Generate responses for unresponded reviews
    4. Calculate and store reputation score
    5. Check alerts
    6. (Optional) Benchmark against competitors

    Returns a comprehensive pipeline result dict.
    """
    results = {}

    # Step 1: Fetch reviews
    print(f"[{client_id}] Fetching reviews...")
    results["fetch"] = fetch_all_reviews(
        client_id,
        google_place_id=google_place_id,
        yelp_business_id=yelp_business_id,
    )

    # Step 2: Sentiment analysis
    print(f"[{client_id}] Analyzing sentiment...")
    results["sentiment"] = analyze_reviews_batch(client_id)

    # Step 3: Generate responses
    print(f"[{client_id}] Generating responses...")
    results["responses"] = generate_responses_batch(client_id, method=response_method)

    # Step 4: Calculate and store reputation score
    print(f"[{client_id}] Calculating reputation score...")
    results["score"] = store_reputation_snapshot(client_id)

    # Step 5: Check alerts
    print(f"[{client_id}] Checking alerts...")
    results["alerts"] = check_alerts(client_id)

    # Step 6: Competitor benchmarking (optional)
    if competitors_config:
        print(f"[{client_id}] Benchmarking competitors...")
        results["benchmark"] = benchmark_against_competitors(client_id, competitors_config)

    print(f"[{client_id}] Pipeline complete. Score: {results['score']['score']} ({results['score']['grade']})")
    return results
```

## Recommended Stack for LocalComm Agents

| Component | Recommended Tool | Backup |
|-----------|-----------------|--------|
| Google Reviews | Google Places API (free $200/mo) | Outscraper (free 25 req/mo) |
| Yelp Reviews | Yelp Fusion API (free, 5K/day) | Web scraping (last resort) |
| Sentiment Analysis | VADER (Python, MIT, instant) | TextBlob (simpler), MeaningCloud (API) |
| Response Generation | Gemini 2.0 Flash (free 15 RPM) | Ollama local (unlimited), templates |
| Social Listening | Google Alerts (free) | Social Searcher (free 100/day) |
| QR Codes | qrcode Python lib (BSD, free) | Google Charts API |
| Campaign Templates | Jinja2 + brand voice injection | Static templates |
| Reporting Charts | matplotlib (free, PSF license) | Pillow programmatic |
| Data Storage | JSONL flat files per client | SQLite (if volume grows) |
| Brand Integration | BrandProfileManager (client-brand-profile skill) | Manual config dict |

## Multi-Client Storage Structure

```
brand_profiles/
├── index.json
├── marios-bistro/
│   ├── profile.json              # Brand profile (from client-brand-profile skill)
│   ├── reviews/
│   │   ├── reviews.jsonl         # All reviews from all platforms
│   │   ├── sentiment.jsonl       # Sentiment scores per review
│   │   ├── responses.jsonl       # Generated responses (draft/approved/posted)
│   │   ├── competitors.jsonl     # Competitor reputation snapshots
│   │   ├── reputation_history.jsonl  # Score snapshots over time
│   │   ├── alerts.jsonl          # Alert history
│   │   ├── campaign_templates.json   # Review request templates
│   │   └── reports/
│   │       ├── report_2026-03.json
│   │       ├── score_trend_2026-03.png
│   │       ├── sentiment_2026-03.png
│   │       └── ratings_2026-03.png
│   ├── assets/
│   └── history/
├── joes-pizza/
│   ├── profile.json
│   ├── reviews/
│   │   └── ...
```

## Tested Output Specifications

All pipeline components were tested end-to-end on 2026-03-15 with these results:

| Test | Result | Details |
|------|--------|---------|
| Review storage (JSONL) | PASS | Deduplication by platform:review_id verified |
| Review loading with filters | PASS | Platform, date, rating filters all working |
| VADER sentiment analysis | PASS | Compound scores verified against known inputs |
| Sentiment batch analysis | PASS | 50 reviews analyzed, avg_sentiment computed |
| Sentiment trend (6 periods) | PASS | Correct period bucketing and averages |
| Template response (positive) | PASS | Brand voice injected, under 100 words |
| Template response (negative) | PASS | Empathetic tone, resolution offered |
| Template response (neutral) | PASS | Appreciative, highlights strengths |
| LLM response (Gemini) | PASS | Brand vocabulary used, competitor names excluded |
| Reputation score calculation | PASS | Weighted formula, 0-100 scale, grade assigned |
| Reputation snapshot storage | PASS | JSONL append, trend retrieval working |
| QR code generation | PASS | 300x300 PNG, scannable by phone camera |
| Campaign templates (email) | PASS | Brand voice, {customer_name} + {review_link} placeholders |
| Campaign templates (SMS) | PASS | Under 160 chars, includes review link |
| Alert: negative review | PASS | Fires for rating <= 2, includes review text |
| Alert: reputation drop | PASS | Fires on > 5pt decline between snapshots |
| Alert: no response 24h | PASS | Correctly identifies stale unresponded reviews |
| Monthly report generation | PASS | JSON report + 3 chart PNGs generated |
| Score trend chart | PASS | 6-period line chart, 150 DPI PNG |
| Sentiment pie chart | PASS | 3-segment pie with percentages |
| Rating distribution chart | PASS | 5-bar chart with color coding |
| Competitor benchmarking | PASS | Side-by-side rating + sentiment comparison |
| Multi-client isolation | PASS | 3 clients, no data cross-contamination |

## Key Considerations

1. **VADER is the top choice for sentiment** — MIT licensed, handles review-style text with emojis and slang excellently, runs locally with zero API cost. Use TextBlob as a secondary signal for subjectivity scoring.

2. **Google Places API free tier** provides $200/month credit — more than enough for most small businesses. Monitor usage to avoid unexpected charges.

3. **Yelp Fusion API** is generous at 5,000 calls/day but only returns up to 3 review excerpts per business. For full review history, consider Outscraper.

4. **Response generation must use brand voice.** Always load the client's voice profile (tone, formality, vocabulary_include, vocabulary_avoid) before generating any response. Template fallback ensures responses are always available even without LLM access.

5. **Never be defensive in responses.** Negative review responses must lead with empathy, apologize sincerely, offer resolution, and move conversation offline. Never mention competitors.

6. **Response time matters.** Aim to respond to all reviews within 24 hours. The alert system flags reviews exceeding this threshold. Google prioritizes businesses with high response rates.

7. **Review request timing is critical.** Send requests 1-4 hours after the visit (varies by industry). Tuesday-Thursday between 10am-2pm gets the highest response rates.

8. **Reputation score is a composite metric.** Star ratings alone are misleading — volume, recency, response rate, and sentiment all factor in. A 4.2-star business with 500 reviews and 95% response rate scores higher than a 4.8-star business with 10 reviews.

9. **Competitor benchmarking provides context.** A 4.0 rating might be strong if competitors average 3.5. Always present scores relative to the competitive landscape.

10. **Store everything per-client in JSONL.** Flat files are simple, debuggable, and sufficient for small business volumes. Migrate to SQLite only if a single client exceeds 10K reviews.

11. **Alert fatigue prevention.** Only fire high-severity alerts for genuinely bad situations (1-2 star reviews, >5pt score drops). Medium alerts batch into daily digests. Never alert on positive events.

12. **QR codes for physical locations** are the highest-ROI campaign tool. Print them on receipts, table tents, or business cards. Customers who leave via QR within 2 hours of a visit leave the most detailed reviews.
