# CODING-PATTERNS.md — LocalComm/Workers Architecture Patterns
*Last updated: 2026-03-20 | Source: Cloudflare official docs + production patterns*

---

## PATTERN 1: D1 Index-First Schema Design

**Rule:** Every column used in a WHERE clause MUST have an index before shipping.

**LocalComm applies this to:**
- `business_profiles`: index on `slug`, `tier`, `vertical`
- `content_items`: index on `status`, `business_id`, `scheduled_at`
- `reviews`: index on `rating`, `response_status`, `business_id`
- `users`: UNIQUE index on `email`

**SQL pattern:**
```sql
-- Always use IF NOT EXISTS to make migrations idempotent
CREATE INDEX IF NOT EXISTS idx_content_status_biz ON content_items(status, business_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating_status ON reviews(rating, response_status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);
```

**When NOT to index:** Columns with high write volume and rare reads (logs, audit trails).

---

## PATTERN 2: D1 Sessions API for Global Read Scaling

**Rule:** For any multi-user SaaS (LocalComm dashboard), use D1's Sessions API to route reads to geo-local replicas. This cuts latency for reads by 3-10x when users are far from the primary DB region.

**Implementation:**
```typescript
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // Pass bookmark from cookie/header for session continuity
    const bookmark = request.headers.get('x-d1-bookmark') ?? 'first-unconstrained';
    const session = env.DB.withSession(bookmark);
    
    const response = await handleRequest(request, session);
    
    // Return bookmark so next request continues where this one left off
    response.headers.set('x-d1-bookmark', session.getBookmark() ?? '');
    return response;
  }
};
```

**Key insight:** Sessions API gives *sequential consistency* within a user session — reads always see their own writes, even when served by a replica.

---

## PATTERN 3: Workers Config — Always Keep Current

**Rules (from Cloudflare production guidance):**
1. `compatibility_date` = today on new projects; update quarterly on existing
2. Always add `nodejs_compat` flag — avoids runtime import errors for npm packages
3. Run `wrangler types` after every binding change — never hand-write the `Env` interface
4. Secrets via `wrangler secret put` ONLY — never in wrangler.toml or source

**wrangler.jsonc template for LocalComm:**
```jsonc
{
  "name": "localcomm-api",
  "main": "src/index.ts",
  "compatibility_date": "2026-03-20",
  "compatibility_flags": ["nodejs_compat"],
  "vars": {
    "ENVIRONMENT": "production",
    "APP_URL": "https://app.localcomm.co"
  }
  // Secrets (set via wrangler secret put, NOT here):
  // STRIPE_SECRET_KEY, OPENAI_API_KEY, RESEND_API_KEY
}
```

---

## PATTERN 4: D1 Batch Writes for Agent Pipelines

**Rule:** Never write one row per agent action. Batch writes in D1 are critical for throughput — the Workers runtime has a 50ms CPU time limit per request.

**Pattern: batch() for multi-row inserts**
```typescript
// BAD — N round trips
for (const item of contentItems) {
  await env.DB.prepare('INSERT INTO content_items ...').bind(...).run();
}

// GOOD — single round trip
const stmts = contentItems.map(item =>
  env.DB.prepare('INSERT INTO content_items (id, business_id, status, body) VALUES (?, ?, ?, ?)')
    .bind(item.id, item.businessId, item.status, item.body)
);
await env.DB.batch(stmts);
```

**LocalComm use cases:** bulk content scheduling, bulk review import, analytics aggregation writes.

---

## PATTERN 5: JSON Column Pattern for Flexible Agent Metadata

**Rule:** Store agent-generated metadata as JSON in D1 TEXT columns using `json_extract()` for querying. Avoids schema migrations for evolving AI output.

```sql
-- Schema: metadata TEXT (stores JSON blob)
CREATE TABLE content_items (
  id TEXT PRIMARY KEY,
  business_id TEXT NOT NULL,
  status TEXT NOT NULL,
  body TEXT,
  metadata TEXT  -- JSON: { "agent": "content_v2", "score": 0.87, "hashtags": [...] }
);

-- Query into JSON fields without migration
SELECT id, json_extract(metadata, '$.score') as score
FROM content_items
WHERE json_extract(metadata, '$.agent') = 'content_v2'
  AND status = 'qa_passed';
```

