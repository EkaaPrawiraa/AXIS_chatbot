package main

import (
	"context"
	"log/slog"
	"net/http"

	"github.com/EkaaPrawiraa/companionshipchatbot/configs"
	memoryApp "github.com/EkaaPrawiraa/companionshipchatbot/services/memory/app"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/database"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/logger"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/middleware"
)

func main() {
	slog.SetDefault(logger.New())
	cfg := configs.Load()
	driver, err := database.NewNeo4jDriver(cfg.Neo4j)
	if err != nil {
		slog.Error("open neo4j", "error", err)
		return
	}
	defer driver.Close(context.Background())

	addr := ":" + cfg.HTTPPortMemory
	slog.Info("memory service listening", "addr", addr)
	if err := http.ListenAndServe(addr, middleware.RequestLogger(memoryApp.Handler(driver, cfg))); err != nil {
		slog.Error("memory service stopped", "error", err)
	}
}
