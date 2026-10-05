from decimal import Decimal
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
import re

from src.domain.models import PlanType, SubscriberState, Role

MOBILE_REGEX = re.compile(r"^[0-9]{10}$")

class RegisterSubscriberRequest(BaseModel):
    mobile_number: str = Field(..., description="10-digit mobile MSISDN", examples=["9876543210"])
    identity_proof_ref: str = Field(..., min_length=3, description="Government or KYC proof document reference", examples=["AADHAAR-8821"])
    preferred_plan_type: PlanType = Field(..., description="Prepaid or Postpaid preferred plan")

    @field_validator("mobile_number")
    def validate_mobile(cls, v: str) -> str:
        clean = (v or "").strip()
        if not MOBILE_REGEX.match(clean):
            raise ValueError("Mobile number must be a valid 10-digit numeric MSISDN")
        return clean

class ActivateSubscriberRequest(BaseModel):
    subscriber_id: str = Field(..., description="Subscriber identifier", examples=["SUB-4a8f9c12"])
    kyc_status: str = Field(..., description="KYC status from validation stub", examples=["VERIFIED"])
    dealer_code: str = Field(..., description="Authorized dealer identifier", examples=["DEALER_001"])
    mnp_status: str = Field("COMPLETED", description="MNP clearance status", examples=["COMPLETED"])
    initial_plan_id: str = Field(..., description="Catalog plan to activate on", examples=["PLAN-PRE-STARTER"])

class PlanChangeRequest(BaseModel):
    subscriber_id: str = Field(..., description="Target subscriber identifier")
    new_plan_id: str = Field(..., description="Target catalog plan identifier")
    days_used: Optional[int] = Field(None, ge=0, le=31, description="Days used in cycle; derived server-side if omitted")
    cycle_days: int = Field(30, ge=1, le=31, description="Cycle duration in days (28-31)")
    immediate_pro_rata: bool = Field(False, description="Flag for immediate mid-cycle pro-rata postpaid upgrade")

class ProRataPreviewRequest(BaseModel):
    subscriber_id: str = Field(...)
    new_plan_id: str = Field(...)
    days_used: Optional[int] = Field(None, ge=0, le=31)
    cycle_days: int = Field(30, ge=1, le=31)

class SuspendSubscriberRequest(BaseModel):
    subscriber_id: str = Field(...)
    reason: str = Field("REQUESTED_BY_USER", description="Reason: REQUESTED_BY_USER, NON_PAYMENT, FRAUD_ALERT, ADMIN_INTERVENTION")

class ReactivateSubscriberRequest(BaseModel):
    subscriber_id: str = Field(...)

class PortOutInitiateRequest(BaseModel):
    subscriber_id: str = Field(...)
    recipient_operator: str = Field(..., description="Allowed: AIRTEL_IND, JIO_IND, VI_IND, REC_TELCO_5G, REC_OPERATOR_01, COMPETITOR_TELCO")

class PortOutCancelRequest(BaseModel):
    subscriber_id: str = Field(...)

class PortOutFinalizeRequest(BaseModel):
    subscriber_id: str = Field(...)
    force_override: bool = Field(False, description="Admin override of 7-day cooling period")
    override_reason: Optional[str] = Field(None, description="Mandatory reason if force_override is true")

class AuthTokenRequest(BaseModel):
    principal_id: str = Field(..., description="Username / agent identifier / subscriber ID", examples=["DEALER_001", "CSR_AGENT_99", "ADMIN_USER"])
    role: Role = Field(..., description="Role to authenticate: DEALER, CSR, ADMIN, SUBSCRIBER")
    password: Optional[str] = Field("telcolane-secure", description="Credentials")
    bound_subscriber_id: Optional[str] = Field(None, description="Subscriber ID bound to token if SUBSCRIBER role")
    bound_dealer_code: Optional[str] = Field(None, description="Dealer code bound to token if DEALER role")

class TerminateSubscriberRequest(BaseModel):
    subscriber_id: str = Field(...)
    reason: str = Field("ACCOUNT_CLOSED")

class CSROverrideRequest(BaseModel):
    subscriber_id: str = Field(...)
    initial_plan_id: Optional[str] = Field(None)
    reason_code: str = Field(..., description="Allowed: OVERRIDE_KYC_MANUAL, OVERRIDE_DEALER_SPECIAL, OVERRIDE_TENURE_WAIVER, OVERRIDE_MNP_CLEARANCE, OVERRIDE_BILLING_DISPUTE")
    rejection_id: Optional[str] = Field(None, description="Linked rejection event identifier")
    justification: Optional[str] = Field("Operational CSR exception authorized", description="Audit justification details")

class CreatePlanRequest(BaseModel):
    plan_id: str = Field(...)
    name: str = Field(...)
    plan_type: PlanType = Field(...)
    monthly_rent: Decimal = Field(..., ge=0)
    validity_days: int = Field(..., gt=0)
    data_gb: int = Field(..., ge=0)
    voice_minutes: int = Field(-1)
    sms_count: int = Field(-1)
    min_tenure_days: int = Field(0, ge=0)
    is_published: bool = Field(False)
