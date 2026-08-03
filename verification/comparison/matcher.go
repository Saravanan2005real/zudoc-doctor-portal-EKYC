package comparison

import (
	"math"
	"regexp"
	"strings"
)

var prefixRegex = regexp.MustCompile(`(?i)\b(dr|dr\.|doctor|prof|prof\.|mr|mrs|ms)\b`)
var nonAlphaNumRegex = regexp.MustCompile(`[^a-z0-9\s]`)
var multiSpaceRegex = regexp.MustCompile(`\s+`)

func NormalizeName(name string) string {
	lower := strings.ToLower(name)
	strippedPrefix := prefixRegex.ReplaceAllString(lower, "")
	cleanAlpha := nonAlphaNumRegex.ReplaceAllString(strippedPrefix, " ")
	singleSpace := multiSpaceRegex.ReplaceAllString(cleanAlpha, " ")
	return strings.TrimSpace(singleSpace)
}

func JaroWinklerSimilarity(s1, s2 string) float64 {
	n1 := NormalizeName(s1)
	n2 := NormalizeName(s2)

	if n1 == n2 {
		return 1.0
	}
	if len(n1) == 0 || len(n2) == 0 {
		return 0.0
	}

	matchDistance := int(math.Floor(math.Max(float64(len(n1)), float64(len(n2)))/2.0)) - 1
	if matchDistance < 0 {
		matchDistance = 0
	}

	s1Matches := make([]bool, len(n1))
	s2Matches := make([]bool, len(n2))

	matches := 0
	for i := 0; i < len(n1); i++ {
		start := int(math.Max(0, float64(i-matchDistance)))
		end := int(math.Min(float64(i+matchDistance+1), float64(len(n2))))

		for j := start; j < end; j++ {
			if s2Matches[j] {
				continue
			}
			if n1[i] != n2[j] {
				continue
			}
			s1Matches[i] = true
			s2Matches[j] = true
			matches++
			break
		}
	}

	if matches == 0 {
		return 0.0
	}

	t := 0.0
	k := 0
	for i := 0; i < len(n1); i++ {
		if !s1Matches[i] {
			continue
		}
		for !s2Matches[k] {
			k++
		}
		if n1[i] != n2[k] {
			t += 0.5
		}
		k++
	}

	m := float64(matches)
	jaro := (m/float64(len(n1)) + m/float64(len(n2)) + (m-t)/m) / 3.0

	// Winkler scaling factor
	prefixLength := 0
	maxPrefix := int(math.Min(4, math.Min(float64(len(n1)), float64(len(n2)))))
	for i := 0; i < maxPrefix; i++ {
		if n1[i] == n2[i] {
			prefixLength++
		} else {
			break
		}
	}

	return jaro + float64(prefixLength)*0.1*(1.0-jaro)
}

func CalculateNameMatchPercentage(name1, name2 string) float64 {
	similarity := JaroWinklerSimilarity(name1, name2)
	return math.Round(similarity*10000.0) / 100.0
}
