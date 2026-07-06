package auth

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
	"time"
)

const (
	DefaultCookieName = "axis_session"
	CSRFCookieName    = "axis_csrf"
	DefaultTTL        = 24 * time.Hour
)

type Claims struct {
	Subject   string `json:"sub"`
	IssuedAt  int64  `json:"iat"`
	ExpiresAt int64  `json:"exp"`
	ID        string `json:"jti"`
}

func SecretFromEnv() string {
	return strings.TrimSpace(firstNonEmpty(
		os.Getenv("JWT_SECRET"),
		os.Getenv("AUTH_JWT_SECRET"),
		os.Getenv("AGENTIC_GATEWAY_PRIVATE_KEY"),
	))
}

func Sign(userID string, ttl time.Duration, secret string) (string, error) {
	userID = strings.TrimSpace(userID)
	if userID == "" {
		return "", errors.New("user id is required")
	}
	if secret == "" {
		return "", errors.New("jwt secret is required")
	}
	if ttl <= 0 {
		ttl = DefaultTTL
	}
	now := time.Now().UTC()
	claims := Claims{
		Subject:   userID,
		IssuedAt:  now.Unix(),
		ExpiresAt: now.Add(ttl).Unix(),
		ID:        randomID(),
	}
	header := map[string]string{"alg": "HS256", "typ": "JWT"}
	headerJSON, err := json.Marshal(header)
	if err != nil {
		return "", err
	}
	claimsJSON, err := json.Marshal(claims)
	if err != nil {
		return "", err
	}
	unsigned := encode(headerJSON) + "." + encode(claimsJSON)
	return unsigned + "." + signature(unsigned, secret), nil
}

func Verify(token string, secret string) (Claims, error) {
	if secret == "" {
		return Claims{}, errors.New("jwt secret is required")
	}
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return Claims{}, errors.New("invalid token")
	}
	unsigned := parts[0] + "." + parts[1]
	if !hmac.Equal([]byte(parts[2]), []byte(signature(unsigned, secret))) {
		return Claims{}, errors.New("invalid token signature")
	}
	payload, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return Claims{}, fmt.Errorf("decode token: %w", err)
	}
	var claims Claims
	if err := json.Unmarshal(payload, &claims); err != nil {
		return Claims{}, fmt.Errorf("parse token: %w", err)
	}
	if strings.TrimSpace(claims.Subject) == "" {
		return Claims{}, errors.New("token subject is required")
	}
	if claims.ExpiresAt <= time.Now().UTC().Unix() {
		return Claims{}, errors.New("token expired")
	}
	return claims, nil
}

func BearerToken(header string) string {
	if !strings.HasPrefix(header, "Bearer ") {
		return ""
	}
	return strings.TrimSpace(strings.TrimPrefix(header, "Bearer "))
}

func NewCSRFToken() string {
	return randomID()
}

func encode(value []byte) string {
	return base64.RawURLEncoding.EncodeToString(value)
}

func signature(unsigned string, secret string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	_, _ = mac.Write([]byte(unsigned))
	return encode(mac.Sum(nil))
}

func randomID() string {
	var b [16]byte
	if _, err := rand.Read(b[:]); err != nil {
		return fmt.Sprintf("%d", time.Now().UnixNano())
	}
	return encode(b[:])
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if value = strings.TrimSpace(value); value != "" {
			return value
		}
	}
	return ""
}
