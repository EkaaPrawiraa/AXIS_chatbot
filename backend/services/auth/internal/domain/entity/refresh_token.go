package entity

import "time"

// buat nyimpen refreshToken, skip tokenPlaintext.
type RefreshToken struct {
	ID        string
	UserID    string
	TokenHash string
	ExpiresAt time.Time
	RevokedAt *time.Time
}
