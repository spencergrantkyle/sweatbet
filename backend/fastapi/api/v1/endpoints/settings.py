"""
User settings and account management for SweatBet.

Provides functionality for:
- Viewing stored user data
- Exporting data (JSON download)
- Disconnecting Strava
- Deleting account
"""

import json
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.dependencies.auth import get_current_user
from backend.fastapi.models.user import User, StravaToken
from backend.fastapi.services.strava import strava_client

router = APIRouter()

# Templates
templates = Jinja2Templates(directory="frontend/sweatbet/templates")


@router.get("/settings")
async def settings_page(
    request: Request,
    db: Session = Depends(get_sync_db)
):
    """
    Display the user settings page.
    
    Shows stored data and provides options for:
    - Data export
    - Account disconnection
    - Account deletion
    """
    user = await get_current_user(request, db)
    
    if not user:
        return RedirectResponse(url="/")
    
    # Get user's token info (without exposing actual tokens)
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
    db: Session = Depends(get_sync_db)
):
    """
    Export all user data as JSON.
    
    Provides a downloadable file containing all stored user information.
    Required for Strava API compliance and GDPR-style data portability.
    """
    user = await get_current_user(request, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user's token info (without sensitive tokens)
    token = db.query(StravaToken).filter(StravaToken.user_id == user.id).first()
    
    # Compile user data
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
    
    # Return as downloadable JSON
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
    db: Session = Depends(get_sync_db)
):
    """
    Disconnect Strava from the user's account.
    
    Removes stored tokens but keeps the user account.
    User can reconnect later via OAuth.
    """
    user = await get_current_user(request, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Delete user's Strava tokens
    db.query(StravaToken).filter(StravaToken.user_id == user.id).delete()
    db.commit()
    
    return RedirectResponse(url="/settings?disconnected=true", status_code=302)


@router.post("/settings/delete")
async def delete_account(
    request: Request,
    db: Session = Depends(get_sync_db)
):
    """
    Permanently delete the user's account and all associated data.
    
    This action is irreversible and removes:
    - User profile
    - All Strava tokens
    - Any associated bets (future)
    
    Required for Strava API compliance.
    """
    user = await get_current_user(request, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Delete user (cascades to tokens due to relationship config)
    db.delete(user)
    db.commit()
    
    # Clear session
    request.session.clear()
    
    return RedirectResponse(url="/?deleted=true", status_code=302)

