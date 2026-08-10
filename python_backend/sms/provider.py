from abc import ABC, abstractmethod

class SMSPayload:
    def __init__(self, mobile: str, otp: str, purpose: str, message: str = ""):
        self.mobile = mobile
        self.otp = otp
        self.purpose = purpose
        self.message = message

class SMSProvider(ABC):
    @abstractmethod
    def send_otp(self, context, payload: SMSPayload):
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass
