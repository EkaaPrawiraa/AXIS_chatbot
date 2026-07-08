package handler

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/domain/entity"
	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/usecase"
	apperrors "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/errors"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/middleware"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/response"
)

type ChatHandler struct {
	uc *usecase.ChatUsecase
}

func NewChatHandler(uc *usecase.ChatUsecase) *ChatHandler {
	return &ChatHandler{uc: uc}
}

type startSessionRequest struct {
	UserID  string `json:"userId"`
	Title   string `json:"title"`
	Channel string `json:"channel"`
}

type sendMessageRequest struct {
	UserID                 string                `json:"userId"`
	Message                string                `json:"message"`
	Content                string                `json:"content"`
	VoiceURL               string                `json:"voiceUrl"`
	Voice                  *usecase.VoiceRequest `json:"voice,omitempty"`
	PHQ9State              map[string]any        `json:"phq9_state,omitempty"`
	CBTState               map[string]any        `json:"cbt_state,omitempty"`
	LanguagePref           string                      `json:"language_pref,omitempty"`
	PreferredResponseModel string                      `json:"preferred_response_model,omitempty"`
	EphemeralHistory       []usecase.EphemeralMessage `json:"ephemeral_history,omitempty"`
}

type updateConversationRequest struct {
	Title string `json:"title"`
}

type synthesizeSpeechRequest struct {
	Text         string `json:"text"`
	VoiceID      string `json:"voice_id"`
	TTSModel     string `json:"tts_model"`
	LanguagePref string `json:"language_pref"`
}

type transcribeSpeechRequest struct {
	AudioBase64  string `json:"audio_base64"`
	AudioMime    string `json:"audio_mime"`
	LanguagePref string `json:"language_pref"`
}

func (h *ChatHandler) StartSession(w http.ResponseWriter, r *http.Request) {
	var req startSessionRequest
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
		response.FromError(w, apperrors.Forbidden("cannot create a conversation for another user"))
		return
	}
	session, err := h.uc.StartSession(r.Context(), usecase.StartSessionInput{
		UserID:  userID,
		Title:   req.Title,
		Channel: entity.Channel(req.Channel),
	})
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.Created(w, usecase.ConversationDTO{
		ID:            session.ID,
		UserID:        session.UserID,
		Title:         session.Title,
		LastMessageAt: session.StartedAt.UnixMilli(),
		MessageCount:  session.TurnCount,
		Preview:       "",
		CreatedAt:     session.CreatedAt.UnixMilli(),
		UpdatedAt:     session.UpdatedAt.UnixMilli(),
	})
}

func (h *ChatHandler) ListConversations(w http.ResponseWriter, r *http.Request) {
	limit, offset := pagination(r, 50)
	out, err := h.uc.ListConversations(r.Context(), requestUserID(r, r.URL.Query().Get("userId")), limit, offset)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *ChatHandler) UpdateConversation(w http.ResponseWriter, r *http.Request) {
	var req updateConversationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	out, err := h.uc.UpdateConversationTitle(r.Context(), requestUserID(r, ""), r.PathValue("conversation_id"), req.Title)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *ChatHandler) DeleteConversation(w http.ResponseWriter, r *http.Request) {
	if err := h.uc.DeleteConversation(r.Context(), requestUserID(r, ""), r.PathValue("conversation_id")); err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, map[string]bool{"deleted": true})
}

