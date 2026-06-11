from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.rules import calculate_confidence, validate_invoice
from app.agent.tools import record_audit_event, record_recommendation, retrieve_invoice_context
from app.config import get_settings
from app.models import AuditLog, ExceptionStatus, ProcurementException


class AgentState(TypedDict, total=False):
    invoice_id: int
    context: dict[str, Any]
    findings: list[dict]
    confidence: float
    recommendation: str
    escalation_note: str
    requires_manual_review: bool
    exception_id: int


def _fallback_recommendation(findings: list[dict]) -> tuple[str, str]:
    codes = {finding["code"] for finding in findings}
    if not findings:
        return (
            "Release for reviewer approval; no deterministic exceptions were detected.",
            "Three-way match validation completed without findings. Human approval is still required.",
        )
    if "MISSING_PO" in codes:
        return (
            "Hold invoice and route to Accounts Payable for manual PO resolution.",
            "The invoice cannot complete three-way matching because no purchase order was found.",
        )
    if "DUPLICATE_INVOICE" in codes:
        return (
            "Place payment hold and verify possible duplicate with Accounts Payable.",
            "A duplicate vendor invoice number was detected. Confirm before any payment action.",
        )
    return (
        "Hold invoice and request buyer review of the identified procurement exceptions.",
        "Business rule validation found: "
        + ", ".join(finding["title"] for finding in findings)
        + ". Human approval is required before further processing.",
    )


def _enhance_with_openai(findings: list[dict], fallback: tuple[str, str]) -> tuple[str, str]:
    settings = get_settings()
    if not settings.openai_api_key:
        return fallback
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(
            model=settings.openai_model,
            input=(
                "Rewrite this procurement recommendation and escalation note clearly and concisely. "
                "Do not approve, reject, or invent facts. Return two lines prefixed RECOMMENDATION: "
                f"and NOTE:. Findings: {findings}. Drafts: {fallback}"
            ),
        )
        text = response.output_text.strip()
        recommendation = text.split("NOTE:", 1)[0].replace("RECOMMENDATION:", "").strip()
        note = text.split("NOTE:", 1)[1].strip()
        return recommendation, note
    except Exception:
        return fallback


def run_triage(db: Session, invoice_id: int) -> ProcurementException:
    settings = get_settings()

    def load_context(state: AgentState) -> AgentState:
        context = retrieve_invoice_context(db, state["invoice_id"])
        record_audit_event(
            db,
            state["invoice_id"],
            "tool_context_retrieved",
            {
                "tool": "retrieve_invoice_context",
                "po_found": context["purchase_order"] is not None,
                "vendor_number": context["vendor"].vendor_number,
            },
        )
        return {"context": context}

    def validate_rules(state: AgentState) -> AgentState:
        findings = validate_invoice(
            db, state["context"]["invoice"], state["context"]["purchase_order"]
        )
        serialized = [finding.model_dump() for finding in findings]
        confidence = float(calculate_confidence(findings))
        record_audit_event(
            db,
            state["invoice_id"],
            "business_rules_validated",
            {"tool": "validate_invoice", "findings": serialized, "confidence": confidence},
        )
        return {"findings": serialized, "confidence": confidence}

    def classify(state: AgentState) -> AgentState:
        requires_manual = state["confidence"] < settings.confidence_threshold
        record_audit_event(
            db,
            state["invoice_id"],
            "exception_classified",
            {
                "finding_codes": [item["code"] for item in state["findings"]],
                "requires_manual_review": requires_manual,
                "threshold": settings.confidence_threshold,
            },
        )
        return {"requires_manual_review": requires_manual}

    def draft(state: AgentState) -> AgentState:
        fallback = _fallback_recommendation(state["findings"])
        recommendation, note = _enhance_with_openai(state["findings"], fallback)
        record_audit_event(
            db,
            state["invoice_id"],
            "recommendation_drafted",
            {
                "tool": "openai_with_deterministic_fallback",
                "used_deterministic_fallback": (recommendation, note) == fallback,
            },
        )
        return {"recommendation": recommendation, "escalation_note": note}

    def persist(state: AgentState) -> AgentState:
        exception = db.scalar(
            select(ProcurementException).where(
                ProcurementException.invoice_id == state["invoice_id"]
            )
        )
        if exception is None:
            exception = ProcurementException(
                invoice_id=state["invoice_id"],
                findings=state["findings"],
                recommendation=state["recommendation"],
                escalation_note=state["escalation_note"],
                confidence=state["confidence"],
                requires_manual_review=state["requires_manual_review"],
                status=(
                    ExceptionStatus.MANUAL_REVIEW
                    if state["requires_manual_review"]
                    else ExceptionStatus.OPEN
                ),
            )
            db.add(exception)
            db.flush()
        else:
            exception.findings = state["findings"]
            exception.confidence = state["confidence"]
            exception.requires_manual_review = state["requires_manual_review"]
            exception.status = (
                ExceptionStatus.MANUAL_REVIEW
                if state["requires_manual_review"]
                else ExceptionStatus.OPEN
            )
        record_recommendation(
            db, exception, state["recommendation"], state["escalation_note"]
        )
        # Attach this run's trace events once the exception has an ID.
        for event in db.query(AuditLog).filter_by(
            invoice_id=state["invoice_id"], exception_id=None
        ):
            event.exception_id = exception.id
        record_audit_event(
            db,
            state["invoice_id"],
            "triage_completed",
            {
                "status": exception.status.value,
                "autonomous_decision": False,
            },
            exception_id=exception.id,
        )
        db.commit()
        return {"exception_id": exception.id}

    graph = StateGraph(AgentState)
    graph.add_node("load_context", load_context)
    graph.add_node("validate_rules", validate_rules)
    graph.add_node("classify", classify)
    graph.add_node("draft", draft)
    graph.add_node("persist", persist)
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "validate_rules")
    graph.add_edge("validate_rules", "classify")
    graph.add_edge("classify", "draft")
    graph.add_edge("draft", "persist")
    graph.add_edge("persist", END)
    result = graph.compile().invoke({"invoice_id": invoice_id})
    return db.get(ProcurementException, result["exception_id"])
