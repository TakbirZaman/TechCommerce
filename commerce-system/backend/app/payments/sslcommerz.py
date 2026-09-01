"""
SSLCommerz provider (Section 15).

Endpoint shapes confirmed against SSLCommerz's official developer docs
(developer.sslcommerz.com):

  POST {domain}/gwprocess/v4/api.php                         - Session/init (returns GatewayPageURL)
  POST {domain}/validator/api/v4/                             - Order/transaction validation

domain = https://sandbox.sslcommerz.com (sandbox) or
         https://securepay.sslcommerz.com (live)

Flow: initiate_payment() creates a session and returns GatewayPageURL for
the frontend to redirect to. SSLCommerz then calls success_url / fail_url /
cancel_url (browser redirects) AND ipn_url (server-to-server) with val_id.
Per Section 15/17, a browser redirect to success_url is NEVER treated as
proof by itself — verify_payment() always re-validates val_id against the
Order Validation API before the order is marked paid.
"""
import json
from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.core.exceptions import PaymentError
from app.payments.base import PaymentInitiationResult, PaymentProvider, PaymentVerificationResult

settings = get_settings()


class SslCommerzPaymentProvider(PaymentProvider):
    def __init__(self) -> None:
        self.domain = (
            "https://sandbox.sslcommerz.com"
            if settings.SSLCOMMERZ_IS_SANDBOX
            else "https://securepay.sslcommerz.com"
        )
        self.store_id = settings.SSLCOMMERZ_STORE_ID
        self.store_password = settings.SSLCOMMERZ_STORE_PASSWORD
        self.success_url = settings.SSLCOMMERZ_SUCCESS_URL
        self.fail_url = settings.SSLCOMMERZ_FAIL_URL
        self.cancel_url = settings.SSLCOMMERZ_CANCEL_URL
        self.ipn_url = settings.SSLCOMMERZ_IPN_URL

    def initiate_payment(
        self, *, merchant_reference: str, amount: Decimal, currency: str, customer_phone: str | None = None
    ) -> PaymentInitiationResult:
        with httpx.Client() as client:
            resp = client.post(
                f"{self.domain}/gwprocess/v4/api.php",
                data={
                    "store_id": self.store_id,
                    "store_passwd": self.store_password,
                    "total_amount": str(amount),
                    "currency": currency,
                    "tran_id": merchant_reference,
                    "success_url": self.success_url,
                    "fail_url": self.fail_url,
                    "cancel_url": self.cancel_url,
                    "ipn_url": self.ipn_url,
                    "cus_name": "Customer",
                    "cus_phone": customer_phone or "N/A",
                    "cus_add1": "N/A",
                    "cus_city": "N/A",
                    "cus_country": "Bangladesh",
                    "shipping_method": "NO",
                    "product_name": "Order",
                    "product_category": "General",
                    "product_profile": "general",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "SUCCESS":
            raise PaymentError(f"SSLCommerz session init failed: {data}")

        return PaymentInitiationResult(
            merchant_reference=merchant_reference,
            gateway_transaction_id=None,  # not known until success callback (val_id)
            redirect_url=data.get("GatewayPageURL"),
            raw_response=json.dumps(data),
        )

    def verify_payment(self, *, gateway_transaction_id: str) -> PaymentVerificationResult:
        """
        gateway_transaction_id here is SSLCommerz's val_id, received on the
        success callback. This calls the Order Validation API — the only
        step that actually proves payment, per Section 15/17.
        """
        with httpx.Client() as client:
            resp = client.get(
                f"{self.domain}/validator/api/v4/",
                params={
                    "val_id": gateway_transaction_id,
                    "store_id": self.store_id,
                    "store_passwd": self.store_password,
                    "format": "json",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        success = data.get("status") in ("VALID", "VALIDATED")
        return PaymentVerificationResult(
            success=success,
            gateway_transaction_id=gateway_transaction_id,
            amount=Decimal(str(data.get("amount", "0"))),
            currency=data.get("currency", "BDT"),
            raw_response=json.dumps(data),
        )

    def verify_callback_signature(self, payload: dict) -> bool:
        """
        SSLCommerz doesn't sign callbacks with an HMAC; instead it hands
        back val_id, which MUST be re-validated server-side via
        verify_payment() before trust is extended (Section 17). This check
        only confirms the callback has the shape needed to attempt that
        verification — it is not itself proof of anything.
        """
        return bool(payload.get("val_id")) and payload.get("store_id") == self.store_id
