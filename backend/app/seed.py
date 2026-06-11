from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Invoice, PurchaseOrder, Vendor


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(Vendor.id).limit(1)):
        return

    today = date.today()
    vendors = [
        Vendor(vendor_number="V-10024", name="Northstar Industrial Supply", payment_terms="Net 30", risk_rating="low"),
        Vendor(vendor_number="V-10038", name="Apex Components Group", payment_terms="Net 45", risk_rating="medium"),
        Vendor(vendor_number="V-10051", name="Meridian Office Systems", payment_terms="Net 30", risk_rating="low"),
    ]
    db.add_all(vendors)
    db.flush()

    purchase_orders = [
        PurchaseOrder(po_number="PO-45009182", vendor_id=vendors[0].id, item_description="Industrial valve assemblies", unit_price=Decimal("125.00"), quantity=80, expected_delivery_date=today - timedelta(days=12), received_date=today - timedelta(days=4), approval_threshold=Decimal("10000.00")),
        PurchaseOrder(po_number="PO-45009217", vendor_id=vendors[1].id, item_description="Control board modules", unit_price=Decimal("240.00"), quantity=40, expected_delivery_date=today - timedelta(days=20), received_date=today - timedelta(days=5), approval_threshold=Decimal("12000.00")),
        PurchaseOrder(po_number="PO-45009264", vendor_id=vendors[2].id, item_description="Ergonomic workstation kits", unit_price=Decimal("780.00"), quantity=10, expected_delivery_date=today + timedelta(days=5), received_date=None, approval_threshold=Decimal("10000.00")),
        PurchaseOrder(po_number="PO-45009301", vendor_id=vendors[0].id, item_description="Replacement actuator kits", unit_price=Decimal("95.00"), quantity=20, expected_delivery_date=today - timedelta(days=1), received_date=today - timedelta(days=2), approval_threshold=Decimal("5000.00")),
    ]
    db.add_all(purchase_orders)
    db.flush()

    invoices = [
        Invoice(invoice_number="INV-78421", vendor_id=vendors[0].id, po_number="PO-45009182", unit_price=Decimal("137.50"), quantity=84, invoice_date=today - timedelta(days=3), due_date=today + timedelta(days=27)),
        Invoice(invoice_number="INV-66104", vendor_id=vendors[1].id, po_number="PO-45009217", unit_price=Decimal("240.00"), quantity=40, invoice_date=today - timedelta(days=5), due_date=today + timedelta(days=40)),
        Invoice(invoice_number="INV-55209", vendor_id=vendors[2].id, po_number=None, unit_price=Decimal("2200.00"), quantity=1, invoice_date=today - timedelta(days=2), due_date=today + timedelta(days=28)),
        Invoice(invoice_number="INV-78421", vendor_id=vendors[0].id, po_number="PO-45009301", unit_price=Decimal("95.00"), quantity=20, invoice_date=today - timedelta(days=1), due_date=today + timedelta(days=29)),
        Invoice(invoice_number="INV-99130", vendor_id=vendors[2].id, po_number="PO-45009264", unit_price=Decimal("780.00"), quantity=10, invoice_date=today, due_date=today + timedelta(days=30)),
    ]
    db.add_all(invoices)
    db.commit()

