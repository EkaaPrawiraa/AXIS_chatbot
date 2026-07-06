package usecase

import (
	"context"
	"database/sql"
	"errors"
	"strings"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/domain/entity"
	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/domain/repository"
	apperrors "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/errors"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/id"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/validator"
)

type AgenticClient interface {
	Invoke(ctx context.Context, req AgenticChatRequest) (AgenticChatResponse, error)
	Stream(ctx context.Context, req AgenticChatRequest, onEvent func(AgenticStreamEvent) error) (AgenticChatResponse, error)
	SynthesizeSpeech(ctx context.Context, req SynthesizeSpeechRequest) (SynthesizeSpeechResponse, error)
	TranscribeSpeech(ctx context.Context, req TranscribeSpeechRequest) (TranscribeSpeechResponse, error)
	PurgeSessionMemory(ctx context.Context, sessionID string, messageIDs []string) error
}

type VoiceCatalogClient interface {
	ListVoices(ctx context.Context) ([]VoiceOptionDTO, error)
}

type AgenticChatRequest struct {
	UserID                 string         `json:"user_id"`
	SessionID              string         `json:"session_id"`
	CurrentMessage         string         `json:"current_message,omitempty"`
	Messages               []ChatMessage  `json:"messages,omitempty"`
	SessionTurn            int            `json:"session_turn"`
	LanguagePref           string         `json:"language_pref,omitempty"`
	PreferredResponseModel string         `json:"preferred_response_model,omitempty"`
	PHQ9State              map[string]any `json:"phq9_state,omitempty"`
	CBTState               map[string]any `json:"cbt_state,omitempty"`
	Voice                  *VoiceRequest  `json:"voice,omitempty"`
	ConfessionMode         bool           `json:"confession_mode,omitempty"`
}

type AgenticChatResponse struct {
	UserID            string         `json:"user_id"`
	SessionID         string         `json:"session_id"`
	Reply             string         `json:"reply"`
	FinalResponse     string         `json:"final_response,omitempty"`
	SessionTurn       int            `json:"session_turn,omitempty"`
	ResolvedLanguage  string         `json:"resolved_language,omitempty"`
	LinguisticSignals map[string]any `json:"linguistic_signals,omitempty"`
	SafetyFlag        string         `json:"safety_flag,omitempty"`
	CrisisTier        string         `json:"crisis_tier,omitempty"`
	KGContext         string         `json:"kg_context,omitempty"`
	PHQ9State         map[string]any `json:"phq9_state,omitempty"`
	CBTState          map[string]any `json:"cbt_state,omitempty"`
	Voice             VoiceResponse  `json:"voice,omitempty"`
}

type AgenticStreamEvent struct {
	Event string
	Data  string
}

type ChatMessage struct {
	Role     string         `json:"role"`
	Content  string         `json:"content"`
	Metadata map[string]any `json:"metadata,omitempty"`
}

type VoiceRequest struct {
	OutputModality   string `json:"output_modality,omitempty"`
	AudioInputBase64 string `json:"audio_input_base64,omitempty"`
	AudioInputMIME   string `json:"audio_input_mime,omitempty"`
	AudioInputURL    string `json:"audio_input_url,omitempty"`
	VoiceID          string `json:"voice_id,omitempty"`
	TTSModel         string `json:"tts_model,omitempty"`
	TTSStreaming     *bool  `json:"tts_streaming,omitempty"`
}

type VoiceResponse struct {
	Transcript           string  `json:"transcript,omitempty"`
	TranscriptConfidence float64 `json:"transcript_confidence,omitempty"`
	TranscriptLanguage   string  `json:"transcript_language,omitempty"`
	OutputModality       string  `json:"output_modality,omitempty"`
	VoiceID              string  `json:"voice_id,omitempty"`
	VoiceProviderID      string  `json:"voice_provider_id,omitempty"`
	SpeechResponse       string  `json:"speech_response,omitempty"`
	SpeechResponseTags   string  `json:"speech_response_tags,omitempty"`
	TTSModel             string  `json:"tts_model,omitempty"`
	TTSProvider          string  `json:"tts_provider,omitempty"`
	TTSStreaming         bool    `json:"tts_streaming,omitempty"`
	AudioOutputBase64    string  `json:"audio_output_base64,omitempty"`
	AudioOutputURL       string  `json:"audio_output_url,omitempty"`
	AudioOutputFormat    string  `json:"audio_output_format,omitempty"`
	VoiceError           string  `json:"voice_error,omitempty"`
}

type SynthesizeSpeechRequest struct {
	Text         string `json:"text"`
	VoiceID      string `json:"voice_id,omitempty"`
	TTSModel     string `json:"tts_model,omitempty"`
	LanguagePref string `json:"language_pref,omitempty"`
}

