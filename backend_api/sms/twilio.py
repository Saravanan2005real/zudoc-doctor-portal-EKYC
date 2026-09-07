import requests
from sms.provider import SMSProvider, SMSPayload

class TwilioProvider(SMSProvider):
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    def send_otp(self, context, payload: SMSPayload):
        if not self.account_sid or not self.auth_token:
            raise ValueError("twilio credentials missing")

        endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        message = f"Your verification OTP for Doctor Verification Portal is: {payload.otp}. Valid for 5 minutes."

        data = {
            "To": payload.mobile,
            "From": self.from_number,
            "Body": message
        }

        response = requests.post(
            endpoint,
            data=data,
            auth=(self.account_sid, self.auth_token),
            timeout=10
        )

        if response.status_code >= 400:
            raise ValueError(f"twilio API error: status code {response.status_code}")

    def get_provider_name(self) -> str:
        return "TWILIO"
