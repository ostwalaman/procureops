from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import DecisionType, ExceptionStatus


class Finding(BaseModel):
    code: str
    severity: str
    title: str
    detail: str


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    vendor_number: str
    name: str
    payment_terms: str
    risk_rating: str


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    po_number: str
    item_description: str
    unit_price: Decimal
    quantity: int
    expected_delivery_date: date
    received_date: date | None
    approval_threshold: Decimal


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_number: str
    po_number: str | None
    unit_price: Decimal
    quantity: int
    invoice_date: date
    due_date: date
    currency: str


class ExceptionSummary(BaseModel):
    id: int
    invoice_id: int
    invoice_number: str
    vendor_name: str
    amount: Decimal
    status: ExceptionStatus
    confidence: Decimal
    requires_manual_review: bool
    findings: list[Finding]
    updated_at: datetime


class ExceptionDetail(ExceptionSummary):
    invoice: InvoiceOut
    vendor: VendorOut
    purchase_order: PurchaseOrderOut | None
    recommendation: str
    escalation_note: str


class DecisionRequest(BaseModel):
    decision: DecisionType
    reviewer: str = Field(min_length=2, max_length=100)
    comment: str | None = Field(default=None, max_length=1000)


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int
    exception_id: int | None
    event_type: str
    actor: str
    detail: dict
    created_at: datetime
