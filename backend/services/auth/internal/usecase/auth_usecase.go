package usecase

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"log/slog"
	"net/mail"
	"strings"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/domain/entity"
	"github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/domain/repository"
	axisauth "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/auth"
	apperrors "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/errors"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/googleauth"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/validator"
	"golang.org/x/crypto/bcrypt"
)

// refreshTTL adalah masa berlaku refresh token (30 hari). Access token tetap
// berumur pendek (24 jam) dan diperbarui melalui mekanisme rotasi refresh token.
const refreshTTL = 30 * 24 * time.Hour

// MemoryPurger deletes a user's KG/pgvector data. Enforced server-side in
// DeleteAccount so full deletion doesn't depend on the frontend correctly
// sequencing two separate API calls.
type MemoryPurger interface {
	PurgeAccount(ctx context.Context, userID string) error
}

// GoogleVerifier checks a Google ID token's signature/claims. Injected
// (rather than calling googleauth.Verify directly) so GoogleLogin can be
// unit-tested with a fake instead of depending on Google's live JWKS
// endpoint -- same reasoning as MemoryPurger above.
type GoogleVerifier interface {
	Verify(ctx context.Context, idToken string, clientID string) (*googleauth.Claims, error)
}

type defaultGoogleVerifier struct{}

func (defaultGoogleVerifier) Verify(ctx context.Context, idToken string, clientID string) (*googleauth.Claims, error) {
	return googleauth.Verify(ctx, idToken, clientID)
}

type AuthUsecase struct {
	users  repository.UserRepository
	memory MemoryPurger
	google GoogleVerifier
}

func NewAuthUsecase(users repository.UserRepository, memory MemoryPurger, google GoogleVerifier) *AuthUsecase {
	if google == nil {
		google = defaultGoogleVerifier{}
	}
	return &AuthUsecase{users: users, memory: memory, google: google}
}

type RegisterInput struct {
	Email               string
	Password            string
	DisplayName         string
	PreferredLanguage   string
	SafetyTermsAccepted bool
	SafetyTermsVersion  string
}

type LoginInput struct {
	Email    string
	Password string
}

type DeleteAccountInput struct {
	UserID   string
	Password string
}

type UpdateProfileInput struct {
	UserID                 string
	Name                   string
	PreferredLanguage      string
	PreferredVoiceID       string
	PreferredTTSModel      string
	PreferredResponseModel string
	Gender                 string
	SafetyTermsAccepted    bool
	SafetyTermsVersion     string
}

type AuthOutput struct {
	Token        string     `json:"token"`
	RefreshToken string     `json:"refreshToken,omitempty"`
	RefreshTTL   int64      `json:"refreshTtl,omitempty"`
	User         UserDTO    `json:"user"`
	TTL          int64      `json:"ttl"`
	Profile      ProfileDTO `json:"profile"`
}

// LogoutInput membawa data yang diperlukan untuk mencabut sesi pengguna.
type LogoutInput struct {
	UserID       string
	AccessJTI    string
	AccessExpiry time.Time
	RefreshToken string
}

type UserDTO struct {
	ID                     string `json:"id"`
	Email                  string `json:"email"`
	DisplayName            string `json:"displayName"`
	PreferredLanguage      string `json:"preferredLanguage"`
	PreferredVoiceID       string `json:"preferredVoiceId,omitempty"`
	PreferredTTSModel      string `json:"preferredTtsModel,omitempty"`
	PreferredResponseModel string `json:"preferredResponseModel,omitempty"`
	Gender                 string `json:"gender,omitempty"`
	SafetyTermsAccepted    bool   `json:"safetyTermsAccepted"`
	SafetyTermsVersion     string `json:"safetyTermsVersion,omitempty"`
	SafetyTermsAcceptedAt  int64  `json:"safetyTermsAcceptedAt,omitempty"`
	CreatedAt              int64  `json:"createdAt"`
	UpdatedAt              int64  `json:"updatedAt"`
}

