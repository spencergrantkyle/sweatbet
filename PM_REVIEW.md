# SweatBet Product Manager Review

**Date:** 2026-03-06
**Reviewer:** Senior Product Manager
**Build:** Phase 1 (Post-QA Audit)
**Branch:** `claude/build-sweatbet-platform-bR6id`

---

## 1. CORE VALUE PROPOSITION DELIVERY

### Promise: "Bet on your fitness goal, get verified automatically"

**Rating: 62/100 - The verification engine works, but the money side is entirely simulated.**

### Full User Journey Walkthrough

| Step | What Happens | Quality | Friction |
|------|-------------|---------|----------|
| 1. Landing Page | User sees hero section with "Put Money on Your Fitness Goals", R50K+ stats, "How It Works" steps, bet type cards (Solo, 1v1 Coming Soon, Group Coming Soon). Clear CTA: "Connect with Strava" | Good | Stats (87% completion, R50K+) are hardcoded marketing claims with no backing data. Minor trust issue if users investigate. |
| 2. Strava OAuth | Click CTA -> redirects to Strava authorization page. CSRF state token generated. Scopes: `activity:read_all,read` | Good | No email/password alternative. If user doesn't have Strava, journey ends here with no explanation. |
| 3. OAuth Callback | Code exchanged for tokens, user created in DB (or updated if returning), session set, redirect to dashboard | Good | If Strava returns error, user sees landing page with URL param `?error=access_denied` displayed at bottom. Easy to miss. |
| 4. Dashboard | User sees their name + avatar, recent Strava activities (live from API), active bets sidebar, stats bar (total/won/active/win rate), CTA to create bet | Good | Dashboard makes a **live Strava API call on every page load** to fetch 10 recent activities. No caching. Slow on high latency connections. If Strava is down, activities section silently shows "No recent activities found" with no explanation. |
| 5. Create Bet | Form with title, description, activity type dropdown (Run/Ride/Walk/Hike/Swim/Workout), distance km, time limit minutes, deadline picker (default 7 days), wager amount (default R50, max R10,000), stake recipient (SweatBet/charity/friend) | Good | **No check for Strava connection.** User can disconnect Strava in settings, then create a bet that can never be verified. The bet will silently expire as LOST. |
| 6. Bet Active | Bet created with status=ACTIVE immediately. User redirected to bet detail page with countdown timer, requirements grid, stakes info, cancel button | Good | No confirmation step. User clicks "Create Bet" and it's immediately active. For a product involving money, this feels too quick. |
| 7. Activity Verification (webhook) | Strava sends webhook on activity create -> background task fetches activity details -> validates type/distance/time/deadline -> marks bet as WON if qualifying | Excellent | This is the core value prop and it works well. The dual verification path (webhook + 5-min scheduler poll) provides redundancy. |
| 8. Activity Verification (scheduler) | Every 5 minutes, checks all users with active bets -> fetches recent activities (24h lookback) -> validates against bets -> deduplicates via ProcessedActivity table | Good | 5-minute delay maximum for scheduler path. Webhook path is near-instant. |
| 9. Bet Won | Bet status updated to WON, verified_at timestamp set, Telegram notification sent to admin | Partial | **User has no notification channel.** Telegram notifications only go to the admin chat. The user has to visit the dashboard or bet detail page to discover they won. No email, no push notification, no in-app toast. |
| 10. Bet Lost (Deadline) | Scheduler checks every 5 minutes -> marks expired bets as LOST -> Telegram notification to admin | Partial | Same problem: user only discovers their bet is lost when they visit the app. No user-facing notification. |
| 11. Payment | **DOES NOT EXIST** | Missing | The wager amount is recorded but there is no payment integration. Users "bet" R50 but no money actually changes hands. The entire financial side is a placeholder. |

### Where the Journey Breaks

1. **No payment rails** - The core "put money on it" promise is unfulfilled. Wager amounts are stored in the DB but never collected or disbursed.
2. **No user notifications** - Telegram goes to admin only. Users discover outcomes by manually checking the app.
3. **No Strava connection check at bet creation** - Users can create unverifiable bets.
4. **Landing page to first bet is ~6 clicks** but feels smooth once Strava is connected.
5. **No onboarding flow** - After OAuth, user lands on dashboard with no guidance on what to do next.

---

## 2. MVP FEATURE AUDIT

