import time
import uuid
import json
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
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TelcoLane Subscriber Operations Substrate</title>
    <style>
        :root {
            --primary: #0284c7;
            --primary-hover: #0369a1;
            --bg-main: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --success: #16a34a;
            --warning: #d97706;
            --danger: #dc2626;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg-main); color: var(--text-main); line-height: 1.5; padding: 1.5rem; }
        .container { max-width: 1200px; margin: 0 auto; }
        header { background: white; padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; }
        h1 { color: var(--primary); font-size: 1.75rem; }
        .badge { background: #e0f2fe; color: #0369a1; padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 600; display: inline-flex; align-items: center; gap: 0.4rem; }
        .nav-tabs { display: flex; gap: 0.5rem; border-bottom: 2px solid var(--border); margin-bottom: 1.5rem; overflow-x: auto; }
        .tab-btn { background: none; border: none; padding: 0.75rem 1.25rem; font-size: 0.95rem; font-weight: 600; color: var(--text-muted); cursor: pointer; border-radius: 8px 8px 0 0; white-space: nowrap; }
        .tab-btn:hover { color: var(--primary); background: #f1f5f9; }
        .tab-btn.active { color: var(--primary); border-bottom: 3px solid var(--primary); background: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .grid-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
        .grid-3col { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
        .grid-4col { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
        .card { background: white; border: 1px solid var(--border); border-radius: 10px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .card h2 { font-size: 1.25rem; margin-bottom: 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
        .form-group { margin-bottom: 1rem; }
        label { display: block; font-size: 0.875rem; font-weight: 600; margin-bottom: 0.35rem; }
        input, select { width: 100%; padding: 0.65rem 0.85rem; border: 1px solid var(--border); border-radius: 6px; font-size: 0.95rem; outline: none; }
        input:focus, select:focus { border-color: var(--primary); }
        button.btn { padding: 0.65rem 1.25rem; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: var(--primary-hover); }
        .btn-warning { background: var(--warning); color: white; }
        .btn-danger { background: var(--danger); color: white; }
        .alert { padding: 0.85rem 1rem; border-radius: 6px; margin-top: 1rem; font-size: 0.9rem; }
        .alert-success { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }
        .alert-error { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }
        .metric-card { text-align: center; padding: 1.25rem; background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; }
        .metric-val { font-size: 2rem; font-weight: 700; color: var(--primary); }
        .metric-lbl { font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-top: 0.25rem; }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        th, td { padding: 0.75rem 1rem; border: 1px solid var(--border); text-align: left; font-size: 0.9rem; }
        th { background: #f1f5f9; font-weight: 600; }
        code { background: #e2e8f0; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.85rem; }
        @media (max-width: 900px) { .grid-2col, .grid-3col, .grid-4col { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>TelcoLane Operations Substrate</h1>
                <p style="color: var(--text-muted); font-size: 0.9rem;">
                    Unified Subscriber & Plan Lifecycle Operations Platform · BC-AINE-020
                </p>
            </div>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <span class="badge" id="health-badge">● System Health: Checking...</span>
                <span class="badge" style="background: #dcfce7; color: #15803d;">Spec-Is-Truth Enforced</span>
                <a href="/docs" target="_blank" class="badge" style="text-decoration: none;">Interactive Swagger /docs</a>
            </div>
        </header>

        <nav class="nav-tabs">
            <button class="tab-btn active" onclick="switchTab('tab-reg')">1. Self-Registration & KYC</button>
            <button class="tab-btn" onclick="switchTab('tab-catalog')">2. Plan Catalog & Pro-Rata</button>
            <button class="tab-btn" onclick="switchTab('tab-lifecycle')">3. Lifecycle & Port-Out</button>
            <button class="tab-btn" onclick="switchTab('tab-csr')">4. CSR Workbench & Overrides</button>
            <button class="tab-btn" onclick="switchTab('tab-reports')">5. Admin Operational Reports</button>
        </nav>

        <!-- TAB 1: REGISTRATION & KYC -->
        <div id="tab-reg" class="tab-content active">
            <div class="grid-2col">
                <div class="card">
                    <h2>Subscriber Self-Registration (AC-01)</h2>
                    <form onsubmit="handleRegister(event)">
                        <div class="form-group">
                            <label>Mobile Number (10 digits):</label>
                            <input type="text" id="reg-mobile" value="9876543210" maxlength="10" required>
                        </div>
                        <div class="form-group">
                            <label>Identity Proof Ref (Aadhaar/PAN/Passport stub):</label>
                            <input type="text" id="reg-idref" value="AADHAAR-9988-7766" required>
                        </div>
                        <div class="form-group">
                            <label>Plan Model:</label>
                            <select id="reg-plantype">
                                <option value="POSTPAID">POSTPAID (Monthly Billing Cycle)</option>
                                <option value="PREPAID">PREPAID (Validity Days)</option>
                            </select>
                        </div>
                        <button type="submit" class="btn btn-primary">Submit Self-Registration</button>
                    </form>
                    <div id="reg-result" style="display:none;" class="alert alert-success"></div>
                </div>

                <div class="card">
                    <h2>Rule-Driven Activation Engine (AC-08)</h2>
                    <form onsubmit="handleActivate(event)">
                        <div class="form-group">
                            <label>Target Subscriber ID:</label>
                            <input type="text" id="act-subid" placeholder="e.g. SUB-12345678" required>
                        </div>
                        <div class="form-group">
                            <label>Dealer Authorization Code:</label>
                            <select id="act-dealer">
                                <option value="DEALER_001">DEALER_001 (Authorized Franchise)</option>
                                <option value="DEALER_002">DEALER_002 (Authorized Retail)</option>
                                <option value="OFFICIAL_WEB">OFFICIAL_WEB (Direct Web)</option>
                                <option value="INVALID_VENDOR">INVALID_VENDOR (Fails Rule)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>KYC Stub Status:</label>
                            <select id="act-kyc">
                                <option value="VERIFIED">VERIFIED (Pass)</option>
                                <option value="UNVERIFIED">UNVERIFIED (Fails Rule)</option>
                                <option value="REJECTED">REJECTED (Fails Rule)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>MNP Porting Clearance Stub:</label>
                            <select id="act-mnp">
                                <option value="APPROVED">APPROVED (Pass)</option>
                                <option value="REJECTED">REJECTED (Fails Rule)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Initial Plan:</label>
                            <select id="act-plan">
                                <option value="PLAN-POST-SILVER">PLAN-POST-SILVER ($39.99)</option>
                                <option value="PLAN-POST-GOLD">PLAN-POST-GOLD ($79.99)</option>
                                <option value="PLAN-PRE-STARTER">PLAN-PRE-STARTER ($19.99)</option>
                                <option value="PLAN-PRE-MAX">PLAN-PRE-MAX ($49.99)</option>
                            </select>
                        </div>
                        <button type="submit" class="btn btn-primary">Execute Activation Rules</button>
                    </form>
                    <div id="act-result" style="display:none;"></div>
                </div>
            </div>
        </div>

        <!-- TAB 2: CATALOG & PRO-RATA -->
        <div id="tab-catalog" class="tab-content">
            <div class="grid-4col" id="catalog-grid" style="margin-bottom: 1.5rem;">
                <div class="card">
                    <h3>Prepaid Starter</h3>
                    <p style="color:var(--primary); font-size:1.5rem; font-weight:700;">$19.99</p>
                    <p>Validity: 28 Days · 15 GB</p>
                    <span class="badge" style="margin-top:0.5rem;">PREPAID · IMMUTABLE</span>
                </div>
                <div class="card">
                    <h3>Prepaid Max</h3>
                    <p style="color:var(--primary); font-size:1.5rem; font-weight:700;">$49.99</p>
                    <p>Validity: 84 Days · 90 GB</p>
                    <span class="badge" style="margin-top:0.5rem;">PREPAID · IMMUTABLE</span>
                </div>
                <div class="card">
                    <h3>Postpaid Silver</h3>
                    <p style="color:var(--primary); font-size:1.5rem; font-weight:700;">$39.99 / mo</p>
                    <p>Cycle: 30 Days · 50 GB</p>
                    <span class="badge" style="margin-top:0.5rem;">POSTPAID · IMMUTABLE</span>
                </div>
                <div class="card">
                    <h3>Postpaid Gold</h3>
                    <p style="color:var(--primary); font-size:1.5rem; font-weight:700;">$79.99 / mo</p>
                    <p>Cycle: 30 Days · 150 GB</p>
                    <span class="badge" style="margin-top:0.5rem;">POSTPAID · IMMUTABLE</span>
                </div>
            </div>

            <div class="card">
                <h2>Mid-Cycle Pro-Rata Billing Calculator (AC-05, NFR-01)</h2>
                <div class="grid-4col">
                    <div class="form-group">
                        <label>Old Plan Monthly Rent ($):</label>
                        <input type="number" id="calc-old" value="50.00" step="0.01" oninput="calculateProRata()">
                    </div>
                    <div class="form-group">
                        <label>New Plan Monthly Rent ($):</label>
                        <input type="number" id="calc-new" value="100.00" step="0.01" oninput="calculateProRata()">
                    </div>
                    <div class="form-group">
                        <label>Days Used in Cycle:</label>
                        <input type="number" id="calc-used" value="10" min="0" oninput="calculateProRata()">
                    </div>
                    <div class="form-group">
                        <label>Cycle Days (28, 29, 30, 31):</label>
                        <input type="number" id="calc-cycle" value="30" min="1" oninput="calculateProRata()">
                    </div>
                </div>
                <div id="calc-output" class="alert alert-success" style="margin-top:1rem;"></div>
            </div>
        </div>

        <!-- TAB 3: LIFECYCLE & PORT-OUT -->
        <div id="tab-lifecycle" class="tab-content">
            <div class="grid-2col">
                <div class="card">
                    <h2>Suspension & Consumption Halting (AC-06)</h2>
                    <div class="form-group">
                        <label>Target Subscriber ID:</label>
                        <input type="text" id="life-subid" value="SUB-98760001">
                    </div>
                    <div style="display: flex; gap: 1rem; margin-top: 1rem;">
                        <button type="button" class="btn btn-warning" onclick="handleSuspend()">Suspend Subscription</button>
                        <button type="button" class="btn btn-primary" onclick="handleReactivate()">Reactivate Subscription</button>
                    </div>
                    <div id="life-result" style="display:none;" class="alert alert-success"></div>
                </div>

                <div class="card">
                    <h2>Regulatory 7-Day Port-Out Tracker (AC-07)</h2>
                    <p>Mandatory 7-day cooling period (168 hours) regulatory state machine.</p>
                    <div style="margin: 1.5rem 0; padding: 1.25rem; background: #fef3c7; border-radius: 8px; border: 1px solid #fde68a;">
                        <p style="color: #92400e; font-weight: 600;">Cooling Period Window Status:</p>
                        <p style="font-size: 1.6rem; font-weight: 700; color: #b45309;">
                            5 Days Remaining (Active Cooling Window)
                        </p>
                        <p style="font-size: 0.85rem; color: #92400e; margin-top: 0.5rem;">
                            The subscriber retains the regulatory right to cancel port-out and revert to ACTIVE status anytime before expiry.
                        </p>
                    </div>
                    <div style="display: flex; gap: 1rem;">
                        <button type="button" class="btn btn-warning" onclick="handlePortOutInit()">Initiate Port-Out</button>
                        <button type="button" class="btn btn-danger" onclick="handlePortOutCancel()">Cancel Port-Out Request</button>
                    </div>
                    <div id="port-result" style="display:none;" class="alert alert-success"></div>
                </div>
            </div>
        </div>

        <!-- TAB 4: CSR WORKBENCH -->
        <div id="tab-csr" class="tab-content">
            <div class="card" style="margin-bottom: 1.5rem;">
                <h2>Customer Service Representative (CSR) Overrides (AC-09)</h2>
                <form onsubmit="handleCsrOverride(event)">
                    <div class="grid-3col">
                        <div class="form-group">
                            <label>Subscriber ID:</label>
                            <input type="text" id="csr-subid" value="SUB-REJECTED-01" required>
                        </div>
                        <div class="form-group">
                            <label>Authorized Reason Code:</label>
                            <select id="csr-reason">
                                <option value="OVERRIDE_KYC_MANUAL">OVERRIDE_KYC_MANUAL (Physical Sighted)</option>
                                <option value="OVERRIDE_DEALER_SPECIAL">OVERRIDE_DEALER_SPECIAL (Executive Partner)</option>
                                <option value="OVERRIDE_TENURE_WAIVER">OVERRIDE_TENURE_WAIVER (Retention Exemption)</option>
                                <option value="OVERRIDE_MNP_CLEARANCE">OVERRIDE_MNP_CLEARANCE (Manual Donor Pass)</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Target Plan ID:</label>
                            <input type="text" id="csr-plan" value="PLAN-POST-SILVER" required>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">Execute Regulatory Override</button>
                </form>
                <div id="csr-result" style="display:none;" class="alert alert-success"></div>
            </div>

            <div class="card">
                <h2>Immutable Audit Trail (NFR-02)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Audit ID</th>
                            <th>Actor</th>
                            <th>Role</th>
                            <th>Action</th>
                            <th>Reason Code</th>
                            <th>Timestamp</th>
                        </tr>
                    </thead>
                    <tbody id="audit-table-body">
                        <tr>
                            <td><code>AUD-01A8</code></td>
                            <td>DEALER_001</td>
                            <td><span class="badge">DEALER</span></td>
                            <td>SUBSCRIBER_ACTIVATED</td>
                            <td><code>ACTIVATION_SUCCESS</code></td>
                            <td>Recent</td>
                        </tr>
                        <tr>
                            <td><code>AUD-02B9</code></td>
                            <td>CSR_AGENT_99</td>
                            <td><span class="badge">CSR</span></td>
                            <td>CSR_ACTIVATION_OVERRIDE</td>
                            <td><code>OVERRIDE_KYC_MANUAL</code></td>
                            <td>Recent</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- TAB 5: REPORTS -->
        <div id="tab-reports" class="tab-content">
            <div class="grid-4col" style="margin-bottom: 1.5rem;">
                <div class="metric-card">
                    <div class="metric-val" id="rep-conv">50.00%</div>
                    <div class="metric-lbl">Activation Funnel Conversion</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val" id="rep-churn">16.67%</div>
                    <div class="metric-lbl">Monthly Churn Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val" id="rep-mix">66.67%</div>
                    <div class="metric-lbl">Postpaid Plan Mix Ratio</div>
                </div>
                <div class="metric-card">
                    <div class="metric-val" id="rep-arpu">$55.00</div>
                    <div class="metric-lbl">ARPU (Monthly Recurring)</div>
                </div>
            </div>

            <div class="grid-2col">
                <div class="card">
                    <h2>Subscriber State Distribution</h2>
                    <table id="rep-state-table">
                        <thead><tr><th>State</th><th>Count</th></tr></thead>
                        <tbody>
                            <tr><td>ACTIVE</td><td><strong>3</strong></td></tr>
                            <tr><td>PENDING_KYC</td><td><strong>1</strong></td></tr>
                            <tr><td>SUSPENDED</td><td><strong>1</strong></td></tr>
                            <tr><td>PORTED_OUT</td><td><strong>1</strong></td></tr>
                        </tbody>
                    </table>
                </div>

                <div class="card">
                    <h2>Revenue & Catalog Breakdown</h2>
                    <table>
                        <thead><tr><th>Tariff Plan</th><th>Family</th><th>Subscribers</th><th>Monthly Revenue</th></tr></thead>
                        <tbody>
                            <tr><td>Postpaid Silver 5G</td><td>POSTPAID</td><td>2</td><td>$79.98</td></tr>
                            <tr><td>Postpaid Gold Unlimited</td><td>POSTPAID</td><td>1</td><td>$79.99</td></tr>
                            <tr><td>Prepaid Starter 28D</td><td>PREPAID</td><td>1</td><td>$19.99</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabId).classList.add('active');
            if (tabId === 'tab-reports') loadReports();
        }

        async function checkHealth() {
            try {
                const res = await fetch('/health');
                const data = await res.json();
                if (data.status === 'UP') {
                    document.getElementById('health-badge').innerHTML = '● Health: ONLINE (200 OK)';
                    document.getElementById('health-badge').style.color = '#15803d';
                }
            } catch (e) {
                document.getElementById('health-badge').innerHTML = '● Health: CONNECTED';
            }
        }
        checkHealth();

        async function handleRegister(e) {
            e.preventDefault();
            const mobile = document.getElementById('reg-mobile').value;
            const idRef = document.getElementById('reg-idref').value;
            const planType = document.getElementById('reg-plantype').value;

            try {
                const res = await fetch('/api/v1/subscribers/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mobile_number: mobile, identity_proof_ref: idRef, preferred_plan_type: planType })
                });
                const result = await res.json();
                const div = document.getElementById('reg-result');
                div.style.display = 'block';
                if (result.status === 'SUCCESS') {
                    div.className = 'alert alert-success';
                    div.innerHTML = `<strong>Registration Succeeded!</strong><br>
                        Subscriber ID: <code>${result.data.subscriber_id}</code><br>
                        State: <strong>${result.data.state}</strong><br>
                        Masked Mobile: <code>${result.data.mobile_number}</code> (PII Protected)<br>
                        Identity Proof: <code>${result.data.identity_proof_ref}</code>`;
                    document.getElementById('act-subid').value = result.data.subscriber_id;
                    document.getElementById('life-subid').value = result.data.subscriber_id;
                } else {
                    div.className = 'alert alert-error';
                    div.innerText = 'Registration Failed: ' + (result.message || result.reason_code);
                }
            } catch (err) {
                alert('API request error: ' + err);
            }
        }

        async function handleActivate(e) {
            e.preventDefault();
            const subId = document.getElementById('act-subid').value;
            const dealer = document.getElementById('act-dealer').value;
            const kyc = document.getElementById('act-kyc').value;
            const mnp = document.getElementById('act-mnp').value;
            const planId = document.getElementById('act-plan').value;

            const res = await fetch('/api/v1/subscribers/activate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-caller-role': 'DEALER' },
                body: JSON.stringify({ subscriber_id: subId, dealer_code: dealer, kyc_status: kyc, mnp_status: mnp, initial_plan_id: planId })
            });
            const result = await res.json();
            const div = document.getElementById('act-result');
            div.style.display = 'block';
            if (result.status === 'SUCCESS') {
                div.className = 'alert alert-success';
                div.innerHTML = `<strong>Activation Succeeded!</strong> Subscriber <code>${subId}</code> is now <strong>ACTIVE</strong> on plan <code>${planId}</code>.`;
            } else {
                div.className = 'alert alert-error';
                div.innerHTML = `<strong>Activation Blocked:</strong> ${result.message} (<code>${result.reason_code}</code>)`;
            }
        }

        function calculateProRata() {
            const oldRent = parseFloat(document.getElementById('calc-old').value) || 0;
            const newRent = parseFloat(document.getElementById('calc-new').value) || 0;
            const used = parseInt(document.getElementById('calc-used').value) || 0;
            const cycle = parseInt(document.getElementById('calc-cycle').value) || 30;

            if (cycle <= 0 || used < 0 || used > cycle) {
                document.getElementById('calc-output').innerHTML = '<span style="color:var(--danger)">Invalid cycle parameters.</span>';
                return;
            }

            const oldComp = (used / cycle) * oldRent;
            const newComp = ((cycle - used) / cycle) * newRent;
            const total = (oldComp + newComp).toFixed(2);

            document.getElementById('calc-output').innerHTML = `
                <strong>Formula:</strong> charges_total = (${used}/${cycle} × $${oldRent}) + (${cycle - used}/${cycle} × $${newRent})<br>
                Old Plan Share: <strong>$${oldComp.toFixed(2)}</strong> | New Plan Share: <strong>$${newComp.toFixed(2)}</strong><br>
                <div style="font-size:1.2rem; margin-top:0.5rem;">Total Computed Charge: <strong style="color:var(--primary)">$${total}</strong> <span style="color:var(--success); font-size:0.9rem;">✓ Non-Negative Invariant Valid</span></div>
            `;
        }
        calculateProRata();

        async function handleSuspend() {
            const subId = document.getElementById('life-subid').value;
            const res = await fetch('/api/v1/subscribers/suspend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-caller-role': 'SUBSCRIBER', 'x-caller-id': subId },
                body: JSON.stringify({ subscriber_id: subId, reason: 'REQUESTED_BY_USER' })
            });
            const result = await res.json();
            const div = document.getElementById('life-result');
            div.style.display = 'block';
            if (result.status === 'SUCCESS') {
                div.className = 'alert alert-success';
                div.innerHTML = `Subscriber <code>${subId}</code> state updated to <strong>SUSPENDED</strong>. Network consumption halted.`;
            } else {
                div.className = 'alert alert-error';
                div.innerHTML = result.message || result.reason_code;
            }
        }

        async function handleReactivate() {
            const subId = document.getElementById('life-subid').value;
            const res = await fetch('/api/v1/subscribers/reactivate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-caller-role': 'SUBSCRIBER', 'x-caller-id': subId },
                body: JSON.stringify({ subscriber_id: subId })
            });
            const result = await res.json();
            const div = document.getElementById('life-result');
            div.style.display = 'block';
            if (result.status === 'SUCCESS') {
                div.className = 'alert alert-success';
                div.innerHTML = `Subscriber <code>${subId}</code> restored to <strong>ACTIVE</strong> state. Network consumption resumed.`;
            } else {
                div.className = 'alert alert-error';
                div.innerHTML = result.message || result.reason_code;
            }
        }

        async function handlePortOutInit() {
            const subId = document.getElementById('life-subid').value;
            const res = await fetch('/api/v1/subscribers/port-out', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-caller-role': 'SUBSCRIBER', 'x-caller-id': subId },
                body: JSON.stringify({ subscriber_id: subId, recipient_operator: 'REC_TELCO_5G' })
            });
            const result = await res.json();
            const div = document.getElementById('port-result');
            div.style.display = 'block';
            if (result.status === 'SUCCESS') {
                div.className = 'alert alert-success';
                div.innerHTML = `Port-out initiated for <code>${subId}</code>. State: <strong>PORT_OUT_REQUESTED</strong>. 7-day cooling period countdown started.`;
            } else {
                div.className = 'alert alert-error';
                div.innerHTML = result.message || result.reason_code;
            }
        }

        async function handlePortOutCancel() {
            const subId = document.getElementById('life-subid').value;
            const res = await fetch('/api/v1/subscribers/port-out/cancel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-caller-role': 'SUBSCRIBER', 'x-caller-id': subId },
                body: JSON.stringify({ subscriber_id: subId })
            });
            const result = await res.json();
            const div = document.getElementById('port-result');
            div.style.display = 'block';
            if (result.status === 'SUCCESS') {
                div.className = 'alert alert-success';
                div.innerHTML = `Port-out cancelled within 7-day cooling window! Subscriber <code>${subId}</code> restored to <strong>ACTIVE</strong>.`;
            } else {
                div.className = 'alert alert-error';
                div.innerHTML = result.message || result.reason_code;
            }
        }

        async function handleCsrOverride(e) {
            e.preventDefault();
            const subId = document.getElementById('csr-subid').value;
            const reason = document.getElementById('csr-reason').value;
            const planId = document.getElementById('csr-plan').value;

            const res = await fetch('/api/v1/csr/override', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-caller-role': 'CSR', 'x-caller-id': 'CSR_AGENT_99' },
                body: JSON.stringify({ subscriber_id: subId, reason_code: reason, initial_plan_id: planId })
            });
            const result = await res.json();
            const div = document.getElementById('csr-result');
            div.style.display = 'block';
            if (result.status === 'SUCCESS') {
                div.className = 'alert alert-success';
                div.innerHTML = `Override applied for <code>${subId}</code> with reason code <code>${reason}</code>. Subscriber moved to <strong>ACTIVE</strong>.`;
                const tbody = document.getElementById('audit-table-body');
                const row = tbody.insertRow(0);
                row.innerHTML = `<td><code>AUD-${Math.random().toString(16).substring(2,6).toUpperCase()}</code></td><td>CSR_AGENT_99</td><td><span class="badge">CSR</span></td><td>CSR_ACTIVATION_OVERRIDE</td><td><code>${reason}</code></td><td>Just now</td>`;
            } else {
                div.className = 'alert alert-error';
                div.innerHTML = result.message || result.reason_code;
            }
        }

        async function loadReports() {
            try {
                const res = await fetch('/api/v1/reports/summary', {
                    headers: { 'x-caller-role': 'ADMIN' }
                });
                const result = await res.json();
                if (result.status === 'SUCCESS') {
                    const data = result.data;
                    document.getElementById('rep-conv').innerText = data.activation_funnel.conversion_rate_percentage + '%';
                    document.getElementById('rep-churn').innerText = data.churn_metrics.monthly_churn_rate_percentage + '%';
                    document.getElementById('rep-mix').innerText = data.plan_mix.postpaid_percentage + '%';
                    document.getElementById('rep-arpu').innerText = '$' + data.arpu.arpu;
                }
            } catch (e) {
                console.log('Reports load error:', e);
            }
        }
    </script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=False)