type ProfileDTO struct {
	ID                     string   `json:"id"`
	UserID                 string   `json:"userId"`
	Name                   string   `json:"name"`
	InteractionStyle       string   `json:"interactionStyle"`
	ReflectionPreference   string   `json:"reflectionPreference"`
	CompanionTraits        []string `json:"companionTraits"`
	Language               string   `json:"language"`
	PreferredVoiceID       string   `json:"preferredVoiceId,omitempty"`
	PreferredTTSModel      string   `json:"preferredTtsModel,omitempty"`
	PreferredResponseModel string   `json:"preferredResponseModel,omitempty"`
	Gender                 string   `json:"gender,omitempty"`
	SafetyTermsAccepted    bool     `json:"safetyTermsAccepted"`
	SafetyTermsVersion     string   `json:"safetyTermsVersion,omitempty"`
	SafetyTermsAcceptedAt  int64    `json:"safetyTermsAcceptedAt,omitempty"`
	Bio                    string   `json:"bio,omitempty"`
	Goals                  []string `json:"goals,omitempty"`
	CreatedAt              int64    `json:"createdAt"`
	UpdatedAt              int64    `json:"updatedAt"`
}

func (u *AuthUsecase) Register(ctx context.Context, input RegisterInput) (AuthOutput, error) {
	email, displayName, lang, err := validateRegistration(input)
	if err != nil {
		return AuthOutput{}, err
	}
	hash, err := bcrypt.GenerateFromPassword([]byte(input.Password), bcrypt.DefaultCost)
	if err != nil {
		return AuthOutput{}, err
	}
	user, err := u.users.Create(ctx, entity.User{
		Email:               email,
		DisplayName:         displayName,
		PasswordHash:        string(hash),
		PreferredLanguage:   lang,
		SafetyTermsAccepted: input.SafetyTermsAccepted,
		SafetyTermsVersion:  defaultString(input.SafetyTermsVersion, "companion-safety-v1"),
	})
	if err != nil {
		return AuthOutput{}, err
	}
	token, err := newToken(user.ID)
	if err != nil {
		return AuthOutput{}, err
	}
	out := authOutput(token, user)
	if err := u.issueRefreshToken(ctx, user.ID, &out); err != nil {
		return AuthOutput{}, err
	}
	return out, nil
}

func (u *AuthUsecase) Login(ctx context.Context, input LoginInput) (AuthOutput, error) {
	email := normalizeEmail(input.Email)
	if email == "" || input.Password == "" {
		return AuthOutput{}, apperrors.Invalid("email and password are required")
	}
	user, err := u.users.FindByEmail(ctx, email)
	if err != nil {
		return AuthOutput{}, err
	}
	if user == nil || user.AccountStatus != entity.UserStatusActive {
		return AuthOutput{}, apperrors.Invalid("invalid email or password")
	}
	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(input.Password)); err != nil {
		return AuthOutput{}, apperrors.Invalid("invalid email or password")
	}
	_ = u.users.TouchLastLogin(ctx, user.ID)
	token, err := newToken(user.ID)
	if err != nil {
		return AuthOutput{}, err
	}
	out := authOutput(token, *user)
	if err := u.issueRefreshToken(ctx, user.ID, &out); err != nil {
		return AuthOutput{}, err
	}
	return out, nil
}

type GoogleLoginInput struct {
	IDToken string
}

