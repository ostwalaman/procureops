from decimal import Decimal

from sqlalchemy import select

from app.agent.rules import calculate_confidence, validate_invoice
from app.agent.workflow import _enhance_with_openai
from app.config import Settings
from app.models import Invoice, PurchaseOrder


def test_detects_price_quantity_late_delivery_and_threshold(session):
    invoice = session.scalar(select(Invoice).where(Invoice.invoice_number == "INV-78421"))
    po = session.scalar(select(PurchaseOrder).where(PurchaseOrder.po_number == "PO-45009182"))

    findings = validate_invoice(session, invoice, po)
    codes = {finding.code for finding in findings}

    assert {"PRICE_MISMATCH", "QUANTITY_MISMATCH", "LATE_DELIVERY", "APPROVAL_THRESHOLD"} <= codes


def test_missing_po_has_low_confidence(session):
    invoice = session.scalar(select(Invoice).where(Invoice.po_number.is_(None)))
    findings = validate_invoice(session, invoice, None)

    assert "MISSING_PO" in {finding.code for finding in findings}
    assert calculate_confidence(findings) == Decimal("0.620")


def test_duplicate_invoice_detection(session):
    invoices = session.scalars(select(Invoice).where(Invoice.invoice_number == "INV-78421")).all()
    findings = validate_invoice(session, invoices[0], None)

    assert "DUPLICATE_INVOICE" in {finding.code for finding in findings}


def test_clean_invoice_has_high_confidence(session):
    invoice = session.scalar(select(Invoice).where(Invoice.invoice_number == "INV-99130"))
    po = session.scalar(select(PurchaseOrder).where(PurchaseOrder.po_number == invoice.po_number))
    findings = validate_invoice(session, invoice, po)

    assert findings == []
    assert calculate_confidence(findings) == Decimal("0.970")


def test_unavailable_ai_service_uses_deterministic_fallback(monkeypatch):
    class UnavailableOpenAI:
        def __init__(self, **_):
            raise RuntimeError("service unavailable")

    fallback = ("Hold invoice for review.", "Deterministic escalation note.")
    monkeypatch.setattr("app.agent.workflow.OpenAI", UnavailableOpenAI)
    monkeypatch.setattr(
        "app.agent.workflow.get_settings",
        lambda: Settings(openai_api_key="configured-for-test"),
    )

    assert _enhance_with_openai([], fallback) == fallback
