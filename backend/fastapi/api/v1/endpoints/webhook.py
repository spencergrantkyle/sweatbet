"""
Strava webhook handler for SweatBet.

Handles webhook events from Strava including:
- Webhook verification challenge
- Deauthorization events (user revokes access in Strava)
- Activity events (for bet verification and notifications)

Sends Telegram notifications for all events.
"""

import hmac
import hashlib
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.models.user import User, StravaToken
from backend.fastapi.core.init_settings import global_settings as settings
from backend.fastapi.services.telegram import telegram_notifier
from backend.fastapi.services.bet_validator import process_new_activity

router = APIRouter()


@router.get("/webhooks/strava")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Handle Strava webhook subscription verification.
    
    When creating a webhook subscription, Strava sends a GET request
    with a challenge that must be echoed back.
    
    Query params from Strava:
    - hub.mode: Should be "subscribe"
    - hub.challenge: Random string to echo back
    - hub.verify_token: Token we provided when creating subscription
    
    CRITICAL: Must respond within 2 seconds and return the challenge.
    """
    # Log the verification attempt
    print(f"Webhook verification request: mode={hub_mode}, token={hub_verify_token}")
    
    # Verify the mode is subscribe
    if hub_mode != "subscribe":
        print(f"Invalid hub.mode: {hub_mode}")
        raise HTTPException(status_code=400, detail="Invalid hub.mode")
    
    # Verify challenge is provided
    if not hub_challenge:
        print("Missing hub.challenge")
        raise HTTPException(status_code=400, detail="Missing hub.challenge")
    
    # Verify the token matches what we configured
    expected_verify_token = settings.STRAVA_WEBHOOK_VERIFY_TOKEN
    
    if hub_verify_token != expected_verify_token:
        print(f"Webhook verify token mismatch: expected '{expected_verify_token}', got '{hub_verify_token}'")
        raise HTTPException(status_code=403, detail="Invalid verify token")
    
    # SUCCESS: Return the challenge to confirm subscription
    print(f"Webhook verification successful! Returning challenge.")
    return JSONResponse(content={"hub.challenge": hub_challenge})


@router.post("/webhooks/strava")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_sync_db)
):
    """
    Handle incoming Strava webhook events.
    
    Event types:
    - deauthorization: User revoked access via Strava settings
    - activity: Activity created/updated/deleted
    - athlete: Athlete profile updated
    
    For SweatBet, we primarily care about:
    1. Deauthorization - clean up user data
    2. Activity events - for bet verification
    
    Sends Telegram notifications for all events (in background).
    CRITICAL: Must respond with 200 OK within 2 seconds.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    # Log incoming webhook for debugging
    print(f"Strava webhook received: {body}")
    
    # Extract event details
    object_type = body.get("object_type")  # "athlete" or "activity"
    aspect_type = body.get("aspect_type")  # "create", "update", "delete"
    owner_id = body.get("owner_id")  # Strava athlete ID
    object_id = body.get("object_id")  # Activity ID or athlete ID
    updates = body.get("updates", {})  # Contains details for update events
    
    # Handle deauthorization event
    # When a user revokes access in Strava, we receive an athlete update
    # with "authorized": "false" in the updates
    if object_type == "athlete" and aspect_type == "update":
        if updates.get("authorized") == "false":
            await handle_deauthorization(owner_id, db)
            # Send Telegram notification in background
            background_tasks.add_task(
                telegram_notifier.notify_deauthorization,
                owner_id
            )
            return JSONResponse(content={"status": "processed", "action": "deauthorization"})
    
    # Handle activity events
    if object_type == "activity":
        print(f"Activity event: {aspect_type} for activity {object_id} by athlete {owner_id}")
        
        # Send Telegram notification in background (doesn't block response)
        background_tasks.add_task(
            telegram_notifier.notify_activity_event,
            aspect_type,
            object_id,
            owner_id,
            updates
        )
        
        # Trigger bet verification when activity is created
        if aspect_type == "create":
            print(f"Triggering bet validation for new activity {object_id}")
            background_tasks.add_task(
                process_new_activity,
                object_id,
                owner_id,
                db
            )
        
        return JSONResponse(content={"status": "processed", "action": f"activity_{aspect_type}"})
    
    # Default response for unhandled events
    return JSONResponse(content={"status": "received"})


async def handle_deauthorization(strava_athlete_id: int, db: Session):
    """Handle deauthorization event - clean up all user data for Strava compliance."""
    import logging
    logger = logging.getLogger(__name__)

    if not strava_athlete_id:
        logger.warning("Deauthorization event received without athlete ID")
        return

    user = db.query(User).filter(User.strava_athlete_id == strava_athlete_id).first()

    if not user:
        logger.warning(f"No user found for Strava athlete ID: {strava_athlete_id}")
        return

    # Count records for audit log before deletion
    from backend.fastapi.models.bet import Bet
    from backend.fastapi.models.processed_activity import ProcessedActivity

    bet_count = db.query(Bet).filter(Bet.creator_id == user.id).count()
    activity_count = db.query(ProcessedActivity).filter(ProcessedActivity.user_id == user.id).count()
    token_count = db.query(StravaToken).filter(StravaToken.user_id == user.id).count()

    logger.info(
        f"Deauthorization audit: user={user.id}, athlete={strava_athlete_id}, "
        f"bets={bet_count}, activities={activity_count}, tokens={token_count}, "
        f"timestamp={datetime.utcnow().isoformat()}"
    )

    # Delete the user - cascades to all related data
    db.delete(user)
    db.commit()

    logger.info(f"Deauthorization complete: all data deleted for user {user.id}")