// GoogleLogin memverifikasi ID token dari tombol "Sign in with Google" lalu
// mencari/membuat user berdasarkan hasilnya. Dua skenario:
//  1. google_id sudah pernah dipakai login sebelumnya -> langsung masuk ke
//     akun itu.
//  2. Belum pernah dan emailnya belum terdaftar sama sekali -> akun baru
//     dibuat tanpa password (password_hash NULL; lihat migration
//     022_google_oauth).
//
// Sengaja TIDAK auto-link ke akun password yang emailnya kebetulan sama
// (lihat error di bawah untuk kasus itu). Registrasi email/password di
// sistem ini tidak pernah memverifikasi kepemilikan email (tidak ada
// email konfirmasi) -- siapa pun bisa mendaftar pakai email orang lain.
// Kalau langkah ini auto-link berdasarkan email, penyerang bisa
// mendaftar duluan pakai email korban, lalu ketika korban asli akhirnya
// "Sign in with Google" pakai email itu, identitas Google korban yang
// SUDAH terverifikasi asli malah otomatis tersambung ke akun bikinan
// penyerang -- pengambilalihan akun penuh. Menolak di sini memaksa
// pengguna login pakai password dulu untuk akun lama; linking manual
// (kalau dibutuhkan nanti) harus jadi aksi eksplisit dari sesi yang
// sudah terautentikasi, bukan efek samping diam-diam saat login.
func (u *AuthUsecase) GoogleLogin(ctx context.Context, input GoogleLoginInput) (AuthOutput, error) {
	idToken := strings.TrimSpace(input.IDToken)
	if idToken == "" {
		return AuthOutput{}, apperrors.Invalid("google id token is required")
	}
	clientID := googleauth.ClientIDFromEnv()
	if clientID == "" {
		return AuthOutput{}, apperrors.Invalid("google sign-in is not configured on this server")
	}
	claims, err := u.google.Verify(ctx, idToken, clientID)
	if err != nil {
		return AuthOutput{}, apperrors.Unauthorized("invalid google sign-in")
	}
	// Google itself controls this claim (it's only true once the account's
	// email address has been confirmed via Google's own verification flow),
	// so an unverified email is not something a client can forge by hand --
	// but it IS something a legitimate Google account can genuinely have,
	// so reject explicitly rather than silently trusting an unconfirmed
	// address as this user's login identity.
	if !claims.EmailVerified {
		return AuthOutput{}, apperrors.Unauthorized("google account email is not verified")
	}

	user, err := u.users.FindByGoogleID(ctx, claims.Subject)
	if err != nil {
		return AuthOutput{}, err
	}
	if user == nil {
		existing, err := u.users.FindByEmail(ctx, claims.Email)
		if err != nil {
			return AuthOutput{}, err
		}
		if existing != nil {
			return AuthOutput{}, apperrors.Conflict(
				"an account with this email already exists -- log in with your password instead",
			)
		}
		displayName := defaultString(claims.Name, strings.SplitN(claims.Email, "@", 2)[0])
		created, err := u.users.Create(ctx, entity.User{
			Email:             claims.Email,
			DisplayName:       displayName,
			GoogleID:          claims.Subject,
			PreferredLanguage: "id",
		})
		if err != nil {
			return AuthOutput{}, err
		}
		user = &created
	}
	if user.AccountStatus != entity.UserStatusActive {
		return AuthOutput{}, apperrors.Invalid("account is not active")
	}
	_ = u.users.TouchLastLogin(ctx, user.ID)
	token, err := newToken(user.ID)
	if err != nil {
		return AuthOutput{}, err
	}
	out := authOutput(token, *user)
	if err := u.issueRefreshToken(ctx, user.ID, &out); err != nil {
		return AuthOutput{}, err
	}
	return out, nil
}

// Refresh memvalidasi refresh token, melakukan rotasi (mencabut token lama dan
// menerbitkan token baru), lalu mengembalikan access token baru.
func (u *AuthUsecase) Refresh(ctx context.Context, refreshToken string) (AuthOutput, error) {
	refreshToken = strings.TrimSpace(refreshToken)
	if refreshToken == "" {
		return AuthOutput{}, apperrors.Unauthorized("refresh token is required")
	}
	stored, err := u.users.FindRefreshToken(ctx, hashToken(refreshToken))
	if err != nil {
		return AuthOutput{}, err
	}
	if stored == nil || stored.RevokedAt != nil || stored.ExpiresAt.Before(time.Now().UTC()) {
		return AuthOutput{}, apperrors.Unauthorized("invalid or expired refresh token")
	}
	user, err := u.users.FindByID(ctx, stored.UserID)
	if err != nil {
		return AuthOutput{}, err
	}
	if user == nil || user.AccountStatus != entity.UserStatusActive {
		return AuthOutput{}, apperrors.Unauthorized("unauthorized")
	}
	// Rotasi: cabut token lama agar tidak dapat dipakai ulang.
	if err := u.users.RevokeRefreshToken(ctx, stored.TokenHash); err != nil {
		return AuthOutput{}, err
	}
	token, err := newToken(user.ID)
	if err != nil {
		return AuthOutput{}, err
	}
	out := authOutput(token, *user)
	if err := u.issueRefreshToken(ctx, user.ID, &out); err != nil {
		return AuthOutput{}, err
	}
	return out, nil
}

