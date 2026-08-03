package ocr

import (
	"context"
	"io"

	"doctor-service/entities"
)

type GoogleVisionOCRProvider struct {
	APIKey string
}

func NewGoogleVisionOCRProvider(apiKey string) *GoogleVisionOCRProvider {
	return &GoogleVisionOCRProvider{APIKey: apiKey}
}

func (p *GoogleVisionOCRProvider) Extract(ctx context.Context, doc *entities.DoctorDocument, fileReader io.Reader) (*OCRResult, error) {
	// Google Cloud Vision API template
	mock := NewMockOCRProvider()
	res, err := mock.Extract(ctx, doc, fileReader)
	if err == nil {
		res.RawJSON = `{"engine":"google_cloud_vision_v1"}`
	}
	return res, err
}

func (p *GoogleVisionOCRProvider) GetProviderName() string {
	return "GOOGLE_CLOUD_VISION"
}
