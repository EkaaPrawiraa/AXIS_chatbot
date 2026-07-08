package middleware

import (
	"net/http"
	"strings"
)

func CORS(next http.Handler, allowedOrigins []string) http.Handler {
	allowed := map[string]bool{}
	allowAny := false
	for _, origin := range allowedOrigins {
		origin = strings.TrimSpace(origin)
		if origin == "" {
			continue
		}
		if origin == "*" {
			allowAny = true
			continue
		}
		allowed[origin] = true
	}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		if origin != "" && (allowAny || allowed[origin]) {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Vary", "Origin")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Authorization, Content-Type, X-Requested-With, X-CSRF-Token")
			w.Header().Set("Access-Control-Allow-Credentials", "true")
			// headers ngga visible buat js frontend
			w.Header().Set(
				"Access-Control-Expose-Headers",
				"X-RateLimit-Limit-Turns, X-RateLimit-Remaining-Turns, "+
					"X-RateLimit-Limit-MessagesDaily, X-RateLimit-Remaining-MessagesDaily, "+
					"X-RateLimit-Limit-Sessions, X-RateLimit-Remaining-Sessions",
			)
		}

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}

		next.ServeHTTP(w, r)
	})
}
