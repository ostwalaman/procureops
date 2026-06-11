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

## Run With Docker

Docker packages the React dashboard, FastAPI backend, Python dependencies, and seeded
demo data into one repeatable application image.

Start Docker Desktop, then run:

```bash
docker compose up --build
```

Open:

- Dashboard: `http://localhost:8080`
- Interactive API documentation: `http://localhost:8080/docs`
- OpenAPI schema: `http://localhost:8080/openapi.json`

The SQLite database is stored in a Docker volume, so demo decisions remain available
after the container restarts. Stop the application with:

```bash
docker compose down
```

To reset the demo database:

```bash
docker compose down --volumes
```

OpenAI is optional. Without an API key, the agent uses deterministic recommendations.
To enable OpenAI-generated wording:

```bash
DOCKER_OPENAI_API_KEY=your-key docker compose up --build
```

Docker uses a separate `DOCKER_OPENAI_API_KEY` variable so a key stored in a local
`.env` file is not passed into the container accidentally.

## API

- `POST /api/invoices/{id}/triage`
- `GET /api/exceptions`
- `GET /api/exceptions/{id}`
- `POST /api/exceptions/{id}/decision`
- `GET /api/exceptions/{id}/audit-log`
- `GET /docs` for the OpenAPI explorer

Run the MCP server from `backend/` with `python -m app.mcp_server`.

### How OpenAPI Helps

OpenAPI is different from OpenAI. FastAPI automatically creates an OpenAPI description
of every REST endpoint, request body, and response type in this project.

The `/docs` page uses that description to provide an interactive browser interface.
It lets a reviewer or recruiter test the API without writing frontend code. For
example, they can run invoice triage, list exceptions, record a reviewer decision,
and inspect an audit log directly from the browser.

OpenAPI does not run Docker or perform invoice analysis. It documents and makes the
backend API easier to test, integrate, and understand.

## Tests

```bash
cd backend
pytest
```

## Development Approach

I built this as a portfolio project using AI-assisted development. I used AI as a
pair-programming tool while iterating on the architecture, implementation, tests,
documentation, and user interface. The project is intentionally presented as a
working SAP-style prototype, not as a production SAP integration.
