import type { AuditEvent, ExceptionDetail, ExceptionSummary, Health, Invoice, Vendor } from "../types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),
  listExceptions: () => request<ExceptionSummary[]>("/api/exceptions"),
  listInvoices: () => request<Invoice[]>("/api/invoices"),
  listVendors: () => request<Vendor[]>("/api/vendors"),
  listAudit: () => request<AuditEvent[]>("/api/audit-log"),
  getException: (id: number) => request<ExceptionDetail>(`/api/exceptions/${id}`),
  getAudit: (id: number) => request<AuditEvent[]>(`/api/exceptions/${id}/audit-log`),
  triage: (invoiceId: number) =>
    request<ExceptionDetail>(`/api/invoices/${invoiceId}/triage`, { method: "POST" }),
  decide: (id: number, decision: string) =>
    request<ExceptionDetail>(`/api/exceptions/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, reviewer: "Demo Reviewer" }),
    }),
};
