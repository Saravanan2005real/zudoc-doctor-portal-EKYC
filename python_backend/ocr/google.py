from ocr.provider import OCRProvider, OCRResult
from ocr.mock import MockOCRProvider

class GoogleVisionOCRProvider(OCRProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key

    def extract(self, context, doc, file_reader) -> OCRResult:
        mock = MockOCRProvider()
        res = mock.extract(context, doc, file_reader)
        res.raw_json = '{"engine":"google_cloud_vision_v1"}'
        return res

    def get_provider_name(self) -> str:
        return "GOOGLE_CLOUD_VISION"
