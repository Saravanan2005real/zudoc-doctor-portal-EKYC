from .provider import CouncilVerificationProvider, CouncilVerificationResult

class ManualFallbackProvider(CouncilVerificationProvider):
    def verify(self, ctx: dict, registration_number: str, council: str) -> CouncilVerificationResult:
        return CouncilVerificationResult(
            is_verified=False,
            registration_number=registration_number,
            council_name=council,
            status="MANUAL_REVIEW_REQUIRED",
            verification_source="MANUAL_FALLBACK",
            remarks="Official online API unavailable for council. Marked for manual review."
        )

    def get_provider_name(self) -> str:
        return "MANUAL_FALLBACK_PROVIDER"
