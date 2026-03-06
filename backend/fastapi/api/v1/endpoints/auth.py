"""
OAuth authentication routes for Strava integration.

Endpoints:
- GET /auth/strava - Redirect to Strava authorization
- GET /auth/callback - Handle OAuth callback from Strava
- GET /auth/logout - Clear session and logout
"""

import secrets
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.models.user import User, StravaToken
from backend.fastapi.services.strava import strava_client

router = APIRouter()


@router.get("/strava")
async def auth_strava(request: Request):
    """
    Initiate Strava OAuth flow.
    
    Generates a state token for CSRF protection and redirects
    the user to Strava's authorization page.
    """
    # Generate a random state token for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    
    # Get the authorization URL
    auth_url = strava_client.get_authorization_url(state=state)
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def auth_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    db: Session = Depends(get_sync_db)
):
    """
    Handle OAuth callback from Strava.
    
    Exchanges the authorization code for access tokens,
    creates or updates the user in the database,
    and sets up the session.
    """
    # Check for errors from Strava
    if error:
        return RedirectResponse(url=f"/?error={error}")
    
    if not code:
        return RedirectResponse(url="/?error=no_code")
    
    # Verify state token (CSRF protection)
    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        return RedirectResponse(url="/?error=invalid_state")
    
    # Clear the state from session
    del request.session["oauth_state"]
    
    try:
        # Exchange the code for tokens
        token_data = await strava_client.exchange_code(code)
        
        # Extract athlete data
        athlete = token_data.get("athlete", {})
        strava_athlete_id = athlete.get("id")
        
        if not strava_athlete_id:
            return RedirectResponse(url="/?error=no_athlete_id")
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            User.strava_athlete_id == strava_athlete_id
        ).first()
        
        if existing_user:
            # Update existing user
            existing_user.firstname = athlete.get("firstname")
            existing_user.lastname = athlete.get("lastname")
            existing_user.profile_picture = athlete.get("profile")
            user = existing_user
            
            # Update or create token for existing user
            existing_token = db.query(StravaToken).filter(
                StravaToken.user_id == user.id
            ).first()
            
            if existing_token:
                existing_token.access_token = token_data["access_token"]
                existing_token.refresh_token = token_data["refresh_token"]
                existing_token.expires_at = token_data["expires_at"]
            else:
                new_token = StravaToken(
                    user_id=user.id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data["refresh_token"],
                    expires_at=token_data["expires_at"],
                    scope="activity:read_all,read"
                )
                db.add(new_token)
        else:
            # Create new user
            user = User(
                strava_athlete_id=strava_athlete_id,
                firstname=athlete.get("firstname"),
                lastname=athlete.get("lastname"),
                profile_picture=athlete.get("profile")
            )
            db.add(user)
            db.flush()  # Get the user ID
            
            # Create token for new user
            token = StravaToken(
                user_id=user.id,
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                expires_at=token_data["expires_at"],
                scope="activity:read_all,read"
            )
            db.add(token)
        
        db.commit()
        
        # Set session data
        request.session["user_id"] = str(user.id)
        request.session["strava_athlete_id"] = strava_athlete_id
        
        # Redirect to dashboard
        return RedirectResponse(url="/dashboard", status_code=302)
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return RedirectResponse(url=f"/?error=auth_failed")


@router.get("/demo-login")
async def demo_login(
    request: Request,
    db: Session = Depends(get_sync_db)
):
    """
    Demo login - bypasses Strava OAuth for local development.
    Creates or finds a demo user and logs them in directly.
    """
    import time
    from backend.fastapi.core.init_settings import global_settings as app_settings
    if getattr(app_settings, 'ENV_MODE', 'prod') != 'dev':
        return RedirectResponse(url="/?error=demo_not_available")

    demo_athlete_id = 12345678

    user = db.query(User).filter(User.strava_athlete_id == demo_athlete_id).first()

    if not user:
        user = User(
            strava_athlete_id=demo_athlete_id,
            firstname="Spencer",
            lastname="Kyle",
            profile_picture=None
        )
        db.add(user)
        db.flush()

        token = StravaToken(
            user_id=user.id,
            access_token="demo_access_token",
            refresh_token="demo_refresh_token",
            expires_at=int(time.time()) + 86400,
            scope="activity:read_all,read"
        )
        db.add(token)
        db.commit()
    else:
        existing_token = db.query(StravaToken).filter(StravaToken.user_id == user.id).first()
        if not existing_token:
            token = StravaToken(
                user_id=user.id,
                access_token="demo_access_token",
                refresh_token="demo_refresh_token",
                expires_at=int(time.time()) + 86400,
                scope="activity:read_all,read"
            )
            db.add(token)
            db.commit()

    request.session["user_id"] = str(user.id)
    request.session["strava_athlete_id"] = demo_athlete_id

    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/logout")
async def auth_logout(request: Request):
    """
    Log out the current user.

    Clears the session and redirects to the landing page.
    """
    request.session.clear()
    return RedirectResponse(url="/")