func (h *ChatHandler) ListMessages(w http.ResponseWriter, r *http.Request) {
	limit, offset := pagination(r, 50)
	out, err := h.uc.ListMessages(r.Context(), requestUserID(r, r.URL.Query().Get("userId")), r.PathValue("conversation_id"), limit, offset)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *ChatHandler) SendMessage(w http.ResponseWriter, r *http.Request) {
	sessionID := r.PathValue("conversation_id")
	if sessionID == "" {
		sessionID = r.PathValue("session_id")
	}
	var req sendMessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	content := req.Content
	if content == "" {
		content = req.Message
	}
	if req.Voice == nil && req.VoiceURL != "" {
		req.Voice = &usecase.VoiceRequest{AudioInputURL: req.VoiceURL, OutputModality: "both"}
	}
	userID := requestUserID(r, req.UserID)
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	if req.UserID != "" && req.UserID != userID {
		response.FromError(w, apperrors.Forbidden("cannot send as another user"))
		return
	}
	out, err := h.uc.SendMessage(r.Context(), usecase.SendMessageInput{
		UserID:                 userID,
		SessionID:              sessionID,
		Message:                content,
		AudioURL:               req.VoiceURL,
		Voice:                  req.Voice,
		PHQ9State:              req.PHQ9State,
		CBTState:               req.CBTState,
		LanguagePref:           req.LanguagePref,
		PreferredResponseModel: req.PreferredResponseModel,
		EphemeralHistory:       req.EphemeralHistory,
	})
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

type regenerateMessageRequest struct {
	UserID                 string         `json:"userId"`
	PHQ9State              map[string]any `json:"phq9_state,omitempty"`
	CBTState               map[string]any `json:"cbt_state,omitempty"`
	LanguagePref           string         `json:"language_pref,omitempty"`
	PreferredResponseModel string         `json:"preferred_response_model,omitempty"`
}

func (h *ChatHandler) RegenerateMessage(w http.ResponseWriter, r *http.Request) {
	sessionID := r.PathValue("conversation_id")
	messageID := r.PathValue("message_id")
	var req regenerateMessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	userID := requestUserID(r, req.UserID)
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	out, err := h.uc.RegenerateMessage(r.Context(), usecase.RegenerateMessageInput{
		UserID:                 userID,
		SessionID:              sessionID,
		MessageID:              messageID,
		LanguagePref:           req.LanguagePref,
		PreferredResponseModel: req.PreferredResponseModel,
		PHQ9State:              req.PHQ9State,
		CBTState:               req.CBTState,
	})
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *ChatHandler) StreamMessage(w http.ResponseWriter, r *http.Request) {
	sessionID := r.PathValue("conversation_id")
	if sessionID == "" {
		sessionID = r.PathValue("session_id")
	}
	var req sendMessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	content := req.Content
	if content == "" {
		content = req.Message
	}
	userID := requestUserID(r, req.UserID)
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	if req.UserID != "" && req.UserID != userID {
		response.FromError(w, apperrors.Forbidden("cannot send as another user"))
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no")
	flusher, _ := w.(http.Flusher)
	writeEvent := func(event string, data string) error {
		if _, err := fmt.Fprintf(w, "event: %s\n", event); err != nil {
			return err
		}
		for _, line := range strings.Split(data, "\n") {
			if _, err := fmt.Fprintf(w, "data: %s\n", line); err != nil {
				return err
			}
		}
		if _, err := fmt.Fprint(w, "\n"); err != nil {
			return err
		}
		if flusher != nil {
			flusher.Flush()
		}
		return nil
	}

	out, err := h.uc.StreamMessage(r.Context(), usecase.StreamMessageInput{
		SendMessageInput: usecase.SendMessageInput{
			UserID:                 userID,
			SessionID:              sessionID,
			Message:                content,
			Voice:                  req.Voice,
			PHQ9State:              req.PHQ9State,
			CBTState:               req.CBTState,
			LanguagePref:           req.LanguagePref,
			PreferredResponseModel: req.PreferredResponseModel,
		},
		OnToken: func(token string) error {
			return writeEvent("token", token)
		},
	})
	if err != nil {
		_ = writeEvent("error", err.Error())
		return
	}
	payload, err := json.Marshal(out)
	if err != nil {
		_ = writeEvent("error", "failed to encode stream result")
		return
	}
	_ = writeEvent("done", string(payload))
}

func requestUserID(r *http.Request, fallback string) string {
	if userID := middleware.AuthenticatedUserID(r); userID != "" {
		return userID
	}
	return fallback
}

func (h *ChatHandler) SynthesizeSpeech(w http.ResponseWriter, r *http.Request) {
	var req synthesizeSpeechRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if req.Text == "" {
		response.ErrorCode(w, http.StatusBadRequest, "invalid_input", "text is required", "text")
		return
	}
	out, err := h.uc.SynthesizeSpeech(r.Context(), usecase.SynthesizeSpeechRequest{
		Text:         req.Text,
		VoiceID:      req.VoiceID,
		TTSModel:     req.TTSModel,
		LanguagePref: req.LanguagePref,
	})
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *ChatHandler) TranscribeSpeech(w http.ResponseWriter, r *http.Request) {
	var req transcribeSpeechRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if req.AudioBase64 == "" {
		response.ErrorCode(w, http.StatusBadRequest, "invalid_input", "audio_base64 is required", "audio_base64")
		return
	}
	out, err := h.uc.TranscribeSpeech(r.Context(), usecase.TranscribeSpeechRequest{
		AudioBase64:  req.AudioBase64,
		AudioMime:    req.AudioMime,
		LanguagePref: req.LanguagePref,
	})
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *ChatHandler) ListVoiceOptions(w http.ResponseWriter, r *http.Request) {
	out, err := h.uc.ListVoiceOptions(r.Context())
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

type submitMoodRequest struct {
	UserID string `json:"userId"`
	Score  int    `json:"score"`
}

func (h *ChatHandler) SubmitMood(w http.ResponseWriter, r *http.Request) {
	var req submitMoodRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	userID := requestUserID(r, req.UserID)
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	out, err := h.uc.SubmitMood(r.Context(), userID, req.Score)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *ChatHandler) MoodTrend(w http.ResponseWriter, r *http.Request) {
	userID := requestUserID(r, r.URL.Query().Get("userId"))
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	days, _ := strconv.Atoi(r.URL.Query().Get("days"))
	out, err := h.uc.MoodTrend(r.Context(), userID, days)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
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
