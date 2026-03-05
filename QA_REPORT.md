# SweatBet QA Audit Report

**Date:** 2026-03-05
**Scope:** Full codebase review after Phase 1 development
**Reviewer:** Senior QA Engineer

---

## 1. TEST COVERAGE AUDIT

### 1.1 Existing Test Inventory

| File | Type | Tests | Covers | Misses |
|---|---|---|---|---|
| `test_bet_validator.py` | Unit | 33 | `validate_activity_for_bet()` pure logic (type, distance, time, deadline), `Bet` model properties | `process_new_activity()` orchestration, DB interactions, token refresh during validation |
| `test_webhook.py` | Integration | 16 | Webhook GET verification, POST event dispatch (all event types), landing page rendering, unauthenticated route redirects | Actual background task execution, deauth data deletion, activity-to-bet verification pipeline end-to-end |
| `test_api_sync.py` | Integration | 6 | Legacy Message CRUD endpoints | Nothing SweatBet-specific |

**Total: 55 tests, 0 end-to-end**

### 1.2 Coverage by Module (Approximate)

| Module | Coverage | Notes |
|---|---|---|
| Auth/Registration (Strava OAuth) | **~5%** | Only tests that unauthenticated users get redirected. Zero tests for the actual OAuth flow (`/auth/strava`, `/auth/callback`, `/auth/logout`). |
| Strava OAuth token lifecycle | **~0%** | No tests for `exchange_code()`, `refresh_access_token()`, `ensure_valid_token()`. |
| Bet creation/management | **~10%** | Model properties tested. Zero tests for `POST /bets/create`, `GET /bets/{id}`, `POST /bets/{id}/cancel` form handlers. |
| Webhook processing | **~40%** | Verification endpoint well-tested. Event dispatch tested at HTTP level. Background task execution NOT tested (tasks are enqueued but not awaited in test). |
| Bet verification engine | **~60%** | `validate_activity_for_bet()` well-tested with 23 cases. `process_new_activity()` orchestration completely untested. |
| Activity scheduler | **~0%** | `check_activities_for_active_bets()`, `check_expired_bets()`, `send_outstanding_bet_reminders()` — all untested. |
| Notifications (Telegram) | **~0%** | All `TelegramNotifier` methods untested. |
| Settings/Data export | **~0%** | `/settings/export`, `/settings/disconnect`, `/settings/delete` — untested. |
| API JSON endpoints | **~0%** | `/api/v1/bets`, `/api/v1/bets/{id}` — untested. |

### 1.3 Five Most Critical Untested Code Paths

1. **`process_new_activity()` in `bet_validator.py:122-243`** — The entire webhook-to-bet-verification pipeline. This IS the product. It fetches activity from Strava, validates against bets, updates bet status to WON, and commits to DB. Zero tests.

2. **`auth_callback()` in `auth.py:41-144`** — OAuth code exchange, user creation/update, token storage, session setup. The only way users get into the system. Zero tests. Contains a `print()` instead of `logger` on error (line 143).

3. **`check_expired_bets()` in `activity_scheduler.py:251-314`** — The deadline cron that marks unverified bets as LOST. If this fails, users who miss deadlines face no consequences. Zero tests.

4. **`create_bet()` POST handler in `bet.py:56-112`** — Form validation, bet creation with all new fields (bet_type, currency, stake_recipient). Users cannot place bets without this working. Zero tests.

5. **`_handle_deauthorization_background()` in `webhook.py:63-84`** — Strava compliance requirement: when a user deauthorizes on Strava, ALL their data must be deleted. If this fails, SweatBet violates the Strava API Agreement. Zero tests beyond HTTP 200 dispatch.

---

## 2. CRITICAL PATH TESTING

### 2.1 Registration & Auth

