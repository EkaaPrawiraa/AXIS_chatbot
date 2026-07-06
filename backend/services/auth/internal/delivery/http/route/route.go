package route

import (
	"net/http"

	authHandler "github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/delivery/http/handler"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/health"
)

func Register(mux *http.ServeMux, handler *authHandler.AuthHandler) {
	mux.HandleFunc("GET /health", health.Handler)
	mux.HandleFunc("POST /auth/register", handler.Register)
	mux.HandleFunc("POST /auth/login", handler.Login)
	mux.HandleFunc("POST /auth/google", handler.GoogleLogin)
	mux.HandleFunc("POST /auth/refresh", handler.Refresh)
	mux.HandleFunc("POST /auth/logout", handler.Logout)
	mux.HandleFunc("GET /auth/session", handler.CurrentSession)
	mux.HandleFunc("GET /profile", handler.GetProfile)
	mux.HandleFunc("PUT /profile", handler.UpdateProfile)
	mux.HandleFunc("GET /profile/personality-insights", handler.PersonalityInsights)
	mux.HandleFunc("POST /profile/generate-insights", handler.PersonalityInsights)
	mux.HandleFunc("POST /account/delete", handler.DeleteAccount)
}
