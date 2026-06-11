import type { ExceptionDetail } from "../types";

const money = (value: string | number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number(value));

export function InvoiceEvidence({ detail }: { detail: ExceptionDetail }) {
  const po = detail.purchase_order;
  const invoiceTotal = Number(detail.invoice.unit_price) * detail.invoice.quantity;
  const poTotal = po ? Number(po.unit_price) * po.quantity : 0;
  return (
    <main className="evidence">
      <div className="detail-title">
        <div><span className="label">INVOICE REVIEW</span><h2>{detail.invoice_number}</h2></div>
        <span className={`status ${detail.status}`}>{detail.status.replace("_", " ")}</span>
      </div>
      <div className="facts">
        <div><span>Vendor</span><strong>{detail.vendor.name}</strong><small>{detail.vendor.vendor_number}</small></div>
        <div><span>Invoice date</span><strong>{detail.invoice.invoice_date}</strong></div>
        <div><span>Invoice amount</span><strong>{money(invoiceTotal)}</strong></div>
        <div><span>Due date</span><strong>{detail.invoice.due_date}</strong></div>
      </div>

      <section className="content-section">
        <div className="section-heading"><div><h3>PO comparison</h3><span>Three-way match evidence</span></div></div>
        {po ? (
          <div className="comparison">
            <div className="comparison-head"><span>Field</span><span>Purchase order</span><span>Invoice</span><span>Variance</span></div>
            <div><span>Reference</span><strong>{po.po_number}</strong><strong>{detail.invoice.po_number}</strong><em>Matched</em></div>
            <div><span>Unit price</span><strong>{money(po.unit_price)}</strong><strong>{money(detail.invoice.unit_price)}</strong><em className={po.unit_price !== detail.invoice.unit_price ? "negative" : ""}>{money(Number(detail.invoice.unit_price) - Number(po.unit_price))}</em></div>
            <div><span>Quantity</span><strong>{po.quantity}</strong><strong>{detail.invoice.quantity}</strong><em className={po.quantity !== detail.invoice.quantity ? "negative" : ""}>{detail.invoice.quantity - po.quantity}</em></div>
            <div><span>Total</span><strong>{money(poTotal)}</strong><strong>{money(invoiceTotal)}</strong><em className={poTotal !== invoiceTotal ? "negative" : ""}>{money(invoiceTotal - poTotal)}</em></div>
          </div>
        ) : <div className="missing-po">No purchase order was provided. Three-way matching cannot complete.</div>}
      </section>

      <section className="content-section">
        <div className="section-heading"><div><h3>Delivery and controls</h3><span>Vendor and approval workflow context</span></div></div>
        <div className="control-strip">
          <div><span>Expected delivery</span><strong>{po?.expected_delivery_date ?? "Unavailable"}</strong></div>
          <div><span>Goods receipt</span><strong>{po?.received_date ?? "Not received"}</strong></div>
          <div><span>Approval threshold</span><strong>{po ? money(po.approval_threshold) : "Unavailable"}</strong></div>
          <div><span>Payment terms</span><strong>{detail.vendor.payment_terms}</strong></div>
        </div>
      </section>

      <section className="content-section findings">
        <div className="section-heading"><div><h3>Business rule findings</h3><span>{detail.findings.length || "No"} exceptions detected</span></div></div>
        {detail.findings.length ? detail.findings.map((finding) => (
          <div className="finding" key={finding.code}>
            <span className={`finding-icon ${finding.severity}`}>!</span>
            <span><strong>{finding.title}</strong><small>{finding.detail}</small></span>
            <em className={`severity ${finding.severity}`}>{finding.severity}</em>
          </div>
        )) : <div className="clean-match">All deterministic business rules passed.</div>}
      </section>
    </main>
  );
}
