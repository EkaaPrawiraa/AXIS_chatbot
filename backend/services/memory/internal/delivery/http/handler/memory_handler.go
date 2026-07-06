package handler

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/domain/entity"
	"github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/usecase"
	apperrors "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/errors"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/middleware"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/response"
)

type MemoryHandler struct {
	uc *usecase.MemoryUsecase
}

func NewMemoryHandler(uc *usecase.MemoryUsecase) *MemoryHandler {
	return &MemoryHandler{uc: uc}
}

type createMemoryRequest struct {
	UserID                string   `json:"userId"`
	Title                 string   `json:"title"`
	Content               string   `json:"content"`
	Tags                  []string `json:"tags"`
	RelatedConversationID string   `json:"relatedConversationId"`
	Source                string   `json:"source"`
	Emotion               string   `json:"emotion"`
}

type updateMemoryRequest struct {
	Title    *string  `json:"title"`
	Content  *string  `json:"content"`
	Tags     []string `json:"tags"`
	IsPinned *bool    `json:"isPinned"`
}

type updateMemoryNodeRequest struct {
	UserID     string         `json:"userId"`
	Properties map[string]any `json:"properties"`
}

func (h *MemoryHandler) UpsertUser(w http.ResponseWriter, r *http.Request) {
	var req entity.User
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if err := h.uc.UpsertUser(r.Context(), req); err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, map[string]string{"status": "ok"})
}

func (h *MemoryHandler) OpenSession(w http.ResponseWriter, r *http.Request) {
	var req entity.Session
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if err := h.uc.OpenSession(r.Context(), req); err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, map[string]string{"status": "ok"})
}

func (h *MemoryHandler) WriteAssessment(w http.ResponseWriter, r *http.Request) {
	var req entity.Assessment
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if err := h.uc.WriteAssessment(r.Context(), req); err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, map[string]string{"status": "ok"})
}

func (h *MemoryHandler) UpsertTopic(w http.ResponseWriter, r *http.Request) {
	var req entity.Topic
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if err := h.uc.UpsertTopic(r.Context(), req); err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, map[string]string{"status": "ok"})
}

func (h *MemoryHandler) ListMemories(w http.ResponseWriter, r *http.Request) {
	limit, offset := pagination(r, 50)
	out, err := h.uc.ListMemories(r.Context(), requestUserID(r, r.URL.Query().Get("userId")), usecase.MemoryFilter{
		Tags:        splitCSV(r.URL.Query().Get("tags")),
		SearchQuery: firstNonEmpty(r.URL.Query().Get("searchQuery"), r.URL.Query().Get("q")),
		Limit:       limit,
		Offset:      offset,
	})
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *MemoryHandler) GetMemory(w http.ResponseWriter, r *http.Request) {
	userID := requestUserID(r, r.URL.Query().Get("userId"))
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	if queryUserID := r.URL.Query().Get("userId"); queryUserID != "" && queryUserID != userID {
		response.FromError(w, apperrors.Forbidden("cannot read another user's memory"))
		return
	}
	out, err := h.uc.GetMemory(r.Context(), userID, r.PathValue("memory_id"))
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *MemoryHandler) CreateMemory(w http.ResponseWriter, r *http.Request) {
	var req createMemoryRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	userID := requestUserID(r, req.UserID)
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	if req.UserID != "" && req.UserID != userID {
		response.FromError(w, apperrors.Forbidden("cannot create memory for another user"))
		return
	}
	out, err := h.uc.CreateMemory(r.Context(), usecase.CreateMemoryInput{
		UserID:                userID,
		Title:                 req.Title,
		Content:               req.Content,
		Tags:                  req.Tags,
		RelatedConversationID: req.RelatedConversationID,
		Source:                req.Source,
		Emotion:               req.Emotion,
	})
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.Created(w, out)
}

func (h *MemoryHandler) UpdateMemory(w http.ResponseWriter, r *http.Request) {
	var req updateMemoryRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	userID := requestUserID(r, r.URL.Query().Get("userId"))
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	if queryUserID := r.URL.Query().Get("userId"); queryUserID != "" && queryUserID != userID {
		response.FromError(w, apperrors.Forbidden("cannot update another user's memory"))
		return
	}
	out, err := h.uc.UpdateMemory(r.Context(), usecase.UpdateMemoryInput{
		UserID:   userID,
		ID:       r.PathValue("memory_id"),
		Title:    req.Title,
		Content:  req.Content,
		Tags:     req.Tags,
		HasTags:  req.Tags != nil,
		IsPinned: req.IsPinned,
	})
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *MemoryHandler) DeleteMemory(w http.ResponseWriter, r *http.Request) {
	userID := requestUserID(r, r.URL.Query().Get("userId"))
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	if queryUserID := r.URL.Query().Get("userId"); queryUserID != "" && queryUserID != userID {
		response.FromError(w, apperrors.Forbidden("cannot delete another user's memory"))
		return
	}
	if err := h.uc.DeleteMemory(r.Context(), userID, r.PathValue("memory_id")); err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, map[string]bool{"deleted": true})
}

