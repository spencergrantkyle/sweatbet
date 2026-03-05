"""
Dashboard routes for authenticated users.

Displays user information, Strava activities, and active bets.
"""

import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.dependencies.auth import get_current_user
from backend.fastapi.models.user import User, StravaToken
from backend.fastapi.models.bet import Bet, BetStatus
from backend.fastapi.services.strava import strava_client

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory="frontend/sweatbet/templates")


@router.get("/dashboard")
async def dashboard(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """Display the user dashboard with Strava activities and active bets."""
    if not user:
        return RedirectResponse(url="/")

    token = db.query(StravaToken).filter(StravaToken.user_id == user.id).first()

    activities = []

    if token:
        try:
            access_token, refresh_token, expires_at, was_refreshed = \
                await strava_client.ensure_valid_token(
                    token.access_token, token.refresh_token, token.expires_at
                )

            if was_refreshed:
                token.access_token = access_token
                token.refresh_token = refresh_token
                token.expires_at = expires_at
                db.commit()

            activities = await strava_client.get_athlete_activities(
                access_token, per_page=10
            )
        except Exception as e:
            logger.error(f"Error fetching activities for user {user.id}: {e}")

    # Get user's active bets
    active_bets = db.query(Bet).filter(
        Bet.creator_id == user.id,
        Bet.status.in_([BetStatus.PENDING, BetStatus.ACTIVE])
    ).order_by(Bet.deadline.asc()).limit(5).all()

    # Get recent completed bets for stats
    total_bets = db.query(Bet).filter(Bet.creator_id == user.id).count()
    won_bets = db.query(Bet).filter(Bet.creator_id == user.id, Bet.status == BetStatus.WON).count()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "activities": activities,
            "active_bets": active_bets,
            "total_bets": total_bets,
            "won_bets": won_bets,
        }
    )
