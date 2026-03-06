"""
Stitch payment service — handles payment initiation and disbursements.

In dev mode, mocks the Stitch API responses so the frontend can be developed
without real Stitch credentials. In production, calls the real Stitch GraphQL API.

Stitch API docs: https://docs.stitch.money
API endpoint: https://api.stitch.money/graphql
"""

import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, field

from backend.fastapi.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Payment method display names
PAYMENT_METHOD_LABELS = {
    "card": "Card Payment",
    "pay_by_bank": "Pay by Bank (EFT)",
    "wallet": "Digital Wallet",
}


@dataclass
class PaymentRequest:
    """Represents a Stitch payment initiation request."""
    id: str
    bet_id: str
    amount: float
    currency: str = "ZAR"
    payment_method: str = "card"
    status: str = "pending"  # pending, complete, failed, closed
    redirect_url: str = ""
    external_reference: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    payer_reference: str = ""
    beneficiary_reference: str = ""


@dataclass
class Disbursement:
    """Represents a Stitch disbursement (payout)."""
    id: str
    amount: float
    currency: str = "ZAR"
    destination_bank: str = ""
    destination_account: str = ""
    nonce: str = ""
    status: str = "pending"  # pending, submitted, completed, error
    created_at: datetime = field(default_factory=datetime.utcnow)


class StitchClient:
    """
    Stitch payment client.

    In dev mode (no STITCH_CLIENT_ID), simulates the full payment flow
    with in-memory state so the UI can be built and tested.

    In production, this will call the Stitch GraphQL API at
    https://api.stitch.money/graphql using client tokens.
    """

    def __init__(self):
        self.client_id = getattr(settings, 'STITCH_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'STITCH_CLIENT_SECRET', '')
        self.is_mock = not self.client_id

        # In-memory store for mock mode
        self._payment_requests: dict[str, PaymentRequest] = {}
        self._disbursements: dict[str, Disbursement] = {}

        if self.is_mock:
            logger.info("Stitch client running in MOCK mode (no credentials)")
        else:
            logger.info("Stitch client initialized with live credentials")

    def create_payment_request(
        self,
        bet_id: str,
        amount: float,
        payment_method: str = "card",
        redirect_uri: str = "",
    ) -> PaymentRequest:
        """
        Create a payment initiation request.

        In production, this calls clientPaymentInitiationRequestCreate via GraphQL.
        In mock mode, returns a simulated payment request that redirects to our
        mock return endpoint.
        """
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        external_ref = f"sweatbet_{bet_id}"
        payer_ref = f"SB-{bet_id[:8]}"[:12]
        beneficiary_ref = "SweatBet Wager"[:20]

        if self.is_mock:
            # Mock: redirect straight to our return page with success
            redirect_url = (
                f"{redirect_uri}?id={payment_id}"
                f"&status=complete"
                f"&externalReference={external_ref}"
                f"&payment_method={payment_method}"
            )

            pr = PaymentRequest(
                id=payment_id,
                bet_id=bet_id,
                amount=amount,
                payment_method=payment_method,
                status="pending",
                redirect_url=redirect_url,
                external_reference=external_ref,
                payer_reference=payer_ref,
                beneficiary_reference=beneficiary_ref,
            )
            self._payment_requests[payment_id] = pr

            logger.info(
                "Mock payment request created: %s for bet %s (R%.0f)",
                payment_id, bet_id, amount
            )
            return pr

        # TODO: Production — call Stitch GraphQL API
        # mutation clientPaymentInitiationRequestCreate {
        #   amount: { quantity: str(amount), currency: "ZAR" }
        #   payerReference: payer_ref
        #   beneficiaryReference: beneficiary_ref
        #   externalReference: external_ref
        #   paymentMethods: { card: { enabled: true } }
        # }
        raise NotImplementedError("Live Stitch API not yet configured")

    def get_payment_request(self, payment_id: str) -> PaymentRequest | None:
        """Get a payment request by ID."""
        if self.is_mock:
            return self._payment_requests.get(payment_id)

        # TODO: Query Stitch API by node ID
        raise NotImplementedError("Live Stitch API not yet configured")

    def complete_mock_payment(self, payment_id: str, status: str = "complete") -> bool:
        """Mark a mock payment as complete (dev mode only)."""
        if not self.is_mock:
            return False

        pr = self._payment_requests.get(payment_id)
        if not pr:
            return False

        pr.status = status
        logger.info("Mock payment %s marked as: %s", payment_id, status)
        return True

    def create_disbursement(
        self,
        amount: float,
        bank_id: str,
        account_number: str,
        account_holder: str,
        account_type: str = "cheque",
        reference: str = "SweatBet Payout",
    ) -> Disbursement:
        """
        Create a disbursement (payout to user's bank account).

        In production, calls the Stitch disbursement GraphQL mutation.
        """
        disbursement_id = f"dis_{uuid.uuid4().hex[:12]}"
        nonce = f"sweatbet_payout_{uuid.uuid4().hex[:8]}"

        if self.is_mock:
            d = Disbursement(
                id=disbursement_id,
                amount=amount,
                destination_bank=bank_id,
                destination_account=account_number,
                nonce=nonce,
                status="completed",
            )
            self._disbursements[disbursement_id] = d

            logger.info(
                "Mock disbursement created: %s — R%.0f to %s ****%s",
                disbursement_id, amount, bank_id, account_number[-4:]
            )
            return d

        # TODO: Production — call Stitch GraphQL mutation
        # clientDisbursementCreate with amount, destination, nonce
        raise NotImplementedError("Live Stitch API not yet configured")


# Singleton
stitch_client = StitchClient()