type SynthesizeSpeechResponse struct {
	AudioOutputBase64 string `json:"audio_output_base64,omitempty"`
	AudioOutputURL    string `json:"audio_output_url,omitempty"`
	AudioOutputFormat string `json:"audio_output_format,omitempty"`
	TTSProvider       string `json:"tts_provider,omitempty"`
	VoiceID           string `json:"voice_id,omitempty"`
	VoiceProviderID   string `json:"voice_provider_id,omitempty"`
	TTSModel          string `json:"tts_model,omitempty"`
	VoiceError        string `json:"voice_error,omitempty"`
}

type TranscribeSpeechRequest struct {
	AudioBase64  string `json:"audio_base64"`
	AudioMime    string `json:"audio_mime,omitempty"`
	LanguagePref string `json:"language_pref,omitempty"`
}

type TranscribeSpeechResponse struct {
	Text       string  `json:"text"`
	Language   string  `json:"language,omitempty"`
	Confidence float64 `json:"confidence,omitempty"`
	VoiceError string  `json:"voice_error,omitempty"`
}

type VoiceOptionDTO struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Provider    string `json:"provider"`
	ProviderID  string `json:"providerId"`
	Category    string `json:"category,omitempty"`
	PreviewURL  string `json:"previewUrl,omitempty"`
	Description string `json:"description,omitempty"`
}

type StartSessionInput struct {
	UserID  string
	Title   string
	Channel entity.Channel
}

type SendMessageInput struct {
	UserID                 string
	SessionID              string
	Message                string
	AudioURL               string
	Voice                  *VoiceRequest
	PHQ9State              map[string]any
	CBTState               map[string]any
	LanguagePref           string
	PreferredResponseModel string
}

type SendMessageOutput struct {
	MessageID      string         `json:"messageId"`
	ConversationID string         `json:"conversationId"`
	UserMessage    MessageDTO     `json:"userMessage"`
	Assistant      MessageDTO     `json:"assistantMessage"`
	Reply          string         `json:"reply"`
	SafetyFlag     string         `json:"safety_flag,omitempty"`
	CrisisTier     string         `json:"crisis_tier,omitempty"`
	PHQ9State      map[string]any `json:"phq9_state,omitempty"`
	CBTState       map[string]any `json:"cbt_state,omitempty"`
	Voice          VoiceResponse  `json:"voice,omitempty"`
}

type StreamMessageInput struct {
	SendMessageInput
	OnToken func(token string) error
}

type ConversationDTO struct {
	ID            string `json:"id"`
	UserID        string `json:"userId"`
	Title         string `json:"title"`
	Description   string `json:"description,omitempty"`
	LastMessageAt int64  `json:"lastMessageAt"`
	MessageCount  int    `json:"messageCount"`
	Preview       string `json:"preview"`
	CreatedAt     int64  `json:"createdAt"`
	UpdatedAt     int64  `json:"updatedAt"`
}

type MessageDTO struct {
	ID             string         `json:"id"`
	ConversationID string         `json:"conversationId"`
	Role           string         `json:"role"`
	Content        string         `json:"content"`
	Status         string         `json:"status"`
	Metadata       map[string]any `json:"metadata,omitempty"`
	CreatedAt      int64          `json:"createdAt"`
	UpdatedAt      int64          `json:"updatedAt"`
}

type ChatUsecase struct {
	sessions repository.SessionRepository
	messages repository.MessageRepository
	moods    repository.MoodRepository
	agentic  AgenticClient
	voices   VoiceCatalogClient
}

func NewChatUsecase(
	sessions repository.SessionRepository,
	messages repository.MessageRepository,
	moods repository.MoodRepository,
	agentic AgenticClient,
	voices VoiceCatalogClient,
) *ChatUsecase {
	return &ChatUsecase{sessions: sessions, messages: messages, moods: moods, agentic: agentic, voices: voices}
}

type MoodDTO struct {
	Date  string `json:"date"`
	Score int    `json:"score"`
}

// SubmitMood records today's mood score (1-5), overwriting any score
// already submitted today.
func (u *ChatUsecase) SubmitMood(ctx context.Context, userID string, score int) (MoodDTO, error) {
	if err := validateUUID("userId", userID); err != nil {
		return MoodDTO{}, err
	}
	if score < 1 || score > 5 {
		return MoodDTO{}, apperrors.Invalid("score must be between 1 and 5")
	}
	mood, err := u.moods.Upsert(ctx, userID, score)
	if err != nil {
		return MoodDTO{}, err
	}
	return MoodDTO{Date: mood.MoodDate.Format("2006-01-02"), Score: mood.Score}, nil
}

// MoodTrend returns the last `days` calendar days of mood entries, most
// recent first, for both the dashboard trend chart and agentic context.
func (u *ChatUsecase) MoodTrend(ctx context.Context, userID string, days int) ([]MoodDTO, error) {
	if err := validateUUID("userId", userID); err != nil {
		return nil, err
	}
	if days <= 0 {
		days = 14
	}
	moods, err := u.moods.ListRecent(ctx, userID, days)
	if err != nil {
		return nil, err
	}
	out := make([]MoodDTO, 0, len(moods))
	for _, mood := range moods {
		out = append(out, MoodDTO{Date: mood.MoodDate.Format("2006-01-02"), Score: mood.Score})
	}
	return out, nil
}

