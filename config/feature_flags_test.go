package config_test

import (
	"testing"

	"doctor-service/config"
)

func TestFeatureFlagsEngine(t *testing.T) {
	flags := config.GetFeatureFlags()

	if !flags.IsEnabled("AUTO_APPROVE_ENABLED") {
		t.Fatalf("expected AUTO_APPROVE_ENABLED to be true by default")
	}

	flags.SetEnabled("EXPERIMENTAL_FRAUD_RULES", true)
	if !flags.IsEnabled("EXPERIMENTAL_FRAUD_RULES") {
		t.Fatalf("expected EXPERIMENTAL_FRAUD_RULES to be true after update")
	}

	if flags.IsEnabled("NON_EXISTENT_FEATURE") {
		t.Fatalf("expected non-existent feature to be false")
	}
}
