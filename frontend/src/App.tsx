import { useEffect, useState } from "react";
import { AgentPanel } from "./components/AgentPanel";
import { ExceptionQueue } from "./components/ExceptionQueue";
import { InvoiceEvidence } from "./components/InvoiceEvidence";
import { RecordsView } from "./components/RecordsView";
import { Sidebar } from "./components/Sidebar";
import { api } from "./lib/api";
import type { AuditEvent, ExceptionDetail, ExceptionSummary, Health, Invoice, Vendor, ViewName } from "./types";
import "./styles.css";

const headings: Record<ViewName, [string, string]> = {
  exceptions: ["Procurement Exception Review", "Review and act on exceptions identified by the agent."],
  invoices: ["Supplier Invoices", "Browse invoices and open them in the exception review workflow."],
  vendors: ["Vendor Master", "Review the supplier records used by procurement controls."],
  audit: ["Audit Log", "Inspect the complete trace of automated and reviewer actions."],
};

export default function App() {
  const [view, setView] = useState<ViewName>("exceptions");
  const [items, setItems] = useState<ExceptionSummary[]>([]);
  const [detail, setDetail] = useState<ExceptionDetail>();
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [allAudit, setAllAudit] = useState<AuditEvent[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [health, setHealth] = useState<Health>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function selectException(id: number) {
    try {
      setError("");
      const [nextDetail, nextAudit] = await Promise.all([api.getException(id), api.getAudit(id)]);
      setDetail(nextDetail);
      setAudit(nextAudit);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load exception");
    }
  }

  async function refresh(preferredId?: number) {
    const [nextItems, nextInvoices, nextVendors, nextAudit, nextHealth] = await Promise.all([
      api.listExceptions(),
      api.listInvoices(),
      api.listVendors(),
      api.listAudit(),
      api.health(),
    ]);
    setItems(nextItems);
    setInvoices(nextInvoices);
    setVendors(nextVendors);
    setAllAudit(nextAudit);
    setHealth(nextHealth);
    const nextId = preferredId ?? detail?.id ?? nextItems[0]?.id;
    if (nextId) await selectException(nextId);
  }

  useEffect(() => {
    void refresh().catch((cause) => setError(cause instanceof Error ? cause.message : "Unable to load data"));
  }, []);

  async function decide(decision: string) {
    if (!detail) return;
    setBusy(true);
    try {
      await api.decide(detail.id, decision);
      await refresh(detail.id);
    } finally {
      setBusy(false);
    }
  }

  async function retriage() {
    if (!detail) return;
    setBusy(true);
    try {
      await api.triage(detail.invoice_id);
      await refresh(detail.id);
    } finally {
      setBusy(false);
    }
  }

  async function openInvoice(invoiceId: number) {
    let exception = items.find((item) => item.invoice_id === invoiceId);
    if (!exception) {
      const created = await api.triage(invoiceId);
      exception = created;
      await refresh(created.id);
    } else {
      await selectException(exception.id);
    }
    setView("exceptions");
  }

  const [title, subtitle] = headings[view];

  return (
    <div className="app-shell">
      <Sidebar active={view} onNavigate={setView} />
      <header className="topbar">
        <div><h1>{title}</h1><p>{subtitle}</p></div>
        <div className="environment">
          <span /> {health?.data_source === "kaggle" ? "Kaggle supply-chain data" : "Seeded demo data"}
        </div>
      </header>
      {error ? <div className="error-banner">{error}</div> : null}
      {view === "exceptions" ? (
        <div className="workspace">
          <ExceptionQueue items={items} selectedId={detail?.id} onSelect={(id) => void selectException(id)} />
          {detail ? <InvoiceEvidence detail={detail} /> : <div className="loading">Loading procurement context…</div>}
          {detail ? <AgentPanel detail={detail} audit={audit} busy={busy} onDecision={(decision) => void decide(decision)} onRetriage={() => void retriage()} /> : null}
        </div>
      ) : (
        <RecordsView view={view} invoices={invoices} vendors={vendors} audit={allAudit} onOpenInvoice={(id) => void openInvoice(id)} />
      )}
    </div>
  );
}
