package comparison

import (
	"strings"

	"doctor-service/entities"
	"doctor-service/ocr"
)

type FieldComparison struct {
	FieldName      string  `json:"field_name"`
	SubmittedValue string  `json:"submitted_value"`
	ExtractedValue string  `json:"extracted_value"`
	MatchScore     float64 `json:"match_score"`
	IsMatch        bool    `json:"is_match"`
}

type ComparisonResult struct {
	NameMatchScore     float64           `json:"name_match_score"`
	RegNoMatch         bool              `json:"reg_no_match"`
	CouncilMatch       bool              `json:"council_match"`
	DegreeMatch        bool              `json:"degree_match"`
	OverallMatchScore  float64           `json:"overall_match_score"`
	FieldComparisons   []FieldComparison `json:"field_comparisons"`
}

type Comparator struct{}

func NewComparator() *Comparator {
	return &Comparator{}
}

func (c *Comparator) CompareDoctorWithOCR(doc *entities.Doctor, licenses []entities.DoctorLicense, quals []entities.DoctorQualification, ocrFields ocr.ExtractedFields) *ComparisonResult {
	doctorFullName := strings.TrimSpace(doc.FirstName + " " + doc.LastName)
	
	// 1. Name Comparison (Fuzzy)
	nameScore := 0.0
	if ocrFields.DoctorName != "" {
		nameScore = CalculateNameMatchPercentage(doctorFullName, ocrFields.DoctorName)
	}

	// 2. Registration Number Comparison (Exact normalized)
	regNoMatch := false
	subRegNo := ""
	if len(licenses) > 0 {
		subRegNo = licenses[0].RegistrationNumber
	}
	if subRegNo != "" && ocrFields.RegistrationNumber != "" {
		regNoMatch = strings.EqualFold(strings.TrimSpace(subRegNo), strings.TrimSpace(ocrFields.RegistrationNumber))
	}

	// 3. Council Comparison
	councilMatch := false
	subCouncil := ""
	if len(licenses) > 0 {
		subCouncil = licenses[0].RegistrationCouncil
	}
	if subCouncil != "" && ocrFields.RegistrationCouncil != "" {
		councilMatch = strings.Contains(strings.ToLower(ocrFields.RegistrationCouncil), strings.ToLower(subCouncil)) ||
			strings.Contains(strings.ToLower(subCouncil), strings.ToLower(ocrFields.RegistrationCouncil))
	}

	// 4. Degree Comparison
	degreeMatch := false
	subDegree := ""
	if len(quals) > 0 {
		subDegree = quals[0].Degree
	}
	if subDegree != "" && ocrFields.Degree != "" {
		degreeMatch = strings.EqualFold(strings.TrimSpace(subDegree), strings.TrimSpace(ocrFields.Degree))
	}

	// 5. Composite Score Calculation
	weightsSum := 0.0
	totalWeight := 0.0

	// Name weight: 40%
	weightsSum += (nameScore / 100.0) * 40.0
	totalWeight += 40.0

	// Reg No weight: 35%
	if regNoMatch {
		weightsSum += 35.0
	}
	totalWeight += 35.0

	// Council weight: 15%
	if councilMatch {
		weightsSum += 15.0
	}
	totalWeight += 15.0

	// Degree weight: 10%
	if degreeMatch {
		weightsSum += 10.0
	}
	totalWeight += 10.0

	overallScore := (weightsSum / totalWeight) * 100.0

	fieldComparisons := []FieldComparison{
		{
			FieldName:      "Doctor Name",
			SubmittedValue: doctorFullName,
			ExtractedValue: ocrFields.DoctorName,
			MatchScore:     nameScore,
			IsMatch:        nameScore >= 85.0,
		},
		{
			FieldName:      "Registration Number",
			SubmittedValue: subRegNo,
			ExtractedValue: ocrFields.RegistrationNumber,
			MatchScore:     boolToScore(regNoMatch),
			IsMatch:        regNoMatch,
		},
		{
			FieldName:      "Registration Council",
			SubmittedValue: subCouncil,
			ExtractedValue: ocrFields.RegistrationCouncil,
			MatchScore:     boolToScore(councilMatch),
			IsMatch:        councilMatch,
		},
		{
			FieldName:      "Degree",
			SubmittedValue: subDegree,
			ExtractedValue: ocrFields.Degree,
			MatchScore:     boolToScore(degreeMatch),
			IsMatch:        degreeMatch,
		},
	}

	return &ComparisonResult{
		NameMatchScore:    nameScore,
		RegNoMatch:        regNoMatch,
		CouncilMatch:      councilMatch,
		DegreeMatch:       degreeMatch,
		OverallMatchScore: overallScore,
		FieldComparisons:  fieldComparisons,
	}
}

func boolToScore(b bool) float64 {
	if b {
		return 100.0
	}
	return 0.0
}