func (u *ChatUsecase) StartSession(ctx context.Context, input StartSessionInput) (entity.Session, error) {
	if err := validateUUID("userId", input.UserID); err != nil {
		return entity.Session{}, err
	}
	title := strings.TrimSpace(input.Title)
	if title == "" {
		title = "New Conversation"
	}
	if len(title) > 200 {
		return entity.Session{}, apperrors.InvalidField("title", "title must be at most 200 characters")
	}
	session, err := u.sessions.Create(ctx, entity.NewSession(input.UserID, title, input.Channel))
	if err != nil {
		return entity.Session{}, err
	}
	return session, nil
}

func (u *ChatUsecase) ListConversations(ctx context.Context, userID string, limit int, offset int) ([]ConversationDTO, error) {
	if err := validateUUID("userId", userID); err != nil {
		return nil, err
	}
	conversations, err := u.sessions.ListConversations(ctx, userID, validator.ClampInt(limit, 1, 100), max(offset, 0))
	if err != nil {
		return nil, err
	}
	out := make([]ConversationDTO, 0, len(conversations))
	for _, c := range conversations {
		out = append(out, conversationDTO(c))
	}
	return out, nil
}

func (u *ChatUsecase) ListMessages(ctx context.Context, userID string, sessionID string, limit int, offset int) ([]MessageDTO, error) {
	if err := validateUUID("conversationId", sessionID); err != nil {
		return nil, err
	}
	if err := validateUUID("userId", userID); err != nil {
		return nil, err
	}
	if _, err := u.ensureSessionOwner(ctx, sessionID, userID); err != nil {
		return nil, err
	}
	messages, err := u.messages.ListBySession(ctx, sessionID, validator.ClampInt(limit, 1, 100), max(offset, 0))
	if err != nil {
		return nil, err
	}
	out := make([]MessageDTO, 0, len(messages))
	for _, msg := range messages {
		out = append(out, messageDTO(msg))
	}
	return out, nil
}

func (u *ChatUsecase) UpdateConversationTitle(ctx context.Context, userID string, sessionID string, title string) (ConversationDTO, error) {
	if err := validateUUID("conversationId", sessionID); err != nil {
		return ConversationDTO{}, err
	}
	if err := validateUUID("userId", userID); err != nil {
		return ConversationDTO{}, err
	}
	if _, err := u.ensureSessionOwner(ctx, sessionID, userID); err != nil {
		return ConversationDTO{}, err
	}
	title = strings.TrimSpace(title)
	if title == "" {
		return ConversationDTO{}, apperrors.InvalidField("title", "title is required")
	}
	if len(title) > 200 {
		return ConversationDTO{}, apperrors.InvalidField("title", "title must be at most 200 characters")
	}
	session, err := u.sessions.UpdateTitle(ctx, sessionID, title)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return ConversationDTO{}, apperrors.NotFound("conversation not found")
		}
		return ConversationDTO{}, err
	}
	return ConversationDTO{
		ID:            session.ID,
		UserID:        session.UserID,
		Title:         session.Title,
		LastMessageAt: millis(session.UpdatedAt),
		MessageCount:  session.TurnCount * 2,
		CreatedAt:     millis(session.CreatedAt),
		UpdatedAt:     millis(session.UpdatedAt),
	}, nil
}

func (u *ChatUsecase) DeleteConversation(ctx context.Context, userID string, sessionID string) error {
	if err := validateUUID("conversationId", sessionID); err != nil {
		return err
	}
	if err := validateUUID("userId", userID); err != nil {
		return err
	}
	if _, err := u.ensureSessionOwner(ctx, sessionID, userID); err != nil {
		return err
	}
	if u.agentic == nil {
		return apperrors.Invalid("agentic service is not configured")
	}
	messageIDs, err := u.messages.ListIDsBySession(ctx, sessionID)
	if err != nil {
		return err
	}
	if err := u.agentic.PurgeSessionMemory(ctx, sessionID, messageIDs); err != nil {
		return err
	}
	if err := u.sessions.Delete(ctx, sessionID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return apperrors.NotFound("conversation not found")
		}
		return err
	}
	return nil
}

