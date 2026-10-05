import os
import time
import uuid
import json
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, Header, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from src.domain.models import Role, DomainException
from src.services.subscription_service import SubscriptionService
from src.services.reporting_service import ReportingService
from src.controllers.api_controller import APIController
from src.controllers.schemas import (
    RegisterSubscriberRequest, ActivateSubscriberRequest,
    PlanChangeRequest, ProRataPreviewRequest,
    SuspendSubscriberRequest, ReactivateSubscriberRequest,
    PortOutInitiateRequest, PortOutCancelRequest, PortOutFinalizeRequest,
    TerminateSubscriberRequest, CSROverrideRequest,
    CreatePlanRequest, AuthTokenRequest
)
from src.infrastructure.auth import Principal, verify_token, mint_principal_token
from src.infrastructure.database import create_sqlite_subscription_service
from src.seed import seed_database

# --- Structured JSON Logger (NFR-06) ---
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        for attr in ("correlation_id", "subscriber_id", "action"):
            if hasattr(record, attr):
                log_obj[attr] = getattr(record, attr)
        return json.dumps(log_obj)

api_logger = logging.getLogger("telcolane.api")
api_logger.setLevel(logging.INFO)
if not api_logger.handlers:
    sh = logging.StreamHandler()
    sh.setFormatter(JSONFormatter())
    api_logger.addHandler(sh)

# Initialize core services and SQLite persistence
db_path = os.environ.get("TELCOLANE_DB_PATH", "telcolane.db")
service = create_sqlite_subscription_service(db_path)
seed_database(service)
reporting_service = ReportingService(service.subscriber_repo, service.plan_repo, service.audit_repo, service.billing_repo)
controller = APIController(service, reporting_service)

app = FastAPI(
    title="TelcoLane Subscriber Operations Substrate",
    version="1.0.0",
    description="Telecom Subscriber Lifecycle & Plan Management Platform (BC-AINE-020)"
)

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"]
)

CORRELATION_ID_REGEX = re.compile(r"^[A-Za-z0-9-]{8,64}$")

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    raw_corr_id = request.headers.get("X-Correlation-ID")
    if raw_corr_id and CORRELATION_ID_REGEX.match(raw_corr_id):
        corr_id = raw_corr_id
    else:
        corr_id = f"REQ-{uuid.uuid4().hex}"
    request.state.correlation_id = corr_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = corr_id
    return response

# --- Authentication & Principal Resolution (NFR-04) ---

def resolve_principal(
    request: Request,
    default_role: Optional[Role] = None
) -> Principal:
    """
    Derives caller identity strictly through cryptographically signed Bearer JWTs.
    Zero unauthenticated header fallbacks in production paths.
    """
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif request.headers.get("X-Auth-Token"):
        token = request.headers.get("X-Auth-Token").strip()

    if token:
        return verify_token(token)

    # Allow public fallback only when explicitly declared for public endpoints
    if default_role is not None:
        return Principal(principal_id="PUBLIC_CALLER", role=default_role)

    # Deny-by-default on missing or invalid credentials (NFR-04)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "ERR_UNAUTHENTICATED", "message": "Authentication required. Valid Bearer JWT token required."}
    )

# --- Authentication Token Issuance Endpoint (NFR-04) ---
@app.post("/api/v1/auth/token")
def authenticate_and_issue_token(req: AuthTokenRequest):
    """Issues RFC-7519 signed JWT access tokens with role claims."""
    token = mint_principal_token(
        role=req.role,
        principal_id=req.principal_id,
        bound_subscriber_id=req.bound_subscriber_id,
        bound_dealer_code=req.bound_dealer_code
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": req.role.value,
        "principal_id": req.principal_id,
        "expires_in": 86400
    }

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

# --- REST Endpoints (AC-01 through AC-10) ---

@app.post("/api/v1/subscribers/register")
def register_subscriber(req: RegisterSubscriberRequest, request: Request):
    corr_id = getattr(request.state, "correlation_id", None)
    return controller.handle_register(req.model_dump(), caller_role=Role.SUBSCRIBER, correlation_id=corr_id)

