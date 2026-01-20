"""
Activity Scheduler Service for SweatBet.

Background scheduler that periodically:
1. Checks for new Strava activities for users with active bets
2. Validates activities against bet requirements
3. Sends reminder notifications for outstanding bets

Uses APScheduler for reliable background task scheduling.
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from backend.fastapi.core.init_settings import global_settings as settings
from backend.fastapi.dependencies.database import SyncSessionLocal
from backend.fastapi.models.bet import Bet, BetStatus
from backend.fastapi.models.user import User, StravaToken
from backend.fastapi.models.processed_activity import ProcessedActivity
from backend.fastapi.models.bet_reminder import BetReminder
from backend.fastapi.services.strava import strava_client
from backend.fastapi.services.telegram import telegram_notifier
from backend.fastapi.services.bet_validator import validate_activity_for_bet

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


def get_db_session() -> Session:
    """Create a new database session for background tasks."""
    return SyncSessionLocal()


async def check_activities_for_active_bets():
    """
    Main job: Check for new Strava activities for all users with active bets.
    
    This function:
    1. Queries all active bets (PENDING/ACTIVE, deadline not passed)
    2. Groups bets by user to minimize API calls
    3. For each user, fetches recent activities from Strava
    4. Validates new activities against their active bets
    5. Records processed activities to prevent duplicates
    """
    logger.info("Starting activity check job...")
    
    db = get_db_session()
    try:
        # Get all active bets that haven't expired
        active_bets = db.query(Bet).filter(
            Bet.status.in_([BetStatus.PENDING, BetStatus.ACTIVE]),
            Bet.deadline > datetime.utcnow()
        ).all()
        
        if not active_bets:
            logger.info("No active bets to check")
            return
        
        logger.info(f"Found {len(active_bets)} active bet(s) to check")
        
        # Group bets by user
        bets_by_user: Dict[Any, List[Bet]] = {}
        for bet in active_bets:
            if bet.creator_id not in bets_by_user:
                bets_by_user[bet.creator_id] = []
            bets_by_user[bet.creator_id].append(bet)
        
        logger.info(f"Checking activities for {len(bets_by_user)} user(s)")
        
        # Process each user
        activities_checked = 0
        bets_won = 0
        
        for user_id, user_bets in bets_by_user.items():
            try:
                result = await process_user_activities(db, user_id, user_bets)
                activities_checked += result.get("activities_checked", 0)
                bets_won += result.get("bets_won", 0)
            except Exception as e:
                logger.error(f"Error processing user {user_id}: {e}")
                continue
        
        logger.info(
            f"Activity check complete: checked {activities_checked} activities, "
            f"{bets_won} bet(s) won"
        )
        
    except Exception as e:
        logger.error(f"Error in activity check job: {e}")
        await telegram_notifier.notify_scheduler_status(
            "error",
            f"Activity check failed: {str(e)}"
        )
    finally:
        db.close()


async def process_user_activities(
    db: Session,
    user_id: Any,
    user_bets: List[Bet]
) -> Dict[str, int]:
    """
    Process activities for a single user.
    
    Args:
        db: Database session
        user_id: User ID to process
        user_bets: List of active bets for this user
        
    Returns:
        Dict with counts of activities checked and bets won
    """
    result = {"activities_checked": 0, "bets_won": 0}
    
    # Get user and their Strava token
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User {user_id} not found")
        return result
    
    token = db.query(StravaToken).filter(StravaToken.user_id == user_id).first()
    if not token:
        logger.warning(f"No Strava token for user {user_id}")
        return result
    
    # Ensure token is valid (refresh if needed)
    try:
        access_token, refresh_token, expires_at, was_refreshed = await strava_client.ensure_valid_token(
            token.access_token,
            token.refresh_token,
            token.expires_at
        )
        
        if was_refreshed:
            token.access_token = access_token
            token.refresh_token = refresh_token
            token.expires_at = expires_at
            db.commit()
            logger.info(f"Refreshed token for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to refresh token for user {user_id}: {e}")
        return result
    
    # Fetch recent activities (lookback period from settings)
    lookback_seconds = settings.ACTIVITY_LOOKBACK_HOURS * 3600
    after_timestamp = int(time.time() - lookback_seconds)
    
    try:
        activities = await strava_client.get_athlete_activities(
            access_token,
            page=1,
            per_page=30,
            after=after_timestamp
        )
    except Exception as e:
        logger.error(f"Failed to fetch activities for user {user_id}: {e}")
        return result
    
    logger.info(f"Fetched {len(activities)} recent activities for user {user.full_name}")
    
    # Process each activity
    for activity in activities:
        activity_id = activity.get("id")
        if not activity_id:
            continue
        
        # Check if activity was already processed
        existing = db.query(ProcessedActivity).filter(
            ProcessedActivity.strava_activity_id == activity_id
        ).first()
        
        if existing:
            logger.debug(f"Activity {activity_id} already processed, skipping")
            continue
        
        result["activities_checked"] += 1
        
        # Validate against each active bet
        for bet in user_bets:
            # Skip if bet is already won
            if bet.status == BetStatus.WON:
                continue
            
            validation = validate_activity_for_bet(activity, bet)
            
            if validation.success:
                # Bet won!
                bet.status = BetStatus.WON
                bet.verified_activity_id = str(activity_id)
                bet.verified_at = datetime.utcnow()
                db.commit()
                
                result["bets_won"] += 1
                logger.info(f"Bet '{bet.title}' marked as WON via scheduler!")
                
                # Send notification
                await telegram_notifier.notify_bet_completed(
                    bet_title=bet.title,
                    activity_name=activity.get("name", "Unknown Activity"),
                    activity_type=activity.get("type", ""),
                    distance_km=activity.get("distance", 0) / 1000,
                    user_name=user.full_name
                )
                
                # Record processed activity
                processed = ProcessedActivity(
                    strava_activity_id=activity_id,
                    user_id=user_id,
                    bet_id=bet.id,
                    validation_result="won",
                    validation_details=validation.reason
                )
                db.add(processed)
                db.commit()
                
                # Break to check next activity (this bet is now won)
                break
            else:
                # Record that we checked this activity (didn't meet requirements)
                logger.debug(f"Activity {activity_id} didn't meet bet requirements: {validation.reason}")
        
        # If activity wasn't matched to any bet, still record it as processed
        existing_record = db.query(ProcessedActivity).filter(
            ProcessedActivity.strava_activity_id == activity_id
        ).first()
        
        if not existing_record:
            processed = ProcessedActivity(
                strava_activity_id=activity_id,
                user_id=user_id,
                bet_id=None,
                validation_result="not_met",
                validation_details="No matching bet requirements"
            )
            db.add(processed)
            db.commit()
    
    return result


async def check_expired_bets():
    """
    Expiration job: Check for bets that have passed their deadline.
    
    This function:
    1. Queries all bets that are still PENDING/ACTIVE but have passed their deadline
    2. Marks them as LOST
    3. Sends Telegram notification to inform the user
    """
    logger.info("Starting expired bets check job...")
    
    db = get_db_session()
    try:
        # Find bets that have expired (deadline passed, still pending/active)
        expired_bets = db.query(Bet).filter(
            Bet.status.in_([BetStatus.PENDING, BetStatus.ACTIVE]),
            Bet.deadline <= datetime.utcnow()
        ).all()
        
        if not expired_bets:
            logger.info("No expired bets found")
            return
        
        logger.info(f"Found {len(expired_bets)} expired bet(s)")
        
        bets_marked_lost = 0
        
        for bet in expired_bets:
            try:
                # Get user info for notification
                user = db.query(User).filter(User.id == bet.creator_id).first()
                user_name = user.full_name if user else "SweatBetter"
                
                # Mark bet as LOST
                bet.status = BetStatus.LOST
                db.commit()
                
                bets_marked_lost += 1
                logger.info(f"Bet '{bet.title}' marked as LOST (expired)")
                
                # Send expiration notification
                await telegram_notifier.notify_bet_expired(
                    bet_title=bet.title,
                    activity_type=bet.activity_type.value,
                    distance_km=bet.distance_km or 0,
                    deadline=bet.deadline,
                    user_name=user_name,
                    wager_amount=bet.wager_amount or 0
                )
                
            except Exception as e:
                logger.error(f"Error processing expired bet {bet.id}: {e}")
                continue
        
        logger.info(f"Expired bets check complete: {bets_marked_lost} bet(s) marked as LOST")
        
    except Exception as e:
        logger.error(f"Error in expired bets check job: {e}")
        await telegram_notifier.notify_scheduler_status(
            "error",
            f"Expired bets check failed: {str(e)}"
        )
    finally:
        db.close()


async def send_outstanding_bet_reminders():
    """
    Reminder job: Send notifications for outstanding bets.
    
    This function:
    1. Queries all outstanding bets (active but not completed)
    2. Checks if a reminder is due (respects cooldown period)
    3. Sends Telegram reminders for bets needing attention
    4. Updates reminder tracking records
    """
    logger.info("Starting reminder check job...")
    
    db = get_db_session()
    try:
        # Get all outstanding bets (active/pending, not completed, not expired)
        outstanding_bets = db.query(Bet).filter(
            Bet.status.in_([BetStatus.PENDING, BetStatus.ACTIVE]),
            Bet.verified_activity_id.is_(None),
            Bet.deadline > datetime.utcnow()
        ).all()
        
        if not outstanding_bets:
            logger.info("No outstanding bets requiring reminders")
            return
        
        logger.info(f"Found {len(outstanding_bets)} outstanding bet(s)")
        
        reminders_sent = 0
        cooldown_hours = settings.REMINDER_COOLDOWN_HOURS
        
        for bet in outstanding_bets:
            try:
                # Get or create reminder tracking record
                reminder = db.query(BetReminder).filter(
                    BetReminder.bet_id == bet.id
                ).first()
                
                if not reminder:
                    # First time checking this bet - create reminder record
                    reminder = BetReminder(bet_id=bet.id)
                    db.add(reminder)
                    db.commit()
                
                # Check if reminder is due
                should_remind = False
                
                if reminder.last_reminder_sent is None:
                    # Never reminded - send first reminder
                    should_remind = True
                else:
                    # Check cooldown period
                    time_since_last = datetime.utcnow() - reminder.last_reminder_sent
                    if time_since_last >= timedelta(hours=cooldown_hours):
                        should_remind = True
                
                if should_remind:
                    # Get user info
                    user = db.query(User).filter(User.id == bet.creator_id).first()
                    user_name = user.full_name if user else "SweatBetter"
                    
                    # Send reminder
                    success = await telegram_notifier.notify_bet_reminder(
                        bet_title=bet.title,
                        activity_type=bet.activity_type.value,
                        distance_km=bet.distance_km or 0,
                        deadline=bet.deadline,
                        user_name=user_name,
                        reminder_count=reminder.reminder_count + 1
                    )
                    
                    if success:
                        # Update reminder record
                        reminder.last_reminder_sent = datetime.utcnow()
                        reminder.reminder_count += 1
                        db.commit()
                        reminders_sent += 1
                        logger.info(f"Sent reminder #{reminder.reminder_count} for bet '{bet.title}'")
                        
            except Exception as e:
                logger.error(f"Error sending reminder for bet {bet.id}: {e}")
                continue
        
        logger.info(f"Reminder check complete: sent {reminders_sent} reminder(s)")
        
    except Exception as e:
        logger.error(f"Error in reminder job: {e}")
        await telegram_notifier.notify_scheduler_status(
            "error",
            f"Reminder check failed: {str(e)}"
        )
    finally:
        db.close()


def start_scheduler():
    """
    Initialize and start the APScheduler.
    
    Sets up three jobs:
    1. Activity check job - runs every ACTIVITY_CHECK_INTERVAL_MINUTES
    2. Expired bets check job - runs every ACTIVITY_CHECK_INTERVAL_MINUTES
    3. Reminder job - runs every REMINDER_CHECK_INTERVAL_HOURS
    """
    global scheduler
    
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler is disabled via settings")
        return
    
    scheduler = AsyncIOScheduler()
    
    # Job 1: Check for new activities
    scheduler.add_job(
        check_activities_for_active_bets,
        trigger=IntervalTrigger(minutes=settings.ACTIVITY_CHECK_INTERVAL_MINUTES),
        id="activity_check",
        name="Check Strava Activities",
        replace_existing=True,
        max_instances=1  # Prevent overlapping runs
    )
    
    # Job 2: Check for expired bets and mark them as LOST
    scheduler.add_job(
        check_expired_bets,
        trigger=IntervalTrigger(minutes=settings.ACTIVITY_CHECK_INTERVAL_MINUTES),
        id="expired_bets_check",
        name="Check Expired Bets",
        replace_existing=True,
        max_instances=1
    )
    
    # Job 3: Send reminders for outstanding bets
    scheduler.add_job(
        send_outstanding_bet_reminders,
        trigger=IntervalTrigger(hours=settings.REMINDER_CHECK_INTERVAL_HOURS),
        id="reminder_check",
        name="Send Bet Reminders",
        replace_existing=True,
        max_instances=1
    )
    
    scheduler.start()
    logger.info(
        f"Activity scheduler started: "
        f"activity check every {settings.ACTIVITY_CHECK_INTERVAL_MINUTES} min, "
        f"expired bets check every {settings.ACTIVITY_CHECK_INTERVAL_MINUTES} min, "
        f"reminders every {settings.REMINDER_CHECK_INTERVAL_HOURS} hour(s)"
    )
    
    # Send startup notification (don't block)
    asyncio.create_task(
        telegram_notifier.notify_scheduler_status(
            "started",
            f"Activity check: {settings.ACTIVITY_CHECK_INTERVAL_MINUTES}min, "
            f"Expired bets: {settings.ACTIVITY_CHECK_INTERVAL_MINUTES}min, "
            f"Reminders: {settings.REMINDER_CHECK_INTERVAL_HOURS}h"
        )
    )


def stop_scheduler():
    """Gracefully stop the scheduler."""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Activity scheduler stopped")
        
        # Note: Can't await in shutdown, so we skip the notification here
        # The scheduler will be restarted on next app startup


def get_scheduler_status() -> Dict[str, Any]:
    """
    Get current scheduler status and job information.
    
    Returns:
        Dict with scheduler status and job details
    """
    if not scheduler:
        return {"running": False, "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None
        })
    
    return {
        "running": scheduler.running,
        "jobs": jobs
    }