// Logout mencabut refresh token pengguna dan memasukkan jti access token ke
// daftar hitam (token blacklist) sehingga sesi tidak dapat diperpanjang.
func (u *AuthUsecase) Logout(ctx context.Context, input LogoutInput) error {
	if refreshToken := strings.TrimSpace(input.RefreshToken); refreshToken != "" {
		if err := u.users.RevokeRefreshToken(ctx, hashToken(refreshToken)); err != nil {
			return err
		}
	} else if strings.TrimSpace(input.UserID) != "" {
		if err := u.users.RevokeAllRefreshTokens(ctx, input.UserID); err != nil {
			return err
		}
	}
	if jti := strings.TrimSpace(input.AccessJTI); jti != "" && strings.TrimSpace(input.UserID) != "" {
		expiry := input.AccessExpiry
		if expiry.IsZero() {
			expiry = time.Now().UTC().Add(axisauth.DefaultTTL)
		}
		if err := u.users.BlacklistAccessToken(ctx, jti, input.UserID, expiry); err != nil {
			return err
		}
	}
	return nil
}

func (u *AuthUsecase) issueRefreshToken(ctx context.Context, userID string, out *AuthOutput) error {
	plain, hash, err := newRefreshToken()
	if err != nil {
		return err
	}
	expiresAt := time.Now().UTC().Add(refreshTTL)
	if err := u.users.CreateRefreshToken(ctx, entity.RefreshToken{
		UserID:    userID,
		TokenHash: hash,
		ExpiresAt: expiresAt,
	}); err != nil {
		return err
	}
	out.RefreshToken = plain
	out.RefreshTTL = int64(refreshTTL.Seconds())
	return nil
}

func (u *AuthUsecase) CurrentSession(ctx context.Context, userID string) (AuthOutput, error) {
	if err := validateUUID("userId", userID); err != nil {
		return AuthOutput{}, err
	}
	user, err := u.users.FindByID(ctx, userID)
	if err != nil {
		return AuthOutput{}, err
	}
	if user == nil || user.AccountStatus != entity.UserStatusActive {
		return AuthOutput{}, apperrors.Unauthorized("unauthorized")
	}
	return authOutput("", *user), nil
}

func (u *AuthUsecase) GetProfile(ctx context.Context, userID string) (ProfileDTO, error) {
	if err := validateUUID("userId", userID); err != nil {
		return ProfileDTO{}, err
	}
	user, err := u.users.FindByID(ctx, userID)
	if err != nil {
		return ProfileDTO{}, err
	}
	if user == nil {
		return ProfileDTO{}, apperrors.NotFound("user not found")
	}
	return profileDTO(*user), nil
}

