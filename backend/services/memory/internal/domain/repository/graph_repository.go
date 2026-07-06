package repository

import (
	"context"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/domain/entity"
)

type GraphRepository interface {
	UpsertUser(ctx context.Context, user entity.User) error
	GetUser(ctx context.Context, userID string) (*entity.User, error)
	MarkOnboardingComplete(ctx context.Context, userID string) error

	OpenSession(ctx context.Context, session entity.Session) error
	CloseSession(ctx context.Context, sessionID string, summary string, sentimentAvg float64) error
	MarkPHQ9Administered(ctx context.Context, sessionID string) error

	WriteAssessment(ctx context.Context, assessment entity.Assessment) error
	GetLatestAssessment(ctx context.Context, userID string, instrument string) (*entity.Assessment, error)
	UpsertTopic(ctx context.Context, topic entity.Topic) error

	ListMemories(ctx context.Context, userID string, filter MemoryFilter) ([]entity.Memory, error)
	GetMemory(ctx context.Context, userID string, memoryID string) (*entity.Memory, error)
	CreateMemory(ctx context.Context, memory entity.Memory) (entity.Memory, error)
	UpdateMemory(ctx context.Context, memory entity.Memory) (entity.Memory, error)
	DeleteMemory(ctx context.Context, userID string, memoryID string) error

	GetEscalationSignals(ctx context.Context, userID string) (entity.EscalationSignals, error)
	ArchiveUserMemory(ctx context.Context, userID string) error
}

type MemoryFilter struct {
	Tags        []string
	SearchQuery string
	Limit       int
	Offset      int
}
