"""
Bet confirmation endpoint - view and confirm/decline bets.
Sends Telegram notifications on confirm/decline actions.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.dependencies.auth import get_current_user
from backend.fastapi.models.bet import Bet, BetStatus
from backend.fastapi.models.user import User
from backend.fastapi.services.telegram import telegram_notifier

router = APIRouter()
templates = Jinja2Templates(directory="frontend/sweatbet/templates")


class ConfirmAction(BaseModel):
    action: str  # "confirm" or "decline"


@router.get("/bet/{bet_id}/confirm")
async def bet_confirm_page(
    bet_id: str,
    request: Request,
    db: Session = Depends(get_sync_db)
):
    """Display the bet confirmation page."""
    try:
        bet_uuid = uuid.UUID(bet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bet ID")

    bet = db.query(Bet).filter(Bet.id == bet_uuid).first()
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")

    creator = db.query(User).filter(User.id == bet.creator_id).first()

    # Build template-compatible bet dict
    bet_data = {
        "id": str(bet.id),
        "betType": "Solo Challenge",
        "challengeName": bet.title,
        "betName": bet.title,
        "activityType": bet.activity_type.value,
        "activityIcon": _get_activity_icon(bet.activity_type.value),
        "weeklyTarget": bet.distance_km or 0,
        "metricTarget": bet.distance_km or 0,
        "metricUnit": "km",
        "durationWeeks": max(1, (bet.deadline - bet.created_at).days // 7) if bet.deadline and bet.created_at else 1,
        "startDate": bet.created_at.strftime("%Y-%m-%d") if bet.created_at else "",
        "endDate": bet.deadline.strftime("%Y-%m-%d") if bet.deadline else "",
        "timezone": "UTC",
        "stakeAmount": bet.wager_amount or 0,
        "currency": "ZAR",
        "currencySymbol": "R",
        "recipientIfFail": "the pot",
        "termsAndConditions": (
            f"1. Complete the required {bet.activity_type.value} activity before the deadline. "
            f"2. All activities must be recorded and verified via Strava. "
            f"3. Manual entries do not count. "
            f"4. The bet is settled automatically based on Strava data."
        ),
        "participants": [
            {
                "id": str(bet.creator_id),
                "name": creator.firstname or "Creator" if creator else "Creator",
                "initials": _get_initials(creator) if creator else "?",
                "role": "Challenger",
                "confirmed": bet.status != BetStatus.PENDING,
            },
        ],
        "status": bet.status.value,
    }

    return templates.TemplateResponse(
        "bet_confirm.html",
        {"request": request, "bet": bet_data},
    )


@router.post("/bet/{bet_id}/confirm")
async def bet_confirm_action(
    bet_id: str,
    body: ConfirmAction,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_sync_db),
):
    """Confirm or decline a bet."""
    try:
        bet_uuid = uuid.UUID(bet_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bet ID")

    bet = db.query(Bet).filter(Bet.id == bet_uuid).first()
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")

    creator = db.query(User).filter(User.id == bet.creator_id).first()
    creator_name = creator.firstname if creator else "Unknown"
    timestamp = datetime.now().strftime("%d %b %Y, %H:%M")

    if body.action == "confirm":
        bet.status = BetStatus.ACTIVE
        db.commit()

        wager_line = f"Wager: R{bet.wager_amount:,.0f}\n" if bet.wager_amount else ""
        message = (
            "\U0001F91D <b>BET CONFIRMED!</b>\n\n"
            f"Bet: {bet.title}\n"
            f"Activity: {bet.activity_type.value}\n"
            f"{wager_line}"
            f"\u23F0 Confirmed at: {timestamp}\n\n"
            "<i>SweatBet</i>"
        )
    else:
        bet.status = BetStatus.CANCELLED
        db.commit()

        message = (
            "\u274C <b>BET DECLINED</b>\n\n"
            f"{creator_name} declined the bet: {bet.title}\n"
            f"\u23F0 Declined at: {timestamp}\n\n"
            "<i>SweatBet</i>"
        )

    background_tasks.add_task(telegram_notifier.send_message, message)

    return JSONResponse({"status": "ok", "action": body.action})


def _get_activity_icon(activity_type: str) -> str:
    icons = {
        "Run": "\U0001F3C3",
        "Ride": "\U0001F6B4",
        "Walk": "\U0001F6B6",
        "Hike": "\U0001F97E",
        "Swim": "\U0001F3CA",
        "Workout": "\U0001F3CB",
    }
    return icons.get(activity_type, "\U0001F3C3")


def _get_initials(user: User) -> str:
    first = (user.firstname or "?")[0].upper()
    last = (user.lastname or "")[0].upper() if user.lastname else ""
    return first + last
