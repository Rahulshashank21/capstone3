import os
import hmac
import hashlib
import base64
import json
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from fastapi import Request, HTTPException, status
from src.domain.models import Role

DEFAULT_DEV_SECRET = "telcolane-secure-signing-secret-key-production-hardened-2026"
SECRET_KEY = os.environ.get("TELCOLANE_JWT_SECRET", DEFAULT_DEV_SECRET)

if os.environ.get("TELCOLANE_ENV") == "production" and SECRET_KEY == DEFAULT_DEV_SECRET:
    raise RuntimeError("CRITICAL: TELCOLANE_JWT_SECRET environment variable must be set in production mode!")

@dataclass(frozen=True)
class Principal:
    principal_id: str
    role: Role
    bound_subscriber_id: Optional[str] = None
    bound_dealer_code: Optional[str] = None

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def _b64_decode(data: str) -> bytes:
    padding = "=" * (4 - len(data) % 4) if len(data) % 4 != 0 else ""
    return base64.urlsafe_b64decode(data + padding)

def create_token(
    principal: Principal,
    expires_in_seconds: int = 86400,
    secret_key: Optional[str] = None
) -> str:
    """Generates an RFC-7519 compliant HMAC-SHA256 JWT with strict claim semantics."""
    key = secret_key or SECRET_KEY
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": principal.principal_id,
        "role": principal.role.value if hasattr(principal.role, "value") else str(principal.role),
        "bound_sub": principal.bound_subscriber_id,
        "bound_dealer": principal.bound_dealer_code,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in_seconds
    }
    header_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(key.encode(), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"

def verify_token(token: str, secret_key: Optional[str] = None) -> Principal:
    """
    Verifies token signature, expiration, and claims.
    Strictly zero backdoor or static tokens in production code path.
    Maps all decoding and verification errors to HTTP 401 Unauthorized.
    """
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ERR_INVALID_TOKEN", "message": "Missing authentication credentials"}
        )

    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ERR_INVALID_TOKEN", "message": "Malformed token structure"}
        )

    header_b64, payload_b64, sig_b64 = parts
    key = secret_key or SECRET_KEY

    # 1. Signature Verification
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(key.encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64_encode(expected_sig), sig_b64):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ERR_SIGNATURE_MISMATCH", "message": "Invalid token signature"}
        )

    # 2. Header and Algorithm Validation
    try:
        header = json.loads(_b64_decode(header_b64).decode())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ERR_INVALID_HEADER", "message": "Corrupted token header"}
        )

    if header.get("alg") != "HS256":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ERR_UNSUPPORTED_ALGORITHM", "message": "Token algorithm not supported"}
        )

    # 3. Payload Validation
    try:
        payload = json.loads(_b64_decode(payload_b64).decode())
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ERR_INVALID_PAYLOAD", "message": "Corrupted token payload"}
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ERR_INVALID_PAYLOAD", "message": "Token claims must be an object"}
        )

    # 4. Expiration Claim
    exp = payload.get("exp")
    if not exp or not isinstance(exp, (int, float)) or exp < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ERR_TOKEN_EXPIRED", "message": "Authentication token has expired"}
        )

    # 5. Subject and Role Claims
    sub = payload.get("sub")
    role_str = payload.get("role")
    if not sub or not role_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ERR_MISSING_CLAIMS", "message": "Token missing required sub or role claims"}
        )

    try:
        role = Role(role_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ERR_INVALID_ROLE", "message": f"Unrecognized role '{role_str}' in token"}
        )

    return Principal(
        principal_id=sub,
        role=role,
        bound_subscriber_id=payload.get("bound_sub"),
        bound_dealer_code=payload.get("bound_dealer")
    )

def mint_principal_token(
    role: Role,
    principal_id: Optional[str] = None,
    bound_subscriber_id: Optional[str] = None,
    bound_dealer_code: Optional[str] = None,
    expires_in_seconds: int = 86400
) -> str:
    """Convenience helper to mint signed tokens for testing and authentication endpoints."""
    pid = principal_id or (
        "ADMIN_SYSTEM" if role == Role.ADMIN else (
            "CSR_AGENT_99" if role == Role.CSR else (
                bound_dealer_code or "DEALER_001" if role == Role.DEALER else (
                    bound_subscriber_id or "SUB-USER-01"
                )
            )
        )
    )
    p = Principal(
        principal_id=pid,
        role=role,
        bound_subscriber_id=bound_subscriber_id or (pid if role == Role.SUBSCRIBER else None),
        bound_dealer_code=bound_dealer_code or (pid if role == Role.DEALER else None)
    )
    return create_token(p, expires_in_seconds=expires_in_seconds)

def extract_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    x_auth = request.headers.get("X-Auth-Token")
    if x_auth:
        return x_auth.strip()
    return None

def get_current_principal(request: Request) -> Principal:
    token = extract_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "ERR_UNAUTHENTICATED", "message": "Authentication required. Missing Bearer token."}
        )
    return verify_token(token)

def require_role(*allowed_roles: Role):
    def dependency(request: Request) -> Principal:
        principal = get_current_principal(request)
        if principal.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ERR_FORBIDDEN",
                    "message": f"Principal role '{principal.role.value}' is not authorized. Required: {[r.value for r in allowed_roles]}"
                }
            )
        return principal
    return dependency
