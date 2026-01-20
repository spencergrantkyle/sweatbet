# SweatBet Product Requirements Document

## 1. Product Overview
**Product Name:** SweatBet  
**Version:** MVP 1.0  
**Purpose:** Fitness motivation platform enabling users to place financial bets on fitness goals, verified automatically via Strava API

## 2. Problem & Solution

**Problem:** Lack of motivation and accountability prevents consistent fitness activity  
**Solution:** Financial stakes + automatic verification = increased commitment and sustained behavior change

## 3. Target Users
- Primary: Strava users (120M+ athletes) - runners and cyclists
- South Africa focus: 1M ParkRun participants, 400K+ race participants annually
- Secondary: Fitness wannabes seeking motivation

## 4. Core User Flow

```
Sign Up → Link Strava → Create Bet → Accept Challenge → Activity Deadline → Auto-Verify → Settle
```

## 5. MVP Feature Requirements

### 5.1 Authentication & Onboarding
- Email/Google/Apple sign-in
- Strava OAuth 2.0 integration (activity:read_all scope)
- Payment method setup (card details/crypto wallet)

### 5.2 Bet Creation
**Required Parameters:**
- Bet title
- Wager amount (ZAR)
- Participant(s): Self or friend challenge
- Activity type: Run or Cycle
- Distance requirement (km)
- Time requirement (optional - e.g., sub-60min 10K)
- Deadline (date + time, default 11:59 PM)

**Bet Types:**
- Individual: User vs. goal
- 1v1: User vs. friend
- Group: Multiple participants, pool distribution

### 5.3 Strava Integration
**Critical API Calls:**
- OAuth authorization
- Get athlete activities (filtered by date range)
- Retrieve activity details (distance, time, type)
- Webhook subscription for real-time activity updates

**Verification Logic:**
- At deadline, query Strava API for activities
- Match activity type (run/ride)
- Verify distance ≥ bet requirement
- Verify time ≤ bet requirement (if specified)
- Flag GPS anomalies/indoor activities if relevant

### 5.4 Bet Settlement
**Win Condition:** Activity meets all bet criteria by deadline  
**Loss Condition:** No qualifying activity by deadline

**Settlement Actions:**
- Individual bets: Charge card on loss
- 1v1 bets: Transfer from loser to winner
- Group bets: Pool distribution to winners OR charitable donation

**Transaction Fees:**
- 5-10% platform fee on all settlements
- 20% cancellation fee
- Non-adherence penalty (both fail): Platform keeps pool OR donation

### 5.5 Notifications
- Bet acceptance (for challenged friends)
- Reminder: 24 hours before deadline
- Settlement result notification
- Payment confirmation

## 6. Technical Requirements

### 6.1 Backend
- Node.js/Express server
- Database: PostgreSQL for user data, bets, transactions
- Strava API client library
- Payment processing: Stripe or PayFast (South Africa)
- Scheduled jobs: Bet verification cron (runs hourly after deadlines)

### 6.2 Strava API Integration
**OAuth Flow:**
```
1. Redirect to Strava authorization
2. Request scopes: activity:read, activity:read_all
3. Exchange code for access + refresh tokens
4. Store tokens securely (encrypted)
5. Refresh tokens before expiry (6-hour lifecycle)
```

**Webhooks Setup:**
- Subscribe to athlete deauthorization events
- Subscribe to activity creation/update events
- Verify webhook signatures
- Handle event processing asynchronously

### 6.3 Frontend
- React web app
- Mobile-responsive design
- Dashboard: Active bets, history, stats
- Forms: Bet creation wizard

### 6.4 Security & Compliance
- PCI DSS compliance for payment data
- Encrypt Strava tokens at rest
- HTTPS only
- South African gambling law compliance review
- POPIA compliance (data privacy)

## 7. Success Metrics

**User Engagement:**
- Weekly active users (WAU)
- Bets created per user
- Bet completion rate

**Business Metrics:**
- GMV (Gross Merchandise Value): Total bet volume
- Transaction revenue
- User retention (30-day, 90-day)

**Target (Month 3):**
- 500 registered users
- 100 active weekly bettors
- R50K GMV
- 70% bet completion rate

## 8. MVP Scope (R50K Budget)

### In Scope:
✅ Core betting flow (individual + 1v1)  
✅ Strava verification for run/cycle distance  
✅ Manual payment settlement (deferred processing)  
✅ Email notifications  
✅ Web app only  

### Out of Scope (Post-MVP):
❌ Group bets with complex pool logic  
❌ Real-time payment processing  
❌ Mobile native apps  
❌ Time-based bet verification  
❌ Charitable donation integration  
❌ Social features (leaderboards, feeds)  

## 9. Launch Strategy

**Phase 1 (Months 1-2):** Single race event integration  
**Phase 2 (Month 3):** RacePass.com partnership  
**Phase 3 (Month 4):** 5 running club partnerships  

**Marketing Channels:**
- Event-based activation
- Running club ambassadors
- Strava club partnerships

## 10. Open Questions & Risks

**Payment Timing:**
- Pre-charge vs. post-bet settlement? (Recommend: Pre-authorize, capture on loss)

**Legal:**
- Gambling license required in South Africa?
- Terms to prevent Strava ToS violations (no activity manipulation incentives)

**Technical:**
- Strava API rate limits: 200/15min, 2000/day - sufficient for MVP scale
- Handling disputed results (GPS errors, manual activities)

