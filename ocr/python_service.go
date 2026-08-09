package ocr

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"time"

	"doctor-service/entities"
)

type PythonOCRProvider struct {
	ServiceURL string
}

func NewPythonOCRProvider(serviceURL string) *PythonOCRProvider {
	if serviceURL == "" {
		serviceURL = "http://127.0.0.1:5001/api/v1/ocr"
	}
	return &PythonOCRProvider{
		ServiceURL: serviceURL,
	}
}

type PythonOCRResponse struct {
	Status               string                 `json:"status"`
	Error                string                 `json:"error,omitempty"`
	OCRConfidence        float64                `json:"ocr_confidence"`
	ParsedFields         map[string]interface{} `json:"parsed_fields"`
	PerspectiveCorrected bool                   `json:"perspective_corrected"`
	RawText              []string               `json:"raw_text"`
}

func (p *PythonOCRProvider) Extract(ctx context.Context, doc *entities.DoctorDocument, fileReader io.Reader) (*OCRResult, error) {
	start := time.Now()

	// Create multipart form
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	
	part, err := writer.CreateFormFile("file", "document.png")
	if err != nil {
		return nil, fmt.Errorf("failed to create form file: %w", err)
	}
	
	if _, err := io.Copy(part, fileReader); err != nil {
		return nil, fmt.Errorf("failed to copy file content: %w", err)
	}
	
	if err := writer.Close(); err != nil {
		return nil, fmt.Errorf("failed to close multipart writer: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, p.ServiceURL, body)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Content-Type", writer.FormDataContentType())

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to call Python OCR service: %w", err)
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	var pyResp PythonOCRResponse
	if err := json.Unmarshal(respBody, &pyResp); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	if pyResp.Status != "success" {
		return nil, fmt.Errorf("python OCR service returned error: %s", pyResp.Error)
	}

	// Map Python parsed fields to Go ExtractedFields
	fields := ExtractedFields{}
	
	if name, ok := pyResp.ParsedFields["name"].(string); ok && name != "" {
		fields.DoctorName = name
	}
	if dob, ok := pyResp.ParsedFields["dob"].(string); ok && dob != "" {
		fields.DOB = dob
	}
	if aadhaar, ok := pyResp.ParsedFields["aadhaar_number"].(string); ok && aadhaar != "" {
		fields.GovtIDNumber = aadhaar
	}

	processingTime := time.Since(start).Milliseconds()

	return &OCRResult{
		RawJSON:          string(respBody),
		ParsedFields:     fields,
		Confidence:       pyResp.OCRConfidence,
		ProcessingTimeMS: processingTime,
	}, nil
}

func (p *PythonOCRProvider) GetProviderName() string {
	return "PYTHON_PADDLE_OCR"
}