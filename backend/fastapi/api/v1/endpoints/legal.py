"""
Legal pages for SweatBet - Privacy Policy and Terms of Service.

These pages are required for Strava API approval.
"""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

# Templates
templates = Jinja2Templates(directory="frontend/sweatbet/templates")


@router.get("/privacy")
async def privacy_policy(request: Request):
    """
    Display the Privacy Policy page.
    
    Required by Strava for API approval - covers data collection,
    usage, retention, and user rights.
    """
    return templates.TemplateResponse(
        "privacy.html",
        {
            "request": request,
            "user": request.session.get("user_id")  # For nav state
        }
    )


@router.get("/terms")
async def terms_of_service(request: Request):
    """
    Display the Terms of Service page.
    
    Covers service description, user responsibilities,
    liability limitations, and dispute resolution.
    """
    return templates.TemplateResponse(
        "terms.html",
        {
            "request": request,
            "user": request.session.get("user_id")  # For nav state
        }
    )

