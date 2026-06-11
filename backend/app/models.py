from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import JSON, Date, DateTime, Enum as SqlEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ExceptionStatus(str, Enum):
    OPEN = "open"
    MANUAL_REVIEW = "manual_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class DecisionType(str, Enum):
    APPROVE_RECOMMENDATION = "approve_recommendation"
    SEND_TO_MANUAL_REVIEW = "send_to_manual_review"
    REJECT_RECOMMENDATION = "reject_recommendation"


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_number: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    payment_terms: Mapped[str] = mapped_column(String(50))
    risk_rating: Mapped[str] = mapped_column(String(20), default="low")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    po_number: Mapped[str] = mapped_column(String(30), unique=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    item_description: Mapped[str] = mapped_column(String(160))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int]
    expected_delivery_date: Mapped[date] = mapped_column(Date)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    approval_threshold: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    vendor: Mapped[Vendor] = relationship()


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(30))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id"))
    po_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int]
    invoice_date: Mapped[date] = mapped_column(Date)
    due_date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    vendor: Mapped[Vendor] = relationship()

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity


class ProcurementException(Base):
    __tablename__ = "procurement_exceptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), unique=True)
    status: Mapped[ExceptionStatus] = mapped_column(
        SqlEnum(ExceptionStatus), default=ExceptionStatus.OPEN
    )
    findings: Mapped[list] = mapped_column(JSON)
    recommendation: Mapped[str] = mapped_column(Text)
    escalation_note: Mapped[str] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    requires_manual_review: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    invoice: Mapped[Invoice] = relationship()


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    exception_id: Mapped[int] = mapped_column(ForeignKey("procurement_exceptions.id"))
    decision: Mapped[DecisionType] = mapped_column(SqlEnum(DecisionType))
    reviewer: Mapped[str] = mapped_column(String(100))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    exception_id: Mapped[int | None] = mapped_column(
        ForeignKey("procurement_exceptions.id"), nullable=True
    )
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    event_type: Mapped[str] = mapped_column(String(60))
    actor: Mapped[str] = mapped_column(String(100))
    detail: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
