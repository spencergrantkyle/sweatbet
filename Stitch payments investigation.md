# Stitch Payments Investigation for SweatBet

**Date:** 2026-03-06
**Purpose:** Evaluate Stitch (stitch.money) payment API for SweatBet's fitness betting platform

---

## 1. What is Stitch?

Stitch is a South African payment gateway and API provider based in Cape Town. They offer a unified GraphQL API at `https://api.stitch.money/graphql` for both sandbox and production. They hold **ISO 27001** and **PCI DSS Level 1** certifications.

Notable clients: Takealot, Betway, Hollywoodbets, Luno, Superbalist, MTN, Vodacom, Cell C.

---

## 2. Available Payment Products

| Product | Description | Relevance to SweatBet |
|---------|-------------|----------------------|
| **Pay By Bank** | Bank-to-bank transfers via redirect flow | **HIGH** - Low-cost way to accept wager deposits |
| **Card Payments** | Debit/credit cards via hosted UI or secure API | **HIGH** - Familiar UX for users |
| **Wallets** | Apple Pay, Samsung Pay, Google Pay | **HIGH** - Frictionless mobile payments |
| **DebiCheck** | Recurring mandate-based collections | **MEDIUM** - Could auto-collect weekly/monthly bets |
| **Manual EFT** | Customer initiates bank transfer manually | **LOW** - Too much friction |
| **Cash** | Cash payments at ATMs | **LOW** - Not relevant for our use case |
| **Crypto** | Cryptocurrency payments | **LOW** - Unnecessary complexity |
| **Disbursements (Payouts)** | Send money to bank accounts | **CRITICAL** - Required to pay out winnings |

---

## 3. Recommended Architecture for SweatBet

### Money In: Accepting Bet Wagers

**Primary: Card Payments (Hosted UI)** - Best for MVP
- Stitch handles PCI compliance entirely
- Supports 3DS authentication
- Simple redirect flow: create payment request → redirect user → receive webhook
- Supports Apple Pay / Google Pay / Samsung Pay via Wallets
- Card tokenization available for repeat bettors (no re-entering card details)

**Secondary: Pay By Bank** - Offer as alternative
- Lower transaction fees than card (typically)
- Good for larger wagers where users want to avoid card limits
- Same redirect flow as card payments

### Money Out: Paying Winnings

**Disbursements** - Only option, and it's well-suited
- Instant or same-day payouts to any SA bank account
- GraphQL mutation with amount + destination account details
- Requires a Stitch float account (funds must be pre-loaded)
- Webhook notifications for payout status updates
- Idempotent via nonce (safe retries)

### Recurring Bets (Future)

**DebiCheck** - For subscription-style betting
- User authorizes a mandate once
- Stitch collects automatically on schedule
- Good for "weekly R50 bet" type products

---

## 4. Technical Integration Details

### Authentication
- **Client Tokens** - For payment requests and disbursements (server-to-server)
- **User Access Tokens** - For accessing customer bank data (not needed for our case)
- Scopes: `client_paymentrequest` (payments in), `client_disbursement` (payouts)

### Core API Flow (Card/Pay By Bank)

```
1. Backend creates payment request via GraphQL mutation
   → clientPaymentInitiationRequestCreate
   → Returns: { id, url }

2. Frontend redirects user to Stitch hosted payment page
   → Append redirect_uri as query param
   → User completes payment (card details, 3DS, or bank login)

3. User redirected back to SweatBet
   → Query params: id, status, externalReference
   → WARNING: status param can be spoofed - DO NOT trust it

4. Webhook fires to our backend (authoritative)
   → PaymentInitiationRequestCompleted / Cancelled / Expired
   → Use this to update bet status in database

5. (Pay By Bank only) Payment confirmation tracks fund settlement
   → PaymentPending → PaymentReceived → estimatedSettlement
   → Requires Stitch intermediary account
   → 7-day timeout before marking as unsettled
```

### Core API Flow (Disbursements / Payouts)

```
1. Backend creates disbursement via GraphQL mutation
   → Requires: amount, destination bank details, nonce, beneficiaryReference

2. Status lifecycle:
   → Pending → Submitted → Completed (or Error)
   → "Completed" is not always final (rare reversals possible)

3. Webhook fires for status updates
   → Submitted, Completed, Error, Paused, Cancelled, Reversed

4. Insufficient funds: held for 7 days, then marked errored
```

### Key Mutation Parameters

