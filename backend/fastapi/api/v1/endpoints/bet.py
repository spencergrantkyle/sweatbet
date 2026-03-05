"""
Bet routes for creating and managing fitness wagers.

Provides endpoints for bet creation, listing, detail view, and management.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Request, Depends, HTTPException, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.dependencies.auth import get_current_user, require_auth
from backend.fastapi.models.user import User
from backend.fastapi.models.bet import (
    Bet, BetStatus as ModelBetStatus, BetType as ModelBetType,
    ActivityType as ModelActivityType, StakeRecipientType as ModelStakeRecipientType
)
from backend.fastapi.schemas.bet import BetRead, BetSummary

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory="frontend/sweatbet/templates")


@router.get("/bets/create", response_class=HTMLResponse)
async def bet_create_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """Display the bet creation form."""
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

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
    stake_recipient: str = Form("sweatbet"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """Create a new bet from form submission."""
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    # Parse deadline
    try:
        deadline_dt = datetime.fromisoformat(deadline)
    except ValueError:
        return _bet_create_error(request, user, "Invalid deadline format", deadline)

    if deadline_dt <= datetime.utcnow():
        return _bet_create_error(request, user, "Deadline must be in the future", deadline)

    # Validate activity type
    try:
        activity_type_enum = ModelActivityType(activity_type)
    except ValueError:
        return _bet_create_error(request, user, "Invalid activity type", deadline)

    # Parse stake recipient
    try:
        stake_recipient_type = ModelStakeRecipientType(stake_recipient)
    except ValueError:
        stake_recipient_type = ModelStakeRecipientType.SWEATBET

    time_seconds = time_minutes * 60 if time_minutes else None

    bet = Bet(
        creator_id=user.id,
        title=title.strip(),
        description=description.strip() if description else None,
        bet_type=ModelBetType.INDIVIDUAL,
        wager_amount=max(0, wager_amount),
        currency="ZAR",
        activity_type=activity_type_enum,
        distance_km=distance_km if distance_km and distance_km > 0 else None,
        time_seconds=time_seconds,
        deadline=deadline_dt,
        status=ModelBetStatus.ACTIVE,  # Individual bets are active immediately
        stake_recipient_type=stake_recipient_type,
    )

    db.add(bet)
    db.commit()
    db.refresh(bet)

    logger.info(f"Bet created: '{bet.title}' by user {user.id}")
    return RedirectResponse(url=f"/bets/{bet.id}", status_code=status.HTTP_302_FOUND)


def _bet_create_error(request, user, error_msg, deadline_val):
    """Return bet creation form with error."""
    return templates.TemplateResponse(
        "bet_create.html",
        {
            "request": request,
            "user": user,
            "error": error_msg,
            "activity_types": [at.value for at in ModelActivityType],
            "default_deadline": deadline_val,
            "min_deadline": datetime.utcnow().strftime("%Y-%m-%dT%H:%M"),
        },
        status_code=400
    )


@router.get("/bets/{bet_id}", response_class=HTMLResponse)
async def bet_detail_page(
    bet_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """Display detailed view of a single bet."""
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    try:
        bet_uuid = uuid.UUID(bet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bet ID")

    bet = db.query(Bet).filter(Bet.id == bet_uuid, Bet.creator_id == user.id).first()
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")

    return templates.TemplateResponse(
        "bet_detail.html",
        {
            "request": request,
            "user": user,
            "bet": bet,
        }
    )


@router.get("/bets", response_class=HTMLResponse)
async def list_bets(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """Display list of all user's bets."""
    if not user:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    bets = db.query(Bet).filter(Bet.creator_id == user.id).order_by(Bet.created_at.desc()).all()

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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_sync_db)
):
    """Cancel a pending or active bet."""
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

    logger.info(f"Bet cancelled: '{bet.title}' by user {user.id}")
    return RedirectResponse(url="/bets", status_code=status.HTTP_302_FOUND)


# JSON API endpoints
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
