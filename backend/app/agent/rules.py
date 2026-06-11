from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Invoice, PurchaseOrder
from app.schemas import Finding


def validate_invoice(
    db: Session, invoice: Invoice, purchase_order: PurchaseOrder | None
) -> list[Finding]:
    findings: list[Finding] = []

    duplicate_count = db.scalar(
        select(func.count(Invoice.id)).where(
            Invoice.invoice_number == invoice.invoice_number,
            Invoice.vendor_id == invoice.vendor_id,
            Invoice.id != invoice.id,
        )
    )
    if duplicate_count:
        findings.append(
            Finding(
                code="DUPLICATE_INVOICE",
                severity="critical",
                title="Possible duplicate invoice",
                detail=f"{duplicate_count} other invoice(s) use this vendor invoice number.",
            )
        )

    if purchase_order is None:
        findings.append(
            Finding(
                code="MISSING_PO",
                severity="critical",
                title="Missing purchase order",
                detail="No purchase order could be matched to this invoice.",
            )
        )
        return findings

    if invoice.unit_price != purchase_order.unit_price:
        variance = invoice.unit_price - purchase_order.unit_price
        findings.append(
            Finding(
                code="PRICE_MISMATCH",
                severity="high",
                title="Unit price mismatch",
                detail=f"Invoice unit price differs from the PO by {variance:+.2f}.",
            )
        )

    if invoice.quantity != purchase_order.quantity:
        variance = invoice.quantity - purchase_order.quantity
        findings.append(
            Finding(
                code="QUANTITY_MISMATCH",
                severity="high",
                title="Quantity mismatch",
                detail=f"Invoice quantity differs from the PO by {variance:+d} units.",
            )
        )

    if (
        purchase_order.received_date
        and purchase_order.received_date > purchase_order.expected_delivery_date
    ):
        days_late = (
            purchase_order.received_date - purchase_order.expected_delivery_date
        ).days
        findings.append(
            Finding(
                code="LATE_DELIVERY",
                severity="medium",
                title="Late delivery",
                detail=f"Goods were received {days_late} days after the expected date.",
            )
        )

    if invoice.total > purchase_order.approval_threshold:
        findings.append(
            Finding(
                code="APPROVAL_THRESHOLD",
                severity="high",
                title="Approval threshold exceeded",
                detail=(
                    f"Invoice total {invoice.total:.2f} exceeds the workflow threshold "
                    f"of {purchase_order.approval_threshold:.2f}."
                ),
            )
        )

    return findings


def calculate_confidence(findings: list[Finding]) -> Decimal:
    codes = {finding.code for finding in findings}
    if "MISSING_PO" in codes:
        return Decimal("0.620")
    if not findings:
        return Decimal("0.970")
    if len(findings) >= 3:
        return Decimal("0.860")
    if "DUPLICATE_INVOICE" in codes:
        return Decimal("0.840")
    return Decimal("0.920")

