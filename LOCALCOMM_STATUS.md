[x] 1.1.1 BIE data model & API endpoint
[next] 1.1.3 AI context engine integration
[x] 1.1.2 UI component for BIE dashboard
[ ] 1.1.4 analytics reporting module

BLOCKERS:
- Need to create src/app/api/bie.ts with POST endpoint
- Need to add BIE schema to db.ts (skipped due to token error)
- Need to create migration for business_profiles

---

## STRATEGY INSIGHTS
*Last updated: 2026-03-19*

### SaaS Growth to $1M ARR — LocalComm Playbook

#### The Three Stages of Local SaaS Growth

**Stage 1: Proof (0 → $10K MRR)**
- Concierge everything. Don't automate. Prove the value manually first.
- Target ONE vertical deeply (home services / plumbers / HVAC) — be the obvious choice there.
- Metrics that matter: activation rate (did they publish content in first 7 days?), not signups.
- The BIE (Business Intelligence Engine) is the wedge — if it surfaces insights they can't get elsewhere, they stay.

**Stage 2: Scale (10K → $50K MRR)**
- Automate the concierge. Build playbooks from what worked manually.
- Introduce tiered pricing based on # of locations or AI actions taken (usage-based unlocks).
- Add referral incentive: "Get 1 free month per business you refer" — SMB word-of-mouth is underrated.
- LocalClaw guides (206 industry playbooks) become the differentiation engine here.

**Stage 3: Velocity ($50K → $83K MRR = $1M ARR)**
- Shift acquisition to inbound via SEO + case studies. Each client = a case study.
- Build vertical landing pages: "AI marketing for Stamford plumbers", "AI reviews for CT restaurants"
- Bundle: Reviews + Social + SEO + Ads in one platform. Price anchoring on agencies ($3K+/mo) makes $397 look cheap.

#### Pricing Psychology for SMBs
- SMBs buy on ROI, not features. Frame as "replaces $2K/mo marketing agency for $397."
- Annual plan with 2 months free reduces churn dramatically — push this hard at close.
- Free trial kills LTV in SMB segment — use "done-for-you setup" instead (white-glove feels premium, locks them in).

#### Churn Prevention (the $1M ARR killer)
- Biggest SMB churn trigger: "I don't see results." → Automated monthly ROI report is non-negotiable.
- Second trigger: "Too complicated." → The BIE dashboard must surface ONE actionable insight per login, not ten.
- Third trigger: ghosting after month 2 → Add a 45-day check-in automation (email + Telegram nudge to OpenClaw).

#### Competitive Positioning
- Vendasta / Birdeye / Yext target agencies — LocalComm targets the business directly. Own that lane.
- Key differentiator: AI that works autonomously (not just a dashboard). "Set it and it runs."
- Content marketing moat: publish "LocalComm vs. hiring a marketing person" comparison landing page.

#### Immediate Actions (Next 30 Days)
1. Ship BIE with a "Your #1 Marketing Priority This Week" widget — one insight, one CTA.
2. Build the monthly ROI email report (pulls from analytics agent, sends automatically).
3. Create a Stamford plumbers landing page + run Google Ads at $300/mo to test CPL.
4. Close Prisco Appliance on annual plan before month 1 ends — lock in the retention.
5. Add referral ask to onboarding flow: "Know another Stamford business? Send them this."

---

## COMPETITIVE INTELLIGENCE
*Last updated: 2026-03-21*

### The Landscape — Who We're Fighting (and Who We're Not)

#### Vendasta (Agency-Reseller Model)
- **Business model:** Sells to agencies/partners who resell to SMBs. NOT direct-to-SMB.
- **Pricing:** Minimum spend tiers ($30-$65/seat/month), 1-20+ SMB client buckets. Complicated.
- **Positioning:** "AI Workforce packages" — Conversations AI, Reputation AI. Enterprise-flavored.
- **Weakness:** SMBs never interact with Vendasta directly. Zero brand affinity. Partners are the bottleneck.
- **Our angle:** We ARE the agency AND the SaaS. No middleman. Faster decisions, personal relationships.

#### Birdeye ("Service-as-a-Software")
- **Business model:** Direct to multi-location brands/enterprises. Reviews + Social + Analytics unified.
- **Pricing:** Not public. Estimated $300-$800/mo per location. Enterprise sales cycle.
- **Positioning:** "Agentic AI" that runs marketing workflows automatically. Smart framing.
- **Weakness:** Built for multi-location chains (dental groups, franchises). Overkill for single-location SMBs. Long sales cycle kills SMB deal velocity.
- **Our angle:** We're purpose-built for single-location Stamford businesses. Faster to value, cheaper, personal.

#### Podium / Yext
- Podium: Messaging/reviews focus, $289-$499/mo. Weak on content generation.
- Yext: Listings management, $199-$449/mo. No AI execution — just data syndication.
- Both require the SMB to do the work. We do it for them.

### The Positioning Triangle

```
                    ENTERPRISE
                   Birdeye/Yext
                       △
                      / \
         AGENCY      /   \    DIRECT-TO-SMB
         Vendasta   /     \   LocalComm ← WE ARE HERE
                   /       \
                  ▽_________▽
              COMPLEX            SIMPLE
```

**Our lane:** Direct-to-SMB, simple pricing, fully autonomous execution.
No sales call needed for $149. Done-for-you at $397. Hands-off at $997.

### Pricing Moat vs. Competitors
| Competitor | SMB Cost | Who Does the Work? |
|-----------|---------|-------------------|
| Vendasta (via agency) | $500-2000/mo | Agency (us, but with overhead) |
| Birdeye | $300-800/location | SMB still has to log in |
| Podium | $289-499/mo | SMB manages conversations |
| Traditional agency | $1500-3000/mo | Humans (slow, expensive) |
| **LocalComm Managed** | **$997/mo** | **AI (fully autonomous)** |

