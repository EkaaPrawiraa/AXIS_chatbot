package entity

import "time"

// RefreshToken merepresentasikan satu token penyegaran (refresh token) yang
// disimpan dalam bentuk hash SHA-256 pada basis data. Token plaintext hanya
// pernah ada di sisi klien dan tidak pernah disimpan.
type RefreshToken struct {
	ID        string
	UserID    string
	TokenHash string
	ExpiresAt time.Time
	RevokedAt *time.Time
}