**Payment Request (money in):**
- `amount`: `{ quantity: "50.00", currency: "ZAR" }`
- `payerReference`: Max 12 chars (shown on user's bank statement)
- `beneficiaryReference`: Max 20 chars (shown on our statement)
- `externalReference`: Max 4096 chars (our internal bet ID)
- `expireAt`: ISO 8601 (auto-expire unpaid requests)
- `paymentMethods.card.enabled`: true
- `payerInformation.payerId`: Required for fraud detection

**Disbursement (money out):**
- `amount`: `{ quantity: "100.00", currency: "ZAR" }`
- `nonce`: Unique string for idempotency (use bet ID + payout attempt)
- `beneficiaryReference`: Max 20 chars (truncated if longer)
- Destination: bankId, accountNumber, name, accountType

### Disbursement Types
| Type | Behaviour |
|------|-----------|
| `INSTANT` | Immediate clearing (extra cost). Not supported by Olympus/Citibank/Grindrod |
| `DEFAULT` | Same-day, rolls to next business day after cutoff |

### Sandbox Testing

**Test card numbers:**
| Card Number | Result |
|-------------|--------|
| `4032035421088592` | 3DS success |
| `4004462059871392` | 3DS failure |
| `4032033425469975` | Authorization failure |
| `4005519200000004` | Insufficient funds |

**Test disbursement amounts:**
| Amount (ZAR) | Result |
|---------------|--------|
| < 400 (account ending in 0) | Success |
| 400 | Bank error |
| 401 | Inactive account |
| 402 | Invalid account |
| > 404 | Paused (insufficient funds in float) |

**Simulating completed Pay By Bank:**
Use `testClientPaymentInitiationRequestSimulateComplete` mutation in sandbox.

**Default whitelisted redirect URIs (sandbox):**
- `https://localhost:8080`, `https://localhost:8080/return`
- `https://localhost:3000`, `https://localhost:3000/return`
- `https://localhost:9000`, `https://localhost:9000/return`

---

## 5. What We Need from Stitch (Account Setup)

1. **Stitch merchant account** - Apply at stitch.money
2. **API client credentials** - Client ID + secret for token generation
3. **Float account** - Required for disbursements (pre-fund to pay out winnings)
4. **Intermediary account** - For Pay By Bank payment confirmation tracking
5. **Webhook endpoint** - Register our callback URL for payment events
6. **Redirect URI whitelist** - Our production domain for payment redirects

---

## 6. SweatBet Integration Plan

### Phase 1: MVP (Card Payments + Disbursements)

**Deposit flow (placing a bet):**
1. User creates bet on SweatBet → bet saved as `pending_payment`
2. Backend calls `clientPaymentInitiationRequestCreate` with card enabled
3. Frontend redirects to Stitch hosted payment page
4. On webhook `Completed` → update bet to `active`
5. On webhook `Cancelled/Expired` → update bet to `cancelled`
6. Use `externalReference` = bet ID for reconciliation

**Payout flow (winning a bet):**
1. Bet verified as won via Strava activity
2. Backend calls disbursement mutation with winner's bank details
3. On webhook `Completed` → update bet to `paid_out`
4. On webhook `Error` → flag for manual review

**User bank details:**
- Collect once during onboarding or first win
- Store: bankId, accountNumber, accountType, name
- Validate via Bank Account Verification (BAV) API before first payout

### Phase 2: Enhanced UX
- **Card tokenization** - Save cards for repeat bettors
- **Apple Pay / Google Pay** - One-tap bet placement
- **Pay By Bank** - Offer as lower-cost alternative at checkout

### Phase 3: Subscription Bets
- **DebiCheck mandates** - Weekly auto-bet collection
- User authorizes once, Stitch collects on schedule

---

## 7. Pricing

**Pricing is not publicly listed.** Stitch operates on custom/enterprise pricing.

Action required: Contact Stitch sales to get a quote. Key questions:
- Per-transaction fee for card payments
- Per-transaction fee for Pay By Bank
- Disbursement fees (DEFAULT vs INSTANT)
- Monthly minimums or platform fees
- Float account requirements and interest

---

## 8. Risks and Considerations

| Risk | Mitigation |
|------|------------|
| **Gambling regulation** | SweatBet is fitness-based, not traditional gambling. May still need legal review on whether wager-based fitness challenges fall under SA gambling laws |
| **Float account funding** | Need enough funds to cover payouts. Monitor float balance and top up proactively |
| **Pay By Bank settlement delay** | Funds may take time to arrive. Don't activate bets until PaymentReceived confirmation |
| **Disbursement reversals** | "Completed" isn't always final. Track reversals via webhooks |
| **Redirect URI spoofing** | Never trust redirect query params for status. Always verify via webhook or API query |
| **Card fraud** | Use 3DS, provide payer metadata (addresses) for Stitch's fraud detection |
| **SA-only** | Stitch only supports South African customers. International expansion would need a different provider |

---

## 9. Key Decisions Needed

1. **Card vs Pay By Bank as primary?** Card is better UX but likely higher fees. Recommend card as default with Pay By Bank as option.
2. **When to collect bank details for payouts?** At registration (friction) vs first win (delays payout). Recommend: collect at registration, validate via BAV.
3. **Float account funding strategy?** Manual top-up vs automated. Start manual, automate later.
4. **Instant vs default disbursements?** Instant costs more but better UX. Recommend: default for now, instant as premium feature later.
5. **Legal review needed?** Fitness wagers in SA - consult with a lawyer before going live with real money.

---

## 10. Next Steps

- [ ] Contact Stitch sales for pricing and merchant account setup
- [ ] Legal review on SA gambling/wagering regulations for fitness bets
- [ ] Design database schema for payment records (payment requests, disbursements, tokens)
- [ ] Build payment service module (`backend/fastapi/services/stitch.py`)
- [ ] Set up Stitch sandbox and test card + disbursement flows
- [ ] Design checkout UI flow with Stitch redirect
- [ ] Implement webhook handler for payment status updates
