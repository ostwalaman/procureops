import type { AuditEvent, Invoice, Vendor, ViewName } from "../types";

const titleCase = (value: string) => value.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
const money = (value: number, currency = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency }).format(value);

export function RecordsView({
  view,
  invoices,
  vendors,
  audit,
  onOpenInvoice,
}: {
  view: Exclude<ViewName, "exceptions">;
  invoices: Invoice[];
  vendors: Vendor[];
  audit: AuditEvent[];
  onOpenInvoice: (invoiceId: number) => void;
}) {
  if (view === "invoices") {
    return (
      <section className="records-page">
        <div className="records-heading"><div><h2>Supplier Invoices</h2><p>All invoices available for procurement validation.</p></div><strong>{invoices.length} records</strong></div>
        <div className="records-table invoices-table">
          <div className="records-row records-header"><span>Invoice</span><span>Purchase order</span><span>Date</span><span>Quantity</span><span>Total</span><span>Action</span></div>
          {invoices.map((invoice) => (
            <div className="records-row" key={invoice.id}>
              <strong>{invoice.invoice_number}</strong><span>{invoice.po_number ?? "Missing PO"}</span><span>{invoice.invoice_date}</span>
              <span>{invoice.quantity}</span><span>{money(Number(invoice.unit_price) * invoice.quantity, invoice.currency)}</span>
              <button onClick={() => onOpenInvoice(invoice.id)}>Open review</button>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (view === "vendors") {
    return (
      <section className="records-page">
        <div className="records-heading"><div><h2>Vendor Master</h2><p>Supplier records used during invoice validation.</p></div><strong>{vendors.length} vendors</strong></div>
        <div className="records-table vendors-table">
          <div className="records-row records-header"><span>Vendor number</span><span>Name</span><span>Payment terms</span><span>Risk rating</span></div>
          {vendors.map((vendor) => (
            <div className="records-row" key={vendor.vendor_number}>
              <strong>{vendor.vendor_number}</strong><span>{vendor.name}</span><span>{vendor.payment_terms}</span>
              <span className={`severity ${vendor.risk_rating}`}>{vendor.risk_rating}</span>
            </div>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="records-page">
      <div className="records-heading"><div><h2>Audit Log</h2><p>Complete trace of agent tools, rules, recommendations, and reviewer actions.</p></div><strong>{audit.length} events</strong></div>
      <div className="records-table audit-table">
        <div className="records-row records-header"><span>Time</span><span>Invoice ID</span><span>Event</span><span>Actor</span><span>Recorded detail</span></div>
        {audit.map((event) => (
          <div className="records-row" key={event.id}>
            <span>{new Date(event.created_at).toLocaleString()}</span><strong>#{event.invoice_id}</strong>
            <span>{titleCase(event.event_type)}</span><span>{event.actor}</span><code>{JSON.stringify(event.detail)}</code>
          </div>
        ))}
      </div>
    </section>
  );
}
