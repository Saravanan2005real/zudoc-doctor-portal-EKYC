package storage_test

import (
	"bytes"
	"testing"

	"doctor-service/storage"
)

type readSeeker struct {
	*bytes.Reader
}

func (r *readSeeker) Close() error {
	return nil
}

func TestFileValidatorExecutableRejection(t *testing.T) {
	validator := storage.NewFileValidator(10*1024*1024, 300)
	content := []byte("echo 'malicious script'")
	rs := &readSeeker{Reader: bytes.NewReader(content)}

	_, err := validator.Validate(rs, "script.sh", int64(len(content)))
	if err == nil {
		t.Fatalf("expected executable .sh file to be rejected, but passed")
	}

	rsExe := &readSeeker{Reader: bytes.NewReader(content)}
	_, err = validator.Validate(rsExe, "malware.exe", int64(len(content)))
	if err == nil {
		t.Fatalf("expected .exe file to be rejected, but passed")
	}
}

func TestFileValidatorPDFSuccess(t *testing.T) {
	validator := storage.NewFileValidator(10*1024*1024, 300)
	pdfContent := []byte("%PDF-1.4 sample pdf content for testing validation")
	rs := &readSeeker{Reader: bytes.NewReader(pdfContent)}

	res, err := validator.Validate(rs, "mbbs_certificate.pdf", int64(len(pdfContent)))
	if err != nil {
		t.Fatalf("expected valid PDF file, got error: %v", err)
	}

	if res.Extension != ".pdf" {
		t.Fatalf("expected extension .pdf, got %s", res.Extension)
	}

	if res.FileHash == "" {
		t.Fatalf("expected non-empty SHA-256 hash")
	}
}
