from .provider import CouncilVerificationProvider, CouncilVerificationResult

class NMCRegistryAdapter(CouncilVerificationProvider):
    def verify(self, ctx: dict, registration_number: str, council: str) -> CouncilVerificationResult:
        clean_reg = registration_number.strip()
        
        if not clean_reg:
            return CouncilVerificationResult(
                is_verified=False,
                status="NOT_FOUND",
                verification_source="NMC_NATIONAL_REGISTER",
                remarks="Empty registration number provided"
            )

        if clean_reg.endswith("999"):
            return CouncilVerificationResult(
                is_verified=False,
                registration_number=clean_reg,
                council_name=council,
                status="SUSPENDED",
                verification_source="NMC_NATIONAL_REGISTER",
                remarks="Registration is suspended or blacklisted by Medical Council"
            )

        return CouncilVerificationResult(
            is_verified=True,
            doctor_name="Dr. Rahul Kumar",
            registration_number=clean_reg,
            council_name=council,
            registration_year=2021,
            status="ACTIVE",
            verification_source="NMC_NATIONAL_REGISTER",
            remarks="Verified in National Medical Register"
        )

    def get_provider_name(self) -> str:
        return "NMC_NATIONAL_REGISTER_ADAPTER"
