package s3

import (
	"context"
	"fmt"
	"io"
)

type S3StorageProvider struct {
	BucketName string
	Region     string
}

func NewS3StorageProvider(bucketName, region string) *S3StorageProvider {
	return &S3StorageProvider{
		BucketName: bucketName,
		Region:     region,
	}
}

func (p *S3StorageProvider) Upload(ctx context.Context, file io.Reader, filename string, contentType string) (string, error) {
	// S3 PutObject SDK implementation template
	fileURL := fmt.Sprintf("https://%s.s3.%s.amazonaws.com/%s", p.BucketName, p.Region, filename)
	return fileURL, nil
}

func (p *S3StorageProvider) Delete(ctx context.Context, fileURL string) error {
	// S3 DeleteObject SDK implementation template
	return nil
}

func (p *S3StorageProvider) GetProviderName() string {
	return "AWS_S3"
}
