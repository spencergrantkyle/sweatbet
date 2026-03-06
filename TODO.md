# SweatBet Master To-Do List

Living checklist for taking SweatBet from single-player demo to public multi-user platform.

**Priority order:** Deployment + Strava approval first (blocking), then UI/notifications/payments.

---

## 1. Railway Deployment

**Current state:** Dockerfile and railway.toml already configured. PostgreSQL planned for prod.

- [ ] Create Railway project and link GitHub repo
- [ ] Provision PostgreSQL database on Railway
- [ ] Set all environment variables:
  - `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REDIRECT_URI`
  - `SECRET_KEY`, `DATABASE_URL`, `HOST_URL`
  - `STRAVA_WEBHOOK_VERIFY_TOKEN`, `STRAVA_WEBHOOK_CALLBACK_URL`
- [ ] Update Strava app settings with production callback domain
- [ ] Deploy and verify healthcheck at `/`
- [ ] Register Strava webhook subscription pointing to production URL
- [ ] Test OAuth flow on production
- [ ] Set up custom domain (optional, but helps with Strava approval)

---

## 2. Strava Public App Approval

**Current state:** App works in single-player mode (Spencer's profile). OAuth, webhooks, and token refresh all implemented in `backend/fastapi/services/strava.py`. Webhook management script at `scripts/manage_webhook.py`.

### App Registration
- [ ] Ensure app is registered at strava.com/settings/api with correct details
- [ ] Update Authorization Callback Domain from localhost to Railway production domain

### Brand Guidelines Compliance
- [ ] Use official "Connect with Strava" button (orange/white, correct size 48px@1x / 96px@2x)
- [ ] Add "Powered by Strava" logo on data display pages
- [ ] "View on Strava" links with correct styling (bold/underlined/orange `#FC5200`)
- [ ] Never use "Strava" in app name or imply endorsement

### API Agreement Compliance
- [ ] HTTPS everywhere (Railway handles this)
- [ ] 7-day max data cache policy
- [ ] User data deletion within 48 hours on deauth/request
- [ ] Handle deauthorization webhook events
- [ ] Privacy policy mentioning Strava data usage (already have `privacy.html`)
- [ ] Terms of service (already have `terms.html`)
- [ ] Don't display other users' Strava data to each other (unless <10k users community exception)
- [ ] Don't use data for AI/ML training
- [ ] Don't replicate core Strava functionality

### Submission
- [ ] Verify webhook endpoint handles deauthorization events
- [ ] Test OAuth flow end-to-end on production domain
- [ ] Email developers@strava.com to submit app for review
- [ ] Expect several weeks for approval; 999 athlete limit initially

---

## 3. UI/UX Enhancements

**Current state:** Bet confirmation page at `frontend/sweatbet/templates/bet_confirm.html` (hardcoded for Wasax challenge). Dark theme with Strava orange.

### Bet Confirmation Template
- [ ] Extract bet confirmation page into a reusable template
- [ ] Parameterise all hardcoded values (names, amounts, dates, activity type)
- [ ] Keep the design system (confetti, countdown, progress preview)
- [ ] Make it data-driven from bet model fields

### Dashboard
- [ ] Show active bets with live progress
- [ ] Daily status indicators (done/not done)
- [ ] Earnings/losses summary

### Bet Creation Flow
- [ ] Invite opponent via link/WhatsApp
- [ ] Opponent acceptance flow

---

## 4. Notification System (WhatsApp Business API)

**Current state:** BetReminder model exists (`backend/fastapi/models/bet_reminder.py`) with cooldown tracking. No dispatch mechanism built yet.

### Setup
- [ ] Set up Meta Business account and WhatsApp Business API access
- [ ] Choose WhatsApp BSP (e.g., Twilio, MessageBird, or direct Meta Cloud API)

### Message Templates (must be pre-approved by Meta)
- [ ] Activity acknowledgment: "Activity logged! You earned back RX today. Y days remaining."
- [ ] Daily reminder: "No activity logged yet today for [bet name]. Don't lose your streak!"
- [ ] Bet accepted/declined
- [ ] Bet started
- [ ] Final result (won/lost)
- [ ] Payment confirmation

### Implementation
- [ ] Implement WhatsApp notification service in backend
- [ ] Wire activity acknowledgment to Strava webhook `activity.create` event handler
  - Calculate daily earnings (`wager_amount / total_days`) for the status update
  - Send immediately on activity verification
- [ ] Implement daily reminder check:
  - Scheduled job checks for missing activities by configurable time (e.g., 6pm SAST)
  - Use BetReminder model's cooldown to prevent spam
- [ ] Collect user phone numbers during onboarding

---

## 5. Payment Integration (Stitch Payments)

**Current state:** Nothing built. Stitch chosen for Apple Pay + digital wallet support in SA.

**Why Stitch:** Single API for Apple Pay + Google Pay + Samsung Pay + cards. 90%+ conversion rate on Apple Pay in SA. SA-native, well-funded ($107M raised).

### Setup
- [ ] Sign up for Stitch developer account at stitch.money
- [ ] Complete KYC/onboarding (business registration docs, bank account)
- [ ] Get API keys (sandbox + production)

### Implementation
- [ ] Implement Stitch payment flow:
  - Payment initiation (create payment request when bet is placed)
  - Handle payment confirmation webhooks
  - Store payment references against bets
- [ ] Implement pre-authorization pattern (hold funds when bet placed)
- [ ] Implement settlement flow (capture on loss, release/refund on win)
- [ ] Handle platform fee (5-10% on settlements per PRD)
- [ ] Add payment method selection to bet creation flow (Apple Pay / card / EFT)
- [ ] Test end-to-end in Stitch sandbox environment
- [ ] Go live with Stitch production keys

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `backend/fastapi/services/strava.py` | Strava OAuth + API client |
| `backend/fastapi/models/bet.py` | Bet model with status enum |
| `backend/fastapi/models/bet_reminder.py` | Notification cooldown tracking |
| `backend/fastapi/models/processed_activity.py` | Activity validation |
| `backend/fastapi/api/v1/endpoints/auth.py` | OAuth routes |
| `backend/fastapi/api/v1/endpoints/bet.py` | Bet CRUD |
| `backend/fastapi/api/v1/endpoints/bet_confirm.py` | Bet confirmation page |
| `frontend/sweatbet/templates/bet_confirm.html` | Confirmation UI |
| `frontend/sweatbet/templates/landing.html` | Landing page |
| `scripts/manage_webhook.py` | Webhook subscription management |
| `Dockerfile` | Docker build for Railway |
| `railway.toml` | Railway deployment config |
