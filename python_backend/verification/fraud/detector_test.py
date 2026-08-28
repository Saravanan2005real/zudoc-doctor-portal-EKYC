import unittest
from ..comparison.comparator import ComparisonResult
from ..council.provider import CouncilVerificationResult
from .detector import FraudDetector

class TestFraudDetector(unittest.TestCase):
    def test_fraud_detection_clean_score(self):
        detector = FraudDetector()

        comp = ComparisonResult(
            name_match_score=98.0,
            reg_no_match=True,
            council_match=True,
            degree_match=True,
            overall_match_score=98.5,
            field_comparisons=[]
        )

        council_res = CouncilVerificationResult(
            is_verified=True,
            status="ACTIVE",
            verification_source=""
        )

        res = detector.analyze({}, comp, council_res, 95.0, False, False)

        self.assertEqual(res.fraud_score, 0, f"expected fraud score 0 for clean doctor, got {res.fraud_score}")
        self.assertEqual(res.risk_category, "LOW", f"expected risk category LOW, got {res.risk_category}")

    def test_fraud_detection_high_risk(self):
        detector = FraudDetector()

        comp = ComparisonResult(
            name_match_score=60.0, # Name mismatch
            reg_no_match=False, # Reg no mismatch
            council_match=False,
            degree_match=False,
            overall_match_score=40.0,
            field_comparisons=[]
        )

        council_res = CouncilVerificationResult(
            is_verified=False,
            status="SUSPENDED", # Suspended license
            verification_source=""
        )

        # Trigger duplicate hash (+40), duplicate reg no (+50), name mismatch (+30), reg mismatch (+40), council suspended (+60)
        res = detector.analyze({}, comp, council_res, 70.0, True, True)

        self.assertGreaterEqual(res.fraud_score, 80, f"expected high fraud score >= 80, got {res.fraud_score}")
        self.assertEqual(res.risk_category, "CRITICAL", f"expected risk category CRITICAL, got {res.risk_category}")

if __name__ == '__main__':
    unittest.main()
