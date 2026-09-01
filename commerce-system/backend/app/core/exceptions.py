class CommerceError(Exception):
    """Base class for domain errors. Mapped to HTTP responses in the API layer."""

    status_code = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ProductNotFoundError(CommerceError):
    status_code = 404


class ProductNotPurchasableError(CommerceError):
    status_code = 422


class InsufficientStockError(CommerceError):
    status_code = 409


class CartItemNotFoundError(CommerceError):
    status_code = 404


class InvalidQuantityError(CommerceError):
    status_code = 422


class EmptyCartError(CommerceError):
    status_code = 422


class OrderNotFoundError(CommerceError):
    status_code = 404


class InvalidOrderStateTransitionError(CommerceError):
    status_code = 409


class PaymentError(CommerceError):
    status_code = 402


class DuplicatePaymentCallbackError(CommerceError):
    """
    Not really an "error" in the failure sense — raised internally so the
    idempotency guard can short-circuit and return the prior result instead
    of reprocessing. Kept as a distinct type for clarity in logs.
    """

    status_code = 200
