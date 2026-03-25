# LocalComm — The Autonomous Marketing Operating System
## $1B Platform Build Plan · March 2026

**One-liner:** LocalComm is the AI CMO for every Main Street business — it knows your business, runs your marketing, and proves the ROI. Fully autonomous. No learning curve. No agency fees.

**North Star:** An SMB owner signs up, completes the Business Intelligence Engine onboarding, and within 24 hours their reviews are being auto-responded to, social posts are going out, and SAGE is surfacing their weekly marketing P&L — all with zero manual effort.

**Exit target:** $76M ARR × 12–15x = $912M–$1.14B. Strategic acquirer (HubSpot, Salesforce, Adobe) premium = **$1.5B–$2B.**

---

## STACK
**Repo:** ~/shellcorp/localcomm/
**Framework:** Next.js 15, Cloudflare Pages + Workers, D1 (SQLite), KV, Tailwind v4
**AI:** OLMx Qwen3-30B at :8080 via audit_api.py at :8030 — NO Anthropic API, local models only
**Dev:** `pnpm dev --port 3030` in ~/shellcorp/localcomm/
**Build check:** `cd ~/shellcorp/localcomm && pnpm build`
**Git:** `git add -A && git commit -m "feat: ..." && git push origin main`

---

## HOW TO RUN EACH BUILD SESSION

1. `cat ~/.openclaw/workspace/LOCALCOMM_STATUS.md` — find FIRST `[ ]` item
2. `cat ~/.openclaw/workspace/LOCALCOMM_BUILD.md` — read full spec for that item
3. Survey existing code: `ls ~/shellcorp/localcomm/src/app/`, `ls src/components/`, `ls src/app/api/`
4. **Read** every file you'll touch BEFORE editing. Never assume what's there.
5. Implement completely — UI + API route + D1 query + types
6. `cd ~/shellcorp/localcomm && pnpm build` — fix ALL errors. Do not commit broken code.
7. `git add -A && git commit -m "feat: ..." && git push origin main 2>/dev/null || true`
8. Update `LOCALCOMM_STATUS.md` — mark done, note blockers

---

## KEY FILES

| File | Purpose |
|------|---------|
| `src/lib/db.ts` | ALL D1 SQL functions here |
| `src/lib/auth.ts` | JWT + KV sessions, getTokenFromRequest(), getSession() |
| `src/lib/openclaw.ts` | OLMx agent client via audit_api.py :8030 |
| `src/app/api/` | All API routes |
| `src/app/dashboard/` | Auth-gated dashboard pages |
| `src/app/(auth)/` | Login + signup |
| `src/app/page.tsx` | Landing page |
| `src/app/onboarding/` | BIE onboarding wizard |
| `src/components/` | Shared UI |
| `src/types/index.ts` | TypeScript types |
| `migrations/0001_schema.sql` | D1 schema |

**Auth pattern (required on every API route):**
```typescript
const token = getTokenFromRequest(req)
if (!token) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
const db = await getDB()
const session = await getSession(db, token)
if (!session) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
```

**D1 pattern:** `.prepare(sql).bind(...params).all()` or `.run()` — NEVER string-concatenate SQL.

---

## THE PRODUCT ARCHITECTURE

### The Six Agents (SAGE coordinates all of them)

| Agent | Role | What It Does |
|-------|------|-------------|
| **SAGE** | Orchestrator / CMO Brain | Holds Business Memory, coordinates agents, makes strategic decisions, generates weekly P&L report |
| **SCOUT** | Intelligence | Monitors competitors, tracks local trends, scrapes review signals, feeds SAGE daily intel |
| **SCRIBE** | Content | Generates on-brand social (7 platforms), email sequences, SMS, Google posts in the business's exact voice |
| **SPROUT** | Growth | Manages Google + Meta paid ads autonomously — allocates budget, tests creatives, kills losers, scales winners |
| **SENTRY** | Reputation | Monitors all review platforms 24/7, generates personalized responses, escalates negatives, runs post-visit review-request campaigns |
| **SIGNAL** | Analytics | Ingests all channel data, tracks attribution, surfaces insights, generates plain-English weekly CMO reports |

