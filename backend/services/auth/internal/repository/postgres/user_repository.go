package postgres

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/domain/entity"
	apperrors "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/errors"
	"github.com/lib/pq"
)

type UserRepository struct {
	db *sql.DB
}

func NewUserRepository(db *sql.DB) *UserRepository {
	return &UserRepository{db: db}
}

func (r *UserRepository) Create(ctx context.Context, user entity.User) (entity.User, error) {
	row := r.db.QueryRowContext(ctx, `
		INSERT INTO users (
		    email, display_name, password_hash, google_id, preferred_language,
		    safety_terms_accepted, safety_terms_version, safety_terms_accepted_at
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, CASE WHEN $6 THEN NOW() ELSE NULL END)
		RETURNING id, email, COALESCE(phone, ''), display_name, COALESCE(password_hash, ''),
		          COALESCE(google_id, ''),
		          preferred_language, COALESCE(preferred_voice_id, ''), COALESCE(preferred_tts_model, ''),
		          COALESCE(preferred_response_model, ''), COALESCE(gender, ''),
		          safety_terms_accepted, COALESCE(safety_terms_version, ''), safety_terms_accepted_at,
		          onboarding_complete, account_status,
		          created_at, updated_at, last_login_at
	`, user.Email, user.DisplayName, optionalNullString(user.PasswordHash), optionalNullString(user.GoogleID),
		user.PreferredLanguage, user.SafetyTermsAccepted, optionalNullString(user.SafetyTermsVersion))
	created, err := scanUser(row)
	if err != nil {
		var pqErr *pq.Error
		if errors.As(err, &pqErr) && string(pqErr.Code) == "23505" {
			if pqErr.Constraint == "users_google_id_idx" {
				return entity.User{}, apperrors.Conflict("google account is already linked to another user")
			}
			return entity.User{}, apperrors.Conflict("email is already registered")
		}
		return entity.User{}, fmt.Errorf("user create: %w", err)
	}
	return created, nil
}

func (r *UserRepository) FindByEmail(ctx context.Context, email string) (*entity.User, error) {
	row := r.db.QueryRowContext(ctx, `
		SELECT id, email, COALESCE(phone, ''), display_name, COALESCE(password_hash, ''),
		       COALESCE(google_id, ''),
		       preferred_language, COALESCE(preferred_voice_id, ''), COALESCE(preferred_tts_model, ''),
		       COALESCE(preferred_response_model, ''), COALESCE(gender, ''),
		       safety_terms_accepted, COALESCE(safety_terms_version, ''), safety_terms_accepted_at,
		       onboarding_complete, account_status,
		       created_at, updated_at, last_login_at
		FROM users
		WHERE email = $1
		  AND deleted_at IS NULL
	`, email)
	user, err := scanUser(row)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("user find by email: %w", err)
	}
	return &user, nil
}

func (r *UserRepository) FindByID(ctx context.Context, userID string) (*entity.User, error) {
	row := r.db.QueryRowContext(ctx, `
		SELECT id, email, COALESCE(phone, ''), display_name, COALESCE(password_hash, ''),
		       COALESCE(google_id, ''),
		       preferred_language, COALESCE(preferred_voice_id, ''), COALESCE(preferred_tts_model, ''),
		       COALESCE(preferred_response_model, ''), COALESCE(gender, ''),
		       safety_terms_accepted, COALESCE(safety_terms_version, ''), safety_terms_accepted_at,
		       onboarding_complete, account_status,
		       created_at, updated_at, last_login_at
		FROM users
		WHERE id = $1
		  AND deleted_at IS NULL
	`, userID)
	user, err := scanUser(row)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("user find by id: %w", err)
	}
	return &user, nil
}

