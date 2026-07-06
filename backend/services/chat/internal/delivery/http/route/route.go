package route

import (
	"net/http"

	chatHandler "github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/delivery/http/handler"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/health"
)

func Register(mux *http.ServeMux, handler *chatHandler.ChatHandler) {
	mux.HandleFunc("GET /health", health.Handler)
	mux.HandleFunc("GET /conversations", handler.ListConversations)
	mux.HandleFunc("POST /conversations", handler.StartSession)
	mux.HandleFunc("PATCH /conversations/{conversation_id}", handler.UpdateConversation)
	mux.HandleFunc("DELETE /conversations/{conversation_id}", handler.DeleteConversation)
	mux.HandleFunc("GET /conversations/{conversation_id}/messages", handler.ListMessages)
	mux.HandleFunc("POST /conversations/{conversation_id}/messages/send", handler.SendMessage)
	mux.HandleFunc("POST /conversations/{conversation_id}/messages/{message_id}/regenerate", handler.RegenerateMessage)
	mux.HandleFunc("POST /conversations/{conversation_id}/messages/stream", handler.StreamMessage)
	mux.HandleFunc("GET /voice/options", handler.ListVoiceOptions)
	mux.HandleFunc("POST /voice/synthesize", handler.SynthesizeSpeech)
	mux.HandleFunc("POST /voice/transcribe", handler.TranscribeSpeech)

	mux.HandleFunc("POST /mood", handler.SubmitMood)
	mux.HandleFunc("GET /mood/trend", handler.MoodTrend)

	mux.HandleFunc("POST /sessions", handler.StartSession)
	mux.HandleFunc("POST /sessions/{session_id}/messages", handler.SendMessage)
}
