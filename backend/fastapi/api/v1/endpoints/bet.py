"""
Bet routes for creating and managing fitness wagers.

Provides endpoints for bet creation, listing, and management.
"""

import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Request, Depends, HTTPException, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.dependencies.auth import get_current_user, require_auth
from backend.fastapi.models.user import User
from backend.fastapi.models.bet import Bet, BetStatus as ModelBetStatus, ActivityType as ModelActivityType
from backend.fastapi.schemas.bet import BetCreate, BetRead, BetSummary

router = APIRouter()

# Templates
templates = Jinja2Templates(directory="frontend/sweatbet/templates")


@router.get("/bets/create", response_class=HTMLResponse)
async def bet_create_page(
    request: Request,
    db: Session = Depends(get_sync_db)
):
    """
    Display the bet creation form.
    
    Requires authentication - redirects to landing if not logged in.
    """
    user = await get_current_user(request, db)
    
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    # Default deadline is 1 week from now
    default_deadline = datetime.utcnow() + timedelta(days=7)
    
    return templates.TemplateResponse(
        "bet_create.html",
        {
            "request": request,
            "user": user,
            "activity_types": [at.value for at in ModelActivityType],
            "default_deadline": default_deadline.strftime("%Y-%m-%dT%H:%M"),
            "min_deadline": datetime.utcnow().strftime("%Y-%m-%dT%H:%M"),
        }
    )


@router.post("/bets/create")
async def create_bet(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    activity_type: str = Form(...),
    distance_km: float = Form(None),
    time_minutes: int = Form(None),
    wager_amount: float = Form(0),
    deadline: str = Form(...),
    db: Session = Depends(get_sync_db)
):
    """
    Create a new bet.
    
    Form submission endpoint that creates a bet and redirects to dashboard.
    """
    user = await get_current_user(request, db)
    
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    # Parse deadline
    try:
        deadline_dt = datetime.fromisoformat(deadline)
    except ValueError:
        return templates.TemplateResponse(
            "bet_create.html",
            {
                "request": request,
                "user": user,
                "error": "Invalid deadline format",
                "activity_types": [at.value for at in ModelActivityType],
                "default_deadline": deadline,
                "min_deadline": datetime.utcnow().strftime("%Y-%m-%dT%H:%M"),
            },
            status_code=400
        )
    
    # Validate deadline is in future
    if deadline_dt <= datetime.utcnow():
        return templates.TemplateResponse(
            "bet_create.html",
            {
                "request": request,
                "user": user,
                "error": "Deadline must be in the future",
                "activity_types": [at.value for at in ModelActivityType],
                "default_deadline": deadline,
                "min_deadline": datetime.utcnow().strftime("%Y-%m-%dT%H:%M"),
            },
            status_code=400
        )
    
    # Validate activity type
    try:
        activity_type_enum = ModelActivityType(activity_type)
    except ValueError:
        return templates.TemplateResponse(
            "bet_create.html",
            {
                "request": request,
                "user": user,
                "error": "Invalid activity type",
                "activity_types": [at.value for at in ModelActivityType],
                "default_deadline": deadline,
                "min_deadline": datetime.utcnow().strftime("%Y-%m-%dT%H:%M"),
            },
            status_code=400
        )
    
    # Convert time from minutes to seconds
    time_seconds = time_minutes * 60 if time_minutes else None
    
    # Create the bet
    bet = Bet(
        creator_id=user.id,
        title=title.strip(),
        description=description.strip() if description else None,
        wager_amount=max(0, wager_amount),
        activity_type=activity_type_enum,
        distance_km=distance_km if distance_km and distance_km > 0 else None,
        time_seconds=time_seconds,
        deadline=deadline_dt,
        status=ModelBetStatus.PENDING
    )
    
    db.add(bet)
    db.commit()
    db.refresh(bet)

    return RedirectResponse(url=f"/bet/{bet.id}/confirm", status_code=status.HTTP_302_FOUND)


@router.get("/bets", response_class=HTMLResponse)
async def list_bets(
    request: Request,
    db: Session = Depends(get_sync_db)
):
    """
    Display list of all user's bets.
    """
    user = await get_current_user(request, db)
    
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    # Get all bets for this user
    bets = db.query(Bet).filter(Bet.creator_id == user.id).order_by(Bet.created_at.desc()).all()
    
    # Separate by status
    active_bets = [b for b in bets if b.status in (ModelBetStatus.PENDING, ModelBetStatus.ACTIVE)]
    completed_bets = [b for b in bets if b.status in (ModelBetStatus.WON, ModelBetStatus.LOST)]
    cancelled_bets = [b for b in bets if b.status == ModelBetStatus.CANCELLED]
    
    return templates.TemplateResponse(
        "bets_list.html",
        {
            "request": request,
            "user": user,
            "active_bets": active_bets,
            "completed_bets": completed_bets,
            "cancelled_bets": cancelled_bets,
        }
    )


@router.post("/bets/{bet_id}/cancel")
async def cancel_bet(
    bet_id: str,
    request: Request,
    db: Session = Depends(get_sync_db)
):
    """
    Cancel a pending bet.
    """
    user = await get_current_user(request, db)
    
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    try:
        bet_uuid = uuid.UUID(bet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bet ID")
    
    bet = db.query(Bet).filter(Bet.id == bet_uuid, Bet.creator_id == user.id).first()
    
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    if bet.status not in (ModelBetStatus.PENDING, ModelBetStatus.ACTIVE):
        raise HTTPException(status_code=400, detail="Cannot cancel completed bet")
    
    bet.status = ModelBetStatus.CANCELLED
    db.commit()
    
    return RedirectResponse(url="/bets", status_code=status.HTTP_302_FOUND)


# API endpoints for future use
@router.get("/api/v1/bets", response_model=List[BetSummary])
async def api_list_bets(
    user: User = Depends(require_auth),
    db: Session = Depends(get_sync_db)
):
    """API endpoint to list user's bets."""
    bets = db.query(Bet).filter(Bet.creator_id == user.id).order_by(Bet.created_at.desc()).all()
    return bets


@router.get("/api/v1/bets/{bet_id}", response_model=BetRead)
async def api_get_bet(
    bet_id: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_sync_db)
):
    """API endpoint to get a specific bet."""
    try:
        bet_uuid = uuid.UUID(bet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bet ID")
    
    bet = db.query(Bet).filter(Bet.id == bet_uuid, Bet.creator_id == user.id).first()
    
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    return bet

