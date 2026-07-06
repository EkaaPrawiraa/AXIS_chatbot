package main

import (
	"log/slog"
	"net/http"

	"github.com/EkaaPrawiraa/companionshipchatbot/configs"
	chatApp "github.com/EkaaPrawiraa/companionshipchatbot/services/chat/app"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/database"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/logger"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/middleware"
	_ "github.com/lib/pq"
)

func main() {
	slog.SetDefault(logger.New())
	cfg := configs.Load()

	db, err := database.OpenPostgres(cfg.Postgres)
	if err != nil {
		slog.Error("open postgres", "error", err)
		return
	}
	defer db.Close()

	addr := ":" + cfg.HTTPPortChat
	slog.Info("chat service listening", "addr", addr)
	if err := http.ListenAndServe(addr, middleware.RequestLogger(chatApp.Handler(db, cfg))); err != nil {
		slog.Error("chat service stopped", "error", err)
	}
}
