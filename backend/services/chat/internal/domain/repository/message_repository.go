package repository

import (
	"context"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/domain/entity"
)

type MessageRepository interface {
	Append(ctx context.Context, message entity.Message) (entity.Message, error)
	UpdateContent(ctx context.Context, messageID string, content string) (entity.Message, error)
	UpdateRegeneratedContent(ctx context.Context, messageID string, content string, safetyFlag *string, crisisTier *string) (entity.Message, error)
	UpdateStatusAndContent(ctx context.Context, messageID, status, content string) error
	UpdateStatusContentAndMetadata(ctx context.Context, messageID, status, content string, metadata map[string]any) error
	NextTurnIndex(ctx context.Context, sessionID string) (int, error)
	ListBySession(ctx context.Context, sessionID string, limit int, offset int) ([]entity.Message, error)
	ListIDsBySession(ctx context.Context, sessionID string) ([]string, error)
}
