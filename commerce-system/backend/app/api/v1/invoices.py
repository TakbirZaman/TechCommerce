from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import OrderNotFoundError
from app.core.security import CurrentUser, get_current_user
from app.models.invoice import Invoice
from app.services import order_service, storage_service

router = APIRouter(prefix="/api/v1/orders", tags=["invoices"])


@router.get("/{order_id}/invoice")
def get_invoice_download_url(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    # Ownership check first — customers can only ever reach their own invoice.
    order = order_service.get_order_for_customer(db, current_user.id, order_id)

    invoice = db.execute(select(Invoice).where(Invoice.order_id == order.id)).scalar_one_or_none()
    if invoice is None:
        raise OrderNotFoundError("Invoice not yet generated for this order")

    url = storage_service.generate_presigned_download_url(key=invoice.storage_key)
    return {"invoice_number": invoice.invoice_number, "download_url": url}
