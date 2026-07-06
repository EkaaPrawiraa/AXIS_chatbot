package repository

import (
	"context"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/domain/entity"
)

type MoodRepository interface {
	Upsert(ctx context.Context, userID string, score int) (entity.Mood, error)
	ListRecent(ctx context.Context, userID string, days int) ([]entity.Mood, error)
}
