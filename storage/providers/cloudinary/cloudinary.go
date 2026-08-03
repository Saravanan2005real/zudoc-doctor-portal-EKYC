package cloudinary

import (
	"context"
	"fmt"
	"io"
)

type CloudinaryStorageProvider struct {
	CloudName string
}

func NewCloudinaryStorageProvider(cloudName string) *CloudinaryStorageProvider {
	return &CloudinaryStorageProvider{
		CloudName: cloudName,
	}
}

func (p *CloudinaryStorageProvider) Upload(ctx context.Context, file io.Reader, filename string, contentType string) (string, error) {
	// Cloudinary upload API implementation template
	fileURL := fmt.Sprintf("https://res.cloudinary.com/%s/image/upload/v1/%s", p.CloudName, filename)
	return fileURL, nil
}

func (p *CloudinaryStorageProvider) Delete(ctx context.Context, fileURL string) error {
	return nil
}

func (p *CloudinaryStorageProvider) GetProviderName() string {
	return "CLOUDINARY"
}