func (u *ChatUsecase) SendMessage(ctx context.Context, input SendMessageInput) (SendMessageOutput, error) {
	if err := validateUUID("conversationId", input.SessionID); err != nil {
		return SendMessageOutput{}, err
	}
	input.Message = strings.TrimSpace(input.Message)
	hasAudio := input.Voice != nil && (input.Voice.AudioInputBase64 != "" || input.Voice.AudioInputURL != "")
	if input.Message == "" && !hasAudio {
		return SendMessageOutput{}, apperrors.InvalidField("content", "content or voice audio is required")
	}
	if len(input.Message) > 4000 {
		return SendMessageOutput{}, apperrors.InvalidField("content", "content must be at most 4000 characters")
	}

	session, err := u.sessions.FindByID(ctx, input.SessionID)
	if err != nil {
		return SendMessageOutput{}, err
	}
	if session == nil {
		return SendMessageOutput{}, apperrors.NotFound("conversation not found")
	}
	if strings.TrimSpace(input.UserID) == "" {
		input.UserID = session.UserID
	} else {
		if err := validateUUID("userId", input.UserID); err != nil {
			return SendMessageOutput{}, err
		}
		if session.UserID != input.UserID {
			return SendMessageOutput{}, apperrors.NotFound("conversation not found")
		}
	}

	// Confession Space's whole premise, shown right in its own UI header,
	// is that nothing said there is stored permanently. SendMessage used
	// to persist both the user and assistant message unconditionally,
	// regardless of channel -- every confession was silently written to
	// the same `messages` table as a normal conversation. For this
	// channel we never call u.messages.Append/NextTurnIndex/ListBySession
	// at all: turn index comes from the session's own counter, history is
	// empty (no persisted turns to read back, by design), and the
	// response DTOs are built from in-memory-only entities with a
	// generated id -- so nothing about this exchange ever touches
	// Postgres beyond the session-level turn counter and safety flag.
	isConfession := session.Channel == entity.ChannelConfession

	var (
		turnIndex   int
		userMessage entity.Message
		history     []entity.Message
	)
	if isConfession {
		turnIndex = session.TurnCount + 1
		userMessage = entity.NewUserMessage(input.SessionID, input.UserID, input.Message, optionalString(input.AudioURL), turnIndex)
		userMessage.ID, err = id.NewUUID()
		if err != nil {
			return SendMessageOutput{}, err
		}
		userMessage.CreatedAt = time.Now()
	} else {
		turnIndex, err = u.messages.NextTurnIndex(ctx, input.SessionID)
		if err != nil {
			return SendMessageOutput{}, err
		}
		userMessage = entity.NewUserMessage(input.SessionID, input.UserID, input.Message, optionalString(input.AudioURL), turnIndex)
		userMessage, err = u.messages.Append(ctx, userMessage)
		if err != nil {
			return SendMessageOutput{}, err
		}
		if session.TurnCount == 0 && session.Title == "New Conversation" && input.Message != "" {
			_, _ = u.sessions.UpdateTitle(ctx, input.SessionID, titleFromMessage(input.Message))
		}

		historyOffset := max(turnIndex-29, 0)
		history, err = u.messages.ListBySession(ctx, input.SessionID, 30, historyOffset)
		if err != nil {
			return SendMessageOutput{}, err
		}
	}
	agenticMessages := make([]ChatMessage, 0, len(history))
	for _, msg := range history {
		agenticMessages = append(agenticMessages, ChatMessage{
			Role:     string(msg.Role),
			Content:  msg.Content,
			Metadata: messageMetadata(msg),
		})
	}

	resp, err := u.agentic.Invoke(ctx, AgenticChatRequest{
		UserID:                 input.UserID,
		SessionID:              input.SessionID,
		CurrentMessage:         input.Message,
		Messages:               agenticMessages,
		SessionTurn:            session.TurnCount + 1,
		LanguagePref:           defaultString(input.LanguagePref, "id"),
		PreferredResponseModel: strings.TrimSpace(input.PreferredResponseModel),
		PHQ9State:              input.PHQ9State,
		CBTState:               input.CBTState,
		Voice:                  input.Voice,
		ConfessionMode:         isConfession,
	})
	if err != nil {
		return SendMessageOutput{}, err
	}
	reply := agenticReply(resp, input.LanguagePref)
	if input.Message == "" && strings.TrimSpace(resp.Voice.Transcript) != "" {
		transcript := strings.TrimSpace(resp.Voice.Transcript)
		if isConfession {
			userMessage.Content = transcript
		} else {
			updatedUserMessage, updateErr := u.messages.UpdateContent(ctx, userMessage.ID, transcript)
			if updateErr == nil {
				userMessage = updatedUserMessage
			}
			if session.TurnCount == 0 && session.Title == "New Conversation" {
				_, _ = u.sessions.UpdateTitle(ctx, input.SessionID, titleFromMessage(transcript))
			}
		}
	}
	safetyFlag := optionalString(resp.SafetyFlag)
	crisisTier := optionalString(resp.CrisisTier)
	assistantMessage := entity.NewAssistantMessage(
		input.SessionID,
		input.UserID,
		reply,
		turnIndex+1,
		safetyFlag,
		crisisTier,
	)
	assistantMessage.Metadata = responseMetadata(resp.PHQ9State)
	if isConfession {
		assistantMessage.ID, err = id.NewUUID()
		if err != nil {
			return SendMessageOutput{}, err
		}
		assistantMessage.CreatedAt = time.Now()
	} else {
		assistantMessage, err = u.messages.Append(ctx, assistantMessage)
		if err != nil {
			return SendMessageOutput{}, err
		}
	}
	if resp.SafetyFlag == "crisis" || resp.SafetyFlag == "escalate" {
		_ = u.sessions.MarkSafetyEscalated(ctx, input.SessionID)
	}
	_ = u.sessions.IncrementTurn(ctx, input.SessionID)

	assistantDTO := messageDTO(assistantMessage)
	if phq9Meta := phq9MetadataFromState(resp.PHQ9State); phq9Meta != nil {
		if assistantDTO.Metadata == nil {
			assistantDTO.Metadata = map[string]any{}
		}
		assistantDTO.Metadata["phq9"] = phq9Meta
	}

	return SendMessageOutput{
		MessageID:      assistantMessage.ID,
		ConversationID: input.SessionID,
		UserMessage:    messageDTO(userMessage),
		Assistant:      assistantDTO,
		Reply:          reply,
		SafetyFlag:     resp.SafetyFlag,
		CrisisTier:     resp.CrisisTier,
		PHQ9State:      resp.PHQ9State,
		CBTState:       resp.CBTState,
		Voice:          resp.Voice,
	}, nil
}

