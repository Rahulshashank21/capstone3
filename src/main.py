import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

from src.domain.models import Role
from src.services.subscription_service import SubscriptionService
from src.services.reporting_service import ReportingService
from src.controllers.api_controller import APIController
from src.seed import seed_database

# Initialize core services and seed data
service = SubscriptionService()
seed_database(service)
reporting_service = ReportingService(service.subscriber_repo, service.plan_repo, service.audit_repo, service.billing_repo)
controller = APIController(service, reporting_service)

app = FastAPI(
    title="TelcoLane Subscriber Operations Substrate",
    version="1.0.0",
    description="Telecom Subscriber Lifecycle & Plan Management Platform (BC-AINE-020)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    corr_id = request.headers.get("X-Correlation-ID") or f"REQ-{uuid.uuid4().hex[:8]}"
    request.state.correlation_id = corr_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response

# --- Health Check (NFR-07) ---
@app.get("/health")
def health_check():
    """NFR-07: Health endpoint returns 200 within 1 second of startup."""
    return {
        "status": "UP",
        "service": "telcolane-substrate",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }

# --- REST Endpoints ---
@app.post("/api/v1/subscribers/register")
def register_subscriber(payload: Dict[str, Any], request: Request):
    corr_id = getattr(request.state, "correlation_id", None)
    return controller.handle_register(payload, caller_role=Role.SUBSCRIBER, correlation_id=corr_id)

@app.post("/api/v1/subscribers/activate")
def activate_subscriber(payload: Dict[str, Any], request: Request, x_caller_role: str = Header("DEALER")):
    corr_id = getattr(request.state, "correlation_id", None)
    role = Role(x_caller_role.upper()) if x_caller_role.upper() in Role._value2member_map_ else Role.DEALER
    return controller.handle_activate(payload, caller_role=role, correlation_id=corr_id)

@app.get("/api/v1/subscribers/{subscriber_id}")
def get_subscriber(
    subscriber_id: str,
    request: Request,
    x_caller_role: str = Header("ADMIN"),
    x_caller_id: str = Header("ADMIN_USER")
):
    corr_id = getattr(request.state, "correlation_id", None)
    role = Role(x_caller_role.upper()) if x_caller_role.upper() in Role._value2member_map_ else Role.ADMIN
    return controller.handle_get_subscriber(subscriber_id, caller_role=role, caller_id=x_caller_id, correlation_id=corr_id)

@app.get("/api/v1/plans")
def list_plans(request: Request):
    corr_id = getattr(request.state, "correlation_id", None)
    return controller.handle_list_plans(correlation_id=corr_id)

@app.post("/api/v1/subscribers/change-plan")
def change_plan(
    payload: Dict[str, Any],
    request: Request,
    x_caller_role: str = Header("SUBSCRIBER"),
    x_caller_id: Optional[str] = Header(None)
):
    corr_id = getattr(request.state, "correlation_id", None)
    role = Role(x_caller_role.upper()) if x_caller_role.upper() in Role._value2member_map_ else Role.SUBSCRIBER
    caller_id = x_caller_id or payload.get("subscriber_id", "")
    return controller.handle_change_plan(payload, caller_role=role, caller_id=caller_id, correlation_id=corr_id)

@app.post("/api/v1/subscribers/suspend")
def suspend_subscriber(
    payload: Dict[str, Any],
    request: Request,
    x_caller_role: str = Header("SUBSCRIBER"),
    x_caller_id: Optional[str] = Header(None)
):
    corr_id = getattr(request.state, "correlation_id", None)
    role = Role(x_caller_role.upper()) if x_caller_role.upper() in Role._value2member_map_ else Role.SUBSCRIBER
    caller_id = x_caller_id or payload.get("subscriber_id", "")
    return controller.handle_suspend(payload, caller_role=role, caller_id=caller_id, correlation_id=corr_id)

@app.post("/api/v1/subscribers/reactivate")
def reactivate_subscriber(
    payload: Dict[str, Any],
    request: Request,
    x_caller_role: str = Header("SUBSCRIBER"),
    x_caller_id: Optional[str] = Header(None)
):
    corr_id = getattr(request.state, "correlation_id", None)
    role = Role(x_caller_role.upper()) if x_caller_role.upper() in Role._value2member_map_ else Role.SUBSCRIBER
    caller_id = x_caller_id or payload.get("subscriber_id", "")
    return controller.handle_reactivate(payload, caller_role=role, caller_id=caller_id, correlation_id=corr_id)

@app.post("/api/v1/subscribers/port-out")
def initiate_port_out(
    payload: Dict[str, Any],
    request: Request,
    x_caller_role: str = Header("SUBSCRIBER"),
    x_caller_id: Optional[str] = Header(None)
):
    corr_id = getattr(request.state, "correlation_id", None)
    role = Role(x_caller_role.upper()) if x_caller_role.upper() in Role._value2member_map_ else Role.SUBSCRIBER
    caller_id = x_caller_id or payload.get("subscriber_id", "")
    return controller.handle_initiate_port_out(payload, caller_role=role, caller_id=caller_id, correlation_id=corr_id)

@app.post("/api/v1/subscribers/port-out/cancel")
def cancel_port_out(
    payload: Dict[str, Any],
    request: Request,
    x_caller_role: str = Header("SUBSCRIBER"),
    x_caller_id: Optional[str] = Header(None)
):
    corr_id = getattr(request.state, "correlation_id", None)
    role = Role(x_caller_role.upper()) if x_caller_role.upper() in Role._value2member_map_ else Role.SUBSCRIBER
    caller_id = x_caller_id or payload.get("subscriber_id", "")
    return controller.handle_cancel_port_out(payload, caller_role=role, caller_id=caller_id, correlation_id=corr_id)

@app.post("/api/v1/csr/override")
def csr_override(
    payload: Dict[str, Any],
    request: Request,
    x_caller_role: str = Header("CSR"),
    x_caller_id: str = Header("CSR_AGENT_DEFAULT")
):
    corr_id = getattr(request.state, "correlation_id", None)
    role = Role(x_caller_role.upper()) if x_caller_role.upper() in Role._value2member_map_ else Role.CSR
    return controller.handle_csr_override(payload, caller_role=role, caller_id=x_caller_id, correlation_id=corr_id)

@app.get("/api/v1/reports/summary")
def get_reports(request: Request, x_caller_role: str = Header("ADMIN")):
    corr_id = getattr(request.state, "correlation_id", None)
    role = Role(x_caller_role.upper()) if x_caller_role.upper() in Role._value2member_map_ else Role.ADMIN
    return controller.handle_reports(caller_role=role, correlation_id=corr_id)

@app.get("/", response_class=HTMLResponse)
def index_page():
    return """<!DOCTYPE html>
<html>
<head>
    <title>TelcoLane Subscriber Operations Substrate</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 2rem; background: #f8fafc; color: #1e293b; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
        h1 { color: #0284c7; margin-bottom: 0.5rem; }
        .badge { display: inline-block; padding: 0.25rem 0.5rem; background: #e0f2fe; color: #0369a1; border-radius: 4px; font-size: 0.875rem; font-weight: 600; margin-bottom: 1.5rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin-top: 1.5rem; }
        .card { padding: 1.25rem; border: 1px solid #e2e8f0; border-radius: 6px; background: #f8fafc; }
        .card h3 { margin-top: 0; color: #0f172a; font-size: 1.1rem; }
        code { background: #e2e8f0; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.9rem; }
        a { color: #0284c7; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>TelcoLane Operations Substrate</h1>
        <div class="badge">BC-AINE-020 · Spec-Is-Truth · Financial Precision</div>
        <p>Unified Telecom Subscriber & Plan Lifecycle Operations Platform.</p>
        <div class="grid">
            <div class="card">
                <h3>System Health</h3>
                <p>Status: <strong style="color: green;">ONLINE</strong></p>
                <p><a href="/health">View /health JSON</a></p>
            </div>
            <div class="card">
                <h3>API Documentation</h3>
                <p>Interactive OpenAPI documentation:</p>
                <p><a href="/docs">View Swagger /docs</a></p>
            </div>
            <div class="card">
                <h3>Operational Reports</h3>
                <p>View Funnel, Churn, Plan-Mix, ARPU:</p>
                <p><a href="/api/v1/reports/summary">View Reports API</a></p>
            </div>
        </div>
    </div>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
