import time
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.domain.models import Role
from src.infrastructure.auth import mint_principal_token

@pytest.fixture
def client():
    return TestClient(app)

def dealer_auth(dealer_code: str = "DEALER_001"):
    token = mint_principal_token(Role.DEALER, bound_dealer_code=dealer_code)
    return {"Authorization": f"Bearer {token}"}

def sub_auth(sub_id: str):
    token = mint_principal_token(Role.SUBSCRIBER, principal_id=sub_id, bound_subscriber_id=sub_id)
    return {"Authorization": f"Bearer {token}"}

def csr_auth(csr_id: str = "CSR_AGENT_99"):
    token = mint_principal_token(Role.CSR, principal_id=csr_id)
    return {"Authorization": f"Bearer {token}"}

def admin_auth(admin_id: str = "ADMIN_SYSTEM"):
    token = mint_principal_token(Role.ADMIN, principal_id=admin_id)
    return {"Authorization": f"Bearer {token}"}

def test_nfr_07_health_endpoint_latency_and_status(client):
    """NFR-07: Health endpoint returns 200 within 1 second of startup."""
    start_time = time.time()
    response = client.get("/health")
    latency = time.time() - start_time

    assert response.status_code == 200
    assert latency < 1.0, f"Health check exceeded SLA of 1.0s: {latency:.4f}s"
    data = response.json()
    assert data["status"] == "UP"
    assert data["service"] == "telcolane-substrate"

def test_ac_01_api_registration_and_pii_masking(client):
    """AC-01 & NFR-03: Registration via REST API returns masked subscriber data."""
    payload = {
        "mobile_number": "9811223344",
        "identity_proof_ref": "PASSPORT-Z12345",
        "preferred_plan_type": "POSTPAID"
    }
    response = client.post("/api/v1/subscribers/register", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "SUCCESS"
    assert "correlation_id" in res
    assert res["data"]["mobile_number"] == "XXXXXX3344"
    assert res["data"]["identity_proof_ref"] == "[REDACTED]"
    assert res["data"]["state"] == "PENDING_KYC"

def test_ac_08_api_activation(client):
    """AC-08: Activation via REST API with whitelisted dealer and verified KYC."""
    reg = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9811223355",
        "identity_proof_ref": "ID-KYC-PASS",
        "preferred_plan_type": "PREPAID"
    }).json()
    sub_id = reg["data"]["subscriber_id"]

    act_payload = {
        "subscriber_id": sub_id,
        "kyc_status": "VERIFIED",
        "dealer_code": "DEALER_001",
        "mnp_status": "APPROVED",
        "initial_plan_id": "PLAN-PRE-STARTER"
    }
    response = client.post("/api/v1/subscribers/activate", json=act_payload, headers=dealer_auth())
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "SUCCESS"
    assert res["data"]["state"] == "ACTIVE"

def test_ac_09_api_csr_override(client):
    """AC-09: CSR override via REST API with valid reason code after rejection."""
    reg = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9811223366",
        "identity_proof_ref": "ID-MANUAL-KYC",
        "preferred_plan_type": "POSTPAID"
    }).json()
    sub_id = reg["data"]["subscriber_id"]

    # Attempt activation which fails KYC check
    act_resp = client.post("/api/v1/subscribers/activate", json={
        "subscriber_id": sub_id,
        "kyc_status": "REJECTED",
        "dealer_code": "DEALER_001",
        "mnp_status": "APPROVED",
        "initial_plan_id": "PLAN-POST-SILVER"
    }, headers=dealer_auth())
    assert act_resp.json()["status"] == "ERROR"

    override_payload = {
        "subscriber_id": sub_id,
        "initial_plan_id": "PLAN-POST-SILVER",
        "reason_code": "OVERRIDE_KYC_MANUAL"
    }
    response = client.post(
        "/api/v1/csr/override",
        json=override_payload,
        headers=csr_auth()
    )
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "SUCCESS"
    assert res["data"]["state"] == "ACTIVE"

def test_ac_10_api_reports_summary(client):
    """AC-10: Operational reports summary endpoint accessible to ADMIN."""
    response = client.get("/api/v1/reports/summary", headers=admin_auth())
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "SUCCESS"
    data = res["data"]
    assert "activation_funnel" in data
    assert "churn_metrics" in data
    assert "plan_mix" in data
    assert "arpu" in data

def test_nfr_04_subscriber_boundary_authorization(client):
    """NFR-04: Subscriber role blocked from accessing another subscriber's records."""
    sub_a = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9811223377",
        "identity_proof_ref": "ID-A",
        "preferred_plan_type": "PREPAID"
    }).json()["data"]["subscriber_id"]

    sub_b = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9811223388",
        "identity_proof_ref": "ID-B",
        "preferred_plan_type": "PREPAID"
    }).json()["data"]["subscriber_id"]

    # Subscriber A attempts to fetch Subscriber B's record using Subscriber A's token
    response = client.get(
        f"/api/v1/subscribers/{sub_b}",
        headers=sub_auth(sub_a)
    )
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "ERROR"
    assert res["reason_code"] == "ERR_FORBIDDEN_CROSS_SUBSCRIBER"