**The pitch:** "The AI does what a $3K/mo agency does. We charge $997. You don't manage it."

### 3 Immediate Strategic Moves (From Competitive Gap Analysis)

1. **OWN "DONE-FOR-YOU" POSITIONING** — Birdeye and Podium require SMB effort. Our entire pitch is zero SMB effort. Make this explicit on every surface: website, outreach, onboarding.

2. **UNDERCUT ON ENTRY, UPSELL ON OUTCOMES** — $149 Self-Service is cheaper than any competitor. Get them in, show wins, upsell to $997. Competitors don't have a low-friction entry point.

3. **GEOGRAPHIC MOAT** — Neither Birdeye nor Vendasta will do a personalized Stamford-specific campaign. We know local competitors, local directories, local newspapers. Build the "Stamford Specialist" brand before anyone else does.

---

## GROWTH LOOPS ARCHITECTURE
*Last updated: 2026-03-21*

### The Difference: Funnels vs. Loops

**Funnel thinking** (what most agencies do):
```
Paid Ad → Landing Page → Trial → Convert → Done
```
Every new customer requires new spend. CAC never improves. Linear ceiling.

**Loop thinking** (what compounds to $1M ARR):
```
Customer value → triggers referral/SEO/review → generates new customer → repeat
```
Each customer makes acquisition of the NEXT customer cheaper. Compounding curve.

### LocalComm's 4 Core Growth Loops

---

#### LOOP 1: THE REVIEW FLYWHEEL (Fastest to activate)
```
We manage reviews → client gets more 5-star reviews → 
Google ranking improves → more Google traffic → 
business gets more customers → owner is happy → 
owner refers us → new client → repeat
```
**Mechanism:** Review management (already in platform) drives organic growth for the SMB.
Their growth = our retention = their referral of us.

**Trigger point:** Client hits 4.5+ star average + 20% traffic increase → AUTOMATED referral ask fires.
**Implementation:** Add to review_monitor agent: track star average trajectory. When 4.5+ sustained 30 days → trigger referral email sequence.

---

#### LOOP 2: THE CONTENT AUTHORITY LOOP (SEO compounding)
```
We publish hyper-local content → Google indexes it → 
"Stamford plumber reviews" ranks → SMB owner finds us →
Signs up → we publish MORE content for them → 
their SEO improves → they refer us → repeat
```
**Mechanism:** Every client's LocalComm content output becomes a LocalComm acquisition channel.
"Powered by LocalComm" footer on published content = distributed SEO signal.

**Trigger point:** After 90 days of content publishing, client's organic traffic data → build case study → publish as landing page.
**Implementation:** social_publisher agent adds subtle "Published with LocalComm AI" attribution (client-approved). Build 3 vertical landing pages from first 3 client case studies.

---

#### LOOP 3: THE VERTICAL SATURATION LOOP (Defensible moat)
```
Sign 1 plumber in Stamford → build deep plumber playbook →
outreach to ALL Stamford plumbers with "we work with [CompetitorName]" social proof →
sign 2nd plumber → social proof increases → 
full vertical saturation → own the vertical → repeat in next vertical
```
**Mechanism:** Being "the agency for Stamford plumbers" makes every subsequent plumber outreach 3x easier.
First client = case study. Third client = category authority.

**Trigger point:** 2 clients in same vertical → vertical landing page goes live → outreach to all remaining vertical members references category authority.
**Implementation:** Track verticals in agency_state.db. Auto-trigger vertical saturation campaign when count ≥ 2.

---

#### LOOP 4: THE RESULTS PROOF LOOP (Upsell + expansion)
```
Client on $149 Self-Service → monthly ROI report shows wins →
upgrade conversation → moves to $397 Assisted →
ROI report shows bigger wins → upgrade to $997 Managed →
becomes champion → refers two $149 clients →
those clients upgrade → MRR compounds
```
**Mechanism:** The automated monthly ROI report IS the sales call. No human needed.
Each tier upgrade is triggered by measurable outcomes, not a sales rep.

**Trigger point:** Client on lower tier with ROI metrics exceeding tier's value → automated upgrade nudge email fires.
**Implementation:** analytics agent generates ROI score monthly. If ROI > 3x tier price → send "You've outgrown Self-Service" email with one-click upgrade link.

---

### Loop Activation Priority (WSJF Order)

| Loop | Speed | Leverage | Blocks Others? | Priority |
|------|-------|----------|----------------|----------|
| Review Flywheel | Fast (30 days) | Medium | No | 2 |
| Results Proof Loop | Medium (60 days) | HIGH | Yes (upsell revenue) | 1 |
| Vertical Saturation | Medium (90 days) | HIGH | Blocks moat building | 3 |
| Content Authority | Slow (6 months) | Very High | No | 4 |

**Activate RESULTS PROOF LOOP first** — it compounds existing clients (zero acquisition cost) AND unblocks expansion revenue.

### Implementation Checklist (Next 14 Days)

- [ ] Build monthly ROI report template (pulls: review count, star avg delta, social post count, traffic estimate)
- [ ] Add ROI score calculation to analytics agent: score = (results delivered / tier price) × 10
- [ ] Build upgrade trigger email: fires when ROI score > 30 on $149 tier, > 25 on $397 tier
- [ ] Add referral trigger to review_monitor: fires when client hits 4.5+ stars sustained 30 days
- [ ] Add vertical tracking query to agency_state.db: `SELECT vertical, COUNT(*) FROM brand_profiles GROUP BY vertical HAVING COUNT(*) >= 2`

