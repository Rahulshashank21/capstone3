import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient

from src.main import app
from src.domain.models import (
    Role, PlanType, SubscriberState, InvalidSubscriberStateException,
    ActivationFailedException, DomainException, CoolingPeriodExpiredException
)
from src.infrastructure.auth import Principal, create_token, mint_principal_token
from src.services.subscription_service import SubscriptionService

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def service():
    srv = SubscriptionService()
    srv.create_plan("PLAN-SEC-PRE", "Sec Prepaid", PlanType.PREPAID, Decimal("20.00"), 28, 10, is_published=True)
    srv.create_plan("PLAN-SEC-POST", "Sec Postpaid", PlanType.POSTPAID, Decimal("60.00"), 30, 30, min_tenure_days=90, is_published=True)
    return srv

def test_vulnerability_fix_anonymous_reports_denied(client):
    """NFR-04: Anonymous requests without authentication headers must be rejected with 401."""
    response = client.get("/api/v1/reports/summary")
    assert response.status_code == 401

def test_vulnerability_fix_anonymous_csr_override_denied(client):
    """NFR-04: CSR overrides without authentication headers must be rejected with 401."""
    payload = {
        "subscriber_id": "SUB-ANY",
        "initial_plan_id": "PLAN-POST-BASE",
        "reason_code": "OVERRIDE_KYC_MANUAL"
    }
    response = client.post("/api/v1/csr/override", json=payload)
    assert response.status_code == 401

def test_vulnerability_fix_subscriber_cannot_activate_accounts(client):
    """NFR-04 & AC-08: Subscriber role attempting activation is blocked with 401/403/ERR_UNAUTHORIZED."""
    reg = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9812345001",
        "identity_proof_ref": "ID-SUB-ACT",
        "preferred_plan_type": "PREPAID"
    }).json()["data"]["subscriber_id"]

    act_payload = {
        "subscriber_id": reg,
        "kyc_status": "VERIFIED",
        "dealer_code": "DEALER_001",
        "mnp_status": "COMPLETED",
        "initial_plan_id": "PLAN-PRE-STARTER"
    }
    sub_token = create_token(Principal(principal_id=reg, role=Role.SUBSCRIBER, bound_subscriber_id=reg))
    response = client.post(
        "/api/v1/subscribers/activate",
        json=act_payload,
        headers={"Authorization": f"Bearer {sub_token}"}
    )
    # Controller returns error status with ERR_UNAUTHORIZED
    res = response.json()
    assert res["status"] == "ERROR"
    assert res["reason_code"] == "ERR_UNAUTHORIZED"