type RegenerateMessageInput struct {
	UserID                 string
	SessionID              string
	MessageID              string
	LanguagePref           string
	PreferredResponseModel string
	PHQ9State              map[string]any
	CBTState               map[string]any
}

// RegenerateMessage re-runs the LAST assistant reply against the same
// preceding user turn and replaces it in place (same message ID/turn index,
// not a new row) — "Buat ulang" only ever applies to the most recent
// assistant message, never older history.
func (u *ChatUsecase) RegenerateMessage(ctx context.Context, input RegenerateMessageInput) (SendMessageOutput, error) {
	if err := validateUUID("conversationId", input.SessionID); err != nil {
		return SendMessageOutput{}, err
	}
	session, err := u.sessions.FindByID(ctx, input.SessionID)
	if err != nil {
		return SendMessageOutput{}, err
	}
	if session == nil || session.UserID != input.UserID {
		return SendMessageOutput{}, apperrors.NotFound("conversation not found")
	}

	history, err := u.messages.ListBySession(ctx, input.SessionID, 200, 0)
	if err != nil {
		return SendMessageOutput{}, err
	}
	if len(history) < 2 {
		return SendMessageOutput{}, apperrors.Invalid("nothing to regenerate yet")
	}
	last := history[len(history)-1]
	if last.ID != input.MessageID {
		return SendMessageOutput{}, apperrors.Invalid("only the most recent assistant message can be regenerated")
	}
	if last.Role != entity.RoleAssistant {
		return SendMessageOutput{}, apperrors.Invalid("only an assistant message can be regenerated")
	}
	precedingUser := history[len(history)-2]
	if precedingUser.Role != entity.RoleUser {
		return SendMessageOutput{}, apperrors.Invalid("no preceding user message to regenerate a reply for")
	}

	// Build history for the agentic call WITHOUT the stale assistant reply,
	// so the model answers the same prompt fresh rather than "continuing"
	// its own previous (about-to-be-replaced) answer.
	contextHistory := history[:len(history)-1]
	agenticMessages := make([]ChatMessage, 0, len(contextHistory))
	for _, msg := range contextHistory {
		agenticMessages = append(agenticMessages, ChatMessage{
			Role:     string(msg.Role),
			Content:  msg.Content,
			Metadata: messageMetadata(msg),
		})
	}

	resp, err := u.agentic.Invoke(ctx, AgenticChatRequest{
		UserID:                 input.UserID,
		SessionID:              input.SessionID,
		CurrentMessage:         precedingUser.Content,
		Messages:               agenticMessages,
		SessionTurn:            session.TurnCount,
		LanguagePref:           defaultString(input.LanguagePref, "id"),
		PreferredResponseModel: strings.TrimSpace(input.PreferredResponseModel),
		PHQ9State:              input.PHQ9State,
		CBTState:               input.CBTState,
		ConfessionMode:         session.Channel == entity.ChannelConfession,
	})
	if err != nil {
		return SendMessageOutput{}, err
	}
	reply := agenticReply(resp, input.LanguagePref)

	updated, err := u.messages.UpdateRegeneratedContent(
		ctx,
		last.ID,
		reply,
		optionalString(resp.SafetyFlag),
		optionalString(resp.CrisisTier),
	)
	if err != nil {
		return SendMessageOutput{}, err
	}
	if resp.SafetyFlag == "crisis" || resp.SafetyFlag == "escalate" {
		_ = u.sessions.MarkSafetyEscalated(ctx, input.SessionID)
	}

	assistantDTO := messageDTO(updated)
	if phq9Meta := phq9MetadataFromState(resp.PHQ9State); phq9Meta != nil {
		if assistantDTO.Metadata == nil {
			assistantDTO.Metadata = map[string]any{}
		}
		assistantDTO.Metadata["phq9"] = phq9Meta
	}

	return SendMessageOutput{
		MessageID:      updated.ID,
		ConversationID: input.SessionID,
		UserMessage:    messageDTO(precedingUser),
		Assistant:      assistantDTO,
		Reply:          reply,
		SafetyFlag:     resp.SafetyFlag,
		CrisisTier:     resp.CrisisTier,
		PHQ9State:      resp.PHQ9State,
		CBTState:       resp.CBTState,
	}, nil
}

func (u *ChatUsecase) StreamMessage(ctx context.Context, input StreamMessageInput) (SendMessageOutput, error) {
	if err := validateUUID("conversationId", input.SessionID); err != nil {
		return SendMessageOutput{}, err
	}
	input.Message = strings.TrimSpace(input.Message)
	hasAudio := input.Voice != nil && (input.Voice.AudioInputBase64 != "" || input.Voice.AudioInputURL != "")
	if input.Message == "" && !hasAudio {
		return SendMessageOutput{}, apperrors.InvalidField("content", "content or voice audio is required")
	}
	if len(input.Message) > 4000 {
		return SendMessageOutput{}, apperrors.InvalidField("content", "content must be at most 4000 characters")
	}
	session, err := u.sessions.FindByID(ctx, input.SessionID)
	if err != nil {
		return SendMessageOutput{}, err
	}
	if session == nil {
		return SendMessageOutput{}, apperrors.NotFound("conversation not found")
	}
	if strings.TrimSpace(input.UserID) == "" {
		input.UserID = session.UserID
	} else {
		if err := validateUUID("userId", input.UserID); err != nil {
			return SendMessageOutput{}, err
		}
		if session.UserID != input.UserID {
			return SendMessageOutput{}, apperrors.NotFound("conversation not found")
		}
	}

	turnIndex, err := u.messages.NextTurnIndex(ctx, input.SessionID)
	if err != nil {
		return SendMessageOutput{}, err
	}
	userMessage := entity.NewUserMessage(input.SessionID, input.UserID, input.Message, nil, turnIndex)
	userMessage, err = u.messages.Append(ctx, userMessage)
	if err != nil {
		return SendMessageOutput{}, err
	}
	if session.TurnCount == 0 && session.Title == "New Conversation" {
		_, _ = u.sessions.UpdateTitle(ctx, input.SessionID, titleFromMessage(input.Message))
	}

	historyOffset := max(turnIndex-29, 0)
	history, err := u.messages.ListBySession(ctx, input.SessionID, 30, historyOffset)
	if err != nil {
		return SendMessageOutput{}, err
	}
	agenticMessages := make([]ChatMessage, 0, len(history))
	for _, msg := range history {
		agenticMessages = append(agenticMessages, ChatMessage{
			Role:     string(msg.Role),
			Content:  msg.Content,
			Metadata: messageMetadata(msg),
		})
	}

	// Pre-create the assistant message as 'streaming' so clients can recover on reconnect.
	assistantMessage, err := u.messages.Append(ctx, entity.Message{
		SessionID: input.SessionID,
		UserID:    input.UserID,
		Role:      entity.RoleAssistant,
		Content:   "",
		Status:    "streaming",
		TurnIndex: turnIndex + 1,
	})
	if err != nil {
		return SendMessageOutput{}, err
	}

	var accumulated strings.Builder
	tokenCount := 0
	// bgCtx survives client disconnect so incremental flushes always reach the DB.
	bgCtx := context.Background()

	resp, err := u.agentic.Stream(ctx, AgenticChatRequest{
		UserID:                 input.UserID,
		SessionID:              input.SessionID,
		CurrentMessage:         input.Message,
		Messages:               agenticMessages,
		SessionTurn:            session.TurnCount + 1,
		LanguagePref:           defaultString(input.LanguagePref, "id"),
		PreferredResponseModel: strings.TrimSpace(input.PreferredResponseModel),
		PHQ9State:              input.PHQ9State,
		CBTState:               input.CBTState,
		Voice:                  input.Voice,
		ConfessionMode:         session.Channel == entity.ChannelConfession,
	}, func(event AgenticStreamEvent) error {
		if event.Event != "token" {
			return nil
		}
		accumulated.WriteString(event.Data)
		tokenCount++
		if input.OnToken != nil {
			if err := input.OnToken(event.Data); err != nil {
				return err
			}
		}
		// Flush accumulated content to DB every 30 tokens so clients can
		// recover after a refresh even if the stream is still in progress.
		if tokenCount%30 == 0 {
			_ = u.messages.UpdateStatusAndContent(bgCtx, assistantMessage.ID, "streaming", accumulated.String())
		}
		return nil
	})
	if err != nil {
		// Stream was interrupted (client disconnect, agentic error, etc.).
		// Persist whatever was accumulated so the user sees partial content.
		_ = u.messages.UpdateStatusAndContent(bgCtx, assistantMessage.ID, "streaming", accumulated.String())
		return SendMessageOutput{}, err
	}

	reply := agenticReply(resp, input.LanguagePref)
	if input.Message == "" && strings.TrimSpace(resp.Voice.Transcript) != "" {
		transcript := strings.TrimSpace(resp.Voice.Transcript)
		updatedUserMessage, updateErr := u.messages.UpdateContent(ctx, userMessage.ID, transcript)
		if updateErr == nil {
			userMessage = updatedUserMessage
		}
		if session.TurnCount == 0 && session.Title == "New Conversation" {
			_, _ = u.sessions.UpdateTitle(ctx, input.SessionID, titleFromMessage(transcript))
		}
	}
	safetyFlag := optionalString(resp.SafetyFlag)
	crisisTier := optionalString(resp.CrisisTier)

	// Finalize: update content, safety metadata, and mark complete.
	assistantMessage.Content = reply
	assistantMessage.SafetyFlag = safetyFlag
	assistantMessage.CrisisTier = crisisTier
	assistantMessage.Status = "complete"
	assistantMessage.Metadata = responseMetadata(resp.PHQ9State)
	if err := u.messages.UpdateStatusContentAndMetadata(bgCtx, assistantMessage.ID, "complete", reply, assistantMessage.Metadata); err != nil {
		return SendMessageOutput{}, err
	}

	if resp.SafetyFlag == "crisis" || resp.SafetyFlag == "escalate" {
		_ = u.sessions.MarkSafetyEscalated(ctx, input.SessionID)
	}
	_ = u.sessions.IncrementTurn(ctx, input.SessionID)

	streamAssistantDTO := messageDTO(assistantMessage)
	if phq9Meta := phq9MetadataFromState(resp.PHQ9State); phq9Meta != nil {
		if streamAssistantDTO.Metadata == nil {
			streamAssistantDTO.Metadata = map[string]any{}
		}
		streamAssistantDTO.Metadata["phq9"] = phq9Meta
	}

	return SendMessageOutput{
		MessageID:      assistantMessage.ID,
		ConversationID: input.SessionID,
		UserMessage:    messageDTO(userMessage),
		Assistant:      streamAssistantDTO,
		Reply:          reply,
		SafetyFlag:     resp.SafetyFlag,
		CrisisTier:     resp.CrisisTier,
		PHQ9State:      resp.PHQ9State,
		CBTState:       resp.CBTState,
		Voice:          resp.Voice,
	}, nil
}

