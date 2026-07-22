package postgres

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/domain/entity"
)

type MessageRepository struct {
	db *sql.DB
}

func NewMessageRepository(db *sql.DB) *MessageRepository {
	return &MessageRepository{db: db}
}

func (r *MessageRepository) Append(ctx context.Context, message entity.Message) (entity.Message, error) {
	status := message.Status
	if status == "" {
		status = "complete"
	}
	metadataJSON, err := marshalMetadata(message.Metadata)
	if err != nil {
		return entity.Message{}, err
	}
	row := r.db.QueryRowContext(ctx, `
		INSERT INTO messages (
			session_id, user_id, role, content, audio_url,
			emotion_label, safety_flag, crisis_tier, turn_index, status, metadata
		)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
		RETURNING id, created_at
	`,
		message.SessionID,
		message.UserID,
		message.Role,
		message.Content,
		message.AudioURL,
		message.EmotionLabel,
		message.SafetyFlag,
		message.CrisisTier,
		message.TurnIndex,
		status,
		metadataJSON,
	)
	if err := row.Scan(&message.ID, &message.CreatedAt); err != nil {
		return entity.Message{}, fmt.Errorf("message append: %w", err)
	}
	message.Status = status
	return message, nil
}

func (r *MessageRepository) UpdateContent(ctx context.Context, messageID string, content string) (entity.Message, error) {
	var msg entity.Message
	var audioURL, emotionLabel, safetyFlag, crisisTier sql.NullString
	var metadata []byte
	row := r.db.QueryRowContext(ctx, `
		UPDATE messages
		SET content = $2
		WHERE id = $1
		RETURNING id, session_id, user_id, role, content, audio_url,
		          emotion_label, safety_flag, crisis_tier, metadata, turn_index, created_at, status
	`, messageID, content)
	if err := row.Scan(
		&msg.ID,
		&msg.SessionID,
		&msg.UserID,
		&msg.Role,
		&msg.Content,
		&audioURL,
		&emotionLabel,
		&safetyFlag,
		&crisisTier,
		&metadata,
		&msg.TurnIndex,
		&msg.CreatedAt,
		&msg.Status,
	); err != nil {
		return entity.Message{}, fmt.Errorf("message update content: %w", err)
	}
	msg.AudioURL = nullableString(audioURL)
	msg.EmotionLabel = nullableString(emotionLabel)
	msg.SafetyFlag = nullableString(safetyFlag)
	msg.CrisisTier = nullableString(crisisTier)
	msg.Metadata = unmarshalMetadata(metadata)
	return msg, nil
}

// ulang, safety, ok.
func (r *MessageRepository) UpdateRegeneratedContent(
	ctx context.Context,
	messageID string,
	content string,
	safetyFlag *string,
	crisisTier *string,
) (entity.Message, error) {
	var msg entity.Message
	var audioURL, emotionLabel, dbSafetyFlag, dbCrisisTier sql.NullString
	var metadata []byte
	row := r.db.QueryRowContext(ctx, `
		UPDATE messages
		SET content = $2, safety_flag = $3, crisis_tier = $4, status = 'sent'
		WHERE id = $1
		RETURNING id, session_id, user_id, role, content, audio_url,
		          emotion_label, safety_flag, crisis_tier, metadata, turn_index, created_at, status
	`, messageID, content, safetyFlag, crisisTier)
	if err := row.Scan(
		&msg.ID,
		&msg.SessionID,
		&msg.UserID,
		&msg.Role,
		&msg.Content,
		&audioURL,
		&emotionLabel,
		&dbSafetyFlag,
		&dbCrisisTier,
		&metadata,
		&msg.TurnIndex,
		&msg.CreatedAt,
		&msg.Status,
	); err != nil {
		return entity.Message{}, fmt.Errorf("message update regenerated content: %w", err)
	}
	msg.AudioURL = nullableString(audioURL)
	msg.EmotionLabel = nullableString(emotionLabel)
	msg.SafetyFlag = nullableString(dbSafetyFlag)
	msg.CrisisTier = nullableString(dbCrisisTier)
	msg.Metadata = unmarshalMetadata(metadata)
	return msg, nil
}

