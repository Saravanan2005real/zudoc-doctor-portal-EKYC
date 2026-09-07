from typing import List, Optional
from ..comparison.comparator import ComparisonResult
from ..council.provider import CouncilVerificationResult

class FraudRuleResult:
    def __init__(self, rule_name: str, triggered: bool, score_impact: int, description: str):
        self.rule_name = rule_name
        self.triggered = triggered
        self.score_impact = score_impact
        self.description = description

class FraudAnalysisResult:
    def __init__(self, fraud_score: int, risk_category: str, rule_results: List[FraudRuleResult]):
        self.fraud_score = fraud_score
        self.risk_category = risk_category
        self.rule_results = rule_results

class FraudDetector:
    def analyze(
        self,
        ctx: dict,
        comp: ComparisonResult,
        council_res: Optional[CouncilVerificationResult],
        ocr_confidence: float,
        duplicate_hash_found: bool,
        duplicate_reg_no_found: bool
    ) -> FraudAnalysisResult:
        total_score = 0
        rules = []

        # Rule 1: Duplicate File Hash across accounts (+40)
        r1 = FraudRuleResult(
            rule_name="DUPLICATE_FILE_HASH",
            triggered=duplicate_hash_found,
            score_impact=40,
            description="Uploaded document SHA-256 hash matches a document uploaded by another doctor account"
        )
        if duplicate_hash_found:
            total_score += 40
        rules.append(r1)

        # Rule 2: Duplicate Registration Number across accounts (+50)
        r2 = FraudRuleResult(
            rule_name="DUPLICATE_REGISTRATION_NUMBER",
            triggered=duplicate_reg_no_found,
            score_impact=50,
            description="Medical registration number is linked to another existing doctor account"
        )
        if duplicate_reg_no_found:
            total_score += 50
        rules.append(r2)

        # Rule 3: Low OCR Confidence (<80%) (+20)
        low_ocr = ocr_confidence < 80.0
        r3 = FraudRuleResult(
            rule_name="LOW_OCR_CONFIDENCE",
            triggered=low_ocr,
            score_impact=20,
            description=f"OCR document processing confidence is below threshold (Confidence: {ocr_confidence:.1f}%)"
        )
        if low_ocr:
            total_score += 20
        rules.append(r3)

        # Rule 4: Name Mismatch below 85% (+30)
        name_mismatch = comp.name_match_score < 85.0
        r4 = FraudRuleResult(
            rule_name="NAME_MISMATCH",
            triggered=name_mismatch,
            score_impact=30,
            description=f"Doctor name mismatch between profile and certificate (Similarity: {comp.name_match_score:.1f}%)"
        )
        if name_mismatch:
            total_score += 30
        rules.append(r4)

        # Rule 5: Registration Number Mismatch (+40)
        reg_no_mismatch = not comp.reg_no_match
        r5 = FraudRuleResult(
            rule_name="REGISTRATION_NO_MISMATCH",
            triggered=reg_no_mismatch,
            score_impact=40,
            description="Registration number on certificate does not match submitted registration number"
        )
        if reg_no_mismatch:
            total_score += 40
        rules.append(r5)

        # Rule 6: Medical Council Suspension (+60)
        council_suspended = council_res is not None and council_res.status == "SUSPENDED"
        r6 = FraudRuleResult(
            rule_name="COUNCIL_REGISTRATION_SUSPENDED",
            triggered=council_suspended,
            score_impact=60,
            description="Medical council registry indicates license is suspended or blacklisted"
        )
        if council_suspended:
            total_score += 60
        rules.append(r6)

        # Cap score at 100
        if total_score > 100:
            total_score = 100

        risk_category = "LOW"
        if total_score >= 75:
            risk_category = "CRITICAL"
        elif total_score >= 45:
            risk_category = "HIGH"
        elif total_score >= 20:
            risk_category = "MEDIUM"

        return FraudAnalysisResult(
            fraud_score=total_score,
            risk_category=risk_category,
            rule_results=rules
        )