**Use for:** AI confidence scores, agent version tracking, generated hashtags, image URLs, variant test data.

---

## PATTERN 6: Next.js 15 + Workers Edge Runtime Split

**Rule:** For LocalComm's Next.js 15 app on Cloudflare Pages + Workers, split compute deliberately:
- **Edge runtime** (`export const runtime = 'edge'`): auth, routing, simple reads — runs in Cloudflare's 300+ PoPs
- **Node.js runtime**: heavy AI processing, PDF generation, complex transforms — runs on Workers with higher limits

**Pattern:**
```typescript
// app/api/dashboard/route.ts — edge: fast reads from D1 replica
export const runtime = 'edge';

export async function GET(request: Request) {
  // Reads from geo-local D1 replica, sub-20ms globally
  const session = env.DB.withSession('first-unconstrained');
  const data = await session.prepare('SELECT ...').all();
  return Response.json(data);
}

// app/api/generate-content/route.ts — Node: AI generation
// (no runtime export = Node.js by default)
export async function POST(request: Request) {
  // CPU-heavy, long-running OK here
}
```

---

## PATTERN 7: D1 Foreign Keys — Enable Explicitly

**Critical gotcha:** D1's SQLite engine has foreign key enforcement DISABLED by default. Must enable per-connection.

```typescript
// In every Worker handler that does writes:
await env.DB.prepare('PRAGMA foreign_keys = ON').run();

// OR in wrangler.toml for D1:
// [[ d1_databases ]]
// database_pragma = { foreign_keys = "ON" }
```

**LocalComm risk:** Without this, orphaned content_items (no business_id match) silently accumulate.

---

## SYNTHESIS — Top 5 Improvements for LocalComm Right Now

1. **Add FK pragma** to all write paths in Cloudflare Workers — prevent data integrity drift
2. **Create missing indexes** on content_items(status, business_id) and reviews(rating, response_status) — current schema does full table scans
3. **Enable D1 read replication + Sessions API** for the dashboard — free global latency reduction
4. **Switch to batch()** for agent bulk writes — content_agent generates 5-10 posts at a time; N round trips is a bug
5. **Adopt JSON metadata column** for AI-generated fields — stop doing schema migrations every time a new model adds an output field

---

## PATTERN 8: Next.js 15 Async Request APIs (Breaking Change)

**Rule:** In Next.js 15, `cookies()`, `headers()`, `params`, and `searchParams` are now async. Always `await` them.

**Why it matters for LocalComm:** Every dashboard page that reads session cookies or route params will break silently in dev and loudly in prod if not updated.

**Pattern:**
```tsx
// WRONG (Next.js 14 style — will warn then break)
export default function DashboardPage({ params }) {
  const { businessId } = params;
  const cookieStore = cookies();
  const token = cookieStore.get('token');
}

// CORRECT (Next.js 15)
export default async function DashboardPage({ params }) {
  const { businessId } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get('token');
}
```

**Migration command:**
```bash
npx @next/codemod@canary next-async-request-api .
```

---

## PATTERN 9: Next.js 15/16 `use cache` Directive — Two-Level Caching

**Rule:** Use `'use cache'` at data-level for shared data, UI-level for full components. Pair with `cacheLife()` for TTL control. Only available with `cacheComponents: true` in next.config.ts.

**Why it matters for LocalComm:** Client dashboard metrics (review counts, content queue depth, analytics) can be cached at the data layer — avoids re-querying D1 on every navigation.