func (u *AuthUsecase) UpdateProfile(ctx context.Context, input UpdateProfileInput) (ProfileDTO, error) {
	if err := validateUUID("userId", input.UserID); err != nil {
		return ProfileDTO{}, err
	}
	current, err := u.users.FindByID(ctx, input.UserID)
	if err != nil {
		return ProfileDTO{}, err
	}
	if current == nil {
		return ProfileDTO{}, apperrors.NotFound("user not found")
	}
	name := strings.TrimSpace(input.Name)
	if name == "" {
		name = current.DisplayName
	}
	if len([]rune(name)) > 100 {
		return ProfileDTO{}, apperrors.InvalidField("name", "name must be at most 100 characters")
	}
	lang := normalizeLanguage(input.PreferredLanguage)
	if lang == "" {
		lang = current.PreferredLanguage
	}
	voiceID := strings.TrimSpace(input.PreferredVoiceID)
	if voiceID == "" {
		voiceID = current.PreferredVoiceID
	}
	if len([]rune(voiceID)) > 120 {
		return ProfileDTO{}, apperrors.InvalidField("preferredVoiceId", "preferredVoiceId must be at most 120 characters")
	}
	ttsModel := strings.TrimSpace(input.PreferredTTSModel)
	if ttsModel == "" {
		ttsModel = current.PreferredTTSModel
	}
	if ttsModel == "" {
		ttsModel = "v2_5_turbo"
	}
	responseModel, err := normalizeResponseModel(input.PreferredResponseModel)
	if err != nil {
		return ProfileDTO{}, err
	}
	if responseModel == "" {
		responseModel = current.PreferredResponseModel
	}
	if responseModel == "" {
		responseModel = "gpt-5.4-nano"
	}
	gender := strings.TrimSpace(input.Gender)
	if gender == "" {
		gender = current.Gender
	} else if gender != "pria" && gender != "wanita" {
		return ProfileDTO{}, apperrors.InvalidField("gender", "gender must be 'pria' or 'wanita'")
	}
	updated, err := u.users.UpdateProfile(ctx, entity.User{
		ID:                     input.UserID,
		DisplayName:            name,
		PreferredLanguage:      lang,
		PreferredVoiceID:       voiceID,
		PreferredTTSModel:      ttsModel,
		PreferredResponseModel: responseModel,
		Gender:                 gender,
		SafetyTermsAccepted:    input.SafetyTermsAccepted,
		SafetyTermsVersion:     defaultString(input.SafetyTermsVersion, "companion-safety-v1"),
	})
	if err != nil {
		return ProfileDTO{}, err
	}
	return profileDTO(updated), nil
}

// DeleteAccount memverifikasi password pengguna, memurge seluruh data
// KG/pgvector via memory service, mencabut seluruh sesi aktif, lalu
// menganonimkan baris pengguna (soft delete).
//
// Purge dipanggil di sini (bukan hanya diandalkan dari frontend settings
// page) supaya "hapus akun = hapus semua data" adalah jaminan sisi server,
// bukan tergantung frontend memanggil dua endpoint terpisah dengan urutan
// yang benar. Kegagalan purge di-log dengan jelas dan TETAP melanjutkan
// soft delete Postgres -- database KG/pgvector belum punya mekanisme
// retry/antrian utk kompensasi kegagalan parsial, jadi memblokir hapus akun
// pengguna hanya karena memory service down akan lebih buruk daripada log
// yang bisa ditindaklanjuti manual.
func (u *AuthUsecase) DeleteAccount(ctx context.Context, input DeleteAccountInput) error {
	if err := validateUUID("userId", input.UserID); err != nil {
		return err
	}
	user, err := u.users.FindByID(ctx, input.UserID)
	if err != nil {
		return err
	}
	if user == nil || user.AccountStatus != entity.UserStatusActive {
		return apperrors.NotFound("user not found")
	}
	if err := bcrypt.CompareHashAndPassword([]byte(user.PasswordHash), []byte(input.Password)); err != nil {
		return apperrors.Invalid("invalid password")
	}
	if u.memory != nil {
		if err := u.memory.PurgeAccount(ctx, input.UserID); err != nil {
			slog.Error("memory purge-account failed during account deletion",
				"user_id", input.UserID, "error", err)
		}
	}
	if err := u.users.RevokeAllRefreshTokens(ctx, input.UserID); err != nil {
		return err
	}
	return u.users.SoftDeleteAccount(ctx, input.UserID)
}

func validateRegistration(input RegisterInput) (string, string, string, error) {
	email := normalizeEmail(input.Email)
	if _, err := mail.ParseAddress(email); err != nil {
		return "", "", "", apperrors.InvalidField("email", "email must be valid")
	}
	if len([]rune(input.Password)) < 8 {
		return "", "", "", apperrors.InvalidField("password", "password must be at least 8 characters")
	}
	displayName := strings.TrimSpace(input.DisplayName)
	if displayName == "" {
		return "", "", "", apperrors.InvalidField("displayName", "displayName is required")
	}
	if len([]rune(displayName)) > 100 {
		return "", "", "", apperrors.InvalidField("displayName", "displayName must be at most 100 characters")
	}
	lang := normalizeLanguage(input.PreferredLanguage)
	if lang == "" {
		lang = "id"
	}
	return email, displayName, lang, nil
}

