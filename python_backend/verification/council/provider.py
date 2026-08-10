from abc import ABC, abstractmethod
from typing import Optional

class CouncilVerificationResult:
    def __init__(
        self,
        is_verified: bool,
        status: str,
        verification_source: str,
        doctor_name: str = "",
        registration_number: str = "",
        council_name: str = "",
        registration_year: int = 0,
        remarks: str = ""
    ):
        self.is_verified = is_verified
        self.doctor_name = doctor_name
        self.registration_number = registration_number
        self.council_name = council_name
        self.registration_year = registration_year
        self.status = status
        self.verification_source = verification_source
        self.remarks = remarks

class CouncilVerificationProvider(ABC):
    @abstractmethod
    def verify(self, ctx: dict, registration_number: str, council: str) -> CouncilVerificationResult:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass
