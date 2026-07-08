// `skip klo error`
package googleauth

import (
	"context"
	"fmt"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/MicahParks/keyfunc/v3"
	"github.com/golang-jwt/jwt/v5"
)

// `read env`
func ClientIDFromEnv() string {
	return strings.TrimSpace(os.Getenv("GOOGLE_CLIENT_ID"))
}

// googleJWKSURL refetch/caching.
const googleJWKSURL = "https://www.googleapis.com/oauth2/v3/certs"

var googleIssuers = map[string]bool{
	"accounts.google.com":     true,
	"https://accounts.google.com": true,
}

// subset id token payload
type Claims struct {
	Subject       string // "sub", Google's stable per-account id
	Email         string
	EmailVerified bool
	Name          string
}

type googleClaims struct {
	jwt.RegisteredClaims
	Email         string `json:"email"`
	EmailVerified bool   `json:"email_verified"`
	Name          string `json:"name"`
}

var (
	jwksOnce sync.Once
	jwksErr  error
	jwks     keyfunc.Keyfunc
)

func loadJWKS() (keyfunc.Keyfunc, error) {
	jwksOnce.Do(func() {
		// bg ctx 2go 1req 1call
		jwks, jwksErr = keyfunc.NewDefaultCtx(context.Background(), []string{googleJWKSURL})
	})
	return jwks, jwksErr
}

// verify signature, validate claims, match clientID
func Verify(ctx context.Context, idToken string, clientID string) (*Claims, error) {
	keys, err := loadJWKS()
	if err != nil {
		return nil, fmt.Errorf("load google jwks: %w", err)
	}
	return verifyWithKeyfunc(idToken, clientID, keys.KeyfuncCtx(ctx))
}

// verifyWithKeyfunc is pure verification logic, decoupled from JWKS loading.
func verifyWithKeyfunc(idToken string, clientID string, keyfn jwt.Keyfunc) (*Claims, error) {
	idToken = strings.TrimSpace(idToken)
	if idToken == "" {
		return nil, fmt.Errorf("id token is required")
	}
	if strings.TrimSpace(clientID) == "" {
		return nil, fmt.Errorf("google client id is not configured")
	}

	var claims googleClaims
	token, err := jwt.ParseWithClaims(idToken, &claims, keyfn,
		jwt.WithValidMethods([]string{"RS256"}),
		jwt.WithAudience(clientID),
		jwt.WithExpirationRequired(),
		jwt.WithLeeway(30*time.Second),
	)
	if err != nil {
		return nil, fmt.Errorf("verify google id token: %w", err)
	}
	if !token.Valid {
		return nil, fmt.Errorf("google id token is not valid")
	}
	if !googleIssuers[claims.Issuer] {
		return nil, fmt.Errorf("unexpected token issuer: %s", claims.Issuer)
	}
	if strings.TrimSpace(claims.Subject) == "" {
		return nil, fmt.Errorf("google id token is missing subject")
	}
	if strings.TrimSpace(claims.Email) == "" {
		return nil, fmt.Errorf("google id token is missing email")
	}

	return &Claims{
		Subject:       claims.Subject,
		Email:         strings.ToLower(strings.TrimSpace(claims.Email)),
		EmailVerified: claims.EmailVerified,
		Name:          strings.TrimSpace(claims.Name),
	}, nil
}
