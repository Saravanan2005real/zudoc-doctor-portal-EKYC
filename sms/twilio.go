package sms

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type TwilioProvider struct {
	AccountSID string
	AuthToken  string
	FromNumber string
	HTTPClient *http.Client
}

func NewTwilioProvider(accountSID, authToken, fromNumber string) *TwilioProvider {
	return &TwilioProvider{
		AccountSID: accountSID,
		AuthToken:  authToken,
		FromNumber: fromNumber,
		HTTPClient: &http.Client{Timeout: 10 * time.Second},
	}
}

func (t *TwilioProvider) SendOTP(ctx context.Context, payload SMSPayload) error {
	if t.AccountSID == "" || t.AuthToken == "" {
		return fmt.Errorf("twilio credentials missing")
	}

	endpoint := fmt.Sprintf("https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json", t.AccountSID)

	message := fmt.Sprintf("Your verification OTP for Doctor Verification Portal is: %s. Valid for 5 minutes.", payload.OTP)

	data := url.Values{}
	data.Set("To", payload.Mobile)
	data.Set("From", t.FromNumber)
	data.Set("Body", message)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, endpoint, strings.NewReader(data.Encode()))
	if err != nil {
		return err
	}

	req.SetBasicAuth(t.AccountSID, t.AuthToken)
	req.Header.Add("Content-Type", "application/x-www-form-urlencoded")

	resp, err := t.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return fmt.Errorf("twilio API error: status code %d", resp.StatusCode)
	}

	return nil
}

func (t *TwilioProvider) GetProviderName() string {
	return "TWILIO"
}