def test_vulnerability_fix_jwt_bearer_token_authentication(client):
    """NFR-04: Cryptographically signed JWT tokens grant access to authorized roles."""
    principal = Principal(principal_id="ADMIN_CHIEF", role=Role.ADMIN)
    token = create_token(principal)

    response = client.get(
        "/api/v1/reports/summary",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "SUCCESS"
    assert "activation_funnel" in res["data"]

def test_vulnerability_fix_cross_subscriber_isolation_no_fallback(client):
    """NFR-04: Subscriber A cannot mutate Subscriber B's plan even if caller_id is omitted."""
    sub_a = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9812345002",
        "identity_proof_ref": "ID-A",
        "preferred_plan_type": "PREPAID"
    }).json()["data"]["subscriber_id"]

    sub_b = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9812345003",
        "identity_proof_ref": "ID-B",
        "preferred_plan_type": "PREPAID"
    }).json()["data"]["subscriber_id"]

    # Subscriber A sends mutation request targeting Subscriber B without passing x-caller-id
    token_a = create_token(Principal(principal_id=sub_a, role=Role.SUBSCRIBER, bound_subscriber_id=sub_a))
    response = client.post(
        "/api/v1/subscribers/suspend",
        json={"subscriber_id": sub_b},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    res = response.json()
    assert res["status"] == "ERROR"
    assert res["reason_code"] == "ERR_FORBIDDEN_CROSS_SUBSCRIBER"

def test_vulnerability_fix_cannot_reactivate_from_pending_kyc(service):
    """AC-06: reactivate_subscriber strictly requires state == SUSPENDED; cannot bypass KYC from PENDING_KYC."""
    sub = service.register_subscriber("9812345004", "ID-BYPASS", PlanType.PREPAID)
    assert sub.state == SubscriberState.PENDING_KYC

    with pytest.raises(InvalidSubscriberStateException) as exc_info:
        service.reactivate_subscriber(sub.subscriber_id)
    assert exc_info.value.reason_code == "ERR_NOT_SUSPENDED"

def test_vulnerability_fix_suspension_preserves_prior_state_and_restores(service):
    """AC-06: Suspending preserves previous_state and reason; reactivation restores prior state."""
    sub = service.register_subscriber("9812345005", "ID-PRIOR", PlanType.POSTPAID)
    service.activate_subscriber(sub.subscriber_id, "VERIFIED", "DEALER_001", "APPROVED", "PLAN-SEC-POST")
    assert sub.state == SubscriberState.ACTIVE

    suspended = service.suspend_subscriber(sub.subscriber_id, reason="NON_PAYMENT")
    assert suspended.state == SubscriberState.SUSPENDED
    assert suspended.previous_state == SubscriberState.ACTIVE
    assert suspended.suspension_reason == "NON_PAYMENT"
    assert suspended.is_consumption_active is False

    reactivated = service.reactivate_subscriber(sub.subscriber_id)
    assert reactivated.state == SubscriberState.ACTIVE
    assert reactivated.previous_state is None
    assert reactivated.suspension_reason is None
    assert reactivated.is_consumption_active is True

def test_vulnerability_fix_finalize_port_out_enforces_cooling_window(client):
    """AC-07: Port-out finalization via endpoint rejects requests before 7 full days have elapsed."""
    reg = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9812345006",
        "identity_proof_ref": "ID-PO",
        "preferred_plan_type": "PREPAID"
    }).json()["data"]["subscriber_id"]

    dealer_token = mint_principal_token(Role.DEALER, bound_dealer_code="DEALER_001")
    sub_token = mint_principal_token(Role.SUBSCRIBER, principal_id=reg, bound_subscriber_id=reg)
    admin_token = mint_principal_token(Role.ADMIN)

    client.post(
        "/api/v1/subscribers/activate",
        json={
            "subscriber_id": reg,
            "kyc_status": "VERIFIED",
            "dealer_code": "DEALER_001",
            "mnp_status": "COMPLETED",
            "initial_plan_id": "PLAN-PRE-STARTER"
        },
        headers={"Authorization": f"Bearer {dealer_token}"}
    )

    client.post(
        "/api/v1/subscribers/port-out",
        json={"subscriber_id": reg, "recipient_operator": "AIRTEL_IND"},
        headers={"Authorization": f"Bearer {sub_token}"}
    )

    # Attempt immediate finalization without override: must be rejected!
    fin_resp = client.post(
        "/api/v1/subscribers/port-out/finalize",
        json={"subscriber_id": reg, "force_override": False},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    res = fin_resp.json()
    assert res["status"] == "ERROR"
    assert res["reason_code"] == "ERR_COOLING_PERIOD_NOT_ELAPSED"

def test_vulnerability_fix_correlation_id_sanitization(client):
    """NFR-05: Malicious or illegal correlation IDs are rejected and replaced with safe UUIDs."""
    malicious_id = "<script>alert('xss')</script>"
    response = client.get("/health", headers={"X-Correlation-ID": malicious_id})
    returned_id = response.headers.get("X-Correlation-ID")
    assert "<" not in returned_id
    assert returned_id.startswith("REQ-")

def test_vulnerability_fix_pro_rata_preview_endpoint(client):
    """AC-05: Non-mutating pro-rata preview calculates itemized amounts accurately."""
    reg = client.post("/api/v1/subscribers/register", json={
        "mobile_number": "9812345007",
        "identity_proof_ref": "ID-PREV",
        "preferred_plan_type": "POSTPAID"
    }).json()["data"]["subscriber_id"]

    dealer_token = mint_principal_token(Role.DEALER, bound_dealer_code="DEALER_001")
    sub_token = mint_principal_token(Role.SUBSCRIBER, principal_id=reg, bound_subscriber_id=reg)

    client.post(
        "/api/v1/subscribers/activate",
        json={
            "subscriber_id": reg,
            "kyc_status": "VERIFIED",
            "dealer_code": "DEALER_001",
            "mnp_status": "COMPLETED",
            "initial_plan_id": "PLAN-POST-SILVER"
        },
        headers={"Authorization": f"Bearer {dealer_token}"}
    )

    preview_resp = client.post(
        "/api/v1/subscribers/pro-rata-preview",
        json={"subscriber_id": reg, "new_plan_id": "PLAN-POST-GOLD", "days_used": 15, "cycle_days": 30},
        headers={"Authorization": f"Bearer {sub_token}"}
    )
    assert preview_resp.status_code == 200
    res = preview_resp.json()
    assert res["status"] == "SUCCESS"
    data = res["data"]
    assert data["target_plan_id"] == "PLAN-POST-GOLD"
    assert "charge" in data
    assert "itemized" in data

def test_jwt_token_creation_and_bearer_auth(client):
    """NFR-04: Genuine signed JWT tokens authenticate API calls."""
    from src.infrastructure.auth import Principal, create_token, verify_token
    from fastapi import HTTPException

    admin_principal = Principal(principal_id="SEC_ADMIN_1", role=Role.ADMIN)
    token = create_token(admin_principal, expires_in_seconds=3600)

    # Verify token decoding
    verified = verify_token(token)
    assert verified.principal_id == "SEC_ADMIN_1"
    assert verified.role == Role.ADMIN

    # Authenticate via Bearer header
    resp = client.get("/api/v1/reports/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"

def test_jwt_token_tampering_and_expiration(client):
    """NFR-04: Tampered and expired tokens are rejected with 401."""
    from src.infrastructure.auth import Principal, create_token, verify_token
    from fastapi import HTTPException

    # 1. Expired token
    expired_token = create_token(Principal("EXP_USER", Role.SUBSCRIBER), expires_in_seconds=-10)
    with pytest.raises(HTTPException) as exc:
        verify_token(expired_token)
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "ERR_TOKEN_EXPIRED"

    # 2. Tampered signature
    valid_token = create_token(Principal("VAL_USER", Role.SUBSCRIBER), expires_in_seconds=3600)
    parts = valid_token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.badsignature123"
    with pytest.raises(HTTPException) as exc:
        verify_token(tampered_token)
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "ERR_SIGNATURE_MISMATCH"

    # 3. Malformed token structure
    with pytest.raises(HTTPException) as exc:
        verify_token("not-a-jwt")
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "ERR_INVALID_TOKEN"

def test_jwt_token_claims_and_algorithm_validation():
    """Validates algorithm check, corrupted header/payload, and claim checks."""
    import hmac, hashlib, json, time
    from fastapi import HTTPException
    from src.infrastructure.auth import _b64_encode, verify_token, SECRET_KEY

    # 1. Unsupported algorithm
    header = _b64_encode(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = _b64_encode(json.dumps({"sub": "U1", "role": "ADMIN", "exp": int(time.time()) + 100}).encode())
    sig = _b64_encode(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    bad_token = f"{header}.{payload}.{sig}"
    with pytest.raises(HTTPException) as exc:
        verify_token(bad_token)
    assert exc.value.detail["code"] == "ERR_UNSUPPORTED_ALGORITHM"

    # 2. Corrupted payload JSON
    header = _b64_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64_encode(b"not-valid-json")
    sig = _b64_encode(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    with pytest.raises(HTTPException) as exc:
        verify_token(f"{header}.{payload}.{sig}")
    assert exc.value.detail["code"] == "ERR_INVALID_PAYLOAD"

    # 3. Missing sub/role claims
    payload = _b64_encode(json.dumps({"exp": int(time.time()) + 100}).encode())
    sig = _b64_encode(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    with pytest.raises(HTTPException) as exc:
        verify_token(f"{header}.{payload}.{sig}")
    assert exc.value.detail["code"] == "ERR_MISSING_CLAIMS"

    # 4. Invalid role
    payload = _b64_encode(json.dumps({"sub": "U1", "role": "HACKER", "exp": int(time.time()) + 100}).encode())
    sig = _b64_encode(hmac.new(SECRET_KEY.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    with pytest.raises(HTTPException) as exc:
        verify_token(f"{header}.{payload}.{sig}")
    assert exc.value.detail["code"] == "ERR_INVALID_ROLE"

