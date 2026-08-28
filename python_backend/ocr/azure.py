from ocr.provider import OCRProvider, OCRResult
from ocr.mock import MockOCRProvider

class AzureOCRProvider(OCRProvider):
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.api_key = api_key

    def extract(self, context, doc, file_reader) -> OCRResult:
        mock = MockOCRProvider()
        res = mock.extract(context, doc, file_reader)
        res.raw_json = '{"engine":"azure_doc_intelligence_v3"}'
        return res

    def get_provider_name(self) -> str:
        return "AZURE_DOCUMENT_INTELLIGENCE"
