package entity

import "time"

// refreshToken merepresentasikan token penyegaran (refresh token) hash SHA-256, sementara token plaintext hanya pernah ada di klien dan tidak disimpan.
type RefreshToken struct {
	ID        string
	UserID    string
	TokenHash string
	ExpiresAt time.Time
	RevokedAt *time.Time
}
