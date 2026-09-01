"""
PaymentProvider abstraction (Section 11).

Order Service -> Payment Service -> Payment Provider -> Gateway

order_service / checkout_service never import bkash/nagad/sslcommerz
directly. They only ever talk to payment_service.py, which resolves the
right PaymentProvider by PaymentMethod and calls these three methods.
Every gateway-specific quirk (headers, signing, polling vs. redirect)
stays inside that gateway's provider class.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PaymentInitiationResult:
    """What the frontend needs to continue the payment flow."""

    merchant_reference: str
    gateway_transaction_id: str | None  # bKash paymentID / Nagad paymentRefId / None for SSLCommerz until redirect
    redirect_url: str | None  # where to send the browser (SSLCommerz GatewayPageURL, Nagad callback URL)
    raw_response: str  # JSON string of the raw gateway response, stored for audit


@dataclass
class PaymentVerificationResult:
    success: bool
    gateway_transaction_id: str
    amount: Decimal
    currency: str
    raw_response: str


class PaymentProvider(ABC):
    @abstractmethod
    def initiate_payment(
        self, *, merchant_reference: str, amount: Decimal, currency: str, customer_phone: str | None = None
    ) -> PaymentInitiationResult:
        """Start a payment session with the gateway. Never called with a client-supplied amount."""

    @abstractmethod
    def verify_payment(self, *, gateway_transaction_id: str) -> PaymentVerificationResult:
        """
        Server-side verification against the gateway's own API. This is the
        ONLY source of truth for whether a payment succeeded — a callback
        or browser redirect alone is never sufficient (Section 17-19).
        """

    @abstractmethod
    def verify_callback_signature(self, payload: dict) -> bool:
        """Validate whatever signature/token mechanism this gateway requires on inbound callbacks."""
