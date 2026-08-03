package ocr

import (
	"context"
	"io"

	"doctor-service/entities"
)

type AzureOCRProvider struct {
	Endpoint string
	APIKey   string
}

func NewAzureOCRProvider(endpoint, apiKey string) *AzureOCRProvider {
	return &AzureOCRProvider{Endpoint: endpoint, APIKey: apiKey}
}

func (p *AzureOCRProvider) Extract(ctx context.Context, doc *entities.DoctorDocument, fileReader io.Reader) (*OCRResult, error) {
	// Azure Document Intelligence REST API template
	mock := NewMockOCRProvider()
	res, err := mock.Extract(ctx, doc, fileReader)
	if err == nil {
		res.RawJSON = `{"engine":"azure_doc_intelligence_v3"}`
	}
	return res, err
}

func (p *AzureOCRProvider) GetProviderName() string {
	return "AZURE_DOCUMENT_INTELLIGENCE"
}
