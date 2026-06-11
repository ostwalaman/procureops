export type Finding = {
  code: string;
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  detail: string;
};

export type ExceptionSummary = {
  id: number;
  invoice_id: number;
  invoice_number: string;
  vendor_name: string;
  amount: string;
  status: string;
  confidence: string;
  requires_manual_review: boolean;
  findings: Finding[];
  updated_at: string;
};

export type ExceptionDetail = ExceptionSummary & {
  invoice: {
    id: number;
    invoice_number: string;
    po_number: string | null;
    unit_price: string;
    quantity: number;
    invoice_date: string;
    due_date: string;
    currency: string;
  };
  vendor: {
    vendor_number: string;
    name: string;
    payment_terms: string;
    risk_rating: string;
  };
  purchase_order: null | {
    po_number: string;
    item_description: string;
    unit_price: string;
    quantity: number;
    expected_delivery_date: string;
    received_date: string | null;
    approval_threshold: string;
  };
  recommendation: string;
  escalation_note: string;
};

export type AuditEvent = {
  id: number;
  invoice_id: number;
  exception_id: number | null;
  event_type: string;
  actor: string;
  detail: Record<string, unknown>;
  created_at: string;
};

export type Invoice = {
  id: number;
  invoice_number: string;
  po_number: string | null;
  unit_price: string;
  quantity: number;
  invoice_date: string;
  due_date: string;
  currency: string;
};

export type Vendor = {
  vendor_number: string;
  name: string;
  payment_terms: string;
  risk_rating: string;
};

export type ViewName = "exceptions" | "invoices" | "vendors" | "audit";
