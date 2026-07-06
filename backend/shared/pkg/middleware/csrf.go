package middleware

import (
	"crypto/subtle"
	"net/http"
	"strings"

	axisauth "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/auth"
)

func CSRF(publicPrefixes ...string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if isPublicPath(r.URL.Path, publicPrefixes) || r.Method == http.MethodOptions || isSafeMethod(r.Method) {
				next.ServeHTTP(w, r)
				return
			}
			if axisauth.BearerToken(r.Header.Get("Authorization")) != "" {
				next.ServeHTTP(w, r)
				return
			}
			sessionCookie, sessionErr := r.Cookie(axisauth.DefaultCookieName)
			if sessionErr != nil || strings.TrimSpace(sessionCookie.Value) == "" {
				next.ServeHTTP(w, r)
				return
			}
			csrfCookie, csrfErr := r.Cookie(axisauth.CSRFCookieName)
			csrfHeader := strings.TrimSpace(r.Header.Get("X-CSRF-Token"))
			if csrfErr != nil || csrfHeader == "" || subtle.ConstantTimeCompare([]byte(csrfCookie.Value), []byte(csrfHeader)) != 1 {
				http.Error(w, `{"success":false,"error":"forbidden","message":"invalid csrf token"}`, http.StatusForbidden)
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

func isSafeMethod(method string) bool {
	switch method {
	case http.MethodGet, http.MethodHead, http.MethodOptions:
		return true
	default:
		return false
	}
}
