from typing import List, Optional
from .matcher import calculate_name_match_percentage

class FieldComparison:
    def __init__(
        self,
        field_name: str,
        submitted_value: str,
        extracted_value: str,
        match_score: float,
        is_match: bool
    ):
        self.field_name = field_name
        self.submitted_value = submitted_value
        self.extracted_value = extracted_value
        self.match_score = match_score
        self.is_match = is_match

class ComparisonResult:
    def __init__(
        self,
        name_match_score: float,
        reg_no_match: bool,
        council_match: bool,
        degree_match: bool,
        overall_match_score: float,
        field_comparisons: List[FieldComparison]
    ):
        self.name_match_score = name_match_score
        self.reg_no_match = reg_no_match
        self.council_match = council_match
        self.degree_match = degree_match
        self.overall_match_score = overall_match_score
        self.field_comparisons = field_comparisons

class Comparator:
    def compare_doctor_with_ocr(self, doc, licenses: list, quals: list, ocr_fields) -> ComparisonResult:
        doctor_full_name = f"{getattr(doc, 'first_name', '')} {getattr(doc, 'last_name', '')}".strip()
        
        # 1. Name Comparison (Fuzzy)
        name_score = 0.0
        if getattr(ocr_fields, 'doctor_name', ""):
            name_score = calculate_name_match_percentage(doctor_full_name, ocr_fields.doctor_name)

        # 2. Registration Number Comparison (Exact normalized)
        reg_no_match = False
        sub_reg_no = ""
        if licenses:
            sub_reg_no = getattr(licenses[0], 'registration_number', "")
        
        ocr_reg_no = getattr(ocr_fields, 'registration_number', "")
        if sub_reg_no and ocr_reg_no:
            reg_no_match = sub_reg_no.strip().lower() == ocr_reg_no.strip().lower()

        # 3. Council Comparison
        council_match = False
        sub_council = ""
        if licenses:
            sub_council = getattr(licenses[0], 'registration_council', "")
        
        ocr_council = getattr(ocr_fields, 'registration_council', "")
        if sub_council and ocr_council:
            council_match = (
                ocr_council.lower() in sub_council.lower() or
                sub_council.lower() in ocr_council.lower()
            )

        # 4. Degree Comparison
        degree_match = False
        sub_degree = ""
        if quals:
            sub_degree = getattr(quals[0], 'degree', "")
        
        ocr_degree = getattr(ocr_fields, 'degree', "")
        if sub_degree and ocr_degree:
            degree_match = sub_degree.strip().lower() == ocr_degree.strip().lower()

        # 5. Composite Score Calculation
        weights_sum = 0.0
        total_weight = 0.0

        # Name weight: 40%
        weights_sum += (name_score / 100.0) * 40.0
        total_weight += 40.0

        # Reg No weight: 35%
        if reg_no_match:
            weights_sum += 35.0
        total_weight += 35.0

        # Council weight: 15%
        if council_match:
            weights_sum += 15.0
        total_weight += 15.0

        # Degree weight: 10%
        if degree_match:
            weights_sum += 10.0
        total_weight += 10.0

        overall_score = (weights_sum / total_weight) * 100.0 if total_weight > 0 else 0.0

        field_comparisons = [
            FieldComparison(
                field_name="Doctor Name",
                submitted_value=doctor_full_name,
                extracted_value=getattr(ocr_fields, 'doctor_name', ""),
                match_score=name_score,
                is_match=name_score >= 85.0
            ),
            FieldComparison(
                field_name="Registration Number",
                submitted_value=sub_reg_no,
                extracted_value=ocr_reg_no,
                match_score=100.0 if reg_no_match else 0.0,
                is_match=reg_no_match
            ),
            FieldComparison(
                field_name="Registration Council",
                submitted_value=sub_council,
                extracted_value=ocr_council,
                match_score=100.0 if council_match else 0.0,
                is_match=council_match
            ),
            FieldComparison(
                field_name="Degree",
                submitted_value=sub_degree,
                extracted_value=ocr_degree,
                match_score=100.0 if degree_match else 0.0,
                is_match=degree_match
            )
        ]

        return ComparisonResult(
            name_match_score=name_score,
            reg_no_match=reg_no_match,
            council_match=council_match,
            degree_match=degree_match,
            overall_match_score=overall_score,
            field_comparisons=field_comparisons
        )
