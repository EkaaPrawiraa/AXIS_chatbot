package entity

import "time"

type MessageRole string

const (
	RoleUser      MessageRole = "user"
	RoleAssistant MessageRole = "assistant"
	RoleSystem    MessageRole = "system"
)

type Message struct {
	ID           string
	SessionID    string
	UserID       string
	Role         MessageRole
	Content      string
	Status       string
	AudioURL     *string
	EmotionLabel *string
	SafetyFlag   *string
	CrisisTier   *string
	Metadata     map[string]any
	TurnIndex    int
	CreatedAt    time.Time
}

func NewUserMessage(sessionID, userID, content string, audioURL *string, turnIndex int) Message {
	return Message{
		SessionID: sessionID,
		UserID:    userID,
		Role:      RoleUser,
		Content:   content,
		AudioURL:  audioURL,
		TurnIndex: turnIndex,
	}
}

func NewAssistantMessage(sessionID, userID, content string, turnIndex int, safetyFlag, crisisTier *string) Message {
	return Message{
		SessionID:  sessionID,
		UserID:     userID,
		Role:       RoleAssistant,
		Content:    content,
		TurnIndex:  turnIndex,
		SafetyFlag: safetyFlag,
		CrisisTier: crisisTier,
	}
}
