import csv
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import Invoice, PurchaseOrder, Vendor

DATASET_REF = "harshsingh2209/supply-chain-analysis"
DATASET_URL = f"https://www.kaggle.com/datasets/{DATASET_REF}"
DATASET_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "kaggle" / "supply_chain_data.csv"
)


def _money(value: str) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"))


def seed_kaggle_data(db: Session, row_limit: int = 30) -> None:
    """Map public Kaggle supply-chain rows into SAP-style procurement records.

    The source does not contain invoices or purchase orders. Those records and their
    dates are derived deterministically from source supplier, SKU, pricing, quantity,
    lead-time, inspection, and defect-rate fields.
    """
    with DATASET_PATH.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))[:row_limit]

    supplier_names = sorted({row["Supplier name"] for row in rows})
    vendors: dict[str, Vendor] = {}
    for index, name in enumerate(supplier_names, start=1):
        vendor = Vendor(
            vendor_number=f"KAG-{index:03d}",
            name=name,
            payment_terms="Net 30",
            risk_rating="medium"
            if any(
                row["Supplier name"] == name
                and row["Inspection results"].lower() == "fail"
                for row in rows
            )
            else "low",
        )
        db.add(vendor)
        vendors[name] = vendor
    db.flush()

    today = date.today()
    for index, row in enumerate(rows, start=1):
        price = _money(row["Price"])
        order_quantity = int(row["Order quantities"])
        lead_time = int(row["Lead time"])
        shipping_time = int(row["Shipping times"])
        inspection = row["Inspection results"].lower()
        defect_rate = Decimal(row["Defect rates"])
        expected_date = today - timedelta(days=max(lead_time, 1))
        received_date = expected_date + timedelta(days=shipping_time)
        po_number = f"KPO-{row['SKU']}-{index:03d}"

        db.add(
            PurchaseOrder(
                po_number=po_number,
                vendor_id=vendors[row["Supplier name"]].id,
                item_description=(
                    f"{row['Product type'].title()} {row['SKU']} via "
                    f"{row['Transportation modes']} ({row['Routes']})"
                ),
                unit_price=price,
                quantity=order_quantity,
                expected_delivery_date=expected_date,
                received_date=received_date,
                approval_threshold=_money(row["Costs"]) * Decimal("10"),
            )
        )

        # Create explainable exception scenarios from quality signals in the source.
        invoice_price = (
            (price * Decimal("1.05")).quantize(Decimal("0.01"))
            if inspection == "fail"
            else price
        )
        invoice_quantity = order_quantity + 1 if defect_rate >= Decimal("4") else order_quantity
        db.add(
            Invoice(
                invoice_number=f"KINV-{row['SKU']}-{index:03d}",
                vendor_id=vendors[row["Supplier name"]].id,
                po_number=po_number,
                unit_price=invoice_price,
                quantity=invoice_quantity,
                invoice_date=today - timedelta(days=index % 10),
                due_date=today + timedelta(days=30),
            )
        )
    db.commit()