func (u *ChatUsecase) SynthesizeSpeech(ctx context.Context, input SynthesizeSpeechRequest) (SynthesizeSpeechResponse, error) {
	input.Text = strings.TrimSpace(input.Text)
	if input.Text == "" {
		return SynthesizeSpeechResponse{}, apperrors.InvalidField("text", "text is required")
	}
	if len([]rune(input.Text)) > 4000 {
		return SynthesizeSpeechResponse{}, apperrors.InvalidField("text", "text must be at most 4000 characters")
	}
	if strings.TrimSpace(input.LanguagePref) == "" {
		input.LanguagePref = "id"
	}
	return u.agentic.SynthesizeSpeech(ctx, input)
}

func (u *ChatUsecase) TranscribeSpeech(ctx context.Context, input TranscribeSpeechRequest) (TranscribeSpeechResponse, error) {
	if strings.TrimSpace(input.AudioBase64) == "" {
		return TranscribeSpeechResponse{}, apperrors.InvalidField("audio_base64", "audio_base64 is required")
	}
	if strings.TrimSpace(input.LanguagePref) == "" {
		input.LanguagePref = "id"
	}
	return u.agentic.TranscribeSpeech(ctx, input)
}

func (u *ChatUsecase) ListVoiceOptions(ctx context.Context) ([]VoiceOptionDTO, error) {
	if u.voices == nil {
		return []VoiceOptionDTO{}, nil
	}
	return u.voices.ListVoices(ctx)
}

func optionalString(value string) *string {
	if value == "" {
		return nil
	}
	return &value
}

func agenticReply(resp AgenticChatResponse, languagePref string) string {
	reply := strings.TrimSpace(resp.Reply)
	if reply == "" {
		reply = strings.TrimSpace(resp.FinalResponse)
	}
	if reply != "" {
		return reply
	}
	if languagePref == "en" {
		return "I'm here with you. Could you send that once more so I can respond properly?"
	}
	return "Aku tetap di sini. Bisa kirim sekali lagi supaya aku bisa merespons dengan tepat?"
}

func (u *ChatUsecase) ensureSession(ctx context.Context, sessionID string) error {
	session, err := u.sessions.FindByID(ctx, sessionID)
	if err != nil {
		return err
	}
	if session == nil {
		return apperrors.NotFound("conversation not found")
	}
	return nil
}

