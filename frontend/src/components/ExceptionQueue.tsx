import type { ExceptionSummary } from "../types";

const money = (value: string) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(Number(value));

export function ExceptionQueue({
  items,
  selectedId,
  onSelect,
}: {
  items: ExceptionSummary[];
  selectedId?: number;
  onSelect: (id: number) => void;
}) {
  return (
    <section className="queue">
      <div className="section-heading">
        <div><h2>Exception Queue</h2><span>{items.length} records requiring reviewer action</span></div>
      </div>
      <div className="queue-header"><span>Invoice / Vendor</span><span>Amount</span><span>Severity</span></div>
      <div className="queue-list">
        {items.map((item) => {
          const severity = item.findings[0]?.severity ?? "low";
          return (
            <button
              key={item.id}
              className={`queue-row ${selectedId === item.id ? "selected" : ""}`}
              onClick={() => onSelect(item.id)}
            >
              <span><strong>{item.invoice_number}</strong><small>{item.vendor_name}</small></span>
              <span>{money(item.amount)}</span>
              <span className={`severity ${severity}`}>{severity}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
