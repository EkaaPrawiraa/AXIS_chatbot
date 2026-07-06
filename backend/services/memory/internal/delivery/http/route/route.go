package route

import (
	"net/http"

	memoryHandler "github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/delivery/http/handler"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/health"
)

func Register(mux *http.ServeMux, handler *memoryHandler.MemoryHandler) {
	mux.HandleFunc("GET /health", health.Handler)
	mux.HandleFunc("GET /memories", handler.ListMemories)
	mux.HandleFunc("POST /memories", handler.CreateMemory)
	mux.HandleFunc("GET /memories/{memory_id}", handler.GetMemory)
	mux.HandleFunc("PATCH /memories/{memory_id}", handler.UpdateMemory)
	mux.HandleFunc("DELETE /memories/{memory_id}", handler.DeleteMemory)
	mux.HandleFunc("GET /memories/kg", handler.ListMemoryNodes)
	mux.HandleFunc("GET /memories/kg/relations", handler.ListMemoryRelations)
	mux.HandleFunc("DELETE /memories/kg/reset", handler.ResetUserMemory)
	mux.HandleFunc("DELETE /memories/kg/purge-account", handler.PurgeUserAccount)
	mux.HandleFunc("PATCH /memories/kg/{node_type}/{node_id}", handler.UpdateMemoryNode)
	mux.HandleFunc("DELETE /memories/kg/{node_type}/{node_id}", handler.DeleteMemoryNode)

	mux.HandleFunc("PUT /users", handler.UpsertUser)
	mux.HandleFunc("POST /sessions", handler.OpenSession)
	mux.HandleFunc("POST /assessments", handler.WriteAssessment)
	mux.HandleFunc("PUT /topics", handler.UpsertTopic)
	mux.HandleFunc("GET /users/{user_id}/escalation-policy", handler.EscalationPolicy)
	mux.HandleFunc("POST /users/{user_id}/archive-memory", handler.ArchiveUserMemory)
}
