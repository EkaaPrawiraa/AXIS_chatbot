package usecase

import (
	"context"
	"testing"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/domain/entity"
)

// Regression test: Confession Space's entire premise (shown in its own UI
// header, "Tidak disimpan permanen -- bebas cerita apa aja") is that
// nothing said there is stored permanently. SendMessage used to call
// u.messages.Append/NextTurnIndex/ListBySession unconditionally regardless
// of session.Channel, so every confession was silently written to the same
// `messages` table as a normal conversation -- a real, user-visible privacy
// promise violation.

type fakeSessionRepo struct {
	session          entity.Session
	incrementCalls   int
	escalateCalls    int
	updateTitleCalls int
}

func (f *fakeSessionRepo) Create(ctx context.Context, session entity.Session) (entity.Session, error) {
	return session, nil
}
func (f *fakeSessionRepo) FindByID(ctx context.Context, sessionID string) (*entity.Session, error) {
	s := f.session
	return &s, nil
}
func (f *fakeSessionRepo) ListConversations(ctx context.Context, userID string, limit int, offset int) ([]entity.Conversation, error) {
	return nil, nil
}
func (f *fakeSessionRepo) UpdateTitle(ctx context.Context, sessionID string, title string) (entity.Session, error) {
	f.updateTitleCalls++
	f.session.Title = title
	return f.session, nil
}
func (f *fakeSessionRepo) Delete(ctx context.Context, sessionID string) error { return nil }
func (f *fakeSessionRepo) IncrementTurn(ctx context.Context, sessionID string) error {
	f.incrementCalls++
	return nil
}
func (f *fakeSessionRepo) MarkSafetyEscalated(ctx context.Context, sessionID string) error {
	f.escalateCalls++
	return nil
}

type fakeMessageRepo struct {
	appendCalls        int
	nextTurnIndexCalls int
	listBySessionCalls int
	updateContentCalls int
}

func (f *fakeMessageRepo) Append(ctx context.Context, message entity.Message) (entity.Message, error) {
	f.appendCalls++
	message.ID = "generated-by-fake-repo"
	message.CreatedAt = time.Now()
	return message, nil
}
func (f *fakeMessageRepo) UpdateContent(ctx context.Context, messageID string, content string) (entity.Message, error) {
	f.updateContentCalls++
	return entity.Message{ID: messageID, Content: content}, nil
}
func (f *fakeMessageRepo) UpdateRegeneratedContent(ctx context.Context, messageID string, content string, safetyFlag *string, crisisTier *string) (entity.Message, error) {
	return entity.Message{}, nil
}
func (f *fakeMessageRepo) UpdateStatusAndContent(ctx context.Context, messageID, status, content string) error {
	return nil
}
func (f *fakeMessageRepo) UpdateStatusContentAndMetadata(ctx context.Context, messageID, status, content string, safetyFlag *string, crisisTier *string, metadata map[string]any) error {
	return nil
}
func (f *fakeMessageRepo) NextTurnIndex(ctx context.Context, sessionID string) (int, error) {
	f.nextTurnIndexCalls++
	return 1, nil
}
func (f *fakeMessageRepo) ListBySession(ctx context.Context, sessionID string, limit int, offset int) ([]entity.Message, error) {
	f.listBySessionCalls++
	return nil, nil
}
func (f *fakeMessageRepo) ListIDsBySession(ctx context.Context, sessionID string) ([]string, error) {
	return nil, nil
}

type fakeAgenticClient struct {
	reply       string
	lastRequest AgenticChatRequest
}

func (f *fakeAgenticClient) Invoke(ctx context.Context, req AgenticChatRequest) (AgenticChatResponse, error) {
	f.lastRequest = req
	return AgenticChatResponse{
		UserID:    req.UserID,
		SessionID: req.SessionID,
		Reply:     f.reply,
	}, nil
}
func (f *fakeAgenticClient) Stream(ctx context.Context, req AgenticChatRequest, onEvent func(AgenticStreamEvent) error) (AgenticChatResponse, error) {
	return AgenticChatResponse{}, nil
}
func (f *fakeAgenticClient) SynthesizeSpeech(ctx context.Context, req SynthesizeSpeechRequest) (SynthesizeSpeechResponse, error) {
	return SynthesizeSpeechResponse{}, nil
}
func (f *fakeAgenticClient) TranscribeSpeech(ctx context.Context, req TranscribeSpeechRequest) (TranscribeSpeechResponse, error) {
	return TranscribeSpeechResponse{}, nil
}
func (f *fakeAgenticClient) PurgeSessionMemory(ctx context.Context, sessionID string, messageIDs []string) error {
	return nil
}

