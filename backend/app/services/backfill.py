"""Idempotent legacy-to-line migration.

Legacy received_date is NOT an independent goods receipt. Such records are
explicitly marked synthetic_legacy and are never treated as verified evidence.
"""
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    GoodsReceipt, GoodsReceiptLine, Invoice, InvoiceLine,
    PurchaseOrder, PurchaseOrderLine,
)


def backfill_legacy_records(db: Session) -> None:
    po_lines: dict[str, PurchaseOrderLine] = {}
    for po in db.scalars(select(PurchaseOrder)).all():
        line = db.scalar(
            select(PurchaseOrderLine).where(PurchaseOrderLine.purchase_order_id == po.id)
        )
        if line is None:
            line = PurchaseOrderLine(
                purchase_order_id=po.id,
                line_number=1,
                description=po.item_description,
                quantity=Decimal(po.quantity),
                unit_price=po.unit_price,
            )
            db.add(line)
            db.flush()
        po_lines[po.po_number] = line

        if po.received_date is not None:
            receipt_number = f"LEGACY-PO-{po.id}"
            receipt = db.scalar(
                select(GoodsReceipt).where(GoodsReceipt.receipt_number == receipt_number)
            )
            if receipt is None:
                receipt = GoodsReceipt(
                    purchase_order_id=po.id,
                    receipt_number=receipt_number,
                    received_date=po.received_date,
                    source="synthetic_legacy",
                    provenance_note=(
                        "Derived from legacy PO.received_date and PO.quantity; "
                        "not independent evidence of goods receipt."
                    ),
                )
                db.add(receipt)
                db.flush()
            existing = db.scalar(
                select(GoodsReceiptLine).where(
                    GoodsReceiptLine.goods_receipt_id == receipt.id,
                    GoodsReceiptLine.purchase_order_line_id == line.id,
                )
            )
            if existing is None:
                db.add(GoodsReceiptLine(
                    goods_receipt_id=receipt.id,
                    purchase_order_line_id=line.id,
                    quantity_received=Decimal(po.quantity),
                ))

    for invoice in db.scalars(select(Invoice)).all():
        exists = db.scalar(
            select(InvoiceLine.id).where(InvoiceLine.invoice_id == invoice.id).limit(1)
        )
        if exists is None:
            po_line = po_lines.get(invoice.po_number) if invoice.po_number else None
            db.add(InvoiceLine(
                invoice_id=invoice.id,
                purchase_order_line_id=po_line.id if po_line else None,
                line_number=1,
                description=po_line.description if po_line else "Unmatched legacy invoice line",
                quantity=Decimal(invoice.quantity),
                unit_price=invoice.unit_price,
            ))
    db.commit()
