package config

import (
	"os"
	"strings"
	"sync"
)

type FeatureFlags struct {
	mu    sync.RWMutex
	flags map[string]bool
}

var globalFlags = &FeatureFlags{
	flags: map[string]bool{
		"NEW_OCR_PROVIDER":        false,
		"EXPERIMENTAL_FRAUD_RULES": false,
		"AUTO_APPROVE_ENABLED":    true,
		"ASYNC_EVENT_BUS":         true,
		"REDIS_CACHE_ENABLED":     true,
	},
}

func GetFeatureFlags() *FeatureFlags {
	return globalFlags
}

func (f *FeatureFlags) IsEnabled(featureName string) bool {
	f.mu.RLock()
	defer f.mu.RUnlock()

	// Check Environment variable override (e.g., FEATURE_NEW_OCR_PROVIDER=true)
	envKey := "FEATURE_" + strings.ToUpper(featureName)
	if val := os.Getenv(envKey); val != "" {
		return strings.EqualFold(val, "true") || val == "1"
	}

	enabled, ok := f.flags[featureName]
	if !ok {
		return false
	}
	return enabled
}

func (f *FeatureFlags) SetEnabled(featureName string, enabled bool) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.flags[featureName] = enabled
}

func (f *FeatureFlags) GetAllFlags() map[string]bool {
	f.mu.RLock()
	defer f.mu.RUnlock()
	result := make(map[string]bool)
	for k, v := range f.flags {
		result[k] = v
	}
	return result
}
