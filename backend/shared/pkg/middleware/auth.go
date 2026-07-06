package middleware

import (
	"context"
	"net/http"
	"strings"

	axisauth "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/auth"
)

type contextKey string

const (
	authUserIDKey             contextKey = "axis.auth.user_id"
	AuthenticatedUserIDHeader            = "X-Authenticated-User-Id"
)

func AuthRequired(secret string, publicPrefixes ...string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if isPublicPath(r.URL.Path, publicPrefixes) || r.Method == http.MethodOptions {
				next.ServeHTTP(w, r)
				return
			}
			token := axisauth.BearerToken(r.Header.Get("Authorization"))
			if token == "" {
				if cookie, err := r.Cookie(axisauth.DefaultCookieName); err == nil {
					token = strings.TrimSpace(cookie.Value)
				}
			}
			claims, err := axisauth.Verify(token, secret)
			if err != nil {
				http.Error(w, `{"success":false,"error":"unauthorized","message":"unauthorized"}`, http.StatusUnauthorized)
				return
			}
			req := r.Clone(context.WithValue(r.Context(), authUserIDKey, claims.Subject))
			req.Header.Set(AuthenticatedUserIDHeader, claims.Subject)
			next.ServeHTTP(w, req)
		})
	}
}

func AuthenticatedUserID(r *http.Request) string {
	if value, ok := r.Context().Value(authUserIDKey).(string); ok {
		return value
	}
	return strings.TrimSpace(r.Header.Get(AuthenticatedUserIDHeader))
}

func isPublicPath(path string, prefixes []string) bool {
	for _, prefix := range prefixes {
		if prefix != "" && strings.HasPrefix(path, prefix) {
			return true
		}
	}
	return false
}
