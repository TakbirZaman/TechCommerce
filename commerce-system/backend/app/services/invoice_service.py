"""
Invoice generation (Section 20-21).

Builds a PDF with ReportLab, uploads it via storage_service (S3/R2 — never
Postgres), and records metadata in the Invoice table. Invoice numbers use
the same year-scoped counter pattern as order numbers, in a separate
sequence namespace (INV-*) so they don't collide with ORD-* numbers.
"""
from datetime import UTC, datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.invoice import Invoice
from app.models.order import Order
from app.models.order_number_counter import OrderNumberCounter
from app.models.payment import Payment, PaymentStatus
from app.services import storage_service

STORE_NAME = "Your Store Name"
STORE_ADDRESS = "House/Road, City, Bangladesh"
STORE_CONTACT = "support@yourstore.com | +880-XXXXXXXXXX"


def _next_invoice_number(db: Session, year: int) -> str:
    key = f"INV-{year}"
    counter = db.execute(
        select(OrderNumberCounter).where(OrderNumberCounter.year == key).with_for_update()
    ).scalar_one_or_none()
    if counter is None:
        counter = OrderNumberCounter(year=key, last_value=0)
        db.add(counter)
        db.flush()
    counter.last_value += 1
    db.flush()
    return f"INV-{year}-{counter.last_value:06d}"


def _build_pdf_bytes(order: Order, payment: Payment | None, invoice_number: str) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>{STORE_NAME}</b>", styles["Title"]))
    story.append(Paragraph(STORE_ADDRESS, styles["Normal"]))
    story.append(Paragraph(STORE_CONTACT, styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"<b>Invoice #:</b> {invoice_number}", styles["Normal"]))
    story.append(Paragraph(f"<b>Order #:</b> {order.order_number}", styles["Normal"]))
    story.append(Paragraph(f"<b>Date:</b> {datetime.now(UTC).strftime('%Y-%m-%d')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Bill To / Delivery Address</b>", styles["Heading3"]))
    story.append(Paragraph(order.shipping_full_name, styles["Normal"]))
    story.append(Paragraph(order.shipping_phone, styles["Normal"]))
    story.append(
        Paragraph(
            f"{order.shipping_address}, {order.shipping_area}, {order.shipping_city} "
            f"{order.shipping_postal_code or ''}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 12))

    table_data = [["Product", "SKU", "Qty", "Unit Price", "Subtotal"]]
    for item in order.items:
        table_data.append(
            [
                item.product_name,
                item.product_sku,
                str(item.quantity),
                f"{item.unit_price:.2f}",
                f"{item.subtotal:.2f}",
            ]
        )

    items_table = Table(table_data, colWidths=[160, 80, 40, 80, 80])
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 12))

    totals_data = [
        ["Subtotal", f"{order.subtotal:.2f}"],
        ["Discount", f"-{order.discount:.2f}"],
        ["Delivery Charge", f"{order.delivery_charge:.2f}"],
        ["Total", f"{order.total_amount:.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[200, 100])
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(totals_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"<b>Payment Method:</b> {order.payment_method.value}", styles["Normal"]))
    if payment is not None:
        story.append(
            Paragraph(f"<b>Transaction ID:</b> {payment.transaction_id or 'N/A'}", styles["Normal"])
        )
        story.append(Paragraph(f"<b>Payment Status:</b> {payment.status.value}", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()


def generate_invoice_for_order(db: Session, order: Order) -> Invoice:
    existing = db.execute(select(Invoice).where(Invoice.order_id == order.id)).scalar_one_or_none()
    if existing is not None:
        return existing  # idempotent: don't regenerate/duplicate on retry

    payment = db.execute(
        select(Payment)
        .where(Payment.order_id == order.id, Payment.status == PaymentStatus.SUCCESS)
        .order_by(Payment.paid_at.desc())
    ).scalars().first()

    year = datetime.now(UTC).year
    invoice_number = _next_invoice_number(db, year)
    pdf_bytes = _build_pdf_bytes(order, payment, invoice_number)

    storage_key = f"invoices/{year}/{invoice_number}.pdf"
    settings = get_settings()
    storage_service.upload_bytes(key=storage_key, data=pdf_bytes, content_type="application/pdf")

    invoice = Invoice(
        order_id=order.id,
        invoice_number=invoice_number,
        storage_key=storage_key,
        storage_bucket=settings.STORAGE_BUCKET,
        content_type="application/pdf",
        file_size_bytes=len(pdf_bytes),
        generated_at=datetime.now(UTC),
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice
