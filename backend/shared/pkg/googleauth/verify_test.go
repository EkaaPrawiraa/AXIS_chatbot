package googleauth

import (
	"crypto/rand"
	"crypto/rsa"
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

const testClientID = "test-client-id.apps.googleusercontent.com"

func newTestKeyPair(t *testing.T) (*rsa.PrivateKey, jwt.Keyfunc) {
	t.Helper()
	priv, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatalf("generate rsa key: %v", err)
	}
	keyfn := func(*jwt.Token) (any, error) {
		return &priv.PublicKey, nil
	}
	return priv, keyfn
}

func signGoogleToken(t *testing.T, priv *rsa.PrivateKey, claims googleClaims) string {
	t.Helper()
	token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	signed, err := token.SignedString(priv)
	if err != nil {
		t.Fatalf("sign token: %v", err)
	}
	return signed
}

func baseClaims() googleClaims {
	now := time.Now()
	return googleClaims{
		RegisteredClaims: jwt.RegisteredClaims{
			Issuer:    "https://accounts.google.com",
			Subject:   "google-user-123",
			Audience:  jwt.ClaimStrings{testClientID},
			ExpiresAt: jwt.NewNumericDate(now.Add(time.Hour)),
			IssuedAt:  jwt.NewNumericDate(now),
		},
		Email:         "student@example.com",
		EmailVerified: true,
		Name:          "Rafid Ahza",
	}
}

func TestVerifyWithKeyfunc_ValidToken(t *testing.T) {
	priv, keyfn := newTestKeyPair(t)
	token := signGoogleToken(t, priv, baseClaims())

	claims, err := verifyWithKeyfunc(token, testClientID, keyfn)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if claims.Subject != "google-user-123" {
		t.Errorf("subject = %q", claims.Subject)
	}
	if claims.Email != "student@example.com" {
		t.Errorf("email = %q", claims.Email)
	}
	if !claims.EmailVerified {
		t.Error("expected email_verified true")
	}
	if claims.Name != "Rafid Ahza" {
		t.Errorf("name = %q", claims.Name)
	}
}

func TestVerifyWithKeyfunc_EmailIsLowercased(t *testing.T) {
	priv, keyfn := newTestKeyPair(t)
	claims := baseClaims()
	claims.Email = "Student@Example.COM"
	token := signGoogleToken(t, priv, claims)

	out, err := verifyWithKeyfunc(token, testClientID, keyfn)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if out.Email != "student@example.com" {
		t.Errorf("email = %q, want lowercased", out.Email)
	}
}

func TestVerifyWithKeyfunc_WrongAudienceRejected(t *testing.T) {
	priv, keyfn := newTestKeyPair(t)
	claims := baseClaims()
	claims.Audience = jwt.ClaimStrings{"some-other-app.apps.googleusercontent.com"}
	token := signGoogleToken(t, priv, claims)

	if _, err := verifyWithKeyfunc(token, testClientID, keyfn); err == nil {
		t.Fatal("expected an error for mismatched audience, got nil")
	}
}

func TestVerifyWithKeyfunc_WrongIssuerRejected(t *testing.T) {
	priv, keyfn := newTestKeyPair(t)
	claims := baseClaims()
	claims.Issuer = "https://not-google.example.com"
	token := signGoogleToken(t, priv, claims)

	if _, err := verifyWithKeyfunc(token, testClientID, keyfn); err == nil {
		t.Fatal("expected an error for wrong issuer, got nil")
	}
}

func TestVerifyWithKeyfunc_ExpiredTokenRejected(t *testing.T) {
	priv, keyfn := newTestKeyPair(t)
	claims := baseClaims()
	claims.ExpiresAt = jwt.NewNumericDate(time.Now().Add(-time.Hour))
	token := signGoogleToken(t, priv, claims)

	if _, err := verifyWithKeyfunc(token, testClientID, keyfn); err == nil {
		t.Fatal("expected an error for expired token, got nil")
	}
}

func TestVerifyWithKeyfunc_WrongSigningKeyRejected(t *testing.T) {
	_, keyfn := newTestKeyPair(t)
	otherPriv, _ := newTestKeyPair(t)
	token := signGoogleToken(t, otherPriv, baseClaims())

	if _, err := verifyWithKeyfunc(token, testClientID, keyfn); err == nil {
		t.Fatal("expected an error for a token signed by a different key, got nil")
	}
}

func TestVerifyWithKeyfunc_UnverifiedEmailStillParsesButFlagsFalse(t *testing.T) {
	// ```Verify()``` just checks flag, no email ver.
	priv, keyfn := newTestKeyPair(t)
	claims := baseClaims()
	claims.EmailVerified = false
	token := signGoogleToken(t, priv, claims)

	out, err := verifyWithKeyfunc(token, testClientID, keyfn)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if out.EmailVerified {
		t.Error("expected EmailVerified to be false")
	}
}

func TestVerifyWithKeyfunc_MissingClientIDRejected(t *testing.T) {
	priv, keyfn := newTestKeyPair(t)
	token := signGoogleToken(t, priv, baseClaims())

	if _, err := verifyWithKeyfunc(token, "", keyfn); err == nil {
		t.Fatal("expected an error when clientID is empty, got nil")
	}
}
