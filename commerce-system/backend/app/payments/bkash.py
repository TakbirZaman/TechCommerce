"""
bKash Tokenized Checkout v1.2.0-beta provider (Section 13).

Endpoint shapes confirmed against bKash's official developer portal
(developer.bka.sh) as of this branch's implementation:

  POST {base}/tokenized/checkout/token/grant     - Grant Token
  POST {base}/tokenized/checkout/create           - Create Payment
  POST {base}/tokenized/checkout/execute          - Execute Payment
  GET  {base}/tokenized/checkout/payment/status   - Query Payment

Grant Token uses `username`/`password` HTTP headers + app_key/app_secret
in the body. Create/Execute use the resulting `id_token` as the
`authorization` header and `app_key` as `x-app-key`.

Credentials are read only from environment variables (via Settings) and
are never returned to the frontend.
"""
import json
from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.core.exceptions import PaymentError
from app.payments.base import PaymentInitiationResult, PaymentProvider, PaymentVerificationResult

settings = get_settings()


class BkashPaymentProvider(PaymentProvider):
    def __init__(self) -> None:
        self.base_url = settings.BKASH_BASE_URL.rstrip("/")
        self.app_key = settings.BKASH_APP_KEY
        self.app_secret = settings.BKASH_APP_SECRET
        self.username = settings.BKASH_USERNAME
        self.password = settings.BKASH_PASSWORD
        self.callback_url = settings.BKASH_CALLBACK_URL

    def _grant_token(self, client: httpx.Client) -> str:
        resp = client.post(
            f"{self.base_url}/tokenized/checkout/token/grant",
            headers={
                "username": self.username,
                "password": self.password,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={"app_key": self.app_key, "app_secret": self.app_secret},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("id_token")
        if not token:
            raise PaymentError(f"bKash grant token failed: {data}")
        return token

    def _auth_headers(self, id_token: str) -> dict:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "authorization": id_token,
            "x-app-key": self.app_key,
        }

    def initiate_payment(
        self, *, merchant_reference: str, amount: Decimal, currency: str, customer_phone: str | None = None
    ) -> PaymentInitiationResult:
        with httpx.Client() as client:
            id_token = self._grant_token(client)
            resp = client.post(
                f"{self.base_url}/tokenized/checkout/create",
                headers=self._auth_headers(id_token),
                json={
                    "mode": "0011",  # checkout (tokenized) mode
                    "payerReference": customer_phone or merchant_reference,
                    "callbackURL": self.callback_url,
                    "amount": str(amount),
                    "currency": currency,
                    "intent": "sale",
                    "merchantInvoiceNumber": merchant_reference,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("statusCode") not in (None, "0000"):
            raise PaymentError(f"bKash create payment failed: {data}")

        return PaymentInitiationResult(
            merchant_reference=merchant_reference,
            gateway_transaction_id=data.get("paymentID"),
            redirect_url=data.get("bkashURL"),
            raw_response=json.dumps(data),
        )

    def verify_payment(self, *, gateway_transaction_id: str) -> PaymentVerificationResult:
        """
        Executes the payment (finalizing user consent) and treats bKash's
        own executePayment response as the source of truth, per Section 13's
        "payment result must be verified server-side" requirement. A
        Query Payment call could additionally be used for reconciliation
        jobs (see app/tasks) without re-executing.
        """
        with httpx.Client() as client:
            id_token = self._grant_token(client)
            resp = client.post(
                f"{self.base_url}/tokenized/checkout/execute",
                headers=self._auth_headers(id_token),
                json={"paymentID": gateway_transaction_id},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        success = data.get("transactionStatus") == "Completed" and data.get("statusCode") == "0000"
        return PaymentVerificationResult(
            success=success,
            gateway_transaction_id=gateway_transaction_id,
            amount=Decimal(str(data.get("amount", "0"))),
            currency=data.get("currency", "BDT"),
            raw_response=json.dumps(data),
        )

    def verify_callback_signature(self, payload: dict) -> bool:
        """
        bKash's Tokenized Checkout callback does not carry an HMAC signature;
        instead the callback is treated as a hint to trigger verify_payment()
        (execute + optionally query), which IS the authoritative check.
        Section 17 requires that a callback alone never be treated as proof,
        so this always returns True (meaning "acceptable to trigger
        verification") rather than "acceptable to trust as final".
        """
        return "paymentID" in payload