func newTestUsecase(session entity.Session, reply string) (*ChatUsecase, *fakeSessionRepo, *fakeMessageRepo, *fakeAgenticClient) {
	sessions := &fakeSessionRepo{session: session}
	messages := &fakeMessageRepo{}
	agentic := &fakeAgenticClient{reply: reply}
	uc := NewChatUsecase(sessions, messages, nil, agentic, nil)
	return uc, sessions, messages, agentic
}

func TestSendMessage_ConfessionChannel_NeverTouchesMessageRepository(t *testing.T) {
	session := entity.Session{
		ID:      "22222222-2222-4222-8222-222222222222",
		UserID:  "11111111-1111-4111-8111-111111111111",
		Title:   "Confession Space",
		Channel: entity.ChannelConfession,
	}
	uc, sessionRepo, messageRepo, agentic := newTestUsecase(session, "balasan AXIS")

	out, err := uc.SendMessage(context.Background(), SendMessageInput{
		UserID:    session.UserID,
		SessionID: session.ID,
		Message:   "ini rahasia yang gak boleh kesimpen",
	})
	if err != nil {
		t.Fatalf("SendMessage returned error: %v", err)
	}

	if messageRepo.appendCalls != 0 {
		t.Fatalf("expected Append to never be called for confession channel, got %d calls", messageRepo.appendCalls)
	}
	if messageRepo.nextTurnIndexCalls != 0 {
		t.Fatalf("expected NextTurnIndex to never be called for confession channel, got %d calls", messageRepo.nextTurnIndexCalls)
	}
	if messageRepo.listBySessionCalls != 0 {
		t.Fatalf("expected ListBySession to never be called for confession channel, got %d calls", messageRepo.listBySessionCalls)
	}

	// The response DTOs must still be usable even though nothing was persisted.
	if out.UserMessage.ID == "" {
		t.Fatal("expected a generated (non-empty) user message id even without persistence")
	}
	if out.UserMessage.Content != "ini rahasia yang gak boleh kesimpen" {
		t.Fatalf("unexpected user message content: %q", out.UserMessage.Content)
	}
	if out.Assistant.ID == "" {
		t.Fatal("expected a generated (non-empty) assistant message id even without persistence")
	}
	if out.Assistant.Content != "balasan AXIS" {
		t.Fatalf("unexpected assistant content: %q", out.Assistant.Content)
	}

	// Session-level bookkeeping (turn counter) is fine to keep -- it carries
	// no message content, unlike the message rows this test guards against.
	if sessionRepo.incrementCalls != 1 {
		t.Fatalf("expected session turn counter to still increment, got %d calls", sessionRepo.incrementCalls)
	}

	if !agentic.lastRequest.ConfessionMode {
		t.Fatal("expected ConfessionMode=true to be forwarded to agentic")
	}
}

func TestSendMessage_NormalChannel_StillPersistsMessages(t *testing.T) {
	session := entity.Session{
		ID:      "22222222-2222-4222-8222-222222222222",
		UserID:  "11111111-1111-4111-8111-111111111111",
		Title:   "Obrolan biasa",
		Channel: entity.ChannelText,
	}
	uc, _, messageRepo, agentic := newTestUsecase(session, "balasan AXIS")

	_, err := uc.SendMessage(context.Background(), SendMessageInput{
		UserID:    session.UserID,
		SessionID: session.ID,
		Message:   "halo AXIS",
	})
	if err != nil {
		t.Fatalf("SendMessage returned error: %v", err)
	}

	if messageRepo.appendCalls != 2 {
		t.Fatalf("expected Append to be called twice (user + assistant) for a normal channel, got %d", messageRepo.appendCalls)
	}
	if messageRepo.nextTurnIndexCalls != 1 {
		t.Fatalf("expected NextTurnIndex to be called once, got %d", messageRepo.nextTurnIndexCalls)
	}
	if messageRepo.listBySessionCalls != 1 {
		t.Fatalf("expected ListBySession to be called once, got %d", messageRepo.listBySessionCalls)
	}
	if agentic.lastRequest.ConfessionMode {
		t.Fatal("expected ConfessionMode=false for a normal text channel session")
	}
}
