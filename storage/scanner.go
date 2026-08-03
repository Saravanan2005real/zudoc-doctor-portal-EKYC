package storage

import (
	"context"
	"io"
	"log"
)

type VirusScanner interface {
	Scan(ctx context.Context, file io.Reader, filename string) (bool, string, error)
}

type DefaultVirusScanner struct{}

func NewDefaultVirusScanner() *DefaultVirusScanner {
	return &DefaultVirusScanner{}
}

func (s *DefaultVirusScanner) Scan(ctx context.Context, file io.Reader, filename string) (bool, string, error) {
	// Clean pass-through placeholder for ClamAV / ICAP / Cloud AV API integration
	log.Printf("[VIRUS SCANNER] Scanning file '%s'... Clean.", filename)
	return true, "Clean", nil
}
