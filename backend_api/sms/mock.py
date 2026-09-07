from sms.provider import SMSProvider, SMSPayload

class MockSMSProvider(SMSProvider):
    def send_otp(self, context, payload: SMSPayload):
        print(f"[MOCK SMS PROVIDER] Sending OTP '{payload.otp}' to mobile '{payload.mobile}' for purpose '{payload.purpose}'")
        print("\n=======================================================")
        print(f"[MOCK SMS] Mobile: {payload.mobile} | OTP: {payload.otp} | Purpose: {payload.purpose}")
        print("=======================================================\n")

    def get_provider_name(self) -> str:
        return "MOCK"
