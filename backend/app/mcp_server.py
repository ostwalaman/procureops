"""Optional stdio MCP server exposing governed procurement tools.

Run with `python -m app.mcp_server` after installing backend requirements.
"""

from mcp.server.fastmcp import FastMCP

from app.database import SessionLocal
from app.models import Invoice, PurchaseOrder, Vendor

mcp = FastMCP("procureops")


def _model_dict(model):
    if model is None:
        return None
    return {
        column.name: str(getattr(model, column.name))
        for column in model.__table__.columns
    }


@mcp.tool()
def get_invoice_context(invoice_id: int) -> dict:
    """Retrieve invoice, vendor master, and purchase-order context."""
    with SessionLocal() as db:
        invoice = db.get(Invoice, invoice_id)
        if invoice is None:
            return {"error": "invoice_not_found"}
        vendor = db.get(Vendor, invoice.vendor_id)
        purchase_order = (
            db.query(PurchaseOrder)
            .filter(PurchaseOrder.po_number == invoice.po_number)
            .first()
            if invoice.po_number
            else None
        )
        return {
            "invoice": _model_dict(invoice),
            "vendor": _model_dict(vendor),
            "purchase_order": _model_dict(purchase_order),
        }


@mcp.tool()
def get_business_rule_catalog() -> list[dict]:
    """Return the deterministic validation controls used by the agent."""
    return [
        {"code": "PRICE_MISMATCH", "control": "Invoice unit price must match PO"},
        {"code": "QUANTITY_MISMATCH", "control": "Invoice quantity must match PO"},
        {"code": "LATE_DELIVERY", "control": "Receipt date must not exceed expected date"},
        {"code": "MISSING_PO", "control": "Invoice must reference a valid PO"},
        {"code": "DUPLICATE_INVOICE", "control": "Vendor invoice number must be unique"},
        {"code": "APPROVAL_THRESHOLD", "control": "Total must remain within approval threshold"},
    ]


if __name__ == "__main__":
    mcp.run()