| # | Scenario | Status | File/Line |
|---|---|---|---|
| A1 | OAuth happy path: redirect to Strava, callback with code, user created, session set | **MISSING** | `auth.py:23-38, 41-144` |
| A2 | OAuth denial: Strava returns `?error=access_denied` | **MISSING** | `auth.py:57-58` |
| A3 | OAuth invalid state (CSRF attack) | **MISSING** | `auth.py:64-66` |
| A4 | OAuth callback without code | **MISSING** | `auth.py:60-61` |
| A5 | Returning user: OAuth re-login updates existing user, doesn't create duplicate | **MISSING** | `auth.py:87-111` |
| A6 | Session persistence: authenticated session survives across requests | **MISSING** | — |
| A7 | Session expiry after 24 hours | **MISSING** | `middleware.py:29` |
| A8 | Logout clears session completely | **MISSING** | `auth.py:147-155` |

**Note:** SweatBet has NO email/password or Google auth. Auth is Strava-only. The prompt's references to email registration and Google OAuth are N/A.

### 2.2 Strava Integration

| # | Scenario | Status | File/Line |
|---|---|---|---|
| S1 | Token refresh when `expires_at` is in the past | **MISSING** | `strava.py:188-214` |
| S2 | Token refresh when refresh_token is revoked (Strava returns 401) | **MISSING** | `strava.py:98-109` |
| S3 | Strava API returns 429 (rate limited) | **MISSING** | `strava.py` (no handling at all) |
| S4 | Strava API returns 5xx | **MISSING** | `strava.py` (raise_for_status will throw, but callers only do generic catch) |
| S5 | Strava API timeout | **MISSING** | `strava.py` (no timeout configured on httpx.AsyncClient) |
| S6 | Deauthorization webhook deletes user + all data | **MISSING** | `webhook.py:63-84` |
| S7 | User disconnects Strava from SweatBet settings | **MISSING** | `settings.py:75-82` |
| S8 | Activity fetch returns empty list | **MISSING** | `activity_scheduler.py:158-164` |

### 2.3 Bet Lifecycle

| # | Scenario | Status | File/Line |
|---|---|---|---|
| B1 | Create bet with valid params → status=ACTIVE, stored in DB | **MISSING** | `bet.py:56-112` |
| B2 | Create bet with deadline in the past → 400 error | **MISSING** | `bet.py:74-75` |
| B3 | Create bet with missing required fields → 422 | **MISSING** | `bet.py:56` (Form(...)) |
| B4 | Create bet without Strava connected (user has no token) | **MISSING** | Not checked at creation time — **BUG** |
| B5 | Negative wager amount → clamped to 0 | **MISSING** | `bet.py:104` |
| B6 | Cancel active bet → status=CANCELLED | **MISSING** | `bet.py:151-174` |
| B7 | Cancel already-won bet → 400 error | **MISSING** | `bet.py:166-167` |
| B8 | View another user's bet by ID → 404 | **MISSING** | `bet.py:132-137` |
| B9 | Bet detail page renders for valid bet | **MISSING** | `bet.py:119-144` |

### 2.4 Webhook & Verification

| # | Scenario | Status | File/Line |
|---|---|---|---|
| W1 | GET verification challenge-response | **TESTED** | `test_webhook.py:14-25` |
| W2 | Invalid/wrong verify token → 403 | **TESTED** | `test_webhook.py:48-57` |
| W3 | POST activity create → background task enqueued | **TESTED** (HTTP-only) | `test_webhook.py:63-78` |
| W4 | POST deauthorization → user data deleted | **HTTP-only** | `test_webhook.py:113-128` — doesn't verify data is actually deleted |
| W5 | Valid activity meets bet → bet status = WON | **MISSING** | `bet_validator.py:215-231` |
| W6 | Activity doesn't meet distance → bet stays ACTIVE | **MISSING** | `bet_validator.py:232-241` |
| W7 | Activity wrong type → bet stays ACTIVE | **MISSING** | `bet_validator.py:65-71` |
| W8 | Activity after deadline → bet stays ACTIVE | **MISSING** | `bet_validator.py:81-87` |
| W9 | Activity for user with no active bets → no-op | **MISSING** | `bet_validator.py:158-160` |
| W10 | Multiple bets active, one matches → only that bet marked WON | **MISSING** | `bet_validator.py:211-241` |
| W11 | Duplicate activity processing → ProcessedActivity prevents re-processing | **MISSING** | `activity_scheduler.py:178-184` |
| W12 | Webhook with malformed JSON → 400 | **TESTED** | `test_webhook.py:144-150` |

