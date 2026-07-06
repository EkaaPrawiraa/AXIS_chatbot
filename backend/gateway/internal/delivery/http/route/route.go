package route

import (
	"net/http"

	"github.com/EkaaPrawiraa/companionshipchatbot/gateway/internal/client/agentic"
	"github.com/EkaaPrawiraa/companionshipchatbot/gateway/internal/client/service"
	gatewayHandler "github.com/EkaaPrawiraa/companionshipchatbot/gateway/internal/delivery/http/handler"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/middleware"
)

// Register mounts all gateway routes and route-level limits.
func Register(
	mux *http.ServeMux,
	health *gatewayHandler.HealthHandler,
	agenticProxy *agentic.Proxy,
	chatProxy *service.Proxy,
	memoryProxy *service.Proxy,
	authProxy *service.Proxy,
	rl *middleware.RateLimiter,
	publicAgenticProxy bool,
) {
	mux.HandleFunc("GET /health", health.Health)

	mux.Handle("/api/auth/", rl.AuthLimit(authProxy))
	mux.Handle("/api/profile", authProxy)
	mux.Handle("/api/profile/", authProxy)
	mux.Handle("/api/account/", rl.AuthLimit(authProxy))

	mux.Handle("/api/conversations", rl.SessionLimit(chatProxy))
	mux.Handle("/api/conversations/", rl.TurnLimit(chatProxy))
	mux.Handle("/api/voice/options", chatProxy)
	mux.Handle("/api/voice/synthesize", chatProxy)
	mux.Handle("/api/voice/transcribe", chatProxy)
	mux.Handle("/api/mood", chatProxy)
	mux.Handle("/api/mood/", chatProxy)

	mux.Handle("/api/memories", memoryProxy)
	mux.Handle("/api/memories/", memoryProxy)

	if publicAgenticProxy {
		mux.Handle("/agentic/", http.StripPrefix("", agenticProxy))
	}
}
