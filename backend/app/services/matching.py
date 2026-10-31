"""Deterministic line-level procurement controls (no LLM decisions)."""
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    GoodsReceipt, GoodsReceiptLine, Invoice, InvoiceLine, MatchRun,
    ProcurementException, ExceptionStatus, PurchaseOrder, PurchaseOrderLine,
)
from app.schemas import Finding

RULE_VERSION = "2.0"


@dataclass(frozen=True)
class MatchEvaluation:
    status: str
    findings: list[Finding]


def evaluate_invoice(
    db: Session, invoice: Invoice, purchase_order: PurchaseOrder | None
) -> MatchEvaluation:
    findings: list[Finding] = []

    def add(code: str, severity: str, title: str, detail: str) -> None:
        findings.append(Finding(code=code, severity=severity, title=title, detail=detail))

    duplicate_count = db.scalar(select(func.count(Invoice.id)).where(
        Invoice.invoice_number == invoice.invoice_number,
        Invoice.vendor_id == invoice.vendor_id,
        Invoice.id != invoice.id,
    )) or 0
    if duplicate_count:
        add("DUPLICATE_INVOICE", "critical", "Possible duplicate invoice",
            f"{duplicate_count} other invoice(s) use this vendor invoice number.")

    if purchase_order is None:
        add("MISSING_PO", "critical", "Missing purchase order",
            "No purchase order could be matched to this invoice.")
        return MatchEvaluation(status="exception", findings=findings)

    if purchase_order.vendor_id != invoice.vendor_id:
        add("VENDOR_MISMATCH", "critical", "Vendor does not match PO",
            "Invoice supplier differs from the supplier on the purchase order.")

    po_lines = db.scalars(select(PurchaseOrderLine).where(
        PurchaseOrderLine.purchase_order_id == purchase_order.id
    )).all()
    invoice_lines = db.scalars(select(InvoiceLine).where(
        InvoiceLine.invoice_id == invoice.id
    )).all()
    if not po_lines or not invoice_lines:
        add("MISSING_LINE_ITEMS", "high", "Missing line-level evidence",
            "Purchase order or invoice has no line items.")
        return MatchEvaluation(status="insufficient_evidence", findings=findings)

    po_by_id = {line.id: line for line in po_lines}
    for line in invoice_lines:
        po_line = po_by_id.get(line.purchase_order_line_id)
        if po_line is None:
            add("UNMATCHED_PO_LINE", "high", "Invoice line has no matching PO line",
                f"Invoice line {line.line_number} cannot be mapped to this purchase order.")
            continue

        if line.unit_price != po_line.unit_price:
            variance = line.unit_price - po_line.unit_price
            add("PRICE_MISMATCH", "high", "Unit price mismatch",
                f"Invoice line {line.line_number} unit price differs from PO by {variance:+.2f}.")

        if line.quantity > po_line.quantity:
            variance = line.quantity - po_line.quantity
            add("QUANTITY_MISMATCH", "high", "Quantity exceeds ordered quantity",
                f"Invoice line {line.line_number} exceeds ordered quantity by {variance} units.")

        receipt_rows = db.execute(
            select(GoodsReceipt, GoodsReceiptLine).join(
                GoodsReceiptLine, GoodsReceiptLine.goods_receipt_id == GoodsReceipt.id
            ).where(
                GoodsReceipt.purchase_order_id == purchase_order.id,
                GoodsReceiptLine.purchase_order_line_id == po_line.id,
            )
        ).all()
        if not receipt_rows:
            add("MISSING_GOODS_RECEIPT", "high", "Goods receipt missing",
                f"No goods receipt evidence exists for PO line {po_line.line_number}.")
            continue

        received = sum((gr_line.quantity_received for _, gr_line in receipt_rows), Decimal("0"))
        if any(receipt.source != "recorded" for receipt, _ in receipt_rows):
            add("UNVERIFIED_GOODS_RECEIPT", "medium", "Synthetic receipt evidence",
                f"PO line {po_line.line_number} uses legacy-derived receipt data, not independently verified delivery evidence.")

        if line.quantity > received:
            add("QUANTITY_EXCEEDS_RECEIPT", "high", "Invoiced quantity exceeds received quantity",
                f"Invoice line {line.line_number}: billed {line.quantity}, received {received}.")

        for receipt, _ in receipt_rows:
            if receipt.received_date > purchase_order.expected_delivery_date:
                days_late = (receipt.received_date - purchase_order.expected_delivery_date).days
                if not any(f.code == "LATE_DELIVERY" for f in findings):
                    add("LATE_DELIVERY", "medium", "Late delivery",
                        f"Goods were received {days_late} days after the expected date.")

        # Count other invoices with an approved review recommendation as reserved,
        # not as proof of payment posting. Reconciliation remains human-controlled.
        reserved = db.scalar(
            select(func.coalesce(func.sum(InvoiceLine.quantity), 0))
            .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
            .join(ProcurementException, ProcurementException.invoice_id == Invoice.id)
            .where(
                InvoiceLine.purchase_order_line_id == po_line.id,
                Invoice.id != invoice.id,
                ProcurementException.status == ExceptionStatus.APPROVED,
            )
        ) or Decimal("0")
        if line.quantity + reserved > received:
            add("CUMULATIVE_RECEIPT_OVERBILL", "high", "Cumulative billed quantity exceeds receipts",
                f"Invoice line {line.line_number} plus previously reviewed quantities exceed received units.")

    total = sum((line.quantity * line.unit_price for line in invoice_lines), Decimal("0"))
    if total > purchase_order.approval_threshold:
        add("APPROVAL_THRESHOLD", "high", "Approval threshold exceeded",
            f"Invoice total {total:.2f} exceeds workflow threshold {purchase_order.approval_threshold:.2f}.")

    evidence_codes = {"MISSING_GOODS_RECEIPT", "UNVERIFIED_GOODS_RECEIPT", "MISSING_LINE_ITEMS"}
    if any(f.code not in evidence_codes for f in findings):
        status = "exception"
    elif findings:
        status = "insufficient_evidence"
    else:
        status = "matched"
    return MatchEvaluation(status=status, findings=findings)
