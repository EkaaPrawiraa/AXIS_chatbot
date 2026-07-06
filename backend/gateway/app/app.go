package app

import (
	"log/slog"
	"net/http"

	"github.com/EkaaPrawiraa/companionshipchatbot/configs"
	"github.com/EkaaPrawiraa/companionshipchatbot/gateway/internal/client/agentic"
	"github.com/EkaaPrawiraa/companionshipchatbot/gateway/internal/client/service"
	gatewayHandler "github.com/EkaaPrawiraa/companionshipchatbot/gateway/internal/delivery/http/handler"
	gatewayRoute "github.com/EkaaPrawiraa/companionshipchatbot/gateway/internal/delivery/http/route"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/database"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/middleware"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/monitoring"
)

// Handler builds the gateway HTTP handler and shared middleware.
func Handler(cfg configs.Config) http.Handler {
	mux := http.NewServeMux()
	mux.Handle("/metrics", monitoring.Handler())

	redisClient := database.NewRedisClient(cfg.Redis)
	rlCfg := middleware.DefaultRateLimitConfig()
	rl := middleware.NewRateLimiter(redisClient, rlCfg)
	slog.Info("rate limiter initialized",
		"redis_addr", cfg.Redis.Addr,
		"max_turns_per_hour", rlCfg.MaxTurnsPerHour,
		"max_sessions_per_day", rlCfg.MaxSessionsPerDay,
	)

	gatewayRoute.Register(
		mux,
		gatewayHandler.NewHealthHandler(),
		agentic.NewProxy(cfg.AgenticBaseURL, cfg.AgenticPrivateKey),
		service.NewProxy(cfg.ChatServiceURL, "/api"),
		service.NewProxy(cfg.MemoryServiceURL, "/api"),
		service.NewProxy(cfg.AuthServiceURL, "/api"),
		rl,
		cfg.PublicAgenticProxy,
	)

	handler := http.Handler(mux)
	handler = middleware.AuthRequired(
		cfg.JWTSecret,
		"/health",
		"/api/auth/login",
		"/api/auth/register",
		"/api/auth/google",
		"/api/auth/refresh",
		"/api/auth/logout",
	)(handler)
	handler = middleware.CSRF(
		"/health",
		"/api/auth/login",
		"/api/auth/register",
		"/api/auth/google",
		"/api/auth/refresh",
		"/api/auth/logout",
	)(handler)
	handler = middleware.SecurityHeaders(handler)
	handler = middleware.CORS(handler, cfg.CORSAllowedOrigins)
	return middleware.RequestLogger(handler)
}