def test_api_list_plans_and_get_subscriber(client):
    """Verifies plan listing and authorized subscriber fetch."""
    plans_res = client.get("/api/v1/plans")
    assert plans_res.status_code == 200
    plans_data = plans_res.json()
    assert plans_data["status"] == "SUCCESS"
    assert len(plans_data["data"]) > 0

    # Register subscriber
    reg = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9811556677",
        "identity_proof_ref": "ID-FETCH-TEST",
        "preferred_plan_type": "PREPAID"
    }).json()
    sub_id = reg["data"]["subscriber_id"]

    # Subscriber fetches own record
    get_res = client.get(
        f"/api/v1/subscribers/{sub_id}",
        headers=sub_auth(sub_id)
    )
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "SUCCESS"
    assert get_res.json()["data"]["subscriber_id"] == sub_id

def test_api_lifecycle_transitions_end_to_end(client):
    """Tests plan change, suspend, reactivate, port-out, cancel, finalize, and terminate via REST."""
    # 1. Register & Activate
    reg = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9811998877",
        "identity_proof_ref": "ID-FULL-FLOW",
        "preferred_plan_type": "POSTPAID"
    }).json()
    sub_id = reg["data"]["subscriber_id"]

    act = client.post("/api/v1/subscribers/activate", json={
        "subscriber_id": sub_id,
        "kyc_status": "VERIFIED",
        "dealer_code": "DEALER_001",
        "mnp_status": "APPROVED",
        "initial_plan_id": "PLAN-POST-SILVER"
    }, headers=dealer_auth())
    assert act.json()["status"] == "SUCCESS"

    # 2. Pro-rata preview
    preview = client.post("/api/v1/subscribers/pro-rata-preview", json={
        "subscriber_id": sub_id,
        "new_plan_id": "PLAN-POST-GOLD",
        "days_used": 10,
        "cycle_days": 30
    }, headers=sub_auth(sub_id))
    assert preview.status_code == 200
    assert preview.json()["status"] == "SUCCESS"
    assert "pro_rata_charge" in preview.json()["data"]

    # 3. Suspend
    susp = client.post("/api/v1/subscribers/suspend", json={
        "subscriber_id": sub_id,
        "reason": "REQUESTED_BY_USER"
    }, headers=sub_auth(sub_id))
    assert susp.status_code == 200
    assert susp.json()["data"]["state"] == "SUSPENDED"

    # 4. Reactivate
    react = client.post("/api/v1/subscribers/reactivate", json={
        "subscriber_id": sub_id
    }, headers=sub_auth(sub_id))
    assert react.status_code == 200
    assert react.json()["data"]["state"] == "ACTIVE"

    # 5. Port-out initiate
    port_init = client.post("/api/v1/subscribers/port-out", json={
        "subscriber_id": sub_id,
        "recipient_operator": "AIRTEL_IND"
    }, headers=sub_auth(sub_id))
    assert port_init.status_code == 200
    assert port_init.json()["data"]["state"] == "PORT_OUT_REQUESTED"

    # 6. Port-out cancel
    port_cancel = client.post("/api/v1/subscribers/port-out/cancel", json={
        "subscriber_id": sub_id
    }, headers=sub_auth(sub_id))
    assert port_cancel.status_code == 200
    assert port_cancel.json()["data"]["state"] == "ACTIVE"

    # 7. Port-out initiate again and finalize (with force_override)
    client.post("/api/v1/subscribers/port-out", json={
        "subscriber_id": sub_id,
        "recipient_operator": "JIO_IND"
    }, headers=sub_auth(sub_id))

    port_fin = client.post("/api/v1/subscribers/port-out/finalize", json={
        "subscriber_id": sub_id,
        "force_override": True,
        "override_reason": "REGULATORY_EXPEDITE"
    }, headers=admin_auth())
    assert port_fin.status_code == 200
    assert port_fin.json()["data"]["state"] == "PORTED_OUT"

    # 8. Register another subscriber to test Terminate
    reg2 = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9811443322",
        "identity_proof_ref": "ID-TERM-TEST",
        "preferred_plan_type": "PREPAID"
    }).json()
    sub_id2 = reg2["data"]["subscriber_id"]

    term = client.post("/api/v1/subscribers/terminate", json={
        "subscriber_id": sub_id2,
        "reason": "ACCOUNT_CLOSED"
    }, headers=csr_auth())
    assert term.status_code == 200
    assert term.json()["data"]["state"] == "TERMINATED"
