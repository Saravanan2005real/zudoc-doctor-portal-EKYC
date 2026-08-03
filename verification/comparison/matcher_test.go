package comparison_test

import (
	"testing"

	"doctor-service/verification/comparison"
)

func TestNameNormalization(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Dr. Rahul Kumar", "rahul kumar"},
		{"Dr.  Rahul   Kumar", "rahul kumar"},
		{"Doctor Rahul Kumar, M.D.", "rahul kumar m d"},
		{"Prof. Rahul Kumar", "rahul kumar"},
	}

	for _, tt := range tests {
		actual := comparison.NormalizeName(tt.input)
		if actual != tt.expected {
			t.Errorf("NormalizeName('%s') = '%s', expected '%s'", tt.input, actual, tt.expected)
		}
	}
}

func TestJaroWinklerFuzzyMatching(t *testing.T) {
	tests := []struct {
		name1    string
		name2    string
		minScore float64
	}{
		{"Dr. Rahul Kumar", "Rahul Kumar", 100.0},
		{"Dr. Rahul Kumar", "Rahul K.", 88.0},
		{"Rahul Kumar", "rahul kumar", 100.0},
		{"Rahul Kumar", "Sunil Sharma", 0.0},
	}

	for _, tt := range tests {
		score := comparison.CalculateNameMatchPercentage(tt.name1, tt.name2)
		if score < tt.minScore {
			t.Errorf("CalculateNameMatchPercentage('%s', '%s') = %.2f, expected at least %.2f", tt.name1, tt.name2, score, tt.minScore)
		}
	}
}
