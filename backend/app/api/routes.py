from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.tools import record_audit_event
from app.agent.workflow import run_triage
from app.config import get_settings
from app.database import get_db
from app.models import (
    ApprovalDecision,
    AuditLog,
    DecisionType,
    ExceptionStatus,
    Invoice,
    ProcurementException,
    PurchaseOrder,
    Vendor,
)
from app.schemas import (
    AuditLogOut,
    DecisionRequest,
    ExceptionDetail,
    ExceptionSummary,
    InvoiceOut,
    PurchaseOrderOut,
    VendorOut,
)

router = APIRouter(prefix="/api")


def _summary(exception: ProcurementException) -> ExceptionSummary:
    return ExceptionSummary(
        id=exception.id,
        invoice_id=exception.invoice_id,
        invoice_number=exception.invoice.invoice_number,
        vendor_name=exception.invoice.vendor.name,
        amount=exception.invoice.total,
        status=exception.status,
        confidence=exception.confidence,
        requires_manual_review=exception.requires_manual_review,
        findings=exception.findings,
        updated_at=exception.updated_at,
    )


def _detail(db: Session, exception: ProcurementException) -> ExceptionDetail:
    purchase_order = (
        db.scalar(
            select(PurchaseOrder).where(
                PurchaseOrder.po_number == exception.invoice.po_number
            )
        )
        if exception.invoice.po_number
        else None
    )
    return ExceptionDetail(
        **_summary(exception).model_dump(),
        invoice=InvoiceOut.model_validate(exception.invoice),
        vendor=VendorOut.model_validate(exception.invoice.vendor),
        purchase_order=PurchaseOrderOut.model_validate(purchase_order)
        if purchase_order
        else None,
        recommendation=exception.recommendation,
        escalation_note=exception.escalation_note,
    )


@router.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "data_source": settings.data_source,
        "kaggle_dataset": (
            "harshsingh2209/supply-chain-analysis"
            if settings.data_source == "kaggle"
            else None
        ),
    }


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db)):
    return db.scalars(select(Invoice).order_by(Invoice.id)).all()


@router.get("/vendors", response_model=list[VendorOut])
def list_vendors(db: Session = Depends(get_db)):
    return db.scalars(select(Vendor).order_by(Vendor.vendor_number)).all()


@router.get("/audit-log", response_model=list[AuditLogOut])
def list_audit_log(db: Session = Depends(get_db)):
    return db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc())).all()


@router.post("/invoices/{invoice_id}/triage", response_model=ExceptionDetail)
def triage_invoice(invoice_id: int, db: Session = Depends(get_db)):
    if db.get(Invoice, invoice_id) is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _detail(db, run_triage(db, invoice_id))


@router.get("/exceptions", response_model=list[ExceptionSummary])
def list_exceptions(db: Session = Depends(get_db)):
    exceptions = db.scalars(
        select(ProcurementException).order_by(ProcurementException.updated_at.desc())
    ).all()
    return [_summary(exception) for exception in exceptions]


@router.get("/exceptions/{exception_id}", response_model=ExceptionDetail)
def get_exception(exception_id: int, db: Session = Depends(get_db)):
    exception = db.get(ProcurementException, exception_id)
    if exception is None:
        raise HTTPException(status_code=404, detail="Exception not found")
    return _detail(db, exception)


@router.post("/exceptions/{exception_id}/decision", response_model=ExceptionDetail)
def decide_exception(
    exception_id: int, request: DecisionRequest, db: Session = Depends(get_db)
):
    exception = db.get(ProcurementException, exception_id)
    if exception is None:
        raise HTTPException(status_code=404, detail="Exception not found")
    statuses = {
        DecisionType.APPROVE_RECOMMENDATION: ExceptionStatus.APPROVED,
        DecisionType.SEND_TO_MANUAL_REVIEW: ExceptionStatus.MANUAL_REVIEW,
        DecisionType.REJECT_RECOMMENDATION: ExceptionStatus.REJECTED,
    }
    exception.status = statuses[request.decision]
    db.add(
        ApprovalDecision(
            exception_id=exception.id,
            decision=request.decision,
            reviewer=request.reviewer,
            comment=request.comment,
        )
    )
    record_audit_event(
        db,
        exception.invoice_id,
        "reviewer_decision_recorded",
        {"decision": request.decision.value, "comment": request.comment},
        exception_id=exception.id,
        actor=request.reviewer,
    )
    db.commit()
    return _detail(db, exception)


@router.get("/exceptions/{exception_id}/audit-log", response_model=list[AuditLogOut])
def get_audit_log(exception_id: int, db: Session = Depends(get_db)):
    if db.get(ProcurementException, exception_id) is None:
        raise HTTPException(status_code=404, detail="Exception not found")
    return db.scalars(
        select(AuditLog)
        .where(AuditLog.exception_id == exception_id)
        .order_by(AuditLog.created_at)
    ).all()
