package storage

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"image"
	_ "image/jpeg"
	_ "image/png"
	"io"
	"net/http"
	"path/filepath"
	"strings"
)

type FileValidationResult struct {
	OriginalFilename string
	MIMEType         string
	Extension        string
	FileSize         int64
	FileHash         string
	Width            *int
	Height           *int
}

type FileValidator struct {
	MaxSizeBytes      int64
	MinImageDimension int
}

func NewFileValidator(maxSizeBytes int64, minImageDimension int) *FileValidator {
	if maxSizeBytes <= 0 {
		maxSizeBytes = 10 * 1024 * 1024 // 10MB default
	}
	if minImageDimension <= 0 {
		minImageDimension = 300
	}
	return &FileValidator{
		MaxSizeBytes:      maxSizeBytes,
		MinImageDimension: minImageDimension,
	}
}

func (v *FileValidator) Validate(file io.ReadSeeker, originalFilename string, declaredSize int64) (*FileValidationResult, error) {
	// 1. Check extension
	ext := strings.ToLower(filepath.Ext(originalFilename))
	blockedExtensions := map[string]bool{
		".exe": true, ".sh": true, ".bat": true, ".cmd": true,
		".js": true, ".py": true, ".php": true, ".zip": true,
		".tar": true, ".gz": true, ".rar": true, ".7z": true,
	}
	if blockedExtensions[ext] {
		return nil, fmt.Errorf("file type '%s' is strictly prohibited for security reasons", ext)
	}

	allowedExtensions := map[string]bool{
		".pdf": true, ".jpg": true, ".jpeg": true, ".png": true,
	}
	if !allowedExtensions[ext] {
		return nil, fmt.Errorf("unsupported file extension '%s'. Only PDF, JPG, JPEG, and PNG files are allowed", ext)
	}

	// 2. Check Size
	if declaredSize > v.MaxSizeBytes {
		return nil, fmt.Errorf("file size exceeds maximum limit of %d MB", v.MaxSizeBytes/(1024*1024))
	}

	// 3. Read header to detect actual MIME type
	buffer := make([]byte, 512)
	n, err := file.Read(buffer)
	if err != nil && !errors.Is(err, io.EOF) {
		return nil, fmt.Errorf("failed to read file header: %w", err)
	}

	detectedMIME := http.DetectContentType(buffer[:n])
	// Adjust for PDF or custom mime checks
	if ext == ".pdf" && !strings.Contains(detectedMIME, "pdf") && !strings.Contains(detectedMIME, "application/octet-stream") {
		// Verify PDF magic bytes '%PDF'
		if n >= 4 && string(buffer[:4]) == "%PDF" {
			detectedMIME = "application/pdf"
		} else {
			return nil, errors.New("file content does not match valid PDF format")
		}
	}

	allowedMIMEs := map[string]bool{
		"application/pdf": true,
		"image/jpeg":      true,
		"image/jpg":       true,
		"image/png":       true,
	}

	if !allowedMIMEs[detectedMIME] && !strings.HasPrefix(detectedMIME, "image/") {
		return nil, fmt.Errorf("invalid file MIME type '%s'", detectedMIME)
	}

	// 4. Compute SHA-256 Hash and Size
	if _, err := file.Seek(0, io.SeekStart); err != nil {
		return nil, err
	}

	hasher := sha256.New()
	size, err := io.Copy(hasher, file)
	if err != nil {
		return nil, fmt.Errorf("failed to compute file hash: %w", err)
	}

	if size > v.MaxSizeBytes {
		return nil, fmt.Errorf("file size %d bytes exceeds maximum limit of %d MB", size, v.MaxSizeBytes/(1024*1024))
	}

	fileHash := hex.EncodeToString(hasher.Sum(nil))

	// 5. Image Resolution Check (if image)
	var widthPtr, heightPtr *int
	if strings.HasPrefix(detectedMIME, "image/") {
		if _, err := file.Seek(0, io.SeekStart); err == nil {
			config, _, err := image.DecodeConfig(file)
			if err == nil {
				w, h := config.Width, config.Height
				if w < v.MinImageDimension || h < v.MinImageDimension {
					return nil, fmt.Errorf("image resolution %dx%d is below minimum required resolution of %dx%d pixels", w, h, v.MinImageDimension, v.MinImageDimension)
				}
				widthPtr = &w
				heightPtr = &h
			}
		}
	}

	// Reset reader position for subsequent upload stream
	_, _ = file.Seek(0, io.SeekStart)

	return &FileValidationResult{
		OriginalFilename: originalFilename,
		MIMEType:         detectedMIME,
		Extension:        ext,
		FileSize:         size,
		FileHash:         fileHash,
		Width:            widthPtr,
		Height:           heightPtr,
	}, nil
}
