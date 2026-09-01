"""
Nagad "Payment by URL" provider (Section 14).

Endpoint shapes confirmed against Nagad's Merchant API Integration Guide:

  POST {base}/check-out/initialize/{merchantId}/{orderId}
  POST {base}/check-out/complete/{paymentRefId}
  GET  {base}/verify/payment/{paymentRefId}

Nagad's protocol is RSA-signature based rather than bearer-token based:
merchant signs a payload with its private key; Nagad encrypts sensitive
response fields with the merchant's public key, decryptable only with the
merchant's private key. Full crypto plumbing (sensitiveData encrypt/decrypt,
challenge/signature generation) is isolated in _sign() / _verify_signature()
below so it can be swapped for a vetted crypto library
(e.g. `cryptography`'s PKCS1v15 + SHA256/SHA1) during hardening — the
shape of the calls is what matters for the rest of the codebase.

Credentials (NAGAD_PRIVATE_KEY / NAGAD_PUBLIC_KEY / NAGAD_MERCHANT_ID) are
read only from environment variables and never exposed to the frontend.
"""
import base64
import json
import uuid
from datetime import datetime
from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.core.exceptions import PaymentError
from app.payments.base import PaymentInitiationResult, PaymentProvider, PaymentVerificationResult

settings = get_settings()


class NagadPaymentProvider(PaymentProvider):
    def __init__(self) -> None:
        self.base_url = settings.NAGAD_BASE_URL.rstrip("/")
        self.merchant_id = settings.NAGAD_MERCHANT_ID
        self.merchant_number = settings.NAGAD_MERCHANT_NUMBER
        self.private_key = settings.NAGAD_PRIVATE_KEY
        self.public_key = settings.NAGAD_PUBLIC_KEY
        self.callback_url = settings.NAGAD_CALLBACK_URL

    def _sign(self, payload: dict) -> str:
        """
        Sign payload with merchant private key (SHA1withRSA per Nagad spec).
        Placeholder using base64 of the JSON payload — REPLACE with real
        RSA signing (e.g. `cryptography.hazmat.primitives.asymmetric.padding.PKCS1v15`)
        wired to NAGAD_PRIVATE_KEY before going to production. Kept isolated
        here specifically so that swap is a one-function change.
        """
        raw = json.dumps(payload, sort_keys=True).encode()
        return base64.b64encode(raw).decode()

    def _verify_signature(self, encrypted_payload: str) -> bool:
        """Placeholder signature/decryption check — see _sign() note above."""
        return bool(encrypted_payload)

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "X-KM-Api-Version": "v-0.2.0",
            "X-KM-IP-V4": "127.0.0.1",  # server's public IP in production
            "X-KM-Client-Type": "PC_WEB",
        }

    def initiate_payment(
        self, *, merchant_reference: str, amount: Decimal, currency: str, customer_phone: str | None = None
    ) -> PaymentInitiationResult:
        order_id = merchant_reference
        date_time = datetime.now().strftime("%Y%m%d%H%M%S")

        sensitive_data = {
            "merchantId": self.merchant_id,
            "datetime": date_time,
            "orderId": order_id,
            "challenge": uuid.uuid4().hex,
        }

        with httpx.Client() as client:
            init_resp = client.post(
                f"{self.base_url}/check-out/initialize/{self.merchant_id}/{order_id}",
                headers=self._headers(),
                json={
                    "accountNumber": self.merchant_number,
                    "dateTime": date_time,
                    "sensitiveData": self._sign(sensitive_data),
                    "signature": self._sign(sensitive_data),
                },
                timeout=30,
            )
            init_resp.raise_for_status()
            init_data = init_resp.json()

            payment_ref_id = init_data.get("paymentReferenceId")
            challenge = init_data.get("challenge")
            if not payment_ref_id:
                raise PaymentError(f"Nagad initialize failed: {init_data}")

            complete_payload = {
                "merchantId": self.merchant_id,
                "orderId": order_id,
                "amount": str(amount),
                "currencyCode": "050",  # ISO 4217 numeric for BDT
                "challenge": challenge,
            }
            complete_resp = client.post(
                f"{self.base_url}/check-out/complete/{payment_ref_id}",
                headers=self._headers(),
                json={
                    "sensitiveData": self._sign(complete_payload),
                    "signature": self._sign(complete_payload),
                    "merchantCallbackURL": self.callback_url,
                },
                timeout=30,
            )
            complete_resp.raise_for_status()
            complete_data = complete_resp.json()

        return PaymentInitiationResult(
            merchant_reference=order_id,
            gateway_transaction_id=payment_ref_id,
            redirect_url=complete_data.get("callBackUrl"),
            raw_response=json.dumps({"init": init_data, "complete": complete_data}),
        )

    def verify_payment(self, *, gateway_transaction_id: str) -> PaymentVerificationResult:
        """
        GET {base}/verify/payment/{paymentRefId} — Nagad's authoritative
        status check, called server-side regardless of what the callback
        claimed (Section 17-19).
        """
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base_url}/verify/payment/{gateway_transaction_id}",
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        success = data.get("status") == "Success"
        return PaymentVerificationResult(
            success=success,
            gateway_transaction_id=gateway_transaction_id,
            amount=Decimal(str(data.get("amount", "0"))),
            currency="BDT",
            raw_response=json.dumps(data),
        )

    def verify_callback_signature(self, payload: dict) -> bool:
        encrypted = payload.get("sensitiveData") or payload.get("payment_ref_id", "")
        return self._verify_signature(str(encrypted))
