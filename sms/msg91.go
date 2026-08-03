package sms

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type MSG91Provider struct {
	AuthKey    string
	TemplateID string
	SenderID   string
	HTTPClient *http.Client
}

func NewMSG91Provider(authKey, templateID, senderID string) *MSG91Provider {
	return &MSG91Provider{
		AuthKey:    authKey,
		TemplateID: templateID,
		SenderID:   senderID,
		HTTPClient: &http.Client{Timeout: 10 * time.Second},
	}
}

func (p *MSG91Provider) SendOTP(ctx context.Context, payload SMSPayload) error {
	if p.AuthKey == "" {
		return fmt.Errorf("msg91 auth key missing")
	}

	url := fmt.Sprintf("https://control.msg91.com/api/v5/otp?template_id=%s&mobile=%s&authkey=%s", p.TemplateID, payload.Mobile, p.AuthKey)
	
	reqBody, err := json.Marshal(map[string]string{
		"OTP": payload.OTP,
	})
	if err != nil {
		return err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewBuffer(reqBody))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := p.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return fmt.Errorf("msg91 API error: status code %d", resp.StatusCode)
	}

	return nil
}

func (p *MSG91Provider) GetProviderName() string {
	return "MSG91"
}
