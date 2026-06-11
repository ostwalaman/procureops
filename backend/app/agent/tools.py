from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Invoice, ProcurementException, PurchaseOrder, Vendor


def retrieve_invoice_context(db: Session, invoice_id: int) -> dict[str, Any]:
    """MCP-compatible tool: retrieve invoice, vendor master, and PO context."""
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise ValueError(f"Invoice {invoice_id} not found")
    vendor = db.get(Vendor, invoice.vendor_id)
    purchase_order = (
        db.scalar(select(PurchaseOrder).where(PurchaseOrder.po_number == invoice.po_number))
        if invoice.po_number
        else None
    )
    return {"invoice": invoice, "vendor": vendor, "purchase_order": purchase_order}


def record_audit_event(
    db: Session,
    invoice_id: int,
    event_type: str,
    detail: dict,
    *,
    exception_id: int | None = None,
    actor: str = "procurement-agent",
) -> AuditLog:
    """MCP-compatible tool: append an immutable agent or reviewer trace event."""
    event = AuditLog(
        exception_id=exception_id,
        invoice_id=invoice_id,
        event_type=event_type,
        actor=actor,
        detail=detail,
    )
    db.add(event)
    db.flush()
    return event


def record_recommendation(
    db: Session, exception: ProcurementException, recommendation: str, note: str
) -> ProcurementException:
    """MCP-compatible tool: persist recommendation output against an exception."""
    exception.recommendation = recommendation
    exception.escalation_note = note
    db.add(exception)
    db.flush()
    return exception

