package local

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

type LocalStorageProvider struct {
	BaseDir string
	BaseURL string
}

func NewLocalStorageProvider(baseDir, baseURL string) (*LocalStorageProvider, error) {
	if baseDir == "" {
		baseDir = "./uploads"
	}
	if baseURL == "" {
		baseURL = "/uploads"
	}

	if err := os.MkdirAll(baseDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create upload directory '%s': %w", baseDir, err)
	}

	return &LocalStorageProvider{
		BaseDir: baseDir,
		BaseURL: baseURL,
	}, nil
}

func (p *LocalStorageProvider) Upload(ctx context.Context, file io.Reader, filename string, contentType string) (string, error) {
	fullPath := filepath.Join(p.BaseDir, filename)
	dir := filepath.Dir(fullPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return "", fmt.Errorf("failed to create directory '%s': %w", dir, err)
	}

	out, err := os.Create(fullPath)
	if err != nil {
		return "", fmt.Errorf("failed to create file '%s': %w", fullPath, err)
	}
	defer out.Close()

	if _, err := io.Copy(out, file); err != nil {
		return "", fmt.Errorf("failed to write file content: %w", err)
	}

	fileURL := fmt.Sprintf("%s/%s", p.BaseURL, filepath.ToSlash(filename))
	return fileURL, nil
}

func (p *LocalStorageProvider) Delete(ctx context.Context, fileURL string) error {
	relPath := filepath.Clean(fileURL)
	fullPath := filepath.Join(p.BaseDir, relPath)
	return os.Remove(fullPath)
}

func (p *LocalStorageProvider) GetProviderName() string {
	return "LOCAL"
}
