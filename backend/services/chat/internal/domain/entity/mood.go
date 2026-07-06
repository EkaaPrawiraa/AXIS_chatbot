package entity

import "time"

type Mood struct {
	ID        string
	UserID    string
	MoodDate  time.Time
	Score     int
	CreatedAt time.Time
	UpdatedAt time.Time
}
