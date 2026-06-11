# ProcureOps: SAP-Style Procurement Exception Agent

ProcureOps is a portfolio project demonstrating an **SAP-style enterprise procurement agent**. It is not built by SAP and is not a Joule implementation.

The application performs deterministic business-rule validation before using an optional OpenAI model to improve recommendation wording. It never autonomously approves or rejects invoices. Every tool call, classification, recommendation, fallback, and reviewer decision is written to an audit trace.

## What It Demonstrates

- Three-way procurement matching across invoice, purchase order, vendor master, and delivery records
- Price, quantity, late-delivery, missing-PO, duplicate-invoice, and approval-threshold controls
- LangGraph orchestration with explicit low-confidence routing
- MCP server exposing procurement-context and rule-catalog tools
- Human approval workflow with immutable audit events
- FastAPI, React, SQLAlchemy, SQLite locally, and Postgres-compatible configuration
- Deterministic fallback when OpenAI is unavailable

## SAP Product Boundary

No licensed SAP product is required to run this portfolio MVP. The application models
procurement concepts commonly managed in SAP S/4HANA: vendor master data, purchase
orders, goods receipts, supplier invoices, three-way matching, approval workflows,
and audit trails.

The current implementation uses local seeded records behind SQLAlchemy instead of a
live SAP system. A production integration would replace that repository boundary with:

- SAP S/4HANA APIs for supplier invoices, purchase orders, business partners, and goods receipts
- SAP BTP destination and connectivity services for governed API access
- SAP CAP/OData as an optional service layer and Fiori Elements as an optional reviewer UI
- SAP Build Process Automation or an S/4HANA workflow for the final human approval step

The agent remains decision support only: it recommends an action and drafts an
escalation note, while a reviewer records the actual approval decision.

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Seed data and initial triage records are created automatically.

## API

- `POST /api/invoices/{id}/triage`
- `GET /api/exceptions`
- `GET /api/exceptions/{id}`
- `POST /api/exceptions/{id}/decision`
- `GET /api/exceptions/{id}/audit-log`
- `GET /docs` for the OpenAPI explorer

Run the MCP server from `backend/` with `python -m app.mcp_server`.

## Tests

```bash
cd backend
pytest
```

## Cloud Run

The root `Dockerfile` builds the React dashboard and Python API into one Cloud Run image. Configure a Postgres `DATABASE_URL` for durable production persistence; SQLite is intended for the local demo.

```bash
gcloud run deploy procureops \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars CONFIDENCE_THRESHOLD=0.75
```

For a real deployment, store `OPENAI_API_KEY` and database credentials in Secret Manager and remove unauthenticated access.
