"""
Payment endpoints for SweatBet — checkout, return, and wallet management.

Handles the Stitch payment flow:
1. /payments/checkout/<bet_id> — shows payment method selection
2. /payments/create — initiates payment via Stitch (or mock)
3. /payments/return — handles redirect back from Stitch
4. /payments/activate-free — activates R0 bets without payment
5. /wallet — shows balance, bank account, transaction history
6. /wallet/bank-account — saves payout bank details
7. /wallet/withdraw — initiates a disbursement
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.fastapi.dependencies.database import get_sync_db
from backend.fastapi.dependencies.auth import get_current_user
from backend.fastapi.models.user import User
from backend.fastapi.models.bet import Bet, BetStatus
from backend.fastapi.services.stitch import stitch_client, PAYMENT_METHOD_LABELS

router = APIRouter()
templates = Jinja2Templates(directory="frontend/sweatbet/templates")


# ── Request schemas ──────────────────────────────────────────────────

class CreatePaymentBody(BaseModel):
    bet_id: str
    payment_method: str = "card"


class ActivateFreeBody(BaseModel):
    bet_id: str


# ── In-memory wallet state (mock — will be replaced by DB) ──────────

_mock_wallets: dict[str, dict] = {}
_mock_bank_accounts: dict[str, dict] = {}
_mock_transactions: dict[str, list] = {}


def _get_wallet(user_id: str) -> dict:
    if user_id not in _mock_wallets:
        _mock_wallets[user_id] = {"balance": 0.0, "pending": 0.0}
    return _mock_wallets[user_id]


def _add_transaction(user_id: str, tx: dict):
    if user_id not in _mock_transactions:
        _mock_transactions[user_id] = []
    _mock_transactions[user_id].insert(0, tx)


# ── Checkout page ────────────────────────────────────────────────────

@router.get("/payments/checkout/{bet_id}", response_class=HTMLResponse)
async def payment_checkout_page(
    bet_id: str,
    request: Request,
    db: Session = Depends(get_sync_db),
):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/", status_code=302)

    try:
        bet = db.query(Bet).filter(
            Bet.id == uuid.UUID(bet_id),
            Bet.creator_id == user.id,
        ).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bet ID")

    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")

    return templates.TemplateResponse(
        "payment_checkout.html",
        {"request": request, "user": user, "bet": bet},
    )


# ── Create payment (API) ────────────────────────────────────────────

@router.post("/payments/create")
async def create_payment(
    body: CreatePaymentBody,
    request: Request,
    db: Session = Depends(get_sync_db),
):
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    try:
        bet = db.query(Bet).filter(
            Bet.id == uuid.UUID(body.bet_id),
            Bet.creator_id == user.id,
        ).first()
    except ValueError:
        return JSONResponse({"error": "Invalid bet ID"}, status_code=400)

    if not bet:
        return JSONResponse({"error": "Bet not found"}, status_code=404)

    if bet.wager_amount <= 0:
        return JSONResponse({"error": "No payment required for this bet"}, status_code=400)

    # Build the return URL for after payment
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/payments/return"

    # Create payment request via Stitch (or mock)
    pr = stitch_client.create_payment_request(
        bet_id=str(bet.id),
        amount=bet.wager_amount,
        payment_method=body.payment_method,
        redirect_uri=redirect_uri,
    )

    return JSONResponse({
        "payment_id": pr.id,
        "redirect_url": pr.redirect_url,
    })


# ── Payment return (redirect from Stitch) ───────────────────────────

@router.get("/payments/return", response_class=HTMLResponse)
async def payment_return(
    request: Request,
    id: str = "",
    status: str = "closed",
    externalReference: str = "",
    payment_method: str = "",
    db: Session = Depends(get_sync_db),
):
    user = await get_current_user(request, db)

    # Try to find the bet from the external reference (format: sweatbet_<bet_id>)
    bet = None
    if externalReference.startswith("sweatbet_"):
        bet_id_str = externalReference.replace("sweatbet_", "")
        try:
            bet = db.query(Bet).filter(Bet.id == uuid.UUID(bet_id_str)).first()
        except ValueError:
            pass

    # In mock mode, mark payment complete and activate the bet
    if status == "complete" and bet:
        stitch_client.complete_mock_payment(id, "complete")

        if bet.status == BetStatus.PENDING:
            bet.status = BetStatus.ACTIVE
            db.commit()

        # Record transaction in mock wallet
        if user:
            uid = str(user.id)
            _add_transaction(uid, {
                "type": "deposit",
                "description": f"Bet wager: {bet.title}",
                "amount": bet.wager_amount,
                "date": datetime.utcnow().strftime("%d %b %Y, %H:%M"),
                "status": "completed",
            })

    method_label = PAYMENT_METHOD_LABELS.get(payment_method, payment_method)

    return templates.TemplateResponse(
        "payment_return.html",
        {
            "request": request,
            "user": user,
            "status": status,
            "bet": bet,
            "payment_method": method_label,
            "payment_ref": id,
        },
    )


# ── Activate free bet (R0 wager) ────────────────────────────────────

@router.post("/payments/activate-free")
async def activate_free_bet(
    body: ActivateFreeBody,
    request: Request,
    db: Session = Depends(get_sync_db),
):
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    try:
        bet = db.query(Bet).filter(
            Bet.id == uuid.UUID(body.bet_id),
            Bet.creator_id == user.id,
        ).first()
    except ValueError:
        return JSONResponse({"error": "Invalid bet ID"}, status_code=400)

    if not bet:
        return JSONResponse({"error": "Bet not found"}, status_code=404)

    if bet.status == BetStatus.PENDING:
        bet.status = BetStatus.ACTIVE
        db.commit()

    return JSONResponse({"redirect_url": f"/payments/return?status=complete&externalReference=sweatbet_{bet.id}"})


# ── Wallet page ──────────────────────────────────────────────────────

@router.get("/wallet", response_class=HTMLResponse)
async def wallet_page(
    request: Request,
    db: Session = Depends(get_sync_db),
):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/", status_code=302)

    uid = str(user.id)
    wallet = _get_wallet(uid)
    bank_account = _mock_bank_accounts.get(uid)
    transactions = _mock_transactions.get(uid, [])

    return templates.TemplateResponse(
        "wallet.html",
        {
            "request": request,
            "user": user,
            "balance": wallet["balance"],
            "pending_amount": wallet["pending"],
            "bank_account": bank_account,
            "transactions": transactions,
        },
    )


# ── Save bank account ───────────────────────────────────────────────

@router.post("/wallet/bank-account")
async def save_bank_account(
    request: Request,
    bank_name: str = Form(...),
    account_number: str = Form(...),
    account_type: str = Form("cheque"),
    account_holder: str = Form(...),
    db: Session = Depends(get_sync_db),
):
    user = await get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/", status_code=302)

    # Bank display names
    bank_labels = {
        "absa": "Absa",
        "capitec": "Capitec Bank",
        "fnb": "FNB",
        "nedbank": "Nedbank",
        "standard_bank": "Standard Bank",
        "tymebank": "TymeBank",
        "discovery": "Discovery Bank",
        "african_bank": "African Bank",
    }

    uid = str(user.id)
    _mock_bank_accounts[uid] = {
        "bank_id": bank_name,
        "bank_name": bank_labels.get(bank_name, bank_name),
        "account_number": account_number,
        "account_type": account_type,
        "account_holder": account_holder,
        "verified": True,  # Mock: auto-verify
    }

    return RedirectResponse(url="/wallet", status_code=302)


# ── Withdraw / Disbursement ──────────────────────────────────────────

@router.post("/wallet/withdraw")
async def withdraw(
    request: Request,
    db: Session = Depends(get_sync_db),
):
    user = await get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    uid = str(user.id)
    wallet = _get_wallet(uid)
    bank_account = _mock_bank_accounts.get(uid)

    if wallet["balance"] <= 0:
        return JSONResponse({"error": "No balance to withdraw"}, status_code=400)

    if not bank_account:
        return JSONResponse({"error": "No bank account linked. Add one in your wallet settings."}, status_code=400)

    amount = wallet["balance"]

    # Create disbursement via Stitch (or mock)
    d = stitch_client.create_disbursement(
        amount=amount,
        bank_id=bank_account["bank_id"],
        account_number=bank_account["account_number"],
        account_holder=bank_account["account_holder"],
        account_type=bank_account["account_type"],
    )

    # Update mock wallet
    wallet["balance"] = 0.0

    _add_transaction(uid, {
        "type": "payout",
        "description": f"Withdrawal to {bank_account['bank_name']}",
        "amount": amount,
        "date": datetime.utcnow().strftime("%d %b %Y, %H:%M"),
        "status": "completed",
    })

    return JSONResponse({"success": True, "disbursement_id": d.id, "amount": amount})
