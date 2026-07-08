package handler

import (
	"encoding/json"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/auth/internal/usecase"
	axisauth "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/auth"
	apperrors "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/errors"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/middleware"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/response"
)

type AuthHandler struct {
	uc *usecase.AuthUsecase
}

func NewAuthHandler(uc *usecase.AuthUsecase) *AuthHandler {
	return &AuthHandler{uc: uc}
}

type registerRequest struct {
	Email               string `json:"email"`
	Password            string `json:"password"`
	DisplayName         string `json:"display_name"`
	DisplayNameCamel    string `json:"displayName"`
	PreferredLanguage   string `json:"preferred_language"`
	PreferredLangCamel  string `json:"preferredLanguage"`
	SafetyTermsAccepted bool   `json:"safetyTermsAccepted"`
	SafetyTermsVersion  string `json:"safetyTermsVersion"`
}

type loginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type googleLoginRequest struct {
	IDToken      string `json:"idToken"`
	IDTokenSnake string `json:"id_token"`
	Credential   string `json:"credential"` // Google Identity Services' own field name for the button callback
}

type updateProfileRequest struct {
	UserID                 string `json:"userId"`
	Name                   string `json:"name"`
	DisplayName            string `json:"displayName"`
	PreferredLanguage      string `json:"preferredLanguage"`
	Language               string `json:"language"`
	PreferredVoiceID       string `json:"preferredVoiceId"`
	PreferredTTSModel      string `json:"preferredTtsModel"`
	PreferredResponseModel string `json:"preferredResponseModel"`
	Gender                 string `json:"gender"`
	SafetyTermsAccepted    bool   `json:"safetyTermsAccepted"`
	SafetyTermsVersion     string `json:"safetyTermsVersion"`
}

func (h *AuthHandler) Register(w http.ResponseWriter, r *http.Request) {
	var req registerRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	displayName := firstNonEmpty(req.DisplayName, req.DisplayNameCamel)
	lang := firstNonEmpty(req.PreferredLanguage, req.PreferredLangCamel)
	out, err := h.uc.Register(r.Context(), usecase.RegisterInput{
		Email:               req.Email,
		Password:            req.Password,
		DisplayName:         displayName,
		PreferredLanguage:   lang,
		SafetyTermsAccepted: req.SafetyTermsAccepted,
		SafetyTermsVersion:  req.SafetyTermsVersion,
	})
	if err != nil {
		response.FromError(w, err)
		return
	}
	setAuthCookies(w, out.Token, out.TTL)
	setRefreshCookie(w, out.RefreshToken, out.RefreshTTL)
	response.Created(w, out)
}

func (h *AuthHandler) Login(w http.ResponseWriter, r *http.Request) {
	var req loginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	out, err := h.uc.Login(r.Context(), usecase.LoginInput{
		Email:    req.Email,
		Password: req.Password,
	})
	if err != nil {
		response.FromError(w, err)
		return
	}
	setAuthCookies(w, out.Token, out.TTL)
	setRefreshCookie(w, out.RefreshToken, out.RefreshTTL)
	response.OK(w, out)
}

func (h *AuthHandler) GoogleLogin(w http.ResponseWriter, r *http.Request) {
	var req googleLoginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	idToken := firstNonEmpty(req.IDToken, req.IDTokenSnake, req.Credential)
	out, err := h.uc.GoogleLogin(r.Context(), usecase.GoogleLoginInput{IDToken: idToken})
	if err != nil {
		response.FromError(w, err)
		return
	}
	setAuthCookies(w, out.Token, out.TTL)
	setRefreshCookie(w, out.RefreshToken, out.RefreshTTL)
	response.OK(w, out)
}

const refreshCookieName = "axis_refresh"

type refreshRequest struct {
	RefreshToken string `json:"refreshToken"`
}

