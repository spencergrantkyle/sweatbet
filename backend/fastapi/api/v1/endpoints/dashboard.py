"""
Dashboard routes for authenticated users.

Displays user information and Strava activities.
"""

import uuid

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.models.user import User, StravaToken
from backend.fastapi.models.bet import Bet, BetStatus
from backend.fastapi.services.strava import strava_client

router = APIRouter()

# Templates
templates = Jinja2Templates(directory="frontend/sweatbet/templates")


async def get_current_user(request: Request, db: Session) -> User | None:
    """Get the current authenticated user from session."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    
    # Convert string back to UUID for database query
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return None
    
    user = db.query(User).filter(User.id == user_uuid).first()
    return user


@router.get("/dashboard")
async def dashboard(
    request: Request,
    db: Session = Depends(get_sync_db)
):
    """
    Display the user dashboard with Strava activities.
    
    Requires authentication - redirects to landing if not logged in.
    """
    user = await get_current_user(request, db)
    
    if not user:
        return RedirectResponse(url="/")
    
    # Get user's token
    token = db.query(StravaToken).filter(StravaToken.user_id == user.id).first()
    
    activities = []

    if token:
        # In demo mode, return mock activities instead of calling Strava API
        if token.access_token == "demo_access_token":
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            activities = [
                {
                    "type": "Run",
                    "name": "Morning 5K Run",
                    "start_date_local": (now - timedelta(hours=2)).isoformat() + "Z",
                    "distance": 5200.0,
                    "moving_time": 1680
                },
                {
                    "type": "Run",
                    "name": "Weekend Long Run",
                    "start_date_local": (now - timedelta(days=1, hours=5)).isoformat() + "Z",
                    "distance": 10500.0,
                    "moving_time": 3300
                },
                {
                    "type": "Ride",
                    "name": "Evening Bike Ride",
                    "start_date_local": (now - timedelta(days=2, hours=3)).isoformat() + "Z",
                    "distance": 25000.0,
                    "moving_time": 4200
                },
                {
                    "type": "Run",
                    "name": "Recovery Jog",
                    "start_date_local": (now - timedelta(days=3)).isoformat() + "Z",
                    "distance": 3100.0,
                    "moving_time": 1200
                },
                {
                    "type": "Walk",
                    "name": "Table Mountain Hike",
                    "start_date_local": (now - timedelta(days=4, hours=8)).isoformat() + "Z",
                    "distance": 8500.0,
                    "moving_time": 7200
                },
            ]
        else:
            try:
                # Check if token needs refresh
                access_token, refresh_token, expires_at, was_refreshed = \
                    await strava_client.ensure_valid_token(
                        token.access_token,
                        token.refresh_token,
                        token.expires_at
                    )

                # Update token if it was refreshed
                if was_refreshed:
                    token.access_token = access_token
                    token.refresh_token = refresh_token
                    token.expires_at = expires_at
                    db.commit()

                # Fetch activities
                activities = await strava_client.get_athlete_activities(
                    access_token,
                    per_page=10
                )
            except Exception as e:
                print(f"Error fetching activities: {e}")
                # Continue with empty activities
    
    # Get user's active bets
    active_bets = db.query(Bet).filter(
        Bet.creator_id == user.id,
        Bet.status.in_([BetStatus.PENDING, BetStatus.ACTIVE])
    ).order_by(Bet.deadline.asc()).limit(5).all()
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "activities": activities,
            "active_bets": active_bets
        }
    )

