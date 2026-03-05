"""
Strava webhook handler for SweatBet.

Handles webhook events from Strava including:
- Webhook verification challenge
- Deauthorization events (user revokes access in Strava)
- Activity events (for bet verification and notifications)
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from backend.fastapi.dependencies.database import SyncSessionLocal
from backend.fastapi.models.user import User
from backend.fastapi.core.init_settings import global_settings as settings
from backend.fastapi.services.telegram import telegram_notifier
from backend.fastapi.services.bet_validator import process_new_activity

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhooks/strava")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    Handle Strava webhook subscription verification.

    CRITICAL: Must respond within 2 seconds and return the challenge.
    """
    logger.info(f"Webhook verification request: mode={hub_mode}")

    if hub_mode != "subscribe":
        raise HTTPException(status_code=400, detail="Invalid hub.mode")

    if not hub_challenge:
        raise HTTPException(status_code=400, detail="Missing hub.challenge")

    if hub_verify_token != settings.STRAVA_WEBHOOK_VERIFY_TOKEN:
        logger.warning("Webhook verify token mismatch")
        raise HTTPException(status_code=403, detail="Invalid verify token")

    logger.info("Webhook verification successful!")
    return JSONResponse(content={"hub.challenge": hub_challenge})


async def _process_activity_background(activity_id: int, athlete_id: int):
    """Background task for processing activities with its own db session."""
    db = SyncSessionLocal()
    try:
        await process_new_activity(activity_id, athlete_id, db)
    except Exception as e:
        logger.error(f"Background activity processing failed: {e}")
        await telegram_notifier.notify_webhook_error(
            f"Background processing failed for activity {activity_id}",
            {"activity_id": activity_id, "athlete_id": athlete_id, "error": str(e)}
        )
    finally:
        db.close()


async def _handle_deauthorization_background(strava_athlete_id: int):
    """Background task for handling deauthorization with its own db session."""
    db = SyncSessionLocal()
    try:
        if not strava_athlete_id:
            logger.warning("Deauthorization event received without athlete ID")
            return

        user = db.query(User).filter(User.strava_athlete_id == strava_athlete_id).first()
        if not user:
            logger.warning(f"No user found for Strava athlete ID: {strava_athlete_id}")
            return

        logger.info(f"Processing deauthorization for user {user.id} (athlete {strava_athlete_id})")
        db.delete(user)
        db.commit()
        logger.info(f"Deleted user {user.id} due to Strava deauthorization")

        await telegram_notifier.notify_deauthorization(strava_athlete_id)
    except Exception as e:
        logger.error(f"Error handling deauthorization for athlete {strava_athlete_id}: {e}")
    finally:
        db.close()


@router.post("/webhooks/strava")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Handle incoming Strava webhook events.

    CRITICAL: Must respond with 200 OK within 2 seconds.
    All heavy processing happens in background tasks with their own db sessions.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    logger.info(f"Strava webhook received: {body}")

    object_type = body.get("object_type")
    aspect_type = body.get("aspect_type")
    owner_id = body.get("owner_id")
    object_id = body.get("object_id")
    updates = body.get("updates", {})

    # Handle deauthorization event
    if object_type == "athlete" and aspect_type == "update":
        if updates.get("authorized") == "false":
            background_tasks.add_task(_handle_deauthorization_background, owner_id)
            return JSONResponse(content={"status": "processed", "action": "deauthorization"})

    # Handle activity events
    if object_type == "activity":
        logger.info(f"Activity event: {aspect_type} for activity {object_id} by athlete {owner_id}")

        background_tasks.add_task(
            telegram_notifier.notify_activity_event,
            aspect_type, object_id, owner_id, updates
        )

        if aspect_type == "create":
            logger.info(f"Triggering bet validation for new activity {object_id}")
            background_tasks.add_task(_process_activity_background, object_id, owner_id)

        return JSONResponse(content={"status": "processed", "action": f"activity_{aspect_type}"})

    return JSONResponse(content={"status": "received"})
