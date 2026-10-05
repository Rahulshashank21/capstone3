from typing import List, Set, Optional
from src.domain.models import ActivationFailedException, MNPStatus

class ActivationPolicy:
    """Enforces telecom activation rules covering KYC, dealer authorization, MNP completion, and active number exclusivity."""

    DEFAULT_VALID_DEALERS: Set[str] = {"DEALER_001", "DEALER_002", "OFFICIAL_WEB"}

    @classmethod
    def validate_activation(
        cls,
        kyc_status: str,
        dealer_code: str,
        mnp_status: str,
        mobile_number_hash: Optional[str] = None,
        active_number_hashes: Optional[Set[str]] = None,
        mobile_number: Optional[str] = None,
        active_numbers: Optional[Set[str]] = None,
        valid_dealers: Optional[List[str]] = None
    ) -> None:
        authorized_dealers = set(valid_dealers) if valid_dealers else cls.DEFAULT_VALID_DEALERS

        # 1. Duplicate active mobile number guard (NFR-08)
        if mobile_number and active_numbers and mobile_number in active_numbers:
            raise ActivationFailedException(
                "Mobile number already holds an ACTIVE subscription on the network",
                "ERR_DUPLICATE_ACTIVE_NUMBER"
            )
        if mobile_number_hash and active_number_hashes and mobile_number_hash in active_number_hashes:
            raise ActivationFailedException(
                "Mobile number already holds an ACTIVE subscription on the network",
                "ERR_DUPLICATE_ACTIVE_NUMBER"
            )

        # 2. Server-side verified KYC status check
        if not kyc_status or kyc_status.upper() != "VERIFIED":
            raise ActivationFailedException(
                f"KYC identity proof verification failed (status: '{kyc_status}'). Must be VERIFIED.",
                "ERR_KYC_FAILED"
            )

        # 3. Dealer code whitelisting check
        if not dealer_code or dealer_code not in authorized_dealers:
            raise ActivationFailedException(
                f"Dealer code '{dealer_code}' is not authorized or not recognized in dealer master",
                "ERR_INVALID_DEALER"
            )

        # 4. Strict MNP Completion Semantics (AC-08): MNP validation must be COMPLETED
        clean_mnp = (mnp_status or "").upper().strip()
        if clean_mnp == "REJECTED":
            raise ActivationFailedException(
                "MNP porting validation rejected downstream by donor operator",
                "ERR_MNP_REJECTED"
            )
        elif clean_mnp not in ["COMPLETED", "APPROVED"]:
            raise ActivationFailedException(
                f"MNP porting validation incomplete (status: '{mnp_status}'). Must be COMPLETED.",
                "ERR_MNP_NOT_COMPLETED"
            )
