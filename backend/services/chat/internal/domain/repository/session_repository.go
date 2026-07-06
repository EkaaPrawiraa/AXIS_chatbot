package repository

import (
	"context"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/domain/entity"
)

type SessionRepository interface {
	Create(ctx context.Context, session entity.Session) (entity.Session, error)
	FindByID(ctx context.Context, sessionID string) (*entity.Session, error)
	ListConversations(ctx context.Context, userID string, limit int, offset int) ([]entity.Conversation, error)
	UpdateTitle(ctx context.Context, sessionID string, title string) (entity.Session, error)
	Delete(ctx context.Context, sessionID string) error
	IncrementTurn(ctx context.Context, sessionID string) error
	MarkSafetyEscalated(ctx context.Context, sessionID string) error
}
