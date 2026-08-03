package controllers

import (
	"encoding/json"
	"net/http"

	"doctor-service/dto"
	"doctor-service/services"
)

type AuthController struct {
	authService services.AuthService
}

func NewAuthController(authService services.AuthService) *AuthController {
	return &AuthController{
		authService: authService,
	}
}

func (c *AuthController) Register(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req dto.RegisterRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid request payload"})
		return
	}

	resp, err := c.authService.Register(r.Context(), req)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	c.respondJSON(w, http.StatusCreated, resp)
}

func (c *AuthController) VerifyOTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req dto.VerifyOTPRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid request payload"})
		return
	}

	resp, err := c.authService.VerifyOTP(r.Context(), req)
	if err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": err.Error()})
		return
	}

	c.respondJSON(w, http.StatusOK, resp)
}

func (c *AuthController) Login(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req dto.LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		c.respondJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid request payload"})
		return
	}

	resp, err := c.authService.Login(r.Context(), req)
	if err != nil {
		c.respondJSON(w, http.StatusUnauthorized, map[string]string{"error": err.Error()})
		return
	}

	c.respondJSON(w, http.StatusOK, resp)
}

func (c *AuthController) respondJSON(w http.ResponseWriter, status int, payload interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
