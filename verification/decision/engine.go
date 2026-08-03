package decision

import (
	"fmt"
	"strings"

	"doctor-service/entities"
	"doctor-service/verification/comparison"
	"doctor-service/verification/council"
	"doctor-service/verification/fraud"
)

type DecisionResult struct {
	FinalStatus entities.DoctorStatus `json:"final_status"`
	Reason      string                `json:"reason"`
}

type DecisionEngine struct{}

func NewDecisionEngine() *DecisionEngine {
	return &DecisionEngine{}
}

func (e *DecisionEngine) Evaluate(
	comp *comparison.ComparisonResult,
	councilRes *council.CouncilVerificationResult,
	fraudRes *fraud.FraudAnalysisResult,
	ocrConfidence float64,
) *DecisionResult {
	// 1. REJECTION Rules
	if councilRes != nil && councilRes.Status == "SUSPENDED" {
		return &DecisionResult{
			FinalStatus: entities.DoctorStatusRejected,
			Reason:      "Automatic rejection: Medical registration is blacklisted or suspended by the state/national council.",
		}
	}

	if fraudRes.FraudScore >= 75 {
		return &DecisionResult{
			FinalStatus: entities.DoctorStatusRejected,
			Reason:      fmt.Sprintf("Automatic rejection: Critical fraud risk score detected (%d/100).", fraudRes.FraudScore),
		}
	}

	// 2. AUTO_VERIFIED Rules
	if councilRes != nil && councilRes.Status == "ACTIVE" &&
		comp.RegNoMatch &&
		comp.NameMatchScore >= 90.0 &&
		ocrConfidence >= 85.0 &&
		fraudRes.FraudScore <= 15 {

		return &DecisionResult{
			FinalStatus: entities.DoctorStatusAutoVerified,
			Reason:      "Automated verification successful: Medical council registration verified active, high document OCR confidence, and low risk score.",
		}
	}

	// 3. MANUAL_REVIEW Rules (Default for discrepancies or moderate confidence)
	reasons := []string{}
	if comp.NameMatchScore < 90.0 {
		reasons = append(reasons, fmt.Sprintf("Name similarity score %.1f%% below auto-verify threshold (90%%)", comp.NameMatchScore))
	}
	if !comp.RegNoMatch {
		reasons = append(reasons, "Registration number on certificate did not match submitted registration number")
	}
	if ocrConfidence < 85.0 {
		reasons = append(reasons, fmt.Sprintf("OCR confidence %.1f%% below auto-verify threshold (85%%)", ocrConfidence))
	}
	if councilRes == nil || councilRes.Status != "ACTIVE" {
		reasons = append(reasons, "Medical council online registry lookup required manual confirmation")
	}
	if fraudRes.FraudScore > 15 {
		reasons = append(reasons, fmt.Sprintf("Elevated risk score (%d/100)", fraudRes.FraudScore))
	}

	reasonStr := "Flagged for manual reviewer approval."
	if len(reasons) > 0 {
		reasonStr = fmt.Sprintf("Flagged for manual review: %s.", strings.Join(reasons, "; "))
	}

	return &DecisionResult{
		FinalStatus: entities.DoctorStatusManualReview,
		Reason:      reasonStr,
	}
}
