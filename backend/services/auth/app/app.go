package app

import (
	"database/sql"
	"net/http"

	"github.com/EkaaPrawiraa/companionshipchatbot/configs"
	memoryClient "github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/client/memory"
	authHandler "github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/delivery/http/handler"
	authRoute "github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/delivery/http/route"
	authPostgres "github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/repository/postgres"
	"github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/usecase"
)

func Handler(db *sql.DB, cfg configs.Config) http.Handler {
	uc := usecase.NewAuthUsecase(
		authPostgres.NewUserRepository(db),
		memoryClient.New(cfg.MemoryServiceURL),
		nil, // defaults to the real Google JWKS verifier
	)
	handler := authHandler.NewAuthHandler(uc)
	mux := http.NewServeMux()
	authRoute.Register(mux, handler)
	return mux
}
