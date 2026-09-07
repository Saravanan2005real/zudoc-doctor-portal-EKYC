import requests
from sms.provider import SMSProvider, SMSPayload

class MSG91Provider(SMSProvider):
    def __init__(self, auth_key: str, template_id: str, sender_id: str):
        self.auth_key = auth_key
        self.template_id = template_id
        self.sender_id = sender_id

    def send_otp(self, context, payload: SMSPayload):
        if not self.auth_key:
            raise ValueError("msg91 auth key missing")

        url = f"https://control.msg91.com/api/v5/otp?template_id={self.template_id}&mobile={payload.mobile}&authkey={self.auth_key}"
        
        data = {"OTP": payload.otp}

        response = requests.post(
            url,
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code >= 400:
            raise ValueError(f"msg91 API error: status code {response.status_code}")

    def get_provider_name(self) -> str:
        return "MSG91"