func normalizeEmail(email string) string {
	return strings.ToLower(strings.TrimSpace(email))
}

func normalizeLanguage(lang string) string {
	lang = strings.ToLower(strings.TrimSpace(lang))
	if len(lang) != 2 {
		return ""
	}
	return lang
}

func normalizeResponseModel(model string) (string, error) {
	model = strings.TrimSpace(model)
	if model == "" {
		return "", nil
	}
	switch model {
	case "gpt-5.5", "gpt-5.4-nano":
		return model, nil
	default:
		return "", apperrors.InvalidField("preferredResponseModel", "preferredResponseModel is not supported")
	}
}

func validateUUID(field string, value string) error {
	value = strings.TrimSpace(value)
	if value == "" {
		return apperrors.InvalidField(field, field+" is required")
	}
	if !validator.UUID(value) {
		return apperrors.InvalidField(field, field+" must be a UUID")
	}
	return nil
}

func newToken(userID string) (string, error) {
	return axisauth.Sign(userID, 24*time.Hour, axisauth.SecretFromEnv())
}

// newRefreshToken menghasilkan refresh token acak (plaintext untuk klien) beserta
// hash SHA-256-nya (untuk disimpan di basis data).
func newRefreshToken() (string, string, error) {
	var b [32]byte
	if _, err := rand.Read(b[:]); err != nil {
		return "", "", err
	}
	plain := base64.RawURLEncoding.EncodeToString(b[:])
	return plain, hashToken(plain), nil
}

// hashToken mengembalikan hash SHA-256 (heksadesimal 64 karakter) dari sebuah token.
func hashToken(token string) string {
	sum := sha256.Sum256([]byte(token))
	return hex.EncodeToString(sum[:])
}

func authOutput(token string, user entity.User) AuthOutput {
	return AuthOutput{
		Token:   token,
		User:    userDTO(user),
		TTL:     int64((24 * time.Hour).Seconds()),
		Profile: profileDTO(user),
	}
}

func userDTO(user entity.User) UserDTO {
	return UserDTO{
		ID:                     user.ID,
		Email:                  user.Email,
		DisplayName:            user.DisplayName,
		PreferredLanguage:      user.PreferredLanguage,
		PreferredVoiceID:       user.PreferredVoiceID,
		PreferredTTSModel:      user.PreferredTTSModel,
		PreferredResponseModel: user.PreferredResponseModel,
		Gender:                 user.Gender,
		SafetyTermsAccepted:    user.SafetyTermsAccepted,
		SafetyTermsVersion:     user.SafetyTermsVersion,
		SafetyTermsAcceptedAt:  millisPtr(user.SafetyTermsAcceptedAt),
		CreatedAt:              millis(user.CreatedAt),
		UpdatedAt:              millis(user.UpdatedAt),
	}
}

func profileDTO(user entity.User) ProfileDTO {
	return ProfileDTO{
		ID:                     user.ID,
		UserID:                 user.ID,
		Name:                   user.DisplayName,
		InteractionStyle:       "empathetic",
		ReflectionPreference:   "guided",
		CompanionTraits:        []string{"supportive", "calm"},
		Language:               user.PreferredLanguage,
		PreferredVoiceID:       user.PreferredVoiceID,
		PreferredTTSModel:      user.PreferredTTSModel,
		PreferredResponseModel: user.PreferredResponseModel,
		Gender:                 user.Gender,
		SafetyTermsAccepted:    user.SafetyTermsAccepted,
		SafetyTermsVersion:     user.SafetyTermsVersion,
		SafetyTermsAcceptedAt:  millisPtr(user.SafetyTermsAcceptedAt),
		CreatedAt:              millis(user.CreatedAt),
		UpdatedAt:              millis(user.UpdatedAt),
	}
}

func millisPtr(t *time.Time) int64 {
	if t == nil {
		return 0
	}
	return millis(*t)
}

func defaultString(value string, fallback string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return fallback
	}
	return value
}

func millis(t time.Time) int64 {
	if t.IsZero() {
		return 0
	}
	return t.UnixMilli()
}