**Pattern:**
```tsx
// next.config.ts
const nextConfig: NextConfig = {
  cacheComponents: true,
}

// Data-level cache (shared across components)
import { cacheLife } from 'next/cache'

export async function getBusinessMetrics(businessId: string) {
  'use cache'
  cacheLife('minutes') // built-in profiles: seconds, minutes, hours, days
  return db.query('SELECT * FROM metrics WHERE business_id = ?', [businessId])
}

// UI-level cache (whole component)
export default async function MetricsSummary({ businessId }: { businessId: string }) {
  'use cache'
  cacheLife('minutes')
  const metrics = await getBusinessMetrics(businessId)
  return <div>{/* render metrics */}</div>
}

// Real-time data: use Suspense + no cache
export default function DashboardPage() {
  return (
    <main>
      <Suspense fallback={<MetricsSkeleton />}>
        <MetricsSummary businessId={id} />  {/* cached */}
      </Suspense>
      <Suspense fallback={<FeedSkeleton />}>
        <LiveReviewFeed />  {/* no cache — always fresh */}
      </Suspense>
    </main>
  )
}
```

**Cache profiles available:** `seconds` (1s), `minutes` (1min), `hours` (1hr), `days` (1day), `weeks` (1wk), `max` (1yr)

---

## PATTERN 10: Partial Prerendering (PPR) — Static Shell + Dynamic Holes

**Rule:** Use PPR to serve a static shell instantly from the edge while streaming dynamic content in parallel. Enable with `experimental.ppr = true`.

**Why it matters for LocalComm:** Dashboard shell (nav, layout, static copy) renders in <100ms from edge; dynamic data (review counts, queue status) streams in without blocking the initial paint.

**Architecture:**
```
User request → Edge CDN returns static shell immediately (0ms wait)
             ↓ (in parallel)
             Server streams dynamic Suspense chunks as they resolve
```

**Pattern:**
```tsx
// next.config.ts
const nextConfig = {
  experimental: {
    ppr: true,
  },
}

// page.tsx — PPR activates automatically at Suspense boundaries
export default function DashboardPage() {
  return (
    <main>
      {/* Static — prerendered at build time, served from edge */}
      <DashboardHeader />
      <SidebarNav />

      {/* Dynamic — Suspense boundary = PPR hole */}
      <Suspense fallback={<ReviewCountSkeleton />}>
        <ReviewCount />   {/* streams from server */}
      </Suspense>

      <Suspense fallback={<ContentQueueSkeleton />}>
        <ContentQueue />  {/* streams from server */}
      </Suspense>
    </main>
  )
}
```

**Key insight:** Suspense boundaries ARE the PPR split point. Static optimization is on-by-default until the component touches cookies/headers/DB.

---

## PATTERN 11: Next.js 15 Caching Defaults (Breaking Change)

**Critical:** In Next.js 15, `fetch` requests, GET Route Handlers, and client navigations are **NO LONGER cached by default**.

**What changed:**
- `fetch()` → `no-store` by default (was `force-cache`)
- GET Route Handlers → not cached by default
- Client navigations → not cached by default

**Action for LocalComm API routes:**
```tsx
// If you WANT caching on a route handler (e.g., industry guide data):
export const dynamic = 'force-static'
export async function GET() {
  const data = await getIndustryGuides()
  return Response.json(data)
}

// If you WANT fetch to cache (e.g., third-party API that rarely changes):
const data = await fetch('https://api.example.com/data', {
  cache: 'force-cache',
  next: { revalidate: 3600 } // revalidate every hour
})

// Default (fresh on every request) — no change needed:
const data = await fetch('https://api.example.com/data')
```

---

## PATTERN 12: `unstable_after` — Post-Response Background Work

**Rule:** Use `unstable_after()` to run non-critical work AFTER the response streams to the user. Ideal for analytics, logging, cache warming.

**Why it matters for LocalComm:** Log analytics events, update "last seen" timestamps, trigger background enrichment — without adding latency to the user-facing response.

**Pattern:**
```tsx
import { unstable_after as after } from 'next/server'

export default async function DashboardPage() {
  after(async () => {
    // Runs AFTER response is sent — doesn't block render
    await logPageView({ page: 'dashboard', businessId })
    await updateLastActiveTimestamp(businessId)
  })

  const metrics = await getMetrics(businessId)
  return <Dashboard metrics={metrics} />
}
```

