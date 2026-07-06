package app

import (
	"database/sql"
	"net/http"

	"github.com/EkaaPrawiraa/companionshipchatbot/configs"
	agenticClient "github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/client/agentic"
	elevenlabsClient "github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/client/elevenlabs"
	chatHandler "github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/delivery/http/handler"
	chatRoute "github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/delivery/http/route"
	chatPostgres "github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/repository/postgres"
	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/usecase"
)

func Handler(db *sql.DB, cfg configs.Config) http.Handler {
	uc := usecase.NewChatUsecase(
		chatPostgres.NewSessionRepository(db),
		chatPostgres.NewMessageRepository(db),
		chatPostgres.NewMoodRepository(db),
		agenticClient.New(cfg.AgenticBaseURL, cfg.AgenticPrivateKey),
		elevenlabsClient.New(cfg.ElevenLabsAPIKey),
	)
	handler := chatHandler.NewChatHandler(uc)
	mux := http.NewServeMux()
	chatRoute.Register(mux, handler)
	return mux
}
