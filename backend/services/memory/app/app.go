package app

import (
	"net/http"

	"github.com/EkaaPrawiraa/companionshipchatbot/configs"
	agenticClient "github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/client/agentic"
	memoryHandler "github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/delivery/http/handler"
	memoryRoute "github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/delivery/http/route"
	neo4jRepo "github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/repository/neo4j"
	"github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/usecase"
	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

func Handler(driver neo4j.DriverWithContext, cfg configs.Config) http.Handler {
	uc := usecase.NewMemoryUsecaseWithAgentic(
		neo4jRepo.NewGraphRepository(driver),
		agenticClient.New(cfg.AgenticBaseURL, cfg.AgenticPrivateKey),
	)
	handler := memoryHandler.NewMemoryHandler(uc)
	mux := http.NewServeMux()
	memoryRoute.Register(mux, handler)
	return mux
}
