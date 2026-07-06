// Package googleauth verifies Google Identity Services ID tokens (the
// credential a "Sign in with Google" button hands back to the frontend),
// without pulling in the full google.golang.org/api SDK.
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

// ClientIDFromEnv reads the OAuth Client ID (public, not a secret) this
// deployment expects Google ID tokens to be issued for.
func ClientIDFromEnv() string {
	return strings.TrimSpace(os.Getenv("GOOGLE_CLIENT_ID"))
}

// googleJWKSURL is Google's published JSON Web Key Set for verifying
// ID tokens signed by accounts.google.com. Keys rotate; keyfunc handles
// refetch/caching for us (default background refresh).
const googleJWKSURL = "https://www.googleapis.com/oauth2/v3/certs"

var googleIssuers = map[string]bool{
	"accounts.google.com":     true,
	"https://accounts.google.com": true,
}

// Claims is the subset of a Google ID token's payload this app trusts.
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
		// context.Background() on purpose: this ties the shared key-refresh
		// goroutine's lifetime, not a single caller's request.
		jwks, jwksErr = keyfunc.NewDefaultCtx(context.Background(), []string{googleJWKSURL})
	})
	return jwks, jwksErr
}

// Verify checks an ID token's signature against Google's current public
// keys, and validates issuer/audience/expiry. clientID must match the
// token's "aud" claim (the OAuth Client ID configured for this app in
// Google Cloud Console).
func Verify(ctx context.Context, idToken string, clientID string) (*Claims, error) {
	keys, err := loadJWKS()
	if err != nil {
		return nil, fmt.Errorf("load google jwks: %w", err)
	}
	return verifyWithKeyfunc(idToken, clientID, keys.KeyfuncCtx(ctx))
}

// verifyWithKeyfunc is the pure verification logic, decoupled from
// package-level JWKS loading so tests can inject their own signing key
// instead of depending on Google's live JWKS endpoint.
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
