---
name: kyc-validation-stub
description: Evaluates subscriber KYC documents, dealer authorizations, and MNP porting clearance stubs.
---

# KYC & Activation Validation Stub Skill

## Policy Checks
1. **KYC Verification**: Evaluates whether customer identity reference has passed biometric or document checks. Status must be `VERIFIED`. If `UNVERIFIED` or `FAILED`, raises `ERR_KYC_FAILED`.
2. **Dealer Registry**: Verifies dealer authorization against whitelist (`DEALER_001`, `DEALER_002`, `OFFICIAL_WEB`). If unlisted, raises `ERR_INVALID_DEALER`.
3. **MNP Clearinghouse**: Checks recipient/donor clearance. If `REJECTED`, raises `ERR_MNP_REJECTED`.
