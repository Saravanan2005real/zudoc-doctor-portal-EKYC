package council

import (
	"context"
	"strings"
)

type NMCRegistryAdapter struct{}

func NewNMCRegistryAdapter() *NMCRegistryAdapter {
	return &NMCRegistryAdapter{}
}

func (a *NMCRegistryAdapter) Verify(ctx context.Context, registrationNumber string, council string) (*CouncilVerificationResult, error) {
	cleanReg := strings.TrimSpace(registrationNumber)
	
	// Simulated National Medical Commission (NMC) India / State Council Registry Adapter
	if cleanReg == "" {
		return &CouncilVerificationResult{
			IsVerified:         false,
			Status:             "NOT_FOUND",
			VerificationSource: "NMC_NATIONAL_REGISTER",
			Remarks:            "Empty registration number provided",
		}, nil
	}

	// Mock simulation check for invalid/suspended registration test cases
	if strings.HasSuffix(cleanReg, "999") {
		return &CouncilVerificationResult{
			IsVerified:         false,
			RegistrationNumber: cleanReg,
			CouncilName:        council,
			Status:             "SUSPENDED",
			VerificationSource: "NMC_NATIONAL_REGISTER",
			Remarks:            "Registration is suspended or blacklisted by Medical Council",
		}, nil
	}

	return &CouncilVerificationResult{
		IsVerified:         true,
		DoctorName:         "Dr. Rahul Kumar",
		RegistrationNumber: cleanReg,
		CouncilName:        council,
		RegistrationYear:   2021,
		Status:             "ACTIVE",
		VerificationSource: "NMC_NATIONAL_REGISTER",
		Remarks:            "Verified in National Medical Register",
	}, nil
}

func (a *NMCRegistryAdapter) GetProviderName() string {
	return "NMC_NATIONAL_REGISTER_ADAPTER"
}
