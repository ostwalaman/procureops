from app.models import Invoice, PurchaseOrder, Vendor


def test_kaggle_seed_maps_public_supply_chain_rows(kaggle_session):
    assert kaggle_session.query(Vendor).count() >= 1
    assert kaggle_session.query(PurchaseOrder).count() == 10
    assert kaggle_session.query(Invoice).count() == 10

    invoice = kaggle_session.query(Invoice).first()
    purchase_order = kaggle_session.query(PurchaseOrder).filter_by(
        po_number=invoice.po_number
    ).one()

    assert invoice.invoice_number.startswith("KINV-SKU")
    assert purchase_order.po_number.startswith("KPO-SKU")
    assert purchase_order.item_description
