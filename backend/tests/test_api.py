from sqlalchemy import select

from app.agent.workflow import run_triage
from app.models import AuditLog, Invoice, ProcurementException


def test_seeded_workflow_routes_cover_clean_and_exception_cases(client):
    expected_findings = {
        1: {
            "DUPLICATE_INVOICE",
            "PRICE_MISMATCH",
            "QUANTITY_MISMATCH",
            "LATE_DELIVERY",
            "APPROVAL_THRESHOLD",
        },
        2: {"LATE_DELIVERY"},
        3: {"MISSING_PO"},
        4: {"DUPLICATE_INVOICE"},
        5: set(),
    }

    for invoice_id, expected_codes in expected_findings.items():
        payload = client.post(f"/api/invoices/{invoice_id}/triage").json()
        assert {finding["code"] for finding in payload["findings"]} == expected_codes

    assert client.post("/api/invoices/3/triage").json()["status"] == "manual_review"
    assert client.post("/api/invoices/5/triage").json()["status"] == "open"


def test_triage_persists_exception_and_complete_trace(client, session):
    response = client.post("/api/invoices/1/triage")
    assert response.status_code == 200
    payload = response.json()
    assert payload["invoice_id"] == 1
    assert payload["recommendation"]
    assert len(payload["findings"]) >= 3

    audit = client.get(f"/api/exceptions/{payload['id']}/audit-log").json()
    events = {entry["event_type"] for entry in audit}
    assert {
        "tool_context_retrieved",
        "business_rules_validated",
        "exception_classified",
        "recommendation_drafted",
        "triage_completed",
    } <= events


def test_low_confidence_routes_to_manual_review(client):
    response = client.post("/api/invoices/3/triage")
    payload = response.json()

    assert payload["requires_manual_review"] is True
    assert payload["status"] == "manual_review"


def test_duplicate_triage_updates_single_exception(client, session):
    client.post("/api/invoices/2/triage")
    client.post("/api/invoices/2/triage")

    count = session.query(ProcurementException).filter_by(invoice_id=2).count()
    assert count == 1


def test_reviewer_decision_is_audited(client):
    exception = client.post("/api/invoices/1/triage").json()
    response = client.post(
        f"/api/exceptions/{exception['id']}/decision",
        json={"decision": "approve_recommendation", "reviewer": "Avery Chen"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    audit = client.get(f"/api/exceptions/{exception['id']}/audit-log").json()
    assert audit[-1]["event_type"] == "reviewer_decision_recorded"
    assert audit[-1]["actor"] == "Avery Chen"


def test_navigation_data_endpoints(client):
    assert len(client.get("/api/invoices").json()) == 5
    assert len(client.get("/api/vendors").json()) == 3

    client.post("/api/invoices/1/triage")
    audit = client.get("/api/audit-log").json()
    assert audit
    assert audit[0]["invoice_id"]