// refresh token.
func (h *AuthHandler) Refresh(w http.ResponseWriter, r *http.Request) {
	refreshToken := ""
	if c, err := r.Cookie(refreshCookieName); err == nil {
		refreshToken = c.Value
	}
	if refreshToken == "" {
		var req refreshRequest
		_ = json.NewDecoder(r.Body).Decode(&req)
		refreshToken = req.RefreshToken
	}
	out, err := h.uc.Refresh(r.Context(), refreshToken)
	if err != nil {
		response.FromError(w, err)
		return
	}
	setAuthCookies(w, out.Token, out.TTL)
	setRefreshCookie(w, out.RefreshToken, out.RefreshTTL)
	response.OK(w, out)
}

// logout, delete token, clean cookies.
func (h *AuthHandler) Logout(w http.ResponseWriter, r *http.Request) {
	input := usecase.LogoutInput{UserID: requestUserID(r, "")}
	if c, err := r.Cookie(refreshCookieName); err == nil {
		input.RefreshToken = c.Value
	}
	if accessToken := readAccessToken(r); accessToken != "" {
		if claims, err := axisauth.Verify(accessToken, axisauth.SecretFromEnv()); err == nil {
			input.AccessJTI = claims.ID
			input.AccessExpiry = time.Unix(claims.ExpiresAt, 0).UTC()
			if input.UserID == "" {
				input.UserID = claims.Subject
			}
		}
	}
	if err := h.uc.Logout(r.Context(), input); err != nil {
		response.FromError(w, err)
		return
	}
	clearAuthCookies(w)
	response.OK(w, map[string]any{"loggedOut": true})
}

func (h *AuthHandler) CurrentSession(w http.ResponseWriter, r *http.Request) {
	userID := requestUserID(r, "")
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	out, err := h.uc.CurrentSession(r.Context(), userID)
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *AuthHandler) GetProfile(w http.ResponseWriter, r *http.Request) {
	out, err := h.uc.GetProfile(r.Context(), requestUserID(r, r.URL.Query().Get("userId")))
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

func (h *AuthHandler) UpdateProfile(w http.ResponseWriter, r *http.Request) {
	var req updateProfileRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	name := firstNonEmpty(req.Name, req.DisplayName)
	lang := firstNonEmpty(req.PreferredLanguage, req.Language)
	userID := requestUserID(r, req.UserID)
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	if req.UserID != "" && req.UserID != userID {
		response.FromError(w, apperrors.Forbidden("cannot update another user profile"))
		return
	}
	out, err := h.uc.UpdateProfile(r.Context(), usecase.UpdateProfileInput{
		UserID:                 userID,
		Name:                   name,
		PreferredLanguage:      lang,
		PreferredVoiceID:       req.PreferredVoiceID,
		PreferredTTSModel:      req.PreferredTTSModel,
		PreferredResponseModel: req.PreferredResponseModel,
		Gender:                 req.Gender,
		SafetyTermsAccepted:    req.SafetyTermsAccepted,
		SafetyTermsVersion:     req.SafetyTermsVersion,
	})
	if err != nil {
		response.FromError(w, err)
		return
	}
	response.OK(w, out)
}

type deleteAccountRequest struct {
	UserID   string `json:"userId"`
	Password string `json:"password"`
}

func (h *AuthHandler) DeleteAccount(w http.ResponseWriter, r *http.Request) {
	var req deleteAccountRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		response.Error(w, http.StatusBadRequest, "invalid request body")
		return
	}
	userID := requestUserID(r, req.UserID)
	if userID == "" {
		response.FromError(w, apperrors.Unauthorized("unauthorized"))
		return
	}
	if req.UserID != "" && req.UserID != userID {
		response.FromError(w, apperrors.Forbidden("cannot delete another user's account"))
		return
	}
	if err := h.uc.DeleteAccount(r.Context(), usecase.DeleteAccountInput{
		UserID:   userID,
		Password: req.Password,
	}); err != nil {
		response.FromError(w, err)
		return
	}
	clearAuthCookies(w)
	response.OK(w, map[string]any{"deleted": true})
}

func requestUserID(r *http.Request, fallback string) string {
	if userID := middleware.AuthenticatedUserID(r); userID != "" {
		return userID
	}
	return fallback
}

