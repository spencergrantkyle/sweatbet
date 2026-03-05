"""
Bet validation service for SweatBet.

Validates Strava activities against active bets to determine if
bet requirements have been met.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

from sqlalchemy.orm import Session

from backend.fastapi.models.bet import Bet, BetStatus, ActivityType
from backend.fastapi.models.user import User, StravaToken
from backend.fastapi.services.strava import strava_client
from backend.fastapi.services.telegram import telegram_notifier

logger = logging.getLogger(__name__)


class BetValidationResult:
    """Result of validating an activity against a bet."""
    
    def __init__(
        self,
        bet: Bet,
        success: bool,
        reason: str,
        activity_data: Optional[Dict[str, Any]] = None
    ):
        self.bet = bet
        self.success = success
        self.reason = reason
        self.activity_data = activity_data


def validate_activity_for_bet(
    activity: Dict[str, Any],
    bet: Bet
) -> BetValidationResult:
    """
    Validate if a Strava activity meets the requirements of a bet.
    
    Args:
        activity: Strava activity data from API
        bet: The bet to validate against
        
    Returns:
        BetValidationResult with success status and reason
    """
    # Extract activity details
    activity_type = activity.get("type", "")
    activity_distance_meters = activity.get("distance", 0)
    activity_distance_km = activity_distance_meters / 1000
    activity_moving_time = activity.get("moving_time", 0)  # seconds
    activity_start_date = activity.get("start_date")  # ISO format
    
    logger.info(
        f"Validating activity: type={activity_type}, distance={activity_distance_km:.2f}km, "
        f"time={activity_moving_time}s against bet: {bet.title}"
    )
    
    # Check 1: Activity type must match
    if activity_type != bet.activity_type.value:
        return BetValidationResult(
            bet=bet,
            success=False,
            reason=f"Activity type '{activity_type}' does not match required type '{bet.activity_type.value}'",
            activity_data=activity
        )
    
    # Check 2: Parse activity start time and verify it's before deadline
    if activity_start_date:
        try:
            # Strava returns ISO format: "2024-01-15T10:30:00Z"
            activity_datetime = datetime.fromisoformat(activity_start_date.replace("Z", "+00:00"))
            # Convert to naive UTC for comparison with bet deadline
            activity_datetime = activity_datetime.replace(tzinfo=None)
            
            if activity_datetime > bet.deadline:
                return BetValidationResult(
                    bet=bet,
                    success=False,
                    reason=f"Activity started after bet deadline ({bet.deadline.strftime('%Y-%m-%d %H:%M')})",
                    activity_data=activity
                )
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse activity start date: {activity_start_date}, error: {e}")
    
    # Check 3: Distance must meet requirement (if specified)
    if bet.distance_km is not None and bet.distance_km > 0:
        if activity_distance_km < bet.distance_km:
            return BetValidationResult(
                bet=bet,
                success=False,
                reason=f"Distance {activity_distance_km:.2f}km is less than required {bet.distance_km:.2f}km",
                activity_data=activity
            )
    
    # Check 4: Time limit (if specified) - activity must be completed within time limit
    if bet.time_seconds is not None and bet.time_seconds > 0:
        if activity_moving_time > bet.time_seconds:
            bet_time_display = f"{bet.time_seconds // 60}m {bet.time_seconds % 60}s"
            activity_time_display = f"{activity_moving_time // 60}m {activity_moving_time % 60}s"
            return BetValidationResult(
                bet=bet,
                success=False,
                reason=f"Activity time {activity_time_display} exceeds limit of {bet_time_display}",
                activity_data=activity
            )
    
    # All checks passed!
    return BetValidationResult(
        bet=bet,
        success=True,
        reason=f"Activity meets all bet requirements! Distance: {activity_distance_km:.2f}km",
        activity_data=activity
    )


async def process_new_activity(
    activity_id: int,
    athlete_id: int,
    db: Session
) -> List[BetValidationResult]:
    """
    Process a new Strava activity and validate it against the user's active bets.
    
    This is the main orchestration function called from the webhook handler.
    
    Args:
        activity_id: Strava activity ID
        athlete_id: Strava athlete ID who owns the activity
        db: Database session
        
    Returns:
        List of validation results for each bet checked
    """
    results = []
    
    # Step 1: Find the user by Strava athlete ID
    user = db.query(User).filter(User.strava_athlete_id == athlete_id).first()
    
    if not user:
        logger.warning(f"No user found for Strava athlete ID: {athlete_id}")
        return results
    
    logger.info(f"Processing activity {activity_id} for user {user.full_name} (ID: {user.id})")
    
    # Step 2: Get user's active bets (PENDING or ACTIVE status, not expired)
    active_bets = db.query(Bet).filter(
        Bet.creator_id == user.id,
        Bet.status.in_([BetStatus.PENDING, BetStatus.ACTIVE]),
        Bet.deadline > datetime.utcnow()
    ).all()
    
    if not active_bets:
        logger.info(f"User {user.id} has no active bets to validate")
        return results
    
    logger.info(f"Found {len(active_bets)} active bet(s) to check")
    
    # Step 3: Get user's Strava token
    token = db.query(StravaToken).filter(StravaToken.user_id == user.id).first()
    
    if not token:
        logger.error(f"No Strava token found for user {user.id}")
        await telegram_notifier.notify_webhook_error(
            f"Cannot validate bet - no Strava token for user {user.full_name}",
            {"activity_id": activity_id, "athlete_id": athlete_id}
        )
        return results
    
    # Step 4: Ensure token is valid (refresh if needed)
    try:
        access_token, refresh_token, expires_at, was_refreshed = await strava_client.ensure_valid_token(
            token.access_token,
            token.refresh_token,
            token.expires_at
        )
        
        # Update token in database if it was refreshed
        if was_refreshed:
            token.access_token = access_token
            token.refresh_token = refresh_token
            token.expires_at = expires_at
            db.commit()
            logger.info(f"Refreshed Strava token for user {user.id}")
    except Exception as e:
        logger.error(f"Failed to refresh Strava token for user {user.id}: {e}")
        await telegram_notifier.notify_webhook_error(
            f"Token refresh failed for user {user.full_name}",
            {"activity_id": activity_id, "error": str(e)}
        )
        return results
    
    # Step 5: Fetch activity details from Strava API
    try:
        activity = await strava_client.get_activity(access_token, activity_id)
        logger.info(f"Fetched activity: {activity.get('name')} ({activity.get('type')})")
    except Exception as e:
        logger.error(f"Failed to fetch activity {activity_id} from Strava: {e}")
        await telegram_notifier.notify_webhook_error(
            f"Failed to fetch activity details from Strava",
            {"activity_id": activity_id, "error": str(e)}
        )
        return results
    
    # Step 6: Validate activity against each active bet
    for bet in active_bets:
        result = validate_activity_for_bet(activity, bet)
        results.append(result)
        
        if result.success:
            # Bet requirements met - update status to WON
            bet.status = BetStatus.WON
            bet.verified_activity_id = str(activity_id)
            bet.verified_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Bet '{bet.title}' (ID: {bet.id}) marked as WON!")
            
            # Send success notification
            await telegram_notifier.notify_bet_completed(
                bet_title=bet.title,
                activity_name=activity.get("name", "Unknown Activity"),
                activity_type=activity.get("type", ""),
                distance_km=activity.get("distance", 0) / 1000,
                user_name=user.full_name
            )

            # Only one bet should be won per activity
            break
        else:
            # Bet requirements not met - send notification but don't change status
            logger.info(f"Bet '{bet.title}' not satisfied: {result.reason}")
            
            await telegram_notifier.notify_bet_not_met(
                bet_title=bet.title,
                activity_name=activity.get("name", "Unknown Activity"),
                reason=result.reason,
                user_name=user.full_name
            )
    
    return results

