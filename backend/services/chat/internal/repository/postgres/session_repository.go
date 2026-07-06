package postgres

import (
	"context"
	"database/sql"
	"fmt"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/domain/entity"
)

type SessionRepository struct {
	db *sql.DB
}

func NewSessionRepository(db *sql.DB) *SessionRepository {
	return &SessionRepository{db: db}
}

func (r *SessionRepository) Create(ctx context.Context, session entity.Session) (entity.Session, error) {
	row := r.db.QueryRowContext(ctx, `
		INSERT INTO chat_sessions (user_id, title, channel, status, updated_at)
		VALUES ($1, $2, $3, $4, NOW())
		RETURNING id, title, started_at, turn_count, safety_escalated, kg_processed, created_at, updated_at
	`, session.UserID, session.Title, session.Channel, session.Status)
	if err := row.Scan(
		&session.ID,
		&session.Title,
		&session.StartedAt,
		&session.TurnCount,
		&session.SafetyEscalated,
		&session.KGProcessed,
		&session.CreatedAt,
		&session.UpdatedAt,
	); err != nil {
		return entity.Session{}, fmt.Errorf("chat session create: %w", err)
	}
	return session, nil
}

func (r *SessionRepository) FindByID(ctx context.Context, sessionID string) (*entity.Session, error) {
	row := r.db.QueryRowContext(ctx, `
		SELECT id, user_id, COALESCE(neo4j_session_id, ''), COALESCE(title, ''), channel, status,
		       started_at, ended_at, turn_count, safety_escalated, kg_processed, created_at, updated_at
		FROM chat_sessions
		WHERE id = $1
	`, sessionID)
	var session entity.Session
	var endedAt sql.NullTime
	if err := row.Scan(
		&session.ID,
		&session.UserID,
		&session.Neo4jSessionID,
		&session.Title,
		&session.Channel,
		&session.Status,
		&session.StartedAt,
		&endedAt,
		&session.TurnCount,
		&session.SafetyEscalated,
		&session.KGProcessed,
		&session.CreatedAt,
		&session.UpdatedAt,
	); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, fmt.Errorf("chat session find: %w", err)
	}
	if endedAt.Valid {
		session.EndedAt = &endedAt.Time
	}
	return &session, nil
}

func (r *SessionRepository) ListConversations(ctx context.Context, userID string, limit int, offset int) ([]entity.Conversation, error) {
	rows, err := r.db.QueryContext(ctx, `
		SELECT
			s.id,
			s.user_id,
			COALESCE(s.title, 'New Conversation') AS title,
			s.started_at,
			COALESCE(s.updated_at, s.started_at) AS updated_at,
			COALESCE(MAX(m.created_at), s.started_at) AS last_message_at,
			COUNT(m.id) AS message_count,
			COALESCE((ARRAY_AGG(m.content ORDER BY m.created_at DESC) FILTER (WHERE m.id IS NOT NULL))[1], '') AS preview
		FROM chat_sessions s
		LEFT JOIN messages m ON m.session_id = s.id
		WHERE s.user_id = $1
		  AND s.status != 'abandoned'
		GROUP BY s.id, s.user_id, s.title, s.started_at, s.updated_at
		ORDER BY last_message_at DESC
		LIMIT $2 OFFSET $3
	`, userID, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("chat conversation list: %w", err)
	}
	defer rows.Close()

	var out []entity.Conversation
	for rows.Next() {
		var c entity.Conversation
		if err := rows.Scan(
			&c.ID,
			&c.UserID,
			&c.Title,
			&c.CreatedAt,
			&c.UpdatedAt,
			&c.LastMessageAt,
			&c.MessageCount,
			&c.Preview,
		); err != nil {
			return nil, fmt.Errorf("chat conversation scan: %w", err)
		}
		out = append(out, c)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("chat conversation rows: %w", err)
	}
	return out, nil
}

func (r *SessionRepository) UpdateTitle(ctx context.Context, sessionID string, title string) (entity.Session, error) {
	row := r.db.QueryRowContext(ctx, `
		UPDATE chat_sessions
		SET title = $2,
		    updated_at = NOW()
		WHERE id = $1
		RETURNING id, user_id, COALESCE(neo4j_session_id, ''), COALESCE(title, ''),
		          channel, status, started_at, ended_at, turn_count,
		          safety_escalated, kg_processed, created_at, updated_at
	`, sessionID, title)
	var session entity.Session
	var endedAt sql.NullTime
	if err := row.Scan(
		&session.ID,
		&session.UserID,
		&session.Neo4jSessionID,
		&session.Title,
		&session.Channel,
		&session.Status,
		&session.StartedAt,
		&endedAt,
		&session.TurnCount,
		&session.SafetyEscalated,
		&session.KGProcessed,
		&session.CreatedAt,
		&session.UpdatedAt,
	); err != nil {
		if err == sql.ErrNoRows {
			return entity.Session{}, sql.ErrNoRows
		}
		return entity.Session{}, fmt.Errorf("chat session update title: %w", err)
	}
	if endedAt.Valid {
		session.EndedAt = &endedAt.Time
	}
	return session, nil
}

func (r *SessionRepository) Delete(ctx context.Context, sessionID string) error {
	result, err := r.db.ExecContext(ctx, `
		UPDATE chat_sessions
		SET status = 'abandoned',
		    ended_at = COALESCE(ended_at, NOW()),
		    updated_at = NOW()
		WHERE id = $1
	`, sessionID)
	if err != nil {
		return fmt.Errorf("chat session delete: %w", err)
	}
	affected, err := result.RowsAffected()
	if err != nil {
		return fmt.Errorf("chat session delete rows: %w", err)
	}
	if affected == 0 {
		return sql.ErrNoRows
	}
	return nil
}

func (r *SessionRepository) IncrementTurn(ctx context.Context, sessionID string) error {
	_, err := r.db.ExecContext(ctx, `
		UPDATE chat_sessions
		SET turn_count = turn_count + 1,
		    updated_at = NOW()
		WHERE id = $1
	`, sessionID)
	if err != nil {
		return fmt.Errorf("chat session increment turn: %w", err)
	}
	return nil
}

func (r *SessionRepository) MarkSafetyEscalated(ctx context.Context, sessionID string) error {
	_, err := r.db.ExecContext(ctx, `
		UPDATE chat_sessions
		SET safety_escalated = TRUE,
		    updated_at = NOW()
		WHERE id = $1
	`, sessionID)
	if err != nil {
		return fmt.Errorf("chat session mark safety escalated: %w", err)
	}
	return nil
}
