from typing import List, Set
from src.domain.models import ActivationFailedException

class ActivationPolicy:
    """Enforces telecom activation rules covering KYC, dealer authorization, MNP status, and active number exclusivity."""

    DEFAULT_VALID_DEALERS: Set[str] = {"DEALER_001", "DEALER_002", "OFFICIAL_WEB"}

    @classmethod
    def validate_activation(
        cls,
        kyc_status: str,
        dealer_code: str,
        mnp_status: str,
        mobile_number: str,
        active_numbers: Set[str],
        valid_dealers: List[str] = None
    ) -> None:
        authorized_dealers = set(valid_dealers) if valid_dealers else cls.DEFAULT_VALID_DEALERS

        # 1. Check duplicate active mobile number (NFR-08)
        if mobile_number in active_numbers:
            raise ActivationFailedException(
                f"Mobile number {mobile_number} already holds an ACTIVE subscription",
                "ERR_DUPLICATE_ACTIVE_NUMBER"
            )

        # 2. Check KYC verification status
        if kyc_status != "VERIFIED":
            raise ActivationFailedException(
                "KYC identity proof verification failed or pending",
                "ERR_KYC_FAILED"
            )

        # 3. Check dealer authorization
        if dealer_code not in authorized_dealers:
            raise ActivationFailedException(
                f"Dealer code '{dealer_code}' is not registered or authorized",
                "ERR_INVALID_DEALER"
            )

        # 4. Check MNP porting clearance
        if mnp_status == "REJECTED":
            raise ActivationFailedException(
                "MNP porting validation failed downstream with donor operator",
                "ERR_MNP_REJECTED"
            )