| Feature | Status | Notes |
|---------|--------|-------|
| User registration (email + social) | ⚠️ Partial | **Strava OAuth only.** No email/password, no Google. Users without Strava cannot register at all. This was a deliberate design choice (Strava-only auth), but limits TAM significantly. |
| Strava OAuth account linking | ✅ Complete | Well-implemented: CSRF state tokens, returning user handling (update not duplicate), token refresh with 5-min buffer. Code exchange, session management, and logout all work. |
| Individual bet creation (title, activity type, distance, deadline, wager) | ✅ Complete | Full form with all fields. Validates deadline (must be future), activity type (enum), distance (optional), time limit (optional), wager (min R0, max R10K in form). Also includes stake recipient selector and description. |
| Bet dashboard with active/completed/failed bets | ⚠️ Partial | Dashboard shows active bets + stats. Separate `/bets` page shows active/completed/cancelled tabs. **Missing: no visual distinction or filtering for LOST vs WON in dashboard stats beyond count. No "completed bets" section on dashboard itself - only on /bets list page.** |
| Webhook-based activity ingestion from Strava | ✅ Complete | GET verification challenge-response works. POST handler dispatches to background tasks with independent DB sessions. Handles create/update/delete events + deauthorization. |
| Automatic bet verification against activity data | ✅ Complete | Dual path: webhook (near-instant) + scheduler (5-min poll). Validates activity type, distance (meters->km), time limit, deadline. ProcessedActivity deduplication. Break-after-first-win logic. |
| Deadline enforcement (cron job at deadline expiry) | ✅ Complete | `check_expired_bets()` runs every 5 minutes. Marks PENDING/ACTIVE bets past deadline as LOST. Sends admin notification via Telegram. |
| Notifications (bet created, bet won, bet lost) | ⚠️ Partial | **Admin-only via Telegram.** Bet won, bet lost (expired), activity events, deauthorization, scheduler status, reminders - all sent to single Telegram chat. **Zero user-facing notifications.** No email, no in-app, no push. |
| Landing page with clear value proposition | ✅ Complete | Strong copy ("Put Money on Your Fitness Goals"), clear 4-step process, bet type cards with Coming Soon badges, trust section (POPIA, SA company), "Powered by Strava" footer compliance. Mobile-responsive with hamburger menu. |
| User data export (POPIA/Strava compliance) | ✅ Complete | `/settings/export` returns JSON with profile + Strava connection info. Content-Disposition header for download. |
| Account deletion | ✅ Complete | Confirmation modal, cascading delete of user + tokens + bets + processed activities. Session cleared. |
| Strava disconnect | ✅ Complete | Deletes token only, preserves user account. Can reconnect later. |
| Privacy Policy / Terms of Service | ✅ Complete | Static pages exist at `/privacy` and `/terms`. |
| Bet cancellation | ✅ Complete | Cancel button on active/pending bets. Status validation (can't cancel completed bets). Confirmation prompt. |
| Bet detail page | ✅ Complete | Shows countdown, requirements, stakes, status badges, verified date for won bets, cancel action for active bets. |

**Overall Phase 1 Completeness: 72%** (core loop works, money/notification gaps are significant)

---

## 3. USER STORIES VALIDATION

### Story 1: "As a new user, I can register and connect my Strava account in under 2 minutes"

**Verdict: PASS (with caveats)**

The flow is: Landing -> Click "Connect with Strava" -> Strava OAuth page -> Authorize -> Redirect to dashboard. This takes ~30 seconds assuming you already have a Strava account.

**Caveat:** If you don't have Strava, there's no guidance. The landing page says "Connect with Strava" but doesn't explain that Strava is required. A user who googles "SweatBet" expecting email signup will bounce.

### Story 2: "As a user, I can create a bet specifying what I want to achieve and by when"

**Verdict: PASS**

Dashboard has prominent "+ Create New Bet" button. Form is well-designed with sensible defaults (7-day deadline, R50 wager). Activity type dropdown, distance, time limit, stake recipient all work. Error handling shows inline messages (past deadline, invalid type).

**Minor gap:** No "suggested bets" or templates. Every bet starts from scratch.

### Story 3: "As a user, after completing my run on Strava, I see my bet automatically verified"

**Verdict: PARTIAL PASS**

The automatic verification works correctly. Webhook triggers within seconds of Strava recording the activity. Bet status updates to WON with verified timestamp.

**Failure:** The user has no way to "see" this happen in real time. There's no notification. They must manually navigate to `/bets/{id}` or `/dashboard` to discover the bet was verified. The bet detail page shows "Bet Won!" with a trophy icon, but the user has to find it themselves.

### Story 4: "As a user, if I miss my deadline, I'm notified that my bet is lost"

**Verdict: FAIL**

The scheduler correctly marks expired bets as LOST. But the notification goes to the admin Telegram chat, not the user. The user discovers their bet is lost only when they visit the app and see the "Bet Lost" status with a heart-broken icon.

**This is the most critical UX gap.** The entire accountability model depends on users feeling the consequence of failure. If they never see the notification, the psychological impact is lost.

### Story 5: "As a user, I can see all my active and past bets in one place"

**Verdict: PASS**

The `/bets` page shows three sections: Active Bets, Completed Bets (won + lost), and Cancelled Bets. Each is a clickable card linking to the detail page. Bet cards show activity type icon, title, distance, wager, and countdown/deadline.

**Minor gap:** No search, no filtering, no sorting options. Fine for MVP but will need pagination for power users.

---

## 4. PRODUCT GAPS & RISKS

### Top 5 Product Gaps That Would Prevent Real Users From Using This

| # | Gap | Impact | Why It Blocks Adoption |
|---|-----|--------|----------------------|
| 1 | **No payment integration** | Critical | The entire value prop is "put money on it." Without actual money changing hands, it's just a fancy Strava activity tracker. Users have no skin in the game. R50 wager means nothing if it's never collected. |
| 2 | **No user notifications** | Critical | Users must manually check the app to learn outcomes. No email, no SMS, no push, no in-app notifications. The "bet won!" moment - the most dopamine-triggering event - is invisible unless the user happens to open the app. |
| 3 | **Strava-only authentication** | High | Excludes users who track fitness with Apple Health, Garmin, Fitbit, Google Fit, or manual entry. Strava is popular among serious cyclists/runners but not the general fitness market. |
| 4 | **No social proof or social features** | High | Accountability works best with social pressure. There's no way to share bets, challenge friends, see a leaderboard, or have an accountability partner. The "1v1 Challenge" and "Group Pool" are Coming Soon placeholders. |
| 5 | **No onboarding or first-bet guidance** | Medium | After OAuth, user lands on empty dashboard. No tutorial, no suggested first bet, no explanation of how verification works. The gap between "I signed up" and "I placed my first bet" is where most users will drop off. |

### What Would Cause Abandonment Before First Bet?

1. **Empty dashboard with no guidance** - "What do I do now?" moment
2. **Confusion about how money works** - "If I bet R50, do I pay now? Later? To whom?" The bet form says "Wager Amount" but there's no explanation of when/how payment happens
3. **No Strava account** - Dead end at landing page
4. **Slow dashboard load** - Live Strava API call on every dashboard visit with no loading indicator
5. **Trust gap** - Stats on landing page (87% completion, R50K+) feel fabricated for a new product

### Confusing States

| State | Confusion Risk |
|-------|---------------|
| Bet ACTIVE but Strava disconnected | User disconnects Strava in settings, has active bets. Bets can never be verified. No warning shown. |
| Bet with R0 wager | User can create a bet with no money on the line. Defeats the purpose. |
| "SweatBet keeps it" stake recipient | Implies SweatBet collects money, but there's no payment system. What does this mean? |
| "Donate to charity" / "Pay a friend" | These options exist in the form but have zero backend implementation. Selecting them does nothing different. |
| Bet WON but no payout mechanism | User wins a bet - what happens to their money? Nothing, because no money was collected. |

### Error Handling UX

| Scenario | User Experience | Verdict |
|----------|----------------|---------|
| OAuth denied | Redirect to landing with `?error=access_denied` at bottom | Acceptable but easy to miss |
| Past deadline on bet creation | Form re-renders with "Deadline must be in the future" | Good |
| Invalid bet ID | Raw JSON `{"detail": "Invalid bet ID"}` | Bad - should be a friendly error page |
| Try to view another user's bet | Raw JSON `{"detail": "Bet not found"}` | Bad |
| Strava API down during dashboard load | "No recent activities found" - misleading | Bad - implies user has no activities |
| Cancel already-won bet | Raw JSON `{"detail": "Cannot cancel completed bet"}` | Bad |

---

## 5. PRIORITIZED BACKLOG

### P0 - Blockers (Must fix before any user sees this)

| # | Item | Rationale |
|---|------|-----------|
| P0-1 | **Add payment integration (Stripe/PayFast)** | Core value prop is broken without it. Even a simple "honor system" payment link would be better than nothing. PayFast recommended for ZAR market. Minimum: collect payment at bet creation, release on win, forfeit on loss. |
| P0-2 | **Add user-facing notifications** | Users need to know when bets are won/lost. Priority: email (Strava provides athlete email in OAuth response with `read` scope). Fallback: at minimum, add a notifications bell/page in the app. |
| P0-3 | **Block bet creation without Strava connection** | Check for active StravaToken at bet creation. Show error: "Connect Strava first to track your activities." |
| P0-4 | **Replace hardcoded stats with real data or remove them** | "87% complete their goals" and "R50K+ on the line" are fabricated. Either show real aggregate stats or remove. New users will notice zero activity on the platform contradicting these claims. |
| P0-5 | **Add friendly error pages for HTTP 400/404** | Replace raw JSON error responses with HTML error pages that match the design system. Include navigation back to dashboard. |

### P1 - Critical (Must fix before public launch)

| # | Item | Rationale |
|---|------|-----------|
| P1-1 | **Add onboarding flow** | After first OAuth: welcome screen -> "Create your first bet" prompt with suggested templates ("Run 5km this week for R50"). Reduce time-to-first-bet from 6 clicks to 3. |
| P1-2 | **Add Strava connection status indicator** | Dashboard should show green/red Strava connection status. Settings already shows this but dashboard doesn't. |
| P1-3 | **Implement "Pay a friend" flow** | The stake_recipient "friend" option collects no friend info. Either remove it or add friend's email/phone field. |
| P1-4 | **Remove or label "charity" option** | "Donate to charity" implies a donation mechanism. Either integrate with a charity API or label as "Coming Soon." |
| P1-5 | **Add bet confirmation step** | "Are you sure you want to bet R100 that you'll run 5km by Saturday?" preview before creating. Money bets deserve a confirmation screen. |
| P1-6 | **Prevent R0 wager bets or add explicit "no stakes" mode** | Either enforce minimum wager (R10?) or make it explicit: "Free challenge (no money on the line)." Don't let users accidentally create stakes-less bets. |
| P1-7 | **Add loading states** | Dashboard Strava activity fetch has no loading indicator. Bet creation form has no submission state. |
| P1-8 | **Timezone handling** | Deadline is stored as naive UTC but user enters in local time. Convert browser timezone on submission or clarify "All times in UTC." |
| P1-9 | **Rate limiting** | `rate_limiter.py` exists but is never connected. Any endpoint can be hammered. Critical for webhook endpoint (public, unauthenticated). |

### P2 - Important (First month)

| # | Item | Rationale |
|---|------|-----------|
| P2-1 | **Dashboard activity caching** | Cache Strava activities (5-10 min TTL) instead of live API call on every page load. Reduces Strava rate limit risk and improves page speed. |
| P2-2 | **Bet templates/suggestions** | "Popular bets" section on create page: "Run 5km this week (R50)", "Cycle 50km this month (R200)". Lower friction to first bet. |
| P2-3 | **Activity detail in bet verification** | When a bet is won, show which specific activity verified it (name, date, distance, link to Strava). Currently only stores activity ID. |
| P2-4 | **Manual activity fraud protection** | Check Strava's `manual` field on activities. Flag or reject manual entries for bet verification. |
| P2-5 | **Social sharing** | "Share your bet" button generating a shareable card/link. Even without 1v1 challenges, social accountability helps retention. |
| P2-6 | **Bet history analytics** | Win rate trends, total distance tracked, monthly summaries. Gamification elements. |
| P2-7 | **Data export includes bets** | Currently `/settings/export` only exports profile + Strava connection. Should include all bets with status and outcomes. |

### P3 - Nice-to-have (Phase 2+)

| # | Item | Rationale |
|---|------|-----------|
| P3-1 | **1v1 Challenges** | "Challenge a friend" - both users bet, loser pays winner. Requires friend invitation system, mutual acceptance flow. |
| P3-2 | **Group Pools** | Multiple athletes, winner takes all or proportional split. Requires group management UI. |
| P3-3 | **Garmin/Apple Health integration** | Expand beyond Strava. Garmin Connect API, Apple HealthKit (requires native app). |
| P3-4 | **Progressive Web App** | Add service worker, offline support, push notifications. Mobile-first UX already exists. |
| P3-5 | **Streak system** | "You've won 5 bets in a row!" - gamification layer. |
| P3-6 | **Admin dashboard** | Currently admin monitoring is Telegram-only. Build a web admin panel for user management, bet monitoring, revenue tracking. |

---

## 6. COMPETITIVE POSITIONING CHECK

### SweatBet vs Competitors (Current Build)

| Feature | SweatBet (Current) | StickK | Beeminder | GoFuckingDoIt |
|---------|-------------------|--------|-----------|---------------|
| **Automatic verification** | ✅ Strava API (real-time) | ❌ Self-report + referee | ⚠️ API integrations (limited fitness) | ❌ Manual + supervisor |
| **Payment integration** | ❌ None | ✅ Credit card, charity | ✅ Credit card (auto-charge) | ✅ Credit card |
| **Fitness-specific** | ✅ Purpose-built | ❌ General commitments | ❌ General goals | ❌ General commitments |
| **Social accountability** | ❌ Solo only | ✅ Referee system | ⚠️ Public graphs | ✅ Supervisor |
| **Mobile experience** | ⚠️ Responsive web | ✅ Native apps | ⚠️ Web-focused | ✅ Simple web |
| **Data-driven insights** | ⚠️ Basic stats | ❌ Minimal | ✅ Graphs, trends | ❌ None |
| **Pricing** | Free (no payments) | Free + optional stakes | Free tier + pledge | One-time fee |
| **ZAR support** | ✅ Native | ❌ USD only | ❌ USD only | ❌ USD only |

### Actual Differentiation in Current Build (Not Pitch Deck)

**What SweatBet actually does better today:**

1. **Automatic verification via Strava** - This is the single real differentiator. No competitor verifies fitness activities automatically. StickK relies on honor system + referee, Beeminder has some integrations but not Strava-native. SweatBet's webhook + scheduler dual path is genuinely better.

2. **ZAR-native** - The only fitness accountability product targeting the South African market with Rand denomination. All competitors are USD-centric.

3. **Fitness-specific UX** - Activity type icons, distance/time requirements, Strava activity feed on dashboard. Competitors are generic goal platforms that happen to support fitness.

**What SweatBet does worse:**

1. **No actual money** - Every competitor has working payment integration. SweatBet's core "put money on it" claim is currently empty. This is a critical credibility gap. Users who've used StickK or Beeminder will immediately notice.

2. **No social layer** - StickK has referees, GoFuckingDoIt has supervisors. SweatBet is entirely solo. The "accountability" comes only from seeing your own bet status. Research consistently shows social accountability is more effective than self-accountability.

3. **No user notifications** - Beeminder sends emergency alerts when you're about to fail. StickK sends reminders. SweatBet sends nothing to the user.

### Would a User Choose SweatBet Today?

**For a South African runner who wants automatic Strava verification: Maybe.** The automatic verification is genuinely compelling if you're tired of self-reporting.

**For anyone else: No.** Without payment integration, SweatBet is a Strava activity viewer with a "bet" label attached. StickK and Beeminder both actually take your money, which is the whole point of a commitment contract.

### Path to Competitive Advantage

The automatic Strava verification is a **strong, defensible moat** if paired with:
1. Working payments (PayFast for SA market)
2. User notifications (email at minimum)
3. Social challenges (1v1 system)

Without payments, SweatBet is a tech demo, not a product.

---

## Summary

SweatBet Phase 1 has built a **technically sound verification engine** with good Strava integration, clean UI, and proper data handling. The bet lifecycle (create -> track -> verify -> outcome) works end-to-end from a data perspective.

The product, however, is **missing its soul**: money. The name is "SweatBet" but no bets are actually placed. Until payment integration exists, the product is a fitness goal tracker with extra steps.

**Recommended priority sequence:**
1. PayFast/Stripe integration (turns it from demo to product)
2. User email notifications (turns it from passive to active)
3. Onboarding flow (turns signups into active users)
4. 1v1 challenges (turns solo tool into social platform)

**Bottom line:** 6-8 weeks of focused work to close the payment + notification gaps would make SweatBet a viable product with genuine differentiation (automatic Strava verification + ZAR market) against established competitors who all rely on manual reporting.