### 2.5 Deadline Processing

| # | Scenario | Status | File/Line |
|---|---|---|---|
| D1 | Bet past deadline, still ACTIVE → marked LOST | **MISSING** | `activity_scheduler.py:265-286` |
| D2 | Already-WON bet with passed deadline → NOT changed | **MISSING** | `activity_scheduler.py:265-268` (filter is correct, but untested) |
| D3 | Multiple bets expire simultaneously → all marked LOST | **MISSING** | `activity_scheduler.py:278-303` |
| D4 | SAST timezone bet stored as UTC → deadline comparison correct | **MISSING** | Deadlines stored as naive UTC — **see Bug B-TZ below** |

---

## 3. EDGE CASES & BOUNDARY CONDITIONS

### BUG: B-STRAVA-DISCONNECT
**File:** `bet.py:56-112` (create_bet)
**Issue:** A user can create a bet even if they have no Strava token. The bet will be ACTIVE but the webhook/scheduler can never verify it because there's no token to call `get_activity()`. The bet will silently expire as LOST.
**Impact:** User loses wager for an impossible-to-verify bet.
**Fix:** Check for active Strava connection at bet creation time.

### BUG: B-TZ (Timezone Handling)
**Files:** `bet.py` model, `bet_validator.py:77-86`, `activity_scheduler.py:61,267`
**Issue:** All datetimes are naive UTC (`datetime.utcnow()`). The bet creation form sends a `datetime-local` from the browser (user's local timezone), which is parsed with `datetime.fromisoformat()` and stored as-is. A user in SAST (UTC+2) setting a deadline of "Saturday 23:59" stores `2026-03-07T23:59:00` but the scheduler compares against `datetime.utcnow()`, effectively giving the user 2 extra hours.
**Impact:** Inconsistent deadline enforcement for non-UTC users.

### BUG: B-DOUBLE-WIN
**File:** `bet_validator.py:211-231`
**Issue:** In `process_new_activity()`, when iterating over `active_bets`, if an activity matches the first bet and marks it WON, the loop continues and could match subsequent bets with the same activity. There's no `break` after the first win.
**Impact:** One activity could win multiple bets. (Note: the scheduler's `process_user_activities` at `activity_scheduler.py:226` DOES have a `break` — so the scheduler path is safe, but the webhook path is not.)

### BUG: B-VERIFIED-DELETE
**File:** Nowhere handled.
**Issue:** If Strava sends a `delete` event for an activity that previously verified a bet (bet.verified_activity_id == deleted activity), the bet stays WON even though the activity no longer exists. Strava activity deletions could be used to game the system (record a fake activity, win bet, delete activity).
**Impact:** Monetary integrity. A won bet based on a deleted activity should be re-evaluated.

### EDGE: E-RACE-CONDITION
**Files:** `webhook.py:93`, `activity_scheduler.py:194`
**Issue:** Both the webhook handler AND the scheduler can process the same activity simultaneously. The webhook fires `_process_activity_background()` immediately, while the scheduler polls every 5 minutes. If both run before `ProcessedActivity` is written, both will validate and potentially double-commit the bet WIN. The `strava_activity_id` UNIQUE constraint on `ProcessedActivity` would cause one to fail, but only the scheduler checks `ProcessedActivity` before processing — the webhook handler in `process_new_activity()` does NOT check `ProcessedActivity`.
**Impact:** Duplicate notifications, potential DB IntegrityError in background task.

### EDGE: E-TWO-ACTIVITIES
**File:** `bet_validator.py:211`
**Issue:** If two qualifying activities arrive for the same bet (e.g., two 5km runs before deadline), the first one wins the bet. The second will find the bet already WON (status check in scheduler at line 191). But in the webhook path, there's no status re-check before `db.commit()` — a stale `active_bets` list could cause a redundant commit.

### EDGE: E-MANUAL-ACTIVITY
**Issue:** Strava allows manual activity entry (no GPS). The `validate_activity_for_bet()` function checks type and distance but has no way to distinguish GPS-tracked from manual entries. Strava's activity data includes a `manual` boolean field that is not checked.
**Impact:** Users could manually enter fake activities to win bets.

### EDGE: E-WEBHOOK-DOWNTIME
**Issue:** If the SweatBet server is down when Strava sends a webhook, the event is lost. Strava does NOT retry webhook events. However, the scheduler polls every 5 minutes with a 24-hour lookback, so activities will still be caught.
**Impact:** Low (scheduler provides backup), but verification may be delayed up to 5 minutes.

### EDGE: E-DB-UNAVAILABLE
**File:** `webhook.py:55-59`
**Issue:** `_process_activity_background()` creates `SyncSessionLocal()`. If the DB is unavailable, this throws an exception caught by the generic `except` on line 57. The activity is lost (no retry mechanism). The scheduler would catch it on next poll.

### EDGE: E-MAX-WAGER
**File:** `bet.py:104`
**Issue:** `wager_amount` is clamped to `max(0, value)` but has no upper bound. A user could create a bet with wager_amount=999999999. No validation in the schema either (`ge=0` only).
**Impact:** Unrealistic wager amounts stored in DB.

---

## 4. API ENDPOINT TESTING

| Endpoint | Method | Auth Required? | Auth Tested? | Authz (own data)? | Input Validation? | Rate Limited? |
|---|---|---|---|---|---|---|
| `/` | GET | No | N/A | N/A | N/A | **No** |
| `/auth/strava` | GET | No | N/A | N/A | N/A | **No** |
| `/auth/callback` | GET | No | **No** | N/A | State token validated | **No** |
| `/auth/logout` | GET | No | **No** | N/A | N/A | **No** |
| `/dashboard` | GET | Yes (redirect) | **Yes** | Yes (own data) | N/A | **No** |
| `/bets/create` | GET | Yes (redirect) | **Yes** | N/A | N/A | **No** |
| `/bets/create` | POST | Yes (redirect) | **No** | N/A | Partial (see below) | **No** |
| `/bets/{id}` | GET | Yes (redirect) | **No** | Yes (creator_id filter) | UUID validated | **No** |
| `/bets` | GET | Yes (redirect) | **Yes** | Yes (creator_id filter) | N/A | **No** |
| `/bets/{id}/cancel` | POST | Yes (redirect) | **No** | Yes (creator_id filter) | Status validated | **No** |
| `/settings` | GET | Yes (redirect) | **Yes** | Yes (own data) | N/A | **No** |
| `/settings/export` | GET | Yes (401) | **No** | Yes (own data) | N/A | **No** |
| `/settings/disconnect` | POST | Yes (401) | **No** | Yes (own tokens) | N/A | **No** |
| `/settings/delete` | POST | Yes (401) | **No** | Yes (own record) | **No confirmation** | **No** |
| `/webhooks/strava` | GET | Token-based | **Yes** | N/A | Verify token checked | **No** |
| `/webhooks/strava` | POST | None (public) | N/A | N/A | JSON parsed | **No** |
| `/api/v1/bets` | GET | Yes (401) | **No** | Yes (creator_id filter) | N/A | **No** |
| `/api/v1/bets/{id}` | GET | Yes (401) | **No** | Yes (creator_id filter) | UUID validated | **No** |
| `/privacy` | GET | No | N/A | N/A | N/A | N/A |
| `/terms` | GET | No | N/A | N/A | N/A | N/A |

**Critical findings:**
- **No rate limiting on ANY endpoint.** `rate_limiter.py` exists but is never wired up. The rate limiter depends on `fastapi_limiter` and `aioredis` which aren't in `requirements.txt`.
- **POST `/settings/delete`** has no CSRF token or confirmation beyond a client-side JS modal. Could be exploited via a malicious link.
- **POST `/webhooks/strava`** is publicly accessible with no authentication beyond the verify token (which only protects GET). Any attacker could POST fake webhook events.

---

## 5. ERROR HANDLING REVIEW

### 5.1 Bare/Swallowed Exceptions

| File | Line | Pattern | Risk |
|---|---|---|---|
| `auth.py` | 142-144 | `except Exception as e: print(...)` | Uses `print()` instead of `logger`. Error context lost in production. User gets generic redirect. |
| `dashboard.py` | 83 | `except Exception as e: logger.error(...)` | Activity fetch failure silently returns empty list. User doesn't know their Strava is broken. |
| `activity_scheduler.py` | 88-90 | `except Exception as e: logger.error(...); continue` | One user's failure skips to next — correct pattern, but no retry or dead-letter. |
| `activity_scheduler.py` | 150-152 | `except Exception as e: ... return result` | Token refresh failure silently abandons all bets for that user. No user notification. |
| `bet_validator.py` | 190-196 | `except Exception as e: ... return results` | Token refresh failure returns empty results. Bet stays active but unverified. |
| `telegram.py` | 87-92 | `except httpx.TimeoutException` + generic `except` | Good pattern — degrades gracefully. |

### 5.2 Strava API Error Handling

| Error Type | Handled? | Where |
|---|---|---|
| HTTP 401 (token revoked) | **No** — `raise_for_status()` throws generic `httpx.HTTPStatusError` | `strava.py:85,108` |
| HTTP 429 (rate limited) | **No** — same generic error | Nowhere |
| HTTP 5xx (server error) | **No** — same generic error | Nowhere |
| Network timeout | **No** — no timeout set on `httpx.AsyncClient()` | `strava.py:75,98,121,160,180` |
| Connection refused | **No** — generic exception | Callers |

**The `StravaClient` creates a new `httpx.AsyncClient()` for EVERY request with no timeout and no retry logic.** This is a significant resilience gap.

### 5.3 User-Facing Errors

- OAuth failures redirect to `/?error=auth_failed` — user sees nothing beyond landing page (error param not visibly displayed unless template checks for it). The landing template does render `{{ error }}` so this is acceptable.
- Bet creation errors re-render the form with error message — good UX.
- 404/400 from bet detail/cancel raise `HTTPException` which returns JSON, not a friendly HTML page. Users hitting these via browser will see raw JSON.

---

## 6. DATA INTEGRITY CHECKS

### 6.1 Transaction Safety

| Operation | Transactional? | Risk |
|---|---|---|
| User + Token creation in OAuth callback | `db.flush()` + `db.commit()` — **single transaction** | Safe. Flush gets user ID before creating token; commit is atomic. |
| Bet creation | `db.add()` + `db.commit()` — single operation | Safe. |
| Bet verification (status + verified_at + verified_activity_id) | `db.commit()` after updating bet fields | **Risk:** If notification send fails AFTER commit, the bet is WON but the user isn't notified. Acceptable since Telegram is best-effort. |
| Token refresh in `process_new_activity()` | `db.commit()` — separate from bet verification | **Risk:** Token is refreshed but if the activity fetch fails immediately after, the token commit can't be rolled back. Acceptable since new token is still valid. |
| Bet status + ProcessedActivity in scheduler | **Two separate commits** at lines 201 and 224 | **Risk:** Bet marked WON (committed) but `ProcessedActivity` write fails → activity could be reprocessed (but bet is already WON so no damage). |
| Deauthorization: delete user (cascade) | `db.delete(user)` + `db.commit()` — single transaction | Safe. Cascade deletes tokens, bets, processed_activities. |

### 6.2 Orphaned Records

| Scenario | Risk | Mitigation |
|---|---|---|
| Bet without creator (user deleted) | None | `ondelete="CASCADE"` on `Bet.creator_id` |
| StravaToken without user | None | `ondelete="CASCADE"` on `StravaToken.user_id` |
| ProcessedActivity without user | None | `ondelete="CASCADE"` on `ProcessedActivity.user_id` |
| ProcessedActivity without bet | Possible (by design) | `ondelete="SET NULL"` — activity tracked even without matching bet |
| BetReminder without bet | **Possible** | `ondelete` not specified on `BetReminder.bet_id` FK — if bet is deleted, reminder record becomes orphaned |

### 6.3 Cascade on Delete

| Table | FK | On Delete | Status |
|---|---|---|---|
| `strava_tokens.user_id` → `users.id` | CASCADE | Correct |
| `bets.creator_id` → `users.id` | CASCADE | Correct |
| `processed_activities.user_id` → `users.id` | CASCADE | Correct |
| `processed_activities.bet_id` → `bets.id` | SET NULL | Correct (preserves audit trail) |
| `bet_reminders.bet_id` → `bets.id` | CASCADE | Correct |

### 6.4 Timestamp Consistency

All models use `datetime.utcnow`. The `StravaToken.expires_at` uses Unix timestamp (BigInteger). The bet `deadline` is stored as naive UTC. **Consistent but timezone-naive throughout** — see Bug B-TZ above.

---

## 7. RECOMMENDED TEST PLAN

### P0: Must Exist Before ANY User Touches This

These tests prevent data loss, financial errors, and Strava API Agreement violations.

---

#### P0-1: `test_process_new_activity_wins_bet`
**Module:** `bet_validator.py:process_new_activity()`
**Input:** Mock user with active bet (Run, 5km), mock Strava API returning a 6km run activity
**Expected:** Bet status updated to WON, `verified_activity_id` set, `verified_at` set
```python
async def test_process_new_activity_wins_bet(db_session, mock_strava):
    user = create_test_user(db_session)
    token = create_test_token(db_session, user.id)
    bet = create_test_bet(db_session, user.id, distance_km=5.0, activity_type="Run")
    mock_strava.get_activity.return_value = {"id": 123, "type": "Run", "distance": 6000, "moving_time": 1800, "start_date": "2026-03-04T10:00:00Z", "name": "Morning Run"}
    results = await process_new_activity(123, user.strava_athlete_id, db_session)
    assert len(results) == 1
    assert results[0].success is True
    db_session.refresh(bet)
    assert bet.status == BetStatus.WON
    assert bet.verified_activity_id == "123"
```

#### P0-2: `test_process_new_activity_insufficient_distance`
**Module:** `bet_validator.py:process_new_activity()`
**Input:** Bet requires 10km, activity is 5km
**Expected:** Bet stays ACTIVE, no verified_activity_id
```python
async def test_process_new_activity_insufficient_distance(db_session, mock_strava):
    # ... setup with distance_km=10.0, activity distance=5000
    results = await process_new_activity(123, user.strava_athlete_id, db_session)
    assert results[0].success is False
    db_session.refresh(bet)
    assert bet.status == BetStatus.ACTIVE
```

#### P0-3: `test_check_expired_bets_marks_lost`
**Module:** `activity_scheduler.py:check_expired_bets()`
**Input:** Active bet with deadline in the past
**Expected:** Bet status changed to LOST
```python
async def test_check_expired_bets_marks_lost(db_session):
    bet = create_test_bet(db_session, deadline=datetime.utcnow() - timedelta(hours=1))
    await check_expired_bets()
    db_session.refresh(bet)
    assert bet.status == BetStatus.LOST
```

#### P0-4: `test_check_expired_bets_skips_already_won`
**Module:** `activity_scheduler.py:check_expired_bets()`
**Input:** WON bet with deadline in the past
**Expected:** Bet stays WON

#### P0-5: `test_deauthorization_deletes_all_user_data`
**Module:** `webhook.py:_handle_deauthorization_background()`
**Input:** Existing user with token, bets, processed activities
**Expected:** User, tokens, bets, processed activities all deleted from DB
```python
async def test_deauthorization_deletes_all_user_data(db_session):
    user = create_test_user(db_session)
    create_test_token(db_session, user.id)
    create_test_bet(db_session, user.id)
    await _handle_deauthorization_background(user.strava_athlete_id)
    assert db_session.query(User).filter(User.id == user.id).first() is None
    assert db_session.query(StravaToken).filter(StravaToken.user_id == user.id).first() is None
    assert db_session.query(Bet).filter(Bet.creator_id == user.id).first() is None
```

#### P0-6: `test_oauth_callback_creates_user_and_token`
**Module:** `auth.py:auth_callback()`
**Input:** Valid OAuth code, mock Strava token exchange
**Expected:** User created in DB, StravaToken created, session contains user_id

#### P0-7: `test_oauth_callback_invalid_state_rejected`
**Module:** `auth.py:auth_callback()`
**Input:** OAuth callback with mismatched state parameter
**Expected:** Redirect to `/?error=invalid_state`, no user created

#### P0-8: `test_create_bet_valid_params`
**Module:** `bet.py:create_bet()`
**Input:** Authenticated user, valid form data (title, Run, 5km, future deadline, R100)
**Expected:** Bet created with status=ACTIVE, redirect to bet detail page

#### P0-9: `test_create_bet_past_deadline_rejected`
**Module:** `bet.py:create_bet()`
**Input:** Deadline in the past
**Expected:** Form re-rendered with error message, no bet created

#### P0-10: `test_cancel_bet_updates_status`
**Module:** `bet.py:cancel_bet()`
**Input:** Authenticated user, own active bet
**Expected:** Bet status changed to CANCELLED

#### P0-11: `test_cannot_view_other_users_bet`
**Module:** `bet.py:bet_detail_page()`
**Input:** Authenticated user A tries to view user B's bet by ID
**Expected:** 404 Not Found

#### P0-12: `test_webhook_post_no_authentication`
**Module:** `webhook.py:handle_webhook()`
**Issue:** Currently the POST endpoint has NO authentication. Verify this is intentional (Strava doesn't sign webhook payloads).
**Input:** POST with arbitrary JSON
**Expected:** Document the security implication. Consider adding subscription_id validation.

---

### P1: Must Exist Before Public Launch

#### P1-1: `test_token_refresh_on_expired_token`
**Input:** StravaToken with `expires_at` in the past
**Expected:** Token refreshed via Strava API, new values stored in DB

#### P1-2: `test_token_refresh_failure_handling`
**Input:** Strava returns 401 on refresh (token revoked)
**Expected:** Error logged, user notified, bet stays active

#### P1-3: `test_strava_api_timeout_handling`
**Input:** Strava API hangs for 30 seconds
**Expected:** Request times out gracefully, error logged, no crash

#### P1-4: `test_strava_api_rate_limit_handling`
**Input:** Strava returns HTTP 429
**Expected:** Error logged with retry-after info, no crash

#### P1-5: `test_activity_for_user_with_no_bets`
**Input:** Webhook receives activity create for user with zero active bets
**Expected:** No-op, no errors

#### P1-6: `test_multiple_bets_only_matching_one_wins`
**Input:** User has 3 active bets (Run 5km, Ride 20km, Run 10km), activity is Run 7km
**Expected:** Only "Run 5km" bet marked WON, other two stay ACTIVE

#### P1-7: `test_scheduler_processes_all_users`
**Input:** 3 users each with active bets
**Expected:** Activities fetched for each, all bets checked

#### P1-8: `test_disconnect_strava_deletes_token`
**Input:** Authenticated user POST to `/settings/disconnect`
**Expected:** StravaToken deleted, user account preserved

#### P1-9: `test_delete_account_cascades`
**Input:** Authenticated user POST to `/settings/delete`
**Expected:** User, tokens, bets all deleted. Session cleared.

#### P1-10: `test_export_data_contains_all_user_info`
**Input:** Authenticated user GET `/settings/export`
**Expected:** JSON response with user profile, Strava connection status

#### P1-11: `test_bet_reminder_respects_cooldown`
**Input:** Bet with reminder sent 12 hours ago, cooldown is 24 hours
**Expected:** No new reminder sent

#### P1-12: `test_bet_reminder_sends_when_due`
**Input:** Bet with reminder sent 25 hours ago, cooldown is 24 hours
**Expected:** New reminder sent, count incremented

---

### P2: Edge Cases That Affect Trust (Money Involved)

#### P2-1: `test_manual_strava_activity_not_checked`
**Input:** Activity with `manual: true` field
**Expected:** Currently passes validation — document as known risk. Future: add `manual` field check to `validate_activity_for_bet()`.

#### P2-2: `test_deleted_activity_after_bet_won`
**Input:** Bet was WON by activity 123, then Strava sends delete event for activity 123
**Expected:** Currently no-op — document as known risk. Future: re-evaluate bet status.

#### P2-3: `test_same_activity_wins_only_one_bet_via_webhook`
**Input:** User has two active Run 5km bets, webhook receives one 6km run
**Expected:** Only ONE bet should be marked WON. **Currently both get marked WON in the webhook path (Bug B-DOUBLE-WIN).**

#### P2-4: `test_wager_amount_upper_bound`
**Input:** Create bet with wager_amount=1000000
**Expected:** Currently accepted — document as known risk. Future: add reasonable maximum.

#### P2-5: `test_concurrent_webhook_and_scheduler`
**Input:** Webhook processes activity at same time as scheduler
**Expected:** Only one path should win the bet. ProcessedActivity unique constraint should prevent double-processing.

#### P2-6: `test_bet_created_without_strava_connection`
**Input:** User with no StravaToken creates a bet
**Expected:** Currently allowed — **should be rejected or warned**.

#### P2-7: `test_timezone_deadline_handling`
**Input:** User in SAST (UTC+2) creates bet with deadline "2026-03-07T23:59" via browser
**Expected:** Document how timezone conversion works (currently doesn't — naive datetime stored as-is).

---

## Summary of Critical Bugs Found

| ID | Severity | Description | File:Line |
|---|---|---|---|
| B-DOUBLE-WIN | **HIGH** | Webhook path marks multiple bets as WON from single activity (no `break` in loop) | `bet_validator.py:211` |
| B-STRAVA-DISCONNECT | **MEDIUM** | User can create bet without Strava connection — bet can never be verified | `bet.py:56` |
| B-TZ | **MEDIUM** | Browser datetime-local stored as naive UTC — incorrect for non-UTC users | `bet.py:71-73` |
| B-REMINDER-FK | ~~LOW~~ | ~~Fixed~~ — `BetReminder.bet_id` already has `ondelete="CASCADE"` | `bet_reminder.py:27` |
| B-VERIFIED-DELETE | **MEDIUM** | Deleted Strava activity doesn't invalidate previously-won bet | `webhook.py` (missing handler) |
| B-NO-RATE-LIMIT | **HIGH** | Rate limiter defined but never connected. No protection against abuse on any endpoint. | `rate_limiter.py` + all routes |
| B-WEBHOOK-UNAUTH | **MEDIUM** | POST `/webhooks/strava` accepts arbitrary payloads with no signature verification | `webhook.py:88` |
| B-PRINT-AUTH | **LOW** | `auth.py:143` uses `print()` instead of `logger` for error logging | `auth.py:143` |
| B-NO-TIMEOUT | **MEDIUM** | `StravaClient` creates `httpx.AsyncClient()` with no request timeout | `strava.py:75,98,121,160,180` |
