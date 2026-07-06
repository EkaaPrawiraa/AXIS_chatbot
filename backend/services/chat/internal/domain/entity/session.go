package entity

import "time"

type Channel string

const (
	ChannelText       Channel = "text"
	ChannelVoice      Channel = "voice"
	ChannelConfession Channel = "confession"
)

type SessionStatus string

const (
	SessionActive    SessionStatus = "active"
	SessionEnded     SessionStatus = "ended"
	SessionAbandoned SessionStatus = "abandoned"
)

type Session struct {
	ID              string
	UserID          string
	Neo4jSessionID  string
	Title           string
	Channel         Channel
	Status          SessionStatus
	StartedAt       time.Time
	EndedAt         *time.Time
	TurnCount       int
	SafetyEscalated bool
	KGProcessed     bool
	CreatedAt       time.Time
	UpdatedAt       time.Time
}

func NewSession(userID string, title string, channel Channel) Session {
	if channel == "" {
		channel = ChannelText
	}
	if title == "" {
		title = "New Conversation"
	}
	return Session{
		UserID:  userID,
		Title:   title,
		Channel: channel,
		Status:  SessionActive,
	}
}

type Conversation struct {
	ID            string
	UserID        string
	Title         string
	Description   string
	LastMessageAt time.Time
	MessageCount  int
	Preview       string
	CreatedAt     time.Time
	UpdatedAt     time.Time
}
