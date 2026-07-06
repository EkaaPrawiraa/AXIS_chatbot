package entity

import "time"

type User struct {
	ID                 string    `json:"id"`
	DisplayName        string    `json:"display_name"`
	LastActive         time.Time `json:"last_active,omitempty"`
	SessionCount       int       `json:"session_count"`
	OnboardingComplete bool      `json:"onboarding_complete"`
}

type Session struct {
	ID               string     `json:"id"`
	UserID           string     `json:"user_id"`
	Channel          string     `json:"channel"`
	Summary          *string    `json:"summary,omitempty"`
	SentimentAvg     *float64   `json:"sentiment_avg,omitempty"`
	PHQ9Administered bool       `json:"phq9_administered"`
	StartedAt        time.Time  `json:"started_at,omitempty"`
	EndedAt          *time.Time `json:"ended_at,omitempty"`
}

type Assessment struct {
	ID                string `json:"id"`
	UserID            string `json:"user_id"`
	SessionID         string `json:"session_id"`
	Instrument        string `json:"instrument"`
	Score             int    `json:"score"`
	SeverityLabel     string `json:"severity_label"`
	DeltaFromPrevious *int   `json:"delta_from_previous,omitempty"`
	Q9Score           int    `json:"q9_score"`
	ItemResponsesJSON string `json:"item_responses"`
}

type Topic struct {
	ID        string  `json:"id"`
	UserID    string  `json:"user_id"`
	Name      string  `json:"name"`
	Sentiment float64 `json:"sentiment"`
}

type MemoryTag string

type Memory struct {
	ID                    string      `json:"id"`
	UserID                string      `json:"user_id"`
	Title                 string      `json:"title"`
	Content               string      `json:"content"`
	Tags                  []MemoryTag `json:"tags"`
	IsPinned              bool        `json:"is_pinned"`
	Source                string      `json:"source"`
	RelatedConversationID string      `json:"related_conversation_id,omitempty"`
	Emotion               string      `json:"emotion,omitempty"`
	Importance            float64     `json:"importance"`
	Active                bool        `json:"active"`
	EmbeddingSynced       bool        `json:"embedding_synced"`
	CreatedAt             time.Time   `json:"created_at"`
	UpdatedAt             time.Time   `json:"updated_at"`
	LastAccessed          time.Time   `json:"last_accessed"`
}

type EscalationSignals struct {
	LatestValence    float64    `json:"latest_valence"`
	LatestIntensity  float64    `json:"latest_intensity"`
	LatestPHQ9Score  int        `json:"latest_phq9_score"`
	PHQ9Delta        int        `json:"phq9_delta"`
	Q9Score          int        `json:"q9_score"`
	SessionsThisWeek int        `json:"sessions_this_week"`
	LastPHQ9At       *time.Time `json:"last_phq9_at,omitempty"`
}

func (s EscalationSignals) ShouldSuppressReminder() bool {
	return s.LatestValence < -0.6 && s.LatestIntensity > 0.7
}

func (s EscalationSignals) IsCrisis() bool {
	return s.Q9Score >= 1
}

func (s EscalationSignals) ShouldSuppressPHQ9(now time.Time) bool {
	if s.LastPHQ9At == nil {
		return false
	}
	return now.Sub(*s.LastPHQ9At) < 7*24*time.Hour && s.PHQ9Delta >= 3
}

func (s EscalationSignals) ShouldNudgeSocialConnection() bool {
	return s.SessionsThisWeek > 20
}
