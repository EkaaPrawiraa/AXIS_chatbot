package entity

import "time"

type UserStatus string

const (
	UserStatusActive    UserStatus = "active"
	UserStatusSuspended UserStatus = "suspended"
	UserStatusDeleted   UserStatus = "deleted"
)

type User struct {
	ID                     string
	Email                  string
	Phone                  string
	DisplayName            string
	PasswordHash           string
	GoogleID               string
	PreferredLanguage      string
	PreferredVoiceID       string
	PreferredTTSModel      string
	PreferredResponseModel string
	Gender                 string
	SafetyTermsAccepted    bool
	SafetyTermsVersion     string
	SafetyTermsAcceptedAt  *time.Time
	OnboardingComplete     bool
	AccountStatus          UserStatus
	CreatedAt              time.Time
	UpdatedAt              time.Time
	LastLoginAt            *time.Time
}
