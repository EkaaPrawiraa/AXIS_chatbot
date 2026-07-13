package repository

import (
	"context"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/domain/entity"
)

type UserRepository interface {
	Create(ctx context.Context, user entity.User) (entity.User, error)
	FindByEmail(ctx context.Context, email string) (*entity.User, error)
	FindByID(ctx context.Context, userID string) (*entity.User, error)
	FindByGoogleID(ctx context.Context, googleID string) (*entity.User, error)
	TouchLastLogin(ctx context.Context, userID string) error
	UpdateProfile(ctx context.Context, user entity.User) (entity.User, error)
	SoftDeleteAccount(ctx context.Context, userID string) error

	// refresh&blacklist
	CreateRefreshToken(ctx context.Context, token entity.RefreshToken) error
	FindRefreshToken(ctx context.Context, tokenHash string) (*entity.RefreshToken, error)
	RevokeRefreshToken(ctx context.Context, tokenHash string) error
	RevokeAllRefreshTokens(ctx context.Context, userID string) error
	BlacklistAccessToken(ctx context.Context, jti string, userID string, expiresAt time.Time) error
}
