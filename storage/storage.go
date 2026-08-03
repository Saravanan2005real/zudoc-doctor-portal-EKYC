package storage

import (
	"context"
	"io"
)

type ReadSeekerCloser interface {
	io.Reader
	io.Seeker
	io.Closer
}

type StorageProvider interface {
	Upload(ctx context.Context, file io.Reader, filename string, contentType string) (string, error)
	Delete(ctx context.Context, fileURL string) error
	GetProviderName() string
}