func (r *MessageRepository) UpdateStatusAndContent(ctx context.Context, messageID, status, content string) error {
	_, err := r.db.ExecContext(ctx, `
		UPDATE messages
		SET status = $2, content = $3
		WHERE id = $1
	`, messageID, status, content)
	if err != nil {
		return fmt.Errorf("message update status: %w", err)
	}
	return nil
}

func (r *MessageRepository) UpdateStatusContentAndMetadata(ctx context.Context, messageID, status, content string, safetyFlag *string, crisisTier *string, metadata map[string]any) error {
	metadataJSON, err := marshalMetadata(metadata)
	if err != nil {
		return err
	}
	_, err = r.db.ExecContext(ctx, `
		UPDATE messages
		SET status = $2, content = $3, safety_flag = $4, crisis_tier = $5, metadata = $6
		WHERE id = $1
	`, messageID, status, content, safetyFlag, crisisTier, metadataJSON)
	if err != nil {
		return fmt.Errorf("message update status metadata: %w", err)
	}
	return nil
}

func (r *MessageRepository) NextTurnIndex(ctx context.Context, sessionID string) (int, error) {
	row := r.db.QueryRowContext(ctx, `
		SELECT COALESCE(MAX(turn_index), -1) + 1
		FROM messages
		WHERE session_id = $1
	`, sessionID)
	var next int
	if err := row.Scan(&next); err != nil {
		return 0, fmt.Errorf("message next turn index: %w", err)
	}
	return next, nil
}

func (r *MessageRepository) ListBySession(ctx context.Context, sessionID string, limit int, offset int) ([]entity.Message, error) {
	if limit <= 0 {
		limit = 30
	}
	if offset < 0 {
		offset = 0
	}
	rows, err := r.db.QueryContext(ctx, `
		SELECT id, session_id, user_id, role, content, audio_url,
		       emotion_label, safety_flag, crisis_tier, metadata, turn_index, created_at, status
		FROM messages
		WHERE session_id = $1
		ORDER BY turn_index ASC
		LIMIT $2 OFFSET $3
	`, sessionID, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("message list: %w", err)
	}
	defer rows.Close()

	var out []entity.Message
	for rows.Next() {
		var msg entity.Message
		var audioURL, emotionLabel, safetyFlag, crisisTier sql.NullString
		var metadata []byte
		if err := rows.Scan(
			&msg.ID,
			&msg.SessionID,
			&msg.UserID,
			&msg.Role,
			&msg.Content,
			&audioURL,
			&emotionLabel,
			&safetyFlag,
			&crisisTier,
			&metadata,
			&msg.TurnIndex,
			&msg.CreatedAt,
			&msg.Status,
		); err != nil {
			return nil, fmt.Errorf("message scan: %w", err)
		}
		msg.AudioURL = nullableString(audioURL)
		msg.EmotionLabel = nullableString(emotionLabel)
		msg.SafetyFlag = nullableString(safetyFlag)
		msg.CrisisTier = nullableString(crisisTier)
		msg.Metadata = unmarshalMetadata(metadata)
		out = append(out, msg)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("message rows: %w", err)
	}
	return out, nil
}

func (r *MessageRepository) ListIDsBySession(ctx context.Context, sessionID string) ([]string, error) {
	rows, err := r.db.QueryContext(ctx, `
		SELECT id
		FROM messages
		WHERE session_id = $1
		ORDER BY turn_index ASC
	`, sessionID)
	if err != nil {
		return nil, fmt.Errorf("message id list: %w", err)
	}
	defer rows.Close()

	out := []string{}
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return nil, fmt.Errorf("message id scan: %w", err)
		}
		out = append(out, id)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("message id rows: %w", err)
	}
	return out, nil
}

func marshalMetadata(metadata map[string]any) ([]byte, error) {
	if len(metadata) == 0 {
		return []byte(`{}`), nil
	}
	raw, err := json.Marshal(metadata)
	if err != nil {
		return nil, fmt.Errorf("message metadata marshal: %w", err)
	}
	return raw, nil
}

func unmarshalMetadata(raw []byte) map[string]any {
	if len(raw) == 0 {
		return nil
	}
	var metadata map[string]any
	if err := json.Unmarshal(raw, &metadata); err != nil {
		return nil
	}
	if len(metadata) == 0 {
		return nil
	}
	return metadata
}

func nullableString(value sql.NullString) *string {
	if !value.Valid {
		return nil
	}
	return &value.String
}
