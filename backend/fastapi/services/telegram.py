"""
Telegram notification service for SweatBet.

Sends real-time notifications to Telegram when Strava webhook events occur.
"""

import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from backend.fastapi.core.init_settings import global_settings as settings

logger = logging.getLogger(__name__)

# Telegram Bot API base URL
TELEGRAM_API_BASE = "https://api.telegram.org/bot"


class TelegramNotifier:
    """
    Telegram Bot API client for sending notifications.
    
    Uses the Telegram Bot API to send messages to a configured chat.
    All methods are async and handle errors gracefully to avoid
    blocking the webhook response.
    """
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            logger.warning(
                "Telegram notifications disabled: "
                "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured"
            )
    
    @property
    def api_url(self) -> str:
        """Get the Telegram Bot API URL for this bot."""
        return f"{TELEGRAM_API_BASE}{self.bot_token}"
    
    async def send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        Send a text message to the configured Telegram chat.
        
        Args:
            text: The message text to send
            parse_mode: Message formatting mode (HTML or Markdown)
            disable_notification: If True, send silently
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Telegram notifications disabled, skipping send")
            return False
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                        "disable_notification": disable_notification
                    }
                )
                
                if response.status_code == 200:
                    logger.info("Telegram notification sent successfully")
                    return True
                else:
                    logger.error(
                        f"Telegram API error: {response.status_code} - {response.text}"
                    )
                    return False
                    
        except httpx.TimeoutException:
            logger.error("Telegram API request timed out")
            return False
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")
            return False
    
    async def notify_activity_event(
        self,
        aspect_type: str,
        activity_id: int,
        athlete_id: int,
        updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification for a Strava activity event.
        
        Args:
            aspect_type: Event type (create, update, delete)
            activity_id: Strava activity ID
            athlete_id: Strava athlete ID who owns the activity
            updates: Optional dict of update details
            
        Returns:
            True if notification was sent successfully
        """
        # Choose emoji based on event type
        emoji_map = {
            "create": "🏃",
            "update": "✏️",
            "delete": "🗑️"
        }
        emoji = emoji_map.get(aspect_type, "📍")
        
        # Build the message
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message = f"""
{emoji} <b>Strava Activity Event</b>

<b>Event Type:</b> {aspect_type.upper()}
<b>Activity ID:</b> <code>{activity_id}</code>
<b>Athlete ID:</b> <code>{athlete_id}</code>
<b>Time:</b> {timestamp}
"""
        
        # Add update details if present
        if updates and aspect_type == "update":
            update_details = "\n".join(
                f"  • {k}: {v}" for k, v in updates.items()
            )
            message += f"\n<b>Changes:</b>\n{update_details}"
        
        message += "\n\n<i>SweatBet Webhook Monitor</i>"
        
        return await self.send_message(message)
    
    async def notify_deauthorization(self, athlete_id: int) -> bool:
        """
        Send a notification when a user deauthorizes the app.
        
        Args:
            athlete_id: Strava athlete ID who deauthorized
            
        Returns:
            True if notification was sent successfully
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message = f"""
⚠️ <b>User Deauthorized</b>

<b>Athlete ID:</b> <code>{athlete_id}</code>
<b>Time:</b> {timestamp}

User has revoked access to SweatBet.
Their data has been deleted from the database.

<i>SweatBet Webhook Monitor</i>
"""
        
        return await self.send_message(message)
    
    async def notify_webhook_error(
        self,
        error_message: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification when a webhook processing error occurs.
        
        Args:
            error_message: Description of the error
            event_data: Optional event data that caused the error
            
        Returns:
            True if notification was sent successfully
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message = f"""
🚨 <b>Webhook Error</b>

<b>Error:</b> {error_message}
<b>Time:</b> {timestamp}
"""
        
        if event_data:
            message += f"\n<b>Event Data:</b>\n<code>{event_data}</code>"
        
        message += "\n\n<i>SweatBet Webhook Monitor</i>"
        
        return await self.send_message(message)
    
    async def notify_bet_completed(
        self,
        bet_title: str,
        activity_name: str,
        activity_type: str,
        distance_km: float,
        user_name: str
    ) -> bool:
        """
        Send a notification when a bet is successfully completed.
        
        Args:
            bet_title: Title of the completed bet
            activity_name: Name of the Strava activity that fulfilled the bet
            activity_type: Type of activity (Run, Walk, etc.)
            distance_km: Distance completed in kilometers
            user_name: Name of the user who completed the bet
            
        Returns:
            True if notification was sent successfully
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message = f"""
🎉 <b>BET COMPLETED!</b> 🏆

<b>Congratulations {user_name}!</b>

You've successfully completed your bet!

<b>Bet:</b> {bet_title}
<b>Activity:</b> {activity_name}
<b>Type:</b> {activity_type}
<b>Distance:</b> {distance_km:.2f} km
<b>Time:</b> {timestamp}

Keep up the great work! 💪

<i>SweatBet</i>
"""
        
        return await self.send_message(message)
    
    async def notify_bet_not_met(
        self,
        bet_title: str,
        activity_name: str,
        reason: str,
        user_name: str
    ) -> bool:
        """
        Send a notification when an activity doesn't meet bet requirements.
        
        Args:
            bet_title: Title of the bet being checked
            activity_name: Name of the Strava activity
            reason: Explanation of why the activity didn't meet requirements
            user_name: Name of the user
            
        Returns:
            True if notification was sent successfully
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message = f"""
⚠️ <b>Activity Didn't Meet Bet Requirements</b>

Hey {user_name}, your recent activity didn't fulfill your active bet.

<b>Bet:</b> {bet_title}
<b>Activity:</b> {activity_name}
<b>Reason:</b> {reason}
<b>Time:</b> {timestamp}

Don't give up! You still have time to complete your bet. 🏃‍♂️

<i>SweatBet</i>
"""
        
        return await self.send_message(message)
    
    async def send_test_message(self) -> bool:
        """
        Send a test message to verify the bot is configured correctly.
        
        Returns:
            True if test message was sent successfully
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        message = f"""
✅ <b>SweatBet Bot Connected!</b>

Your Telegram notifications are working correctly.

<b>Time:</b> {timestamp}
<b>Chat ID:</b> <code>{self.chat_id}</code>

You will receive notifications for:
• New Strava activities
• Activity updates
• Activity deletions
• User deauthorizations

<i>SweatBet Webhook Monitor</i>
"""
        
        return await self.send_message(message)

    async def notify_bet_reminder(
        self,
        bet_title: str,
        activity_type: str,
        distance_km: float,
        deadline: datetime,
        user_name: str,
        reminder_count: int = 1
    ) -> bool:
        """
        Send a reminder notification for an outstanding bet.
        
        Args:
            bet_title: Title of the bet
            activity_type: Required activity type (Run, Walk, etc.)
            distance_km: Required distance in kilometers
            deadline: When the bet expires
            user_name: Name of the user
            reminder_count: How many reminders have been sent
            
        Returns:
            True if notification was sent successfully
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Calculate time remaining
        time_remaining = deadline - datetime.utcnow()
        days_left = time_remaining.days
        hours_left = time_remaining.seconds // 3600
        
        if days_left > 0:
            time_display = f"{days_left} day{'s' if days_left != 1 else ''}, {hours_left} hour{'s' if hours_left != 1 else ''}"
        elif hours_left > 0:
            time_display = f"{hours_left} hour{'s' if hours_left != 1 else ''}"
        else:
            minutes_left = time_remaining.seconds // 60
            time_display = f"{minutes_left} minute{'s' if minutes_left != 1 else ''}"
        
        # Format distance display
        distance_display = f"{distance_km:.1f} km" if distance_km else "Any distance"
        
        # Choose urgency emoji based on time remaining
        if days_left < 1:
            urgency_emoji = "🚨"
            urgency_text = "TIME IS RUNNING OUT!"
        elif days_left < 3:
            urgency_emoji = "⏰"
            urgency_text = "Don't forget your bet!"
        else:
            urgency_emoji = "📣"
            urgency_text = "Friendly reminder!"
        
        message = f"""
{urgency_emoji} <b>SweatBet Reminder</b> {urgency_emoji}

Hey {user_name}! {urgency_text}

You have an active bet waiting to be completed:

<b>Bet:</b> {bet_title}
<b>Activity:</b> {activity_type}
<b>Distance:</b> {distance_display}
<b>Time Remaining:</b> {time_display}
<b>Deadline:</b> {deadline.strftime('%Y-%m-%d %H:%M UTC')}

Get moving and crush your goal! 💪🏃‍♂️

<i>Reminder #{reminder_count} - SweatBet</i>
"""
        
        return await self.send_message(message)

    async def notify_scheduler_status(
        self,
        status: str,
        details: Optional[str] = None
    ) -> bool:
        """
        Send a notification about scheduler status (start/stop/error).
        
        Args:
            status: Status message (e.g., "started", "stopped", "error")
            details: Optional additional details
            
        Returns:
            True if notification was sent successfully
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        emoji_map = {
            "started": "🟢",
            "stopped": "🔴",
            "error": "⚠️",
            "check_complete": "✅"
        }
        emoji = emoji_map.get(status, "ℹ️")
        
        message = f"""
{emoji} <b>Scheduler Status: {status.upper()}</b>

<b>Time:</b> {timestamp}
"""
        
        if details:
            message += f"\n<b>Details:</b> {details}"
        
        message += "\n\n<i>SweatBet Activity Scheduler</i>"
        
        return await self.send_message(message, disable_notification=True)

    async def notify_bet_expired(
        self,
        bet_title: str,
        activity_type: str,
        distance_km: float,
        deadline: datetime,
        user_name: str,
        wager_amount: float = 0.0
    ) -> bool:
        """
        Send a notification when a bet has expired (deadline passed without completion).
        
        Args:
            bet_title: Title of the expired bet
            activity_type: Required activity type (Run, Walk, etc.)
            distance_km: Required distance in kilometers
            deadline: When the bet expired
            user_name: Name of the user
            wager_amount: Amount wagered on the bet
            
        Returns:
            True if notification was sent successfully
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Format distance display
        distance_display = f"{distance_km:.1f} km" if distance_km else "Any distance"
        
        # Format wager display
        wager_display = f"${wager_amount:.2f}" if wager_amount > 0 else "No wager"
        
        message = f"""
💔 <b>BET EXPIRED</b> 💔

Hey {user_name}, unfortunately your bet has expired.

<b>Bet:</b> {bet_title}
<b>Activity Type:</b> {activity_type}
<b>Required Distance:</b> {distance_display}
<b>Deadline:</b> {deadline.strftime('%Y-%m-%d %H:%M UTC')}
<b>Wager:</b> {wager_display}

The deadline has passed without a qualifying activity being recorded.

Don't be discouraged! Create a new bet and try again. 💪

<b>Expired at:</b> {timestamp}

<i>SweatBet</i>
"""
        
        return await self.send_message(message)


# Global notifier instance
telegram_notifier = TelegramNotifier()

