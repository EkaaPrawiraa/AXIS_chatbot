package main

import (
	"log/slog"
	"net/http"

	"github.com/EkaaPrawiraa/companionshipchatbot/configs"
	gatewayApp "github.com/EkaaPrawiraa/companionshipchatbot/gateway/app"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/logger"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/middleware"
)

func main() {
	slog.SetDefault(logger.New())
	cfg := configs.Load()

	addr := ":" + cfg.HTTPPortMain
	slog.Info("gateway listening", "addr", addr)
	if err := http.ListenAndServe(addr, middleware.RequestLogger(gatewayApp.Handler(cfg))); err != nil {
		slog.Error("gateway stopped", "error", err)
	}
}
