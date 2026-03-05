"""
User settings and account management for SweatBet.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.dependencies.auth import get_current_user
from backend.fastapi.models.user import User, StravaToken

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory="frontend/sweatbet/templates")


@router.get("/settings")
async def settings_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """Display the user settings page."""
    if not user:
        return RedirectResponse(url="/")

    token = db.query(StravaToken).filter(StravaToken.user_id == user.id).first()

    token_info = None
    if token:
        token_info = {
            "scope": token.scope,
            "expires_at": datetime.fromtimestamp(token.expires_at).isoformat() if token.expires_at else None,
            "created_at": token.created_at.isoformat() if token.created_at else None
        }

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user": user,
            "token_info": token_info
        }
    )


@router.get("/settings/export")
async def export_user_data(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """Export all user data as JSON. Required for Strava API and POPIA compliance."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = db.query(StravaToken).filter(StravaToken.user_id == user.id).first()

    export_data = {
        "export_date": datetime.utcnow().isoformat(),
        "user": {
            "id": str(user.id),
            "strava_athlete_id": user.strava_athlete_id,
            "firstname": user.firstname,
            "lastname": user.lastname,
            "profile_picture": user.profile_picture,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None
        },
        "strava_connection": {
            "connected": token is not None,
            "scope": token.scope if token else None,
            "token_expires_at": datetime.fromtimestamp(token.expires_at).isoformat() if token and token.expires_at else None,
            "connection_created_at": token.created_at.isoformat() if token and token.created_at else None
        }
    }

    return JSONResponse(
        content=export_data,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="sweatbet_data_export_{datetime.utcnow().strftime("%Y%m%d")}.json"'
        }
    )


@router.post("/settings/disconnect")
async def disconnect_strava(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """Disconnect Strava from the user's account."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db.query(StravaToken).filter(StravaToken.user_id == user.id).delete()
    db.commit()

    logger.info(f"User {user.id} disconnected Strava")
    return RedirectResponse(url="/settings?disconnected=true", status_code=302)


@router.post("/settings/delete")
async def delete_account(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """Permanently delete the user's account and all associated data."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    logger.info(f"Deleting account for user {user.id}")
    db.delete(user)
    db.commit()

    request.session.clear()
    return RedirectResponse(url="/?deleted=true", status_code=302)
