"""
Landing page route for SweatBet.

Displays the main landing page with Strava connect button.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()

# Templates
templates = Jinja2Templates(directory="frontend/sweatbet/templates")


@router.get("/")
async def landing_page(request: Request, error: str = None):
    """
    Display the SweatBet landing page.
    
    If user is already logged in, redirect to dashboard.
    """
    # Check if user is logged in
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse(
        "landing.html",
        {
            "request": request,
            "auth_url": "/auth/strava",  # Route through proper OAuth endpoint
            "error": error
        }
    )

