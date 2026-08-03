package fraud_test

import (
	"context"
	"testing"

	"doctor-service/verification/comparison"
	"doctor-service/verification/council"
	"doctor-service/verification/fraud"
)

func TestFraudDetectionCleanScore(t *testing.T) {
	detector := fraud.NewFraudDetector()

	comp := &comparison.ComparisonResult{
		NameMatchScore:    98.0,
		RegNoMatch:        true,
		CouncilMatch:      true,
		DegreeMatch:       true,
		OverallMatchScore: 98.5,
	}

	councilRes := &council.CouncilVerificationResult{
		IsVerified: true,
		Status:     "ACTIVE",
	}

	res := detector.Analyze(context.Background(), comp, councilRes, 95.0, false, false)

	if res.FraudScore != 0 {
		t.Fatalf("expected fraud score 0 for clean doctor, got %d", res.FraudScore)
	}

	if res.RiskCategory != "LOW" {
		t.Fatalf("expected risk category LOW, got %s", res.RiskCategory)
	}
}

func TestFraudDetectionHighRisk(t *testing.T) {
	detector := fraud.NewFraudDetector()

	comp := &comparison.ComparisonResult{
		NameMatchScore:    60.0, // Name mismatch
		RegNoMatch:        false, // Reg no mismatch
		CouncilMatch:      false,
		DegreeMatch:       false,
		OverallMatchScore: 40.0,
	}

	councilRes := &council.CouncilVerificationResult{
		IsVerified: false,
		Status:     "SUSPENDED", // Suspended license
	}

	// Trigger duplicate hash (+40), duplicate reg no (+50), name mismatch (+30), reg mismatch (+40), council suspended (+60)
	res := detector.Analyze(context.Background(), comp, councilRes, 70.0, true, true)

	if res.FraudScore < 80 {
		t.Fatalf("expected high fraud score >= 80, got %d", res.FraudScore)
	}

	if res.RiskCategory != "CRITICAL" {
		t.Fatalf("expected risk category CRITICAL, got %s", res.RiskCategory)
	}
}
