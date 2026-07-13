package usecase_test

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/domain/entity"
	"github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/usecase"
	apperrors "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/errors"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/googleauth"
)

// fakeUserRepo is in-memory stand-in.
type fakeUserRepository struct {
	byID    map[string]*entity.User
	byEmail map[string]*entity.User
	byGoogle map[string]*entity.User
	nextID  int
}

func newFakeUserRepository() *fakeUserRepository {
	return &fakeUserRepository{
		byID:     map[string]*entity.User{},
		byEmail:  map[string]*entity.User{},
		byGoogle: map[string]*entity.User{},
	}
}

func (f *fakeUserRepository) Create(_ context.Context, user entity.User) (entity.User, error) {
	if user.Email != "" {
		if _, exists := f.byEmail[user.Email]; exists {
			return entity.User{}, apperrors.Conflict("email is already registered")
		}
	}
	f.nextID++
	user.ID = "user-" + time.Now().Format("150405.000000000") + "-" + string(rune('a'+f.nextID))
	user.AccountStatus = entity.UserStatusActive
	user.CreatedAt = time.Now()
	user.UpdatedAt = time.Now()
	stored := user
	f.byID[user.ID] = &stored
	if user.Email != "" {
		f.byEmail[user.Email] = &stored
	}
	if user.GoogleID != "" {
		f.byGoogle[user.GoogleID] = &stored
	}
	return stored, nil
}

func (f *fakeUserRepository) FindByEmail(_ context.Context, email string) (*entity.User, error) {
	if u, ok := f.byEmail[email]; ok {
		return u, nil
	}
	return nil, nil
}

func (f *fakeUserRepository) FindByID(_ context.Context, id string) (*entity.User, error) {
	if u, ok := f.byID[id]; ok {
		return u, nil
	}
	return nil, nil
}

func (f *fakeUserRepository) FindByGoogleID(_ context.Context, googleID string) (*entity.User, error) {
	if u, ok := f.byGoogle[googleID]; ok {
		return u, nil
	}
	return nil, nil
}

func (f *fakeUserRepository) TouchLastLogin(_ context.Context, _ string) error { return nil }

func (f *fakeUserRepository) UpdateProfile(_ context.Context, user entity.User) (entity.User, error) {
	return user, nil
}

func (f *fakeUserRepository) SoftDeleteAccount(_ context.Context, _ string) error { return nil }

func (f *fakeUserRepository) CreateRefreshToken(_ context.Context, _ entity.RefreshToken) error {
	return nil
}

func (f *fakeUserRepository) FindRefreshToken(_ context.Context, _ string) (*entity.RefreshToken, error) {
	return nil, nil
}

func (f *fakeUserRepository) RevokeRefreshToken(_ context.Context, _ string) error { return nil }

func (f *fakeUserRepository) RevokeAllRefreshTokens(_ context.Context, _ string) error { return nil }

func (f *fakeUserRepository) BlacklistAccessToken(_ context.Context, _ string, _ string, _ time.Time) error {
	return nil
}

type fakeGoogleVerifier struct {
	claims *googleauth.Claims
	err    error
}

func (f fakeGoogleVerifier) Verify(_ context.Context, _ string, _ string) (*googleauth.Claims, error) {
	if f.err != nil {
		return nil, f.err
	}
	return f.claims, nil
}

