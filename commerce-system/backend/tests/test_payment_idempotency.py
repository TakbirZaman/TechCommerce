from decimal import Decimal
from unittest.mock import patch

from app.models.order import OrderStatus
from app.models.order import PaymentStatus as OrderPaymentStatus
from app.models.payment import PaymentGateway
from app.payments.base import PaymentVerificationResult
from app.schemas.order import CheckoutRequest
from app.services import checkout_service, payment_service


def _checkout(db_session, user_id, product, qty=2):
    from app.services import cart_service

    cart_service.add_item(db_session, user_id, product.id, qty)
    payload = CheckoutRequest.model_validate(
        {
            "delivery": {
                "full_name": "Jane",
                "phone": "017",
                "address": "addr",
                "city": "Dhaka",
                "area": "Gulshan",
            },
            "payment_method": "BKASH",
        }
    )
    return checkout_service.checkout(db_session, user_id, payload)


def _checkout_with_payment(db_session, user_id, product, qty=2):
    """Checkout + manually insert the Payment row that initiate_payment_for_order
    would normally create, without making a real HTTP call to the gateway."""
    from app.models.payment import Payment, PaymentGateway as PG, PaymentStatus as PS

    order = _checkout(db_session, user_id, product, qty)
    payment = Payment(
        order_id=order.id,
        gateway=PG.BKASH,
        merchant_reference=order.order_number,
        transaction_id=None,
        amount=order.total_amount,
        currency="BDT",
        status=PS.INITIATED,
    )
    db_session.add(payment)
    db_session.commit()
    return order, payment


def _fake_verify_success(amount):
    def _verify(self, *, gateway_transaction_id):
        return PaymentVerificationResult(
            success=True,
            gateway_transaction_id=gateway_transaction_id,
            amount=amount,
            currency="BDT",
            raw_response="{}",
        )
    return _verify


def test_successful_callback_marks_order_paid_and_finalizes_inventory(db_session, seed_user, seed_product):
    order, _ = _checkout_with_payment(db_session, seed_user.id, seed_product, qty=2)

    with patch("app.payments.bkash.BkashPaymentProvider.verify_callback_signature", return_value=True), \
         patch("app.payments.bkash.BkashPaymentProvider.verify_payment", _fake_verify_success(order.total_amount)):
        result = payment_service.process_callback(
            db_session, PaymentGateway.BKASH, {"paymentID": "PAY123", "merchantInvoiceNumber": order.order_number}
        )

    assert result["status"] == "SUCCESS"
    assert result["duplicate"] is False

    db_session.refresh(order)
    assert order.order_status == OrderStatus.PAID
    assert order.payment_status == OrderPaymentStatus.PAID

    db_session.refresh(seed_product)
    assert seed_product.total_stock == 8  # 10 - 2 finalized
    assert seed_product.reserved_stock == 0


def test_duplicate_callback_does_not_reprocess(db_session, seed_user, seed_product):
    order, _ = _checkout_with_payment(db_session, seed_user.id, seed_product, qty=1)

    with patch("app.payments.bkash.BkashPaymentProvider.verify_callback_signature", return_value=True), \
         patch("app.payments.bkash.BkashPaymentProvider.verify_payment", _fake_verify_success(order.total_amount)):
        first = payment_service.process_callback(
            db_session, PaymentGateway.BKASH, {"paymentID": "PAY999", "merchantInvoiceNumber": order.order_number}
        )
        second = payment_service.process_callback(
            db_session, PaymentGateway.BKASH, {"paymentID": "PAY999", "merchantInvoiceNumber": order.order_number}
        )

    assert first["duplicate"] is False
    assert second["duplicate"] is True

    db_session.refresh(seed_product)
    # Stock finalized exactly once despite two callbacks for the same transaction.
    assert seed_product.total_stock == 9  # 10 - 1, not 10 - 2


def test_failed_verification_releases_inventory(db_session, seed_user, seed_product):
    order, _ = _checkout_with_payment(db_session, seed_user.id, seed_product, qty=4)

    def _verify_fail(self, *, gateway_transaction_id):
        return PaymentVerificationResult(
            success=False,
            gateway_transaction_id=gateway_transaction_id,
            amount=order.total_amount,
            currency="BDT",
            raw_response="{}",
        )

    with patch("app.payments.bkash.BkashPaymentProvider.verify_callback_signature", return_value=True), \
         patch("app.payments.bkash.BkashPaymentProvider.verify_payment", _verify_fail):
        result = payment_service.process_callback(
            db_session, PaymentGateway.BKASH, {"paymentID": "PAYFAIL", "merchantInvoiceNumber": order.order_number}
        )

    assert result["status"] == "FAILED"
    db_session.refresh(seed_product)
    assert seed_product.reserved_stock == 0  # released back
    assert seed_product.available_stock == 10


def test_amount_mismatch_treated_as_failure(db_session, seed_user, seed_product):
    order, _ = _checkout_with_payment(db_session, seed_user.id, seed_product, qty=1)

    with patch("app.payments.bkash.BkashPaymentProvider.verify_callback_signature", return_value=True), \
         patch("app.payments.bkash.BkashPaymentProvider.verify_payment", _fake_verify_success(Decimal("1.00"))):
        result = payment_service.process_callback(
            db_session, PaymentGateway.BKASH, {"paymentID": "PAYMISMATCH", "merchantInvoiceNumber": order.order_number}
        )

    assert result["status"] == "FAILED"