### Business Intelligence Engine (BIE)
The moat. A 50-question deep onboarding that builds a living business profile:
- Business basics: name, location, vertical, hours, team size
- Services/menu + pricing (what they sell, price points)
- Customer profile (who buys, avg ticket, repeat rate)
- Brand voice (3 adjectives, sample copy they like/dislike)
- Competitors (who they lose deals to, who they admire)
- Goals (reviews target, revenue goal, biggest pain)
- Seasonality (slow months, busy months, key promotions)
- Marketing history (what's been tried, what worked)

This data feeds every agent. It IS the moat — competitors cannot copy 2 years of accumulated client knowledge.

### Pricing
| Tier | Price | Human Hours | Ad Fee |
|------|-------|-------------|--------|
| Self-Service | $149/mo | 0 hrs (AI only) | — |
| Assisted | $399/mo | 2 hrs (our team) | 12% of ad spend |
| Managed | $997+/mo | 10 hrs (LocalLoop) | 10% of ad spend |

### Vertical Focus
**Restaurants first.** Then: salons/med spas → dental → HVAC → chiropractic.
Vertical depth beats horizontal breadth. POS integrations: Toast, Square, OpenTable, Mindbody, Vagaro.

---

## DATABASE SCHEMA (D1)

Check `migrations/0001_schema.sql` for current tables. Required tables:

```sql
-- Core auth (likely exists)
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT,
  business_name TEXT,
  vertical TEXT,
  city TEXT,
  plan TEXT DEFAULT 'self_service',
  onboarding_completed INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Business Intelligence Engine data (the moat)
CREATE TABLE IF NOT EXISTS business_profiles (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL UNIQUE,
  -- Identity
  business_name TEXT,
  vertical TEXT,
  city TEXT,
  address TEXT,
  website_url TEXT,
  phone TEXT,
  hours_json TEXT,           -- JSON: { mon: "9-5", tue: "9-5", ... }
  -- Products/Services
  services_json TEXT,        -- JSON: [{ name, price, description }]
  avg_ticket_usd INTEGER,
  -- Customers
  customer_profile TEXT,     -- plain text description
  customer_avg_age TEXT,
  -- Brand
  brand_voice_words TEXT,    -- comma-separated adjectives
  brand_sample_good TEXT,    -- example copy they like
  brand_sample_bad TEXT,     -- example copy they dislike
  -- Competition
  competitors_json TEXT,     -- JSON: [{ name, url, notes }]
  -- Goals
  review_target INTEGER,
  monthly_revenue_goal INTEGER,
  biggest_pain TEXT,
  -- Seasonality
  slow_months TEXT,          -- comma-separated month numbers
  busy_months TEXT,
  -- Marketing history
  past_channels TEXT,        -- what they've tried
  what_worked TEXT,
  -- Meta
  bie_score INTEGER DEFAULT 0,  -- 0-100: completeness of profile
  updated_at TEXT DEFAULT (datetime('now')),
  created_at TEXT DEFAULT (datetime('now'))
);

-- Agent memory (SAGE's working memory per client)
CREATE TABLE IF NOT EXISTS agent_memory (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  agent TEXT NOT NULL,        -- sage, scout, scribe, sprout, sentry, signal
  memory_key TEXT NOT NULL,
  memory_value TEXT,
  expires_at TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(user_id, agent, memory_key)
);

-- Connected platforms
CREATE TABLE IF NOT EXISTS connected_accounts (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  platform TEXT NOT NULL,    -- google, facebook, instagram, x, email, sms
  account_id TEXT,
  account_name TEXT,
  access_token TEXT,
  refresh_token TEXT,
  token_expires_at TEXT,
  metadata TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Reviews (SENTRY manages these)
CREATE TABLE IF NOT EXISTS reviews (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  external_id TEXT,
  reviewer_name TEXT,
  rating INTEGER,
  body TEXT,
  response TEXT,
  ai_draft TEXT,
  responded_at TEXT,
  published_at TEXT,
  sentiment TEXT,            -- positive, neutral, negative
  escalated INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(platform, external_id)
);

-- Social posts (SCRIBE generates, SPROUT distributes)
CREATE TABLE IF NOT EXISTS social_posts (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  agent TEXT DEFAULT 'scribe', -- which agent generated it
  platforms TEXT NOT NULL,   -- JSON array: ["facebook","instagram"]
  content TEXT NOT NULL,
  media_urls TEXT,           -- JSON array of R2 URLs
  scheduled_at TEXT,
  published_at TEXT,
  status TEXT DEFAULT 'draft', -- draft, scheduled, published, failed
  platform_results TEXT,     -- JSON: { facebook: { post_id, reach }, ... }
  created_at TEXT DEFAULT (datetime('now'))
);

-- Monitored sites (SIGNAL tracks these)
CREATE TABLE IF NOT EXISTS monitored_sites (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  url TEXT NOT NULL,
  name TEXT,
  last_checked_at TEXT,
  last_status INTEGER,
  last_response_ms INTEGER,
  seo_data TEXT,             -- JSON from audit_api
  audit_data TEXT,           -- JSON from audit_api
  created_at TEXT DEFAULT (datetime('now'))
);

-- Site incidents
CREATE TABLE IF NOT EXISTS site_incidents (
  id TEXT PRIMARY KEY,
  site_id TEXT NOT NULL,
  type TEXT NOT NULL,
  message TEXT,
  started_at TEXT,
  resolved_at TEXT
);

-- Ad campaigns (SPROUT manages these)
CREATE TABLE IF NOT EXISTS ad_campaigns (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  platform TEXT NOT NULL,    -- google, meta
  campaign_name TEXT,
  budget_usd INTEGER,        -- monthly budget
  status TEXT DEFAULT 'draft', -- draft, active, paused, ended
  external_campaign_id TEXT,
  performance_json TEXT,     -- JSON: { spend, clicks, leads, revenue }
  created_at TEXT DEFAULT (datetime('now'))
);

-- Weekly CMO reports (SIGNAL generates)
CREATE TABLE IF NOT EXISTS cmo_reports (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  week_start TEXT NOT NULL,
  report_json TEXT,          -- Full structured report
  summary TEXT,              -- Plain-English executive summary
  delivered_at TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- AI agent conversation history
CREATE TABLE IF NOT EXISTS agent_messages (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL,        -- user, assistant, system
  content TEXT,
  agent TEXT DEFAULT 'sage', -- which agent responded
  created_at TEXT DEFAULT (datetime('now'))
);
```

---

## 24-WEEK BUILD ROADMAP

### Phase 1 — Auth Shell ✅ DONE
- [x] D1 schema
- [x] Login / signup / logout / me API routes
- [x] JWT + KV sessions
- [x] Dashboard layout with auth guard + Sidebar

---

### Phase 2 — Business Intelligence Engine (Weeks 1–4)
**Goal:** Deep 50-question onboarding that builds SAGE's brain. This IS the moat.

- [ ] **Landing page** (`src/app/page.tsx`)
  - Hero: "Your AI CMO. Zero learning curve." + "Get started free →" (→ /signup)
  - Sub-headline: "LocalComm knows your business and runs your marketing — content, reviews, ads — every day, automatically."
  - How it works: 3 steps — 1. Tell us about your business (15 min) 2. Watch your AI CMO go to work 3. Get your weekly performance report
  - Agent roster display: 6 agent cards (SAGE, SCOUT, SCRIBE, SPROUT, SENTRY, SIGNAL) with icons and one-line descriptions
  - Pricing table: Self-Service $149 / Assisted $399 / Managed $997
  - "Trusted by local businesses across CT, NY, NJ" + vertical icons
  - Footer: localcomm.ai | © 2026 LocalLoop | Privacy | Terms
  - Style: dark navy + electric blue + white. Clean, confident, premium. Mobile-first. Looks like Notion or Linear.

- [ ] **BIE Onboarding wizard** (`src/app/onboarding/page.tsx`)
  Multi-step form. Progress bar at top showing % complete.

  **Section 1 — Your Business (8 questions)**
  - Business name
  - City/town
  - Vertical (dropdown: Restaurant, Salon/Spa, Medical/Dental, HVAC, Gym/Fitness, Retail, Other)
  - Website URL
  - Phone number
  - Hours (Mon–Sun, open/closed toggle + time pickers)
  - How long in business (dropdown)
  - Team size (1, 2-5, 6-20, 20+)

  **Section 2 — What You Sell (6 questions)**
  - Describe your main services/menu items (textarea)
  - Average ticket / transaction value ($)
  - Best-selling item or service
  - What makes you different from competitors (textarea)
  - Do you offer booking/reservations? (yes/no → URL if yes)
  - Seasonal specials or promotions? (textarea)

  **Section 3 — Your Customers (5 questions)**
  - Describe your typical customer (textarea)
  - Avg customer age range (dropdown)
  - How do most customers find you? (checkboxes: Google, Word of mouth, Social, Walk-by, Other)
  - What do happy customers say? (textarea)
  - What do unhappy customers complain about? (textarea)

  **Section 4 — Competition (5 questions)**
  - Name your top 3 competitors (3 text inputs)
  - Who do you most want to beat and why? (textarea)
  - What does your best competitor do better than you right now? (textarea)
  - Their Google rating if you know it (number input)
  - Their review count if you know it (number input)

  **Section 5 — Brand Voice (6 questions)**
  - 3 words that describe your brand vibe (3 text inputs: e.g., "Friendly, Local, Reliable")
  - Paste an example of marketing copy you LIKE (textarea)
  - Paste an example of marketing copy you DISLIKE (textarea)
  - Tone preference: Professional / Casual / Playful / Bold (radio)
  - Do you use humor in your marketing? (yes / sometimes / never)
  - Any words or phrases to NEVER use? (textarea)

  **Section 6 — Goals (6 questions)**
  - Biggest marketing pain right now (dropdown: Not enough reviews, No time for social, Losing to competitors, Poor website, No ad ROI, Other)
  - Google review target (what count would feel amazing?)
  - Monthly revenue goal ($)
  - Which channels have you tried? (checkboxes: Google Ads, Meta Ads, Email, Social posting, SEO, None)
  - What's worked best in the past? (textarea)
  - Monthly marketing budget you're comfortable with ($, including ad spend)

  **Section 7 — Digital Audit (automated)**
  - "Now we're going to analyze your digital presence..." animated scan
  - POST /api/onboarding/audit (calls audit_api.py at :8030)
  - Show findings: SEO score gauge, top issues, competitor gap, AI audit finding
  - Error fallback: "Audit service is warming up — we'll run it in the background and email you results"

  **Section 8 — Connect Accounts**
  - Google Business Profile (Connect button — disabled "Coming in Phase 4" tooltip)
  - Facebook Page (disabled)
  - Instagram (disabled)
  - "Skip for now" link → goes to dashboard
  - Note: "We'll remind you to connect these. The AI can start working with just your business profile."

  **On complete:** POST /api/onboarding/complete → saves everything → redirect /dashboard

- [ ] **POST /api/onboarding/save-section** route
  - Auth required
  - Body: `{ section: 1-8, data: { ...fields } }`
  - Upserts into `business_profiles` table (creates if not exists)
  - Returns `{ bie_score }` (calculate % of fields filled)
  - Called after each section so progress is saved in real-time

- [ ] **POST /api/onboarding/audit** route
  - Auth required
  - Calls `http://127.0.0.1:8030/audit` with business data
  - Saves to `monitored_sites`
  - Returns audit data or error gracefully

- [ ] **POST /api/onboarding/complete** route
  - Auth required
  - Sets `users.onboarding_completed = 1`
  - Triggers SAGE to generate initial strategy (POST to audit_api.py /agent with business profile as context)
  - Saves initial SAGE message to `agent_messages`
  - Returns `{ redirect: '/dashboard' }`

---

### Phase 3 — Dashboard Home + SENTRY (Weeks 5–8)
**Goal:** Owner logs in, sees what SAGE is doing, approves or edits. Reputation managed automatically.

- [ ] **Dashboard home** (`src/app/dashboard/page.tsx`)
  - Header: "Good morning, [business_name]. Here's your marketing status."
  - **SAGE Brief** widget (top, full width): Latest SAGE insight/recommendation — fetched from last agent_message where role='assistant'. Dark card, prominent.
  - 4 status cards in 2×2 grid:
    1. **Reviews** — avg rating (stars), unanswered count (red if >0), link to /dashboard/reputation
    2. **Social** — posts this week, last published, link to /dashboard/social
    3. **Website** — UP/DOWN badge, response_ms, SEO score, link to /dashboard/website
    4. **Campaigns** — active ad campaigns count, total spend this month, link to /dashboard/campaigns (placeholder)
  - Quick action bar: "Ask SAGE" input (routes to /dashboard/sage)
  - Client component with useEffect + 60s polling from GET /api/dashboard

- [ ] **GET /api/dashboard** route
  - Auth required
  - Returns: `{ sage_brief, reviews: { count, unanswered, avg_rating }, social: { scheduled_week, last_post }, site: { status, response_ms, seo_score }, campaigns: { active, spend_mtd } }`

- [ ] **SENTRY reputation page** (`src/app/dashboard/reputation/page.tsx`)
  - Filter tabs: All / Unanswered / Responded / Negative (escalated)
  - Review list using ReviewCard component
  - "Auto-respond all" button → calls POST /api/reviews/auto-respond-all → SCRIBE generates drafts for all unanswered
  - Stats bar: avg rating, total count, response rate %, avg response time

- [ ] **ReviewCard component** (`src/components/ReviewCard.tsx`)
  - Platform badge (Google=blue, FB=navy, Yelp=red, TripAdvisor=green)
  - Star rating display (filled/empty)
  - Reviewer name + date + review body
  - If `ai_draft` + no `response`: editable textarea pre-filled with draft + "Publish Response" + "Regenerate" buttons
  - If `response`: shows published response + "Edit" option
  - Negative reviews: red border + "Escalated" badge
  - "Publish Response" → PATCH /api/reviews → optimistic update

- [ ] **GET /api/reviews** route (if not exists)
  - Auth required
  - Query params: `?filter=all|unanswered|responded|negative&limit=50`

- [ ] **PATCH /api/reviews** route (if not exists)
  - Auth required
  - Body: `{ id, response }` → updates `responded_at`, sets response

- [ ] **POST /api/reviews/auto-respond-all** route
  - Auth required
  - Gets all unanswered reviews for user
  - For each: calls audit_api.py /agent with prompt "Write a review response for this [rating]-star review from [reviewer] that says: [body]. Business context: [BIE brand_voice_words, business_name, vertical]"
  - Saves ai_draft to each review
  - Returns count of drafts generated

---

### Phase 4 — SCRIBE Social Hub (Weeks 5–8, parallel with SENTRY)
**Goal:** Content calendar filled automatically. Owner approves, SCRIBE posts.

- [ ] **PostComposer component** (`src/components/PostComposer.tsx`)
  - Platform toggles with icons: Facebook, Instagram, X, Google Posts, TikTok (checkboxes)
  - Textarea with char counter per platform (Instagram=2200, X=280, Facebook=63K)
  - "Write it for me" → POST /api/agent with "Draft a [vertical] social post for [business_name] in [city] about [topic]. Brand voice: [brand_voice_words]. Keep it under [charLimit] chars." → streams into textarea
  - Topic suggestions dropdown: "Today's special", "Customer spotlight", "Tip of the week", "Seasonal promotion", "Behind the scenes"
  - "Schedule for" date/time picker (default: next business day 9am)
  - "Add to queue" button → POST /api/social/posts

- [ ] **ContentCalendar component** (`src/components/ContentCalendar.tsx`)
  - Week view grid Mon–Sun
  - Platform-colored blocks: FB=blue, IG=pink/purple, X=black, Google=green, TikTok=teal
  - Click block → side panel with full content + status + edit option
  - "< Prev" / "Next >" navigation
  - Today column highlighted
  - Empty slots: "+ Add post" ghost button

- [ ] **Social page** (`src/app/dashboard/social/page.tsx`)
  - "Generate month of content" button → POST /api/social/generate-month → SCRIBE creates 30 days of posts
  - PostComposer at top
  - ContentCalendar below
  - "Queued" section: posts approved but not yet scheduled

- [ ] **POST /api/social/posts** — save draft/scheduled post
- [ ] **GET /api/social/posts?week=YYYY-WW** — get week's posts
- [ ] **POST /api/social/generate-month** route
  - Auth required
  - Generates 30 days of post drafts using SCRIBE (calls /agent endpoint for each)
  - Uses business profile for context (vertical, brand_voice, services, city)
  - Distributes across platforms: 3x/week Facebook, 5x/week Instagram, 2x/week Google Posts
  - Saves all as `status='draft'` social_posts
  - Returns count generated

---

### Phase 5 — SIGNAL Website Monitor (Weeks 9–12)
**Goal:** SIGNAL watches the site. Owner always knows status and top SEO fixes.

- [ ] **SiteStatus component** (`src/components/SiteStatus.tsx`)
  - Site URL + favicon
  - Status badge: UP (green) / DOWN (red) + last checked time
  - Response time ms (green <500, yellow <2000, red >2000)
  - SEO score gauge 0-100 (from audit_data)
  - Website quality score gauge
  - Top 3 issues from audit_data.marketing_issues
  - "Check now" button → POST /api/website/monitor?id=SITE_ID

- [ ] **Website page** (`src/app/dashboard/website/page.tsx`)
  - SiteStatus top
  - "Your SEO Action Plan" — numbered list of fixes from audit_data (ranked by impact)
  - Incident history table: last 30 days (date, type, downtime duration)
  - Plugin snippet: `<script src="https://localcomm.ai/plugin.js?id=SITE_ID"></script>` with copy button

- [ ] **POST /api/website/monitor** — runs HTTP check, updates monitored_sites
- [ ] **GET /api/website/plugin** — returns JS beacon script (public, no auth)

---

### Phase 6 — SAGE Chat Interface (Weeks 9–12)
**Goal:** Owner types anything. SAGE responds with specific, actionable answers using BIE context.

- [ ] **AgentChat component** (`src/components/AgentChat.tsx`)
  - Message list (user right-blue, SAGE left-gray with "SAGE" label)
  - Input textarea at bottom + Send (Enter sends, Shift+Enter newlines)
  - Loading: animated pulse dots
  - Load history from GET /api/agent on mount
  - "Suggested questions" chips for new users (no history):
    - "What should I focus on this week?"
    - "Write a review response for my latest review"
    - "Create 5 social posts for this month"
    - "How do I beat [top competitor] on Google?"

- [ ] **SAGE page** (`src/app/dashboard/sage/page.tsx`)
  - Full-height AgentChat
  - "SAGE — Your AI CMO" header
  - Context bar: shows current BIE completeness score + quick links to fill gaps

- [ ] **Agent API route enhancement** (`src/app/api/agent/route.ts`)
  - Pull BIE data from business_profiles table and inject into SAGE context
  - Context should include: business_name, vertical, city, brand_voice_words, competitors, avg_rating, review_count, services, biggest_pain, goals, connected_platforms

---

### Phase 7 — Weekly CMO Report (SIGNAL, Weeks 13–16)
**Goal:** Every Monday morning, owner gets their marketing P&L by SMS/Telegram.

- [ ] **CMO Report generator** (`src/app/api/reports/weekly/route.ts`)
  - POST (internal/cron) — generates weekly report for a user
  - Pulls: reviews responded, social posts published, site status, agent conversations
  - Calls /agent: "Generate a plain-English weekly CMO report for [business_name]. Here's the week's data: [data]. Include: what was done, what worked, what needs attention next week. Under 200 words."
  - Saves to cmo_reports table
  - Sends via Telegram (bot token: 8456903894:AAF_1xCFIzErqZo_tIBIYoYxFzWzri5lqIM) if user has chat_id configured

- [ ] **Reports page** (`src/app/dashboard/reports/page.tsx`)
  - List of weekly reports (most recent first)
  - Click → full report view
  - Summary cards: reviews responded this week, posts published, site uptime %, SAGE interactions

---

### Phase 8 — Polish + Deploy (Weeks 13–16)
**Goal:** Live at localcomm.ai. Zero downtime. CI/CD from GitHub.

- [ ] `metadata` on all page files (title, description)
- [ ] `public/robots.txt` + `public/sitemap.xml`
- [ ] `loading.tsx` skeleton screens for dashboard pages (use Tailwind animate-pulse)
- [ ] `error.tsx` friendly error boundaries
- [ ] Mobile audit: test at 375px, fix overflow/layout issues
- [ ] GitHub push + Cloudflare Pages CI/CD setup instructions in STATUS.md
- [ ] `wrangler d1 migrations apply localcomm --remote` for prod D1
- [ ] Smoke test script: signup → BIE → audit → dashboard → SAGE chat → social post → site check

---

### Phase 9 — Monetization (Weeks 17–20)
**Goal:** First paying customer. Revenue locked in before further scaling.

- [ ] **Stripe integration**
  - POST /api/billing/checkout — Stripe checkout session for plan selection
  - POST /api/billing/webhook — payment success → update users.plan
  - Plan gating: 14-day free trial, then paywall for Assisted/Managed features

- [ ] **Trial countdown** — dashboard banner "X days left in your free trial" + upgrade CTA

- [ ] **Email notifications** (Resend)
  - Welcome email: "Your AI CMO is setting up your marketing profile..."
  - "SAGE found 3 unanswered reviews" daily digest
  - Weekly CMO report email (HTML, branded)

- [ ] **Referral system**
  - /r/[userId] referral link
  - Successful referral = 1 free month both users
  - referrals table in D1

---

### Phase 10 — Agency White-Label (Weeks 21–24)
**Goal:** 10 agencies × 20 clients each = 200 locations = $20K+ MRR instantly.

- [ ] **Agency accounts**
  - agencies table: id, owner_user_id, name, logo_url, custom_domain, branding_json
  - Agency dashboard: list all client accounts with health scores
  - Bulk actions: "Generate content for all clients this week"

- [ ] **White-label reports**
  - GET /api/reports/monthly?client_id=X → PDF with agency branding
  - Agency logo + colors in report header

- [ ] **Client management portal**
  - Agency can onboard new clients (invite via email)
  - Sub-accounts linked to agency
  - Usage + billing rollup

---

## CODING RULES (non-negotiable)

1. **Read files before editing** — never assume what exists
2. **`pnpm build` after every change** — zero TypeScript errors before commit
3. **No console.log** — proper error handling only
4. **Parameterized D1 queries** — never concatenate SQL
5. **Auth on every API route** — use pattern above
6. **Tailwind v4** — utility classes only, no inline styles
7. **No better-sqlite3** — D1 only, edge compatible
8. **No Anthropic API** — OLMx at :8080 via audit_api.py /agent only
9. **Small commits** — one feature per commit, clear message
10. **Think $1B** — every UI decision: would BirdEye or Yext clients pay for this?

---

## COMPETITIVE MOAT SUMMARY

| Moat Layer | Description | Why Hard to Copy |
|------------|-------------|-----------------|
| Business Memory | 50-question BIE builds proprietary client knowledge graph | 2+ years of data = switching cost too high |
| Vertical Flywheel | 100 restaurant clients → agent 10x better for restaurants | Requires real operational data at scale |
| Agency R&D | LocalLoop validates, trains, generates case studies | Competitors can't replicate without an agency arm |
| POS Network | Toast/Square/OpenTable integrations = real transaction data | Partnership deals + technical integrations |
| Autonomy Score | How much the AI does vs. human — we win on automation depth | Requires multi-agent architecture, not just prompts |