func setAuthCookies(w http.ResponseWriter, token string, ttl int64) {
	maxAge := int(ttl)
	if maxAge <= 0 {
		maxAge = int(axisauth.DefaultTTL.Seconds())
	}
	sameSite := http.SameSiteLaxMode
	switch strings.ToLower(strings.TrimSpace(os.Getenv("AUTH_COOKIE_SAMESITE"))) {
	case "strict":
		sameSite = http.SameSiteStrictMode
	case "none":
		sameSite = http.SameSiteNoneMode
	}
	secure := strings.ToLower(strings.TrimSpace(os.Getenv("AUTH_COOKIE_SECURE")))
	sessionCookie := &http.Cookie{
		Name:     axisauth.DefaultCookieName,
		Value:    token,
		Path:     "/",
		MaxAge:   maxAge,
		HttpOnly: true,
		Secure:   secure == "1" || secure == "true" || secure == "yes",
		SameSite: sameSite,
	}
	if domain := strings.TrimSpace(os.Getenv("AUTH_COOKIE_DOMAIN")); domain != "" {
		sessionCookie.Domain = domain
	}
	csrfCookie := &http.Cookie{
		Name:     axisauth.CSRFCookieName,
		Value:    axisauth.NewCSRFToken(),
		Path:     "/",
		MaxAge:   maxAge,
		HttpOnly: false,
		Secure:   sessionCookie.Secure,
		SameSite: sameSite,
	}
	if sessionCookie.Domain != "" {
		csrfCookie.Domain = sessionCookie.Domain
	}
	http.SetCookie(w, sessionCookie)
	http.SetCookie(w, csrfCookie)
}

func setRefreshCookie(w http.ResponseWriter, token string, ttl int64) {
	if strings.TrimSpace(token) == "" {
		return
	}
	maxAge := int(ttl)
	if maxAge <= 0 {
		maxAge = int((30 * 24 * time.Hour).Seconds())
	}
	cookie := &http.Cookie{
		Name:     refreshCookieName,
		Value:    token,
		Path:     "/",
		MaxAge:   maxAge,
		HttpOnly: true,
		Secure:   cookieSecure(),
		SameSite: cookieSameSite(),
	}
	if domain := strings.TrimSpace(os.Getenv("AUTH_COOKIE_DOMAIN")); domain != "" {
		cookie.Domain = domain
	}
	http.SetCookie(w, cookie)
}

func clearAuthCookies(w http.ResponseWriter) {
	domain := strings.TrimSpace(os.Getenv("AUTH_COOKIE_DOMAIN"))
	for _, name := range []string{axisauth.DefaultCookieName, axisauth.CSRFCookieName, refreshCookieName} {
		cookie := &http.Cookie{
			Name:     name,
			Value:    "",
			Path:     "/",
			MaxAge:   -1,
			HttpOnly: name != axisauth.CSRFCookieName,
			Secure:   cookieSecure(),
			SameSite: cookieSameSite(),
		}
		if domain != "" {
			cookie.Domain = domain
		}
		http.SetCookie(w, cookie)
	}
}

func cookieSecure() bool {
	secure := strings.ToLower(strings.TrimSpace(os.Getenv("AUTH_COOKIE_SECURE")))
	return secure == "1" || secure == "true" || secure == "yes"
}

func cookieSameSite() http.SameSite {
	switch strings.ToLower(strings.TrimSpace(os.Getenv("AUTH_COOKIE_SAMESITE"))) {
	case "strict":
		return http.SameSiteStrictMode
	case "none":
		return http.SameSiteNoneMode
	default:
		return http.SameSiteLaxMode
	}
}

func readAccessToken(r *http.Request) string {
	if token := axisauth.BearerToken(r.Header.Get("Authorization")); token != "" {
		return token
	}
	if c, err := r.Cookie(axisauth.DefaultCookieName); err == nil {
		return c.Value
	}
	return ""
}

func (h *AuthHandler) PersonalityInsights(w http.ResponseWriter, r *http.Request) {
	response.OK(w, map[string]any{
		"openness":          50,
		"conscientiousness": 50,
		"extraversion":      50,
		"agreeableness":     50,
		"neuroticism":       50,
		"descriptions":      []string{"Personality insights will appear after enough conversation history is available."},
	})
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if value != "" {
			return value
		}
	}
	return ""
}
