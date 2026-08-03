package fraud

import (
	"context"
	"fmt"

	"doctor-service/verification/comparison"
	"doctor-service/verification/council"
)

type FraudRuleResult struct {
	RuleName    string `json:"rule_name"`
	Triggered   bool   `json:"triggered"`
	ScoreImpact int    `json:"score_impact"`
	Description string `json:"description"`
}

type FraudAnalysisResult struct {
	FraudScore  int               `json:"fraud_score"` // 0 - 100
	RiskCategory string           `json:"risk_category"` // LOW, MEDIUM, HIGH, CRITICAL
	RuleResults  []FraudRuleResult `json:"rule_results"`
}

type FraudDetector struct{}

func NewFraudDetector() *FraudDetector {
	return &FraudDetector{}
}

func (d *FraudDetector) Analyze(
	ctx context.Context,
	comp *comparison.ComparisonResult,
	councilRes *council.CouncilVerificationResult,
	ocrConfidence float64,
	duplicateHashFound bool,
	duplicateRegNoFound bool,
) *FraudAnalysisResult {
	totalScore := 0
	var rules []FraudRuleResult

	// Rule 1: Duplicate File Hash across accounts (+40)
	r1 := FraudRuleResult{
		RuleName:    "DUPLICATE_FILE_HASH",
		Triggered:   duplicateHashFound,
		ScoreImpact: 40,
		Description: "Uploaded document SHA-256 hash matches a document uploaded by another doctor account",
	}
	if duplicateHashFound {
		totalScore += 40
	}
	rules = append(rules, r1)

	// Rule 2: Duplicate Registration Number across accounts (+50)
	r2 := FraudRuleResult{
		RuleName:    "DUPLICATE_REGISTRATION_NUMBER",
		Triggered:   duplicateRegNoFound,
		ScoreImpact: 50,
		Description: "Medical registration number is linked to another existing doctor account",
	}
	if duplicateRegNoFound {
		totalScore += 50
	}
	rules = append(rules, r2)

	// Rule 3: Low OCR Confidence (<80%) (+20)
	lowOCR := ocrConfidence < 80.0
	r3 := FraudRuleResult{
		RuleName:    "LOW_OCR_CONFIDENCE",
		Triggered:   lowOCR,
		ScoreImpact: 20,
		Description: fmt.Sprintf("OCR document processing confidence is below threshold (Confidence: %.1f%%)", ocrConfidence),
	}
	if lowOCR {
		totalScore += 20
	}
	rules = append(rules, r3)

	// Rule 4: Name Mismatch below 85% (+30)
	nameMismatch := comp.NameMatchScore < 85.0
	r4 := FraudRuleResult{
		RuleName:    "NAME_MISMATCH",
		Triggered:   nameMismatch,
		ScoreImpact: 30,
		Description: fmt.Sprintf("Doctor name mismatch between profile and certificate (Similarity: %.1f%%)", comp.NameMatchScore),
	}
	if nameMismatch {
		totalScore += 30
	}
	rules = append(rules, r4)

	// Rule 5: Registration Number Mismatch (+40)
	regNoMismatch := !comp.RegNoMatch
	r5 := FraudRuleResult{
		RuleName:    "REGISTRATION_NO_MISMATCH",
		Triggered:   regNoMismatch,
		ScoreImpact: 40,
		Description: "Registration number on certificate does not match submitted registration number",
	}
	if regNoMismatch {
		totalScore += 40
	}
	rules = append(rules, r5)

	// Rule 6: Medical Council Suspension (+60)
	councilSuspended := councilRes != nil && councilRes.Status == "SUSPENDED"
	r6 := FraudRuleResult{
		RuleName:    "COUNCIL_REGISTRATION_SUSPENDED",
		Triggered:   councilSuspended,
		ScoreImpact: 60,
		Description: "Medical council registry indicates license is suspended or blacklisted",
	}
	if councilSuspended {
		totalScore += 60
	}
	rules = append(rules, r6)

	// Cap score at 100
	if totalScore > 100 {
		totalScore = 100
	}

	riskCategory := "LOW"
	switch {
	case totalScore >= 75:
		riskCategory = "CRITICAL"
	case totalScore >= 45:
		riskCategory = "HIGH"
	case totalScore >= 20:
		riskCategory = "MEDIUM"
	}

	return &FraudAnalysisResult{
		FraudScore:   totalScore,
		RiskCategory: riskCategory,
		RuleResults:  rules,
	}
}