func (h *MemoryHandler) ListMemoryNodes(w http.ResponseWriter, r *http.Request) {
	limit, offset := pagination(r, 50)
	out, err := h.uc.ListMemoryNodes(
		r.Context(),
		requestUserID(r, r.URL.Query().Get("userId")),
		firstNonEmpty(r.URL.Query().Get("nodeType"), r.URL.Query().Get("type")),
		firstNonEmpty(r.URL.Query().Get("searchQuery"), r.URL.Query().Get("q")),
		limit,
		offset,
	)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *MemoryHandler) ListMemoryRelations(w http.ResponseWriter, r *http.Request) {
	limit, _ := pagination(r, 150)
	out, err := h.uc.ListMemoryRelations(
		r.Context(),
		requestUserID(r, r.URL.Query().Get("userId")),
		limit,
	)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *MemoryHandler) UpdateMemoryNode(w http.ResponseWriter, r *http.Request) {
	var req updateMemoryNodeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	out, err := h.uc.UpdateMemoryNode(
		r.Context(),
		requestUserID(r, req.UserID),
		r.PathValue("node_type"),
		r.PathValue("node_id"),
		req.Properties,
	)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *MemoryHandler) DeleteMemoryNode(w http.ResponseWriter, r *http.Request) {
	out, err := h.uc.DeleteMemoryNode(
		r.Context(),
		requestUserID(r, r.URL.Query().Get("userId")),
		r.PathValue("node_type"),
		r.PathValue("node_id"),
	)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *MemoryHandler) ResetUserMemory(w http.ResponseWriter, r *http.Request) {
	userID := requestUserID(r, r.URL.Query().Get("userId"))
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	if queryUserID := r.URL.Query().Get("userId"); queryUserID != "" && queryUserID != userID {
		response.FromError(w, apperrors.Forbidden("cannot reset another user's memory"))
		return
	}
	out, err := h.uc.ResetUserMemory(r.Context(), userID)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *MemoryHandler) PurgeUserAccount(w http.ResponseWriter, r *http.Request) {
	userID := requestUserID(r, r.URL.Query().Get("userId"))
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	if queryUserID := r.URL.Query().Get("userId"); queryUserID != "" && queryUserID != userID {
		response.FromError(w, apperrors.Forbidden("cannot purge another user's memory"))
		return
	}
	out, err := h.uc.PurgeUserAccount(r.Context(), userID)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *MemoryHandler) EscalationPolicy(w http.ResponseWriter, r *http.Request) {
	userID := requestUserID(r, r.PathValue("user_id"))
	policy, err := h.uc.EscalationPolicy(r.Context(), userID)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, policy)
}

func (h *MemoryHandler) ArchiveUserMemory(w http.ResponseWriter, r *http.Request) {
	userID := requestUserID(r, r.PathValue("user_id"))
	if err := h.uc.ArchiveUserMemory(r.Context(), userID); err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, map[string]string{"status": "ok"})
}

func requestUserID(r *http.Request, fallback string) string {
	if userID := middleware.AuthenticatedUserID(r); userID != "" {
		return userID
	}
	return fallback
}

func pagination(r *http.Request, defaultLimit int) (int, int) {
	page, _ := strconv.Atoi(r.URL.Query().Get("page"))
	pageSize, _ := strconv.Atoi(r.URL.Query().Get("pageSize"))
	if page <= 0 {
		page = 1
	}
	if pageSize <= 0 {
		pageSize = defaultLimit
	}
	if pageSize > 100 {
		pageSize = 100
	}
	return pageSize, (page - 1) * pageSize
}

func splitCSV(value string) []string {
	if strings.TrimSpace(value) == "" {
		return nil
	}
	parts := strings.Split(value, ",")
	out := make([]string, 0, len(parts))
	for _, part := range parts {
		if part = strings.TrimSpace(part); part != "" {
			out = append(out, part)
		}
	}
	return out
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return value
		}
	}
	return ""
}