func (r *UserRepository) FindByGoogleID(ctx context.Context, googleID string) (*entity.User, error) {
	row := r.db.QueryRowContext(ctx, `
		SELECT id, email, COALESCE(phone, ''), display_name, COALESCE(password_hash, ''),
		       COALESCE(google_id, ''),
		       preferred_language, COALESCE(preferred_voice_id, ''), COALESCE(preferred_tts_model, ''),
		       COALESCE(preferred_response_model, ''), COALESCE(gender, ''),
		       safety_terms_accepted, COALESCE(safety_terms_version, ''), safety_terms_accepted_at,
		       onboarding_complete, account_status,
		       created_at, updated_at, last_login_at
		FROM users
		WHERE google_id = $1
		  AND deleted_at IS NULL
	`, googleID)
	user, err := scanUser(row)
	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("user find by google id: %w", err)
	}
	return &user, nil
}

func (r *UserRepository) TouchLastLogin(ctx context.Context, userID string) error {
	_, err := r.db.ExecContext(ctx, `
		UPDATE users
		SET last_login_at = NOW(),
		    updated_at = NOW()
		WHERE id = $1
	`, userID)
	if err != nil {
		return fmt.Errorf("user touch last login: %w", err)
	}
	return nil
}

func (r *UserRepository) UpdateProfile(ctx context.Context, user entity.User) (entity.User, error) {
	row := r.db.QueryRowContext(ctx, `
		UPDATE users
		SET display_name = $2,
		    preferred_language = $3,
		    preferred_voice_id = NULLIF($4, ''),
		    preferred_tts_model = NULLIF($5, ''),
		    preferred_response_model = NULLIF($6, ''),
		    gender = NULLIF($9, ''),
		    safety_terms_accepted = CASE WHEN $7 THEN TRUE ELSE safety_terms_accepted END,
		    safety_terms_version = CASE WHEN $7 THEN NULLIF($8, '') ELSE safety_terms_version END,
		    safety_terms_accepted_at = CASE WHEN $7 THEN COALESCE(safety_terms_accepted_at, NOW()) ELSE safety_terms_accepted_at END,
		    updated_at = NOW()
		WHERE id = $1
		  AND deleted_at IS NULL
		RETURNING id, email, COALESCE(phone, ''), display_name, COALESCE(password_hash, ''),
		          COALESCE(google_id, ''),
		          preferred_language, COALESCE(preferred_voice_id, ''), COALESCE(preferred_tts_model, ''),
		          COALESCE(preferred_response_model, ''), COALESCE(gender, ''),
		          safety_terms_accepted, COALESCE(safety_terms_version, ''), safety_terms_accepted_at,
		          onboarding_complete, account_status,
		          created_at, updated_at, last_login_at
	`, user.ID, user.DisplayName, user.PreferredLanguage, user.PreferredVoiceID, user.PreferredTTSModel, user.PreferredResponseModel, user.SafetyTermsAccepted, user.SafetyTermsVersion, user.Gender)
	updated, err := scanUser(row)
	if err != nil {
		if err == sql.ErrNoRows {
			return entity.User{}, apperrors.NotFound("user not found")
		}
		return entity.User{}, fmt.Errorf("user update profile: %w", err)
	}
	return updated, nil
}

// SoftDeleteAccount anonimkan data pribadi, tandai akun sebagai terhapus.
func (r *UserRepository) SoftDeleteAccount(ctx context.Context, userID string) error {
	res, err := r.db.ExecContext(ctx, `
		UPDATE users
		SET email = 'deleted-' || id || '@deleted.axis',
		    display_name = 'Pengguna terhapus',
		    phone = NULL,
		    password_hash = NULL,
		    google_id = NULL,
		    preferred_voice_id = NULL,
		    preferred_tts_model = NULL,
		    preferred_response_model = NULL,
		    gender = NULL,
		    account_status = 'deleted',
		    deleted_at = NOW(),
		    updated_at = NOW()
		WHERE id = $1
		  AND deleted_at IS NULL
	`, userID)
	if err != nil {
		return fmt.Errorf("user soft delete: %w", err)
	}
	affected, err := res.RowsAffected()
	if err != nil {
		return fmt.Errorf("user soft delete rows affected: %w", err)
	}
	if affected == 0 {
		return apperrors.NotFound("user not found")
	}
	return nil
}

