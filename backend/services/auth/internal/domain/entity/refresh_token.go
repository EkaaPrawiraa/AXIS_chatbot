package entity

import "time"

// refreshToken: hash SHA-256, tokenPlaintext: client-only, not stored.
type RefreshToken struct {
	ID        string
	UserID    string
	TokenHash string
	ExpiresAt time.Time
	RevokedAt *time.Time
}
