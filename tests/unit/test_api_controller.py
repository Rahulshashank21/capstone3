import time
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

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
    # Register subscriber first
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
    response = client.post("/api/v1/subscribers/activate", json=act_payload, headers={"x-caller-role": "DEALER"})
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "SUCCESS"
    assert res["data"]["state"] == "ACTIVE"

def test_ac_09_api_csr_override(client):
    """AC-09: CSR override via REST API with valid reason code."""
    reg = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9811223366",
        "identity_proof_ref": "ID-MANUAL-KYC",
        "preferred_plan_type": "POSTPAID"
    }).json()
    sub_id = reg["data"]["subscriber_id"]

    override_payload = {
        "subscriber_id": sub_id,
        "initial_plan_id": "PLAN-POST-SILVER",
        "reason_code": "OVERRIDE_KYC_MANUAL"
    }
    response = client.post(
        "/api/v1/csr/override",
        json=override_payload,
        headers={"x-caller-role": "CSR", "x-caller-id": "CSR_AGENT_99"}
    )
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "SUCCESS"
    assert res["data"]["state"] == "ACTIVE"

def test_ac_10_api_reports_summary(client):
    """AC-10: Operational reports summary endpoint accessible to ADMIN."""
    response = client.get("/api/v1/reports/summary", headers={"x-caller-role": "ADMIN"})
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
    # Register subscriber A and B
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

    # Subscriber A attempts to fetch Subscriber B's record
    response = client.get(
        f"/api/v1/subscribers/{sub_b}",
        headers={"x-caller-role": "SUBSCRIBER", "x-caller-id": sub_a}
    )
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "ERROR"
    assert res["reason_code"] == "ERR_FORBIDDEN_CROSS_SUBSCRIBER"
