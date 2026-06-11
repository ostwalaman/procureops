import type { ViewName } from "../types";

const nav: Array<[string, string, ViewName]> = [
  ["!", "Exceptions", "exceptions"],
  ["▤", "Invoices", "invoices"],
  ["◎", "Vendors", "vendors"],
  ["◇", "Audit", "audit"],
];

export function Sidebar({ active, onNavigate }: { active: ViewName; onNavigate: (view: ViewName) => void }) {
  return (
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">P</span><strong>ProcureOps</strong></div>
      <nav>
        {nav.map(([icon, label, view]) => (
          <button className={active === view ? "active" : ""} key={view} onClick={() => onNavigate(view)}>
            <span>{icon}</span>{label}
          </button>
        ))}
      </nav>
      <div className="sidebar-foot">SAP-style enterprise agent</div>
    </aside>
  );
}