func TestGoogleLogin_NewUser_CreatesAccountWithoutPassword(t *testing.T) {
	t.Setenv("JWT_SECRET", "test-secret")
	t.Setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")

	repo := newFakeUserRepository()
	verifier := fakeGoogleVerifier{claims: &googleauth.Claims{
		Subject: "google-sub-1", Email: "new.student@example.com",
		EmailVerified: true, Name: "New Student",
	}}
	uc := usecase.NewAuthUsecase(repo, nil, verifier)

	out, err := uc.GoogleLogin(context.Background(), usecase.GoogleLoginInput{IDToken: "fake-token"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if out.User.Email != "new.student@example.com" {
		t.Errorf("email = %q", out.User.Email)
	}
	if out.Token == "" {
		t.Error("expected a non-empty access token")
	}
	created := repo.byEmail["new.student@example.com"]
	if created == nil {
		t.Fatal("expected a user to have been created")
	}
	if created.PasswordHash != "" {
		t.Errorf("expected no password hash for a Google-only account, got %q", created.PasswordHash)
	}
	if created.GoogleID != "google-sub-1" {
		t.Errorf("google id = %q", created.GoogleID)
	}
}

func TestGoogleLogin_ExistingGoogleID_LogsInDirectly(t *testing.T) {
	t.Setenv("JWT_SECRET", "test-secret")
	t.Setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")

	repo := newFakeUserRepository()
	existing := entity.User{
		ID: "user-existing", Email: "returning@example.com", DisplayName: "Returning",
		GoogleID: "google-sub-2", AccountStatus: entity.UserStatusActive,
	}
	repo.byID[existing.ID] = &existing
	repo.byEmail[existing.Email] = &existing
	repo.byGoogle[existing.GoogleID] = &existing

	verifier := fakeGoogleVerifier{claims: &googleauth.Claims{
		Subject: "google-sub-2", Email: "returning@example.com", EmailVerified: true,
	}}
	uc := usecase.NewAuthUsecase(repo, nil, verifier)

	out, err := uc.GoogleLogin(context.Background(), usecase.GoogleLoginInput{IDToken: "fake-token"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if out.User.ID != "user-existing" {
		t.Errorf("expected to log into the existing account, got user id %q", out.User.ID)
	}
}

func TestGoogleLogin_ExistingEmailWithoutGoogleID_RejectedNotAutoLinked(t *testing.T) {
	// reject-link
	t.Setenv("JWT_SECRET", "test-secret")
	t.Setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")

	repo := newFakeUserRepository()
	existing := entity.User{
		ID: "user-password-based", Email: "sameemail@example.com", DisplayName: "Password User",
		PasswordHash: "$2a$10$fakehash", AccountStatus: entity.UserStatusActive,
	}
	repo.byID[existing.ID] = &existing
	repo.byEmail[existing.Email] = &existing

	verifier := fakeGoogleVerifier{claims: &googleauth.Claims{
		Subject: "google-sub-3", Email: "sameemail@example.com", EmailVerified: true,
	}}
	uc := usecase.NewAuthUsecase(repo, nil, verifier)

	_, err := uc.GoogleLogin(context.Background(), usecase.GoogleLoginInput{IDToken: "fake-token"})
	if err == nil {
		t.Fatal("expected an error rejecting the login, got nil")
	}
	var appErr *apperrors.Error
	if !errors.As(err, &appErr) || appErr.Code != "conflict" {
		t.Errorf("expected a conflict apperrors.Error, got %v", err)
	}
	if repo.byID["user-password-based"].GoogleID != "" {
		t.Error("the existing password account must NOT have been auto-linked")
	}
}

func TestGoogleLogin_UnverifiedEmail_Rejected(t *testing.T) {
	t.Setenv("JWT_SECRET", "test-secret")
	t.Setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")

	repo := newFakeUserRepository()
	verifier := fakeGoogleVerifier{claims: &googleauth.Claims{
		Subject: "google-sub-4", Email: "unverified@example.com", EmailVerified: false,
	}}
	uc := usecase.NewAuthUsecase(repo, nil, verifier)

	_, err := uc.GoogleLogin(context.Background(), usecase.GoogleLoginInput{IDToken: "fake-token"})
	if err == nil {
		t.Fatal("expected an error for an unverified email, got nil")
	}
	if len(repo.byEmail) != 0 {
		t.Error("expected no account to be created for an unverified email")
	}
}

func TestGoogleLogin_InvalidToken_RejectedAsUnauthorized(t *testing.T) {
	t.Setenv("JWT_SECRET", "test-secret")
	t.Setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")

	repo := newFakeUserRepository()
	verifier := fakeGoogleVerifier{err: errors.New("signature mismatch")}
	uc := usecase.NewAuthUsecase(repo, nil, verifier)

	_, err := uc.GoogleLogin(context.Background(), usecase.GoogleLoginInput{IDToken: "garbage"})
	if err == nil {
		t.Fatal("expected an error for a verifier failure, got nil")
	}
	var appErr *apperrors.Error
	if !errors.As(err, &appErr) || appErr.Code != "unauthorized" {
		t.Errorf("expected an unauthorized apperrors.Error, got %v", err)
	}
}

func TestGoogleLogin_MissingClientIDConfig_RejectedWithClearMessage(t *testing.T) {
	t.Setenv("JWT_SECRET", "test-secret")
	t.Setenv("GOOGLE_CLIENT_ID", "")

	repo := newFakeUserRepository()
	verifier := fakeGoogleVerifier{claims: &googleauth.Claims{
		Subject: "google-sub-5", Email: "x@example.com", EmailVerified: true,
	}}
	uc := usecase.NewAuthUsecase(repo, nil, verifier)

	_, err := uc.GoogleLogin(context.Background(), usecase.GoogleLoginInput{IDToken: "fake-token"})
	if err == nil {
		t.Fatal("expected an error when GOOGLE_CLIENT_ID is not configured, got nil")
	}
}

func TestGoogleLogin_EmptyIDToken_Rejected(t *testing.T) {
	t.Setenv("JWT_SECRET", "test-secret")
	t.Setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")

	repo := newFakeUserRepository()
	uc := usecase.NewAuthUsecase(repo, nil, fakeGoogleVerifier{})

	_, err := uc.GoogleLogin(context.Background(), usecase.GoogleLoginInput{IDToken: "   "})
	if err == nil {
		t.Fatal("expected an error for an empty id token, got nil")
	}
}

func TestGoogleLogin_SuspendedExistingAccount_Rejected(t *testing.T) {
	t.Setenv("JWT_SECRET", "test-secret")
	t.Setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")

	repo := newFakeUserRepository()
	suspended := entity.User{
		ID: "user-suspended", Email: "suspended@example.com",
		AccountStatus: entity.UserStatusSuspended,
	}
	repo.byID[suspended.ID] = &suspended
	repo.byEmail[suspended.Email] = &suspended

	verifier := fakeGoogleVerifier{claims: &googleauth.Claims{
		Subject: "google-sub-6", Email: "suspended@example.com", EmailVerified: true,
	}}
	uc := usecase.NewAuthUsecase(repo, nil, verifier)

	_, err := uc.GoogleLogin(context.Background(), usecase.GoogleLoginInput{IDToken: "fake-token"})
	if err == nil {
		t.Fatal("expected an error for a suspended account, got nil")
	}
}
