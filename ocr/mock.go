package ocr

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"time"

	"doctor-service/entities"
)

type MockOCRProvider struct{}

func NewMockOCRProvider() *MockOCRProvider {
	return &MockOCRProvider{}
}

func (p *MockOCRProvider) Extract(ctx context.Context, doc *entities.DoctorDocument, fileReader io.Reader) (*OCRResult, error) {
	start := time.Now()

	fields := ExtractedFields{}
	confidence := 96.5

	switch doc.DocumentType {
	case entities.DocumentTypeRegistrationCertificate:
		fields = ExtractedFields{
			DoctorName:          "Dr. Rahul Kumar",
			RegistrationNumber:  "123456",
			RegistrationCouncil: "Tamil Nadu Medical Council",
			RegistrationYear:    2021,
			Degree:              "MBBS",
		}
	case entities.DocumentTypeMBBSCertificate, entities.DocumentTypeMDCertificate:
		fields = ExtractedFields{
			DoctorName:    "Rahul Kumar",
			Degree:        "MBBS",
			University:    "The Tamil Nadu Dr. M.G.R. Medical University",
			College:       "Stanley Medical College",
			YearCompleted: 2020,
		}
	case entities.DocumentTypeAadhaar, entities.DocumentTypePAN, entities.DocumentTypePassport:
		fields = ExtractedFields{
			DoctorName:   "Rahul Kumar",
			DOB:          "1995-05-15",
			GovtIDNumber: "9999-8888-7777",
		}
	default:
		fields = ExtractedFields{
			DoctorName: "Rahul Kumar",
		}
	}

	parsedJSON, _ := json.Marshal(fields)
	rawJSON := fmt.Sprintf(`{"engine":"mock_ocr_v1","status":"success","extracted":%s}`, string(parsedJSON))
	processingTime := time.Since(start).Milliseconds()

	return &OCRResult{
		RawJSON:          rawJSON,
		ParsedFields:     fields,
		Confidence:       confidence,
		ProcessingTimeMS: processingTime,
	}, nil
}

func (p *MockOCRProvider) GetProviderName() string {
	return "MOCK_OCR"
}
