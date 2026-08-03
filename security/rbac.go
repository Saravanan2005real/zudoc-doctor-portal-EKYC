package security

import (
	"context"
	"net/http"

	"doctor-service/entities"
)

type contextKey string

const AdminRoleContextKey contextKey = "admin_role"
const AdminIDContextKey contextKey = "admin_id"

func RequireRole(allowedRoles ...entities.AdminRole) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			roleVal := r.Context().Value(AdminRoleContextKey)
			if roleVal == nil {
				// Check header fallback for local dev
				roleHeader := r.Header.Get("X-Admin-Role")
				if roleHeader != "" {
					roleVal = entities.AdminRole(roleHeader)
				}
			}

			if roleVal == nil {
				http.Error(w, `{"error":"Unauthorized: Admin authentication token required"}`, http.StatusUnauthorized)
				return
			}

			userRole := roleVal.(entities.AdminRole)
			authorized := false

			for _, role := range allowedRoles {
				if userRole == role || userRole == entities.AdminRoleSuperAdmin {
					authorized = true
					break
				}
			}

			if !authorized {
				http.Error(w, `{"error":"Forbidden: Insufficient administrative privileges to perform this action"}`, http.StatusForbidden)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func WithAdminContext(ctx context.Context, adminID string, role entities.AdminRole) context.Context {
	ctx = context.WithValue(ctx, AdminIDContextKey, adminID)
	return context.WithValue(ctx, AdminRoleContextKey, role)
}
