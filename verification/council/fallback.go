package council

import "context"

type ManualFallbackProvider struct{}

func NewManualFallbackProvider() *ManualFallbackProvider {
	return &ManualFallbackProvider{}
}

func (p *ManualFallbackProvider) Verify(ctx context.Context, registrationNumber string, council string) (*CouncilVerificationResult, error) {
	return &CouncilVerificationResult{
		IsVerified:         false,
		RegistrationNumber: registrationNumber,
		CouncilName:        council,
		Status:             "MANUAL_REVIEW_REQUIRED",
		VerificationSource: "MANUAL_FALLBACK",
		Remarks:            "Official online API unavailable for council. Marked for manual review.",
	}, nil
}

func (p *ManualFallbackProvider) GetProviderName() string {
	return "MANUAL_FALLBACK_PROVIDER"
}