@app.post("/api/v1/subscribers/activate")
def activate_subscriber(
    req: ActivateSubscriberRequest,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    return controller.handle_activate(
        req.model_dump(),
        caller_role=principal.role,
        caller_id=principal.principal_id,
        correlation_id=corr_id
    )

@app.get("/api/v1/subscribers/{subscriber_id}")
def get_subscriber(
    subscriber_id: str,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    return controller.handle_get_subscriber(
        subscriber_id,
        caller_role=principal.role,
        caller_id=principal.principal_id,
        correlation_id=corr_id
    )

@app.get("/api/v1/plans")
def list_plans(request: Request):
    corr_id = getattr(request.state, "correlation_id", None)
    return controller.handle_list_plans(correlation_id=corr_id)

@app.post("/api/v1/plans")
def create_plan(
    req: CreatePlanRequest,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    if principal.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ERR_FORBIDDEN", "message": "Only ADMIN role can create plans"}
        )
    plan = service.create_plan(
        plan_id=req.plan_id,
        name=req.name,
        plan_type=req.plan_type,
        monthly_rent=req.monthly_rent,
        validity_days=req.validity_days,
        data_gb=req.data_gb,
        voice_minutes=req.voice_minutes,
        sms_count=req.sms_count,
        min_tenure_days=req.min_tenure_days,
        is_published=req.is_published
    )
    return {
        "status": "SUCCESS",
        "correlation_id": corr_id,
        "data": {
            "plan_id": plan.plan_id,
            "version": plan.version,
            "name": plan.name,
            "is_published": plan.is_published
        }
    }

@app.post("/api/v1/subscribers/pro-rata-preview")
def preview_pro_rata(
    req: ProRataPreviewRequest,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    caller_id = principal.bound_subscriber_id or principal.principal_id
    return controller.handle_pro_rata_preview(
        req.model_dump(),
        caller_role=principal.role,
        caller_id=caller_id,
        correlation_id=corr_id
    )

@app.post("/api/v1/subscribers/change-plan")
def change_plan(
    req: PlanChangeRequest,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    caller_id = principal.bound_subscriber_id or principal.principal_id
    return controller.handle_change_plan(req.model_dump(), caller_role=principal.role, caller_id=caller_id, correlation_id=corr_id)

@app.post("/api/v1/subscribers/suspend")
def suspend_subscriber(
    req: SuspendSubscriberRequest,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    caller_id = principal.bound_subscriber_id or principal.principal_id
    return controller.handle_suspend(req.model_dump(), caller_role=principal.role, caller_id=caller_id, correlation_id=corr_id)

@app.post("/api/v1/subscribers/reactivate")
def reactivate_subscriber(
    req: ReactivateSubscriberRequest,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    caller_id = principal.bound_subscriber_id or principal.principal_id
    return controller.handle_reactivate(req.model_dump(), caller_role=principal.role, caller_id=caller_id, correlation_id=corr_id)

@app.post("/api/v1/subscribers/port-out")
def initiate_port_out(
    req: PortOutInitiateRequest,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    caller_id = principal.bound_subscriber_id or principal.principal_id
    return controller.handle_initiate_port_out(req.model_dump(), caller_role=principal.role, caller_id=caller_id, correlation_id=corr_id)

@app.post("/api/v1/subscribers/port-out/cancel")
def cancel_port_out(
    req: PortOutCancelRequest,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    caller_id = principal.bound_subscriber_id or principal.principal_id
    return controller.handle_cancel_port_out(req.model_dump(), caller_role=principal.role, caller_id=caller_id, correlation_id=corr_id)

@app.post("/api/v1/subscribers/port-out/finalize")
def finalize_port_out(
    req: PortOutFinalizeRequest,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    return controller.handle_finalize_port_out(req.model_dump(), caller_role=principal.role, caller_id=principal.principal_id, correlation_id=corr_id)

@app.post("/api/v1/subscribers/terminate")
def terminate_subscriber(
    req: TerminateSubscriberRequest,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    return controller.handle_terminate(req.model_dump(), caller_role=principal.role, caller_id=principal.principal_id, correlation_id=corr_id)

@app.post("/api/v1/csr/override")
def csr_override(
    req: CSROverrideRequest,
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    return controller.handle_csr_override(req.model_dump(), caller_role=principal.role, caller_id=principal.principal_id, correlation_id=corr_id)

@app.get("/api/v1/reports/summary")
def get_reports(
    request: Request
):
    corr_id = getattr(request.state, "correlation_id", None)
    principal = resolve_principal(request)
    return controller.handle_reports(caller_role=principal.role, correlation_id=corr_id)

# --- Static Frontend Serving / API Summary ---
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

@app.get("/", response_class=HTMLResponse)
def index():
    index_file = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    return HTMLResponse(content="""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TelcoLane Operations Substrate</title>
</head>
<body>
    <div id="root">
        <h1>TelcoLane Operations Substrate</h1>
        <span>System Health</span>
        <span>Operational Reports</span>
    </div>
</body>
</html>""", status_code=200)
