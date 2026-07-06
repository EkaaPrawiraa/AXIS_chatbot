package postgres

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/domain/entity"
)

type MoodRepository struct {
	db *sql.DB
}

func NewMoodRepository(db *sql.DB) *MoodRepository {
	return &MoodRepository{db: db}
}

// Upsert records today's mood score, overwriting any score already
// submitted today (one entry per user per calendar day). "Today" is pinned
// to Asia/Jakarta (AXIS's whole user base), not the DB server's own
// timezone (UTC here) — otherwise a mood logged between midnight and 7am
// WIB would land on the wrong calendar day.
func (r *MoodRepository) Upsert(ctx context.Context, userID string, score int) (entity.Mood, error) {
	row := r.db.QueryRowContext(ctx, `
		INSERT INTO user_moods (user_id, mood_date, mood_score, updated_at)
		VALUES ($1, (NOW() AT TIME ZONE 'Asia/Jakarta')::date, $2, NOW())
		ON CONFLICT (user_id, mood_date)
		DO UPDATE SET mood_score = EXCLUDED.mood_score, updated_at = NOW()
		RETURNING id, user_id, mood_date, mood_score, created_at, updated_at
	`, userID, score)
	var mood entity.Mood
	if err := row.Scan(&mood.ID, &mood.UserID, &mood.MoodDate, &mood.Score, &mood.CreatedAt, &mood.UpdatedAt); err != nil {
		return entity.Mood{}, fmt.Errorf("mood upsert: %w", err)
	}
	return mood, nil
}

// ListRecent returns the last `days` calendar days of mood entries, most
// recent first, for trend display and agentic context.
func (r *MoodRepository) ListRecent(ctx context.Context, userID string, days int) ([]entity.Mood, error) {
	rows, err := r.db.QueryContext(ctx, `
		SELECT id, user_id, mood_date, mood_score, created_at, updated_at
		FROM user_moods
		WHERE user_id = $1
		  AND mood_date >= (NOW() AT TIME ZONE 'Asia/Jakarta')::date - ($2 || ' days')::interval
		ORDER BY mood_date DESC
	`, userID, days)
	if err != nil {
		return nil, fmt.Errorf("mood list recent: %w", err)
	}
	defer rows.Close()

	var out []entity.Mood
	for rows.Next() {
		var mood entity.Mood
		if err := rows.Scan(&mood.ID, &mood.UserID, &mood.MoodDate, &mood.Score, &mood.CreatedAt, &mood.UpdatedAt); err != nil {
			return nil, fmt.Errorf("mood list scan: %w", err)
		}
		out = append(out, mood)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("mood list rows: %w", err)
	}
	return out, nil
}
