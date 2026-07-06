package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/configs"
	gatewayApp "github.com/EkaaPrawiraa/companionshipchatbot/gateway/app"
	authApp "github.com/EkaaPrawiraa/companionshipchatbot/services/auth/app"
	chatApp "github.com/EkaaPrawiraa/companionshipchatbot/services/chat/app"
	memoryApp "github.com/EkaaPrawiraa/companionshipchatbot/services/memory/app"
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

	neo4jDriver, err := database.NewNeo4jDriver(cfg.Neo4j)
	if err != nil {
		slog.Error("open neo4j", "error", err)
		return
	}
	defer neo4jDriver.Close(context.Background())

	servers := []namedServer{
		newServer("auth", cfg.HTTPPortAuth, authApp.Handler(db, cfg)),
		newServer("chat", cfg.HTTPPortChat, chatApp.Handler(db, cfg)),
		newServer("memory", cfg.HTTPPortMemory, memoryApp.Handler(neo4jDriver, cfg)),
		newServer("gateway", cfg.HTTPPortMain, gatewayApp.Handler(cfg)),
	}

	errCh := make(chan error, len(servers))
	for _, srv := range servers {
		server := srv
		go func() {
			slog.Info("backend service listening", "name", server.name, "addr", server.http.Addr)
			if err := server.http.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
				errCh <- err
			}
		}()
	}

	stopCh := make(chan os.Signal, 1)
	signal.Notify(stopCh, os.Interrupt, syscall.SIGTERM)

	select {
	case sig := <-stopCh:
		slog.Info("shutdown requested", "signal", sig.String())
	case err := <-errCh:
		slog.Error("backend service stopped", "error", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	for _, srv := range servers {
		if err := srv.http.Shutdown(ctx); err != nil {
			slog.Error("shutdown service", "name", srv.name, "error", err)
		}
	}
}

type namedServer struct {
	name string
	http *http.Server
}

func newServer(name string, port string, handler http.Handler) namedServer {
	return namedServer{
		name: name,
		http: &http.Server{
			Addr:              ":" + port,
			Handler:           middleware.RequestLogger(handler),
			ReadHeaderTimeout: 10 * time.Second,
			IdleTimeout:       60 * time.Second,
			ErrorLog:          slog.NewLogLogger(slog.Default().Handler(), slog.LevelError),
		},
	}
}
