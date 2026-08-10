from typing import Optional
from ..comparison.comparator import ComparisonResult
from ..council.provider import CouncilVerificationResult
from ..fraud.detector import FraudAnalysisResult

class DecisionResult:
    def __init__(self, final_status: str, reason: str):
        self.final_status = final_status
        self.reason = reason

class DecisionEngine:
    def evaluate(
        self,
        comp: ComparisonResult,
        council_res: Optional[CouncilVerificationResult],
        fraud_res: FraudAnalysisResult,
        ocr_confidence: float
    ) -> DecisionResult:
        # 1. REJECTION Rules
        if council_res is not None and council_res.status == "SUSPENDED":
            return DecisionResult(
                final_status="REJECTED",
                reason="Automatic rejection: Medical registration is blacklisted or suspended by the state/national council."
            )

        if fraud_res.fraud_score >= 75:
            return DecisionResult(
                final_status="REJECTED",
                reason=f"Automatic rejection: Critical fraud risk score detected ({fraud_res.fraud_score}/100)."
            )

        # 2. AUTO_VERIFIED Rules
        if (council_res is not None and council_res.status == "ACTIVE" and
            comp.reg_no_match and
            comp.name_match_score >= 90.0 and
            ocr_confidence >= 85.0 and
            fraud_res.fraud_score <= 15):
            
            return DecisionResult(
                final_status="AUTO_VERIFIED",
                reason="Automated verification successful: Medical council registration verified active, high document OCR confidence, and low risk score."
            )

        # 3. MANUAL_REVIEW Rules (Default for discrepancies or moderate confidence)
        reasons = []
        if comp.name_match_score < 90.0:
            reasons.append(f"Name similarity score {comp.name_match_score:.1f}% below auto-verify threshold (90%)")
        if not comp.reg_no_match:
            reasons.append("Registration number on certificate did not match submitted registration number")
        if ocr_confidence < 85.0:
            reasons.append(f"OCR confidence {ocr_confidence:.1f}% below auto-verify threshold (85%)")
        if council_res is None or council_res.status != "ACTIVE":
            reasons.append("Medical council online registry lookup required manual confirmation")
        if fraud_res.fraud_score > 15:
            reasons.append(f"Elevated risk score ({fraud_res.fraud_score}/100)")

        reason_str = "Flagged for manual reviewer approval."
        if reasons:
            reason_str = f"Flagged for manual review: {'; '.join(reasons)}."

        return DecisionResult(
            final_status="MANUAL_REVIEW",
            reason=reason_str
        )