func (u *ChatUsecase) ensureSessionOwner(ctx context.Context, sessionID string, userID string) (*entity.Session, error) {
	session, err := u.sessions.FindByID(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	if session == nil || session.UserID != userID {
		return nil, apperrors.NotFound("conversation not found")
	}
	return session, nil
}

func validateUUID(field string, value string) error {
	if strings.TrimSpace(value) == "" {
		return apperrors.InvalidField(field, field+" is required")
	}
	if !validator.UUID(value) {
		return apperrors.InvalidField(field, field+" must be a UUID")
	}
	return nil
}

func conversationDTO(c entity.Conversation) ConversationDTO {
	return ConversationDTO{
		ID:            c.ID,
		UserID:        c.UserID,
		Title:         c.Title,
		Description:   c.Description,
		LastMessageAt: millis(c.LastMessageAt),
		MessageCount:  c.MessageCount,
		Preview:       c.Preview,
		CreatedAt:     millis(c.CreatedAt),
		UpdatedAt:     millis(c.UpdatedAt),
	}
}

func messageDTO(msg entity.Message) MessageDTO {
	status := messageFrontendStatus(msg)
	return MessageDTO{
		ID:             msg.ID,
		ConversationID: msg.SessionID,
		Role:           string(msg.Role),
		Content:        msg.Content,
		Status:         status,
		Metadata:       messageMetadata(msg),
		CreatedAt:      millis(msg.CreatedAt),
		UpdatedAt:      millis(msg.CreatedAt),
	}
}

// messageFrontendStatus maps the DB status to the frontend MessageStatus type.
// A 'streaming' message that is more than 2 minutes old is treated as 'sent'
// (partial content) because the stream was interrupted and will not complete.
func messageFrontendStatus(msg entity.Message) string {
	switch msg.Status {
	case "streaming":
		if time.Since(msg.CreatedAt) < 2*time.Minute {
			return "sending"
		}
		return "sent"
	case "error":
		return "failed"
	default:
		return "sent"
	}
}

func messageMetadata(msg entity.Message) map[string]any {
	metadata := map[string]any{}
	for key, value := range msg.Metadata {
		metadata[key] = value
	}
	if msg.AudioURL != nil && *msg.AudioURL != "" {
		metadata["voiceUrl"] = *msg.AudioURL
	}
	if msg.EmotionLabel != nil && *msg.EmotionLabel != "" {
		metadata["emotionDetected"] = *msg.EmotionLabel
	}
	if msg.SafetyFlag != nil && *msg.SafetyFlag != "" {
		metadata["safetyFlag"] = *msg.SafetyFlag
	}
	if msg.CrisisTier != nil && *msg.CrisisTier != "" {
		metadata["crisisTier"] = *msg.CrisisTier
	}
	if len(metadata) == 0 {
		return nil
	}
	return metadata
}

func responseMetadata(phq9State map[string]any) map[string]any {
	metadata := map[string]any{}
	if phq9Meta := phq9MetadataFromState(phq9State); phq9Meta != nil {
		metadata["phq9"] = phq9Meta
	}
	if len(metadata) == 0 {
		return nil
	}
	return metadata
}

// phq9MetadataFromState builds the metadata.phq9 payload that the frontend
// expects, derived from the phq9_state returned by the agentic service.
// Returns nil when the phase is idle/offer_pending so plain messages are unaffected.
func phq9MetadataFromState(phq9State map[string]any) map[string]any {
	if len(phq9State) == 0 {
		return nil
	}
	phase, _ := phq9State["phase"].(string)
	switch phase {
	case "", "idle", "offer_pending":
		return nil
	}
	language, _ := phq9State["language"].(string)
	if language == "" {
		language = "id"
	}
	active := phase == "offered" || phase == "in_progress" || phase == "awaiting_clar"
	m := map[string]any{
		"active":          active,
		"phase":           phase,
		"language":        language,
		"allow_free_text": true,
	}
	switch phase {
	case "offered":
		if language == "en" {
			m["options"] = []map[string]any{
				{"score": nil, "label": "Accept"},
				{"score": nil, "label": "Decline"},
			}
		} else {
			m["options"] = []map[string]any{
				{"score": nil, "label": "Mulai"},
				{"score": nil, "label": "Lewati"},
			}
		}
		m["progress"] = map[string]any{"current": 0, "total": 9}
	case "in_progress", "awaiting_clar":
		itemID := 1
		if v, ok := phq9State["active_item"]; ok {
			switch n := v.(type) {
			case float64:
				itemID = int(n)
			case int:
				itemID = n
			}
		}
		if itemID < 1 {
			itemID = 1
		}
		m["item_id"] = itemID
		m["options"] = phq9AnswerOptions(language)
		m["progress"] = map[string]any{"current": itemID, "total": 9}
	default:
		m["active"] = false
		m["progress"] = map[string]any{"current": 9, "total": 9}
	}
	return m
}

func phq9AnswerOptions(language string) []map[string]any {
	if language == "en" {
		return []map[string]any{
			{"score": 0, "label": "Not at all"},
			{"score": 1, "label": "Several days"},
			{"score": 2, "label": "More than half the days"},
			{"score": 3, "label": "Nearly every day"},
		}
	}
	return []map[string]any{
		{"score": 0, "label": "Tidak sama sekali"},
		{"score": 1, "label": "Beberapa hari"},
		{"score": 2, "label": "Lebih dari setengah hari"},
		{"score": 3, "label": "Hampir setiap hari"},
	}
}

func millis(t time.Time) int64 {
	if t.IsZero() {
		return 0
	}
	return t.UnixMilli()
}

func defaultString(value string, fallback string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return fallback
	}
	return value
}

func titleFromMessage(message string) string {
	message = strings.TrimSpace(message)
	runes := []rune(message)
	if len(runes) <= 60 {
		return message
	}
	return strings.TrimSpace(string(runes[:60]))
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