func (r *UserRepository) CreateRefreshToken(ctx context.Context, token entity.RefreshToken) error {
	_, err := r.db.ExecContext(ctx, `
		INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
		VALUES ($1, $2, $3)
	`, token.UserID, token.TokenHash, token.ExpiresAt)
	if err != nil {
		return fmt.Errorf("refresh token create: %w", err)
	}
	return nil
}

func (r *UserRepository) FindRefreshToken(ctx context.Context, tokenHash string) (*entity.RefreshToken, error) {
	row := r.db.QueryRowContext(ctx, `
		SELECT id, user_id, token_hash, expires_at, revoked_at
		FROM refresh_tokens
		WHERE token_hash = $1
	`, tokenHash)
	var token entity.RefreshToken
	var revokedAt sql.NullTime
	if err := row.Scan(&token.ID, &token.UserID, &token.TokenHash, &token.ExpiresAt, &revokedAt); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("refresh token find: %w", err)
	}
	if revokedAt.Valid {
		token.RevokedAt = &revokedAt.Time
	}
	return &token, nil
}

func (r *UserRepository) RevokeRefreshToken(ctx context.Context, tokenHash string) error {
	_, err := r.db.ExecContext(ctx, `
		UPDATE refresh_tokens
		SET revoked_at = NOW()
		WHERE token_hash = $1
		  AND revoked_at IS NULL
	`, tokenHash)
	if err != nil {
		return fmt.Errorf("refresh token revoke: %w", err)
	}
	return nil
}

func (r *UserRepository) RevokeAllRefreshTokens(ctx context.Context, userID string) error {
	_, err := r.db.ExecContext(ctx, `
		UPDATE refresh_tokens
		SET revoked_at = NOW()
		WHERE user_id = $1
		  AND revoked_at IS NULL
	`, userID)
	if err != nil {
		return fmt.Errorf("refresh token revoke all: %w", err)
	}
	return nil
}

func (r *UserRepository) BlacklistAccessToken(ctx context.Context, jti string, userID string, expiresAt time.Time) error {
	_, err := r.db.ExecContext(ctx, `
		INSERT INTO token_blacklist (jti, user_id, expires_at)
		VALUES ($1, $2, $3)
		ON CONFLICT (jti) DO NOTHING
	`, jti, userID, expiresAt)
	if err != nil {
		return fmt.Errorf("access token blacklist: %w", err)
	}
	return nil
}

type rowScanner interface {
	Scan(dest ...any) error
}

func scanUser(row rowScanner) (entity.User, error) {
	var user entity.User
	var lastLogin sql.NullTime
	var safetyTermsAcceptedAt sql.NullTime
	if err := row.Scan(
		&user.ID,
		&user.Email,
		&user.Phone,
		&user.DisplayName,
		&user.PasswordHash,
		&user.GoogleID,
		&user.PreferredLanguage,
		&user.PreferredVoiceID,
		&user.PreferredTTSModel,
		&user.PreferredResponseModel,
		&user.Gender,
		&user.SafetyTermsAccepted,
		&user.SafetyTermsVersion,
		&safetyTermsAcceptedAt,
		&user.OnboardingComplete,
		&user.AccountStatus,
		&user.CreatedAt,
		&user.UpdatedAt,
		&lastLogin,
	); err != nil {
		return entity.User{}, err
	}
	if lastLogin.Valid {
		user.LastLoginAt = &lastLogin.Time
	}
	if safetyTermsAcceptedAt.Valid {
		user.SafetyTermsAcceptedAt = &safetyTermsAcceptedAt.Time
	}
	return user, nil
}

func optionalNullString(value string) any {
	if value == "" {
		return nil
	}
	return value
}
