package neo4jrepo

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/domain/entity"
	"github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/domain/repository"
	apperrors "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/errors"
	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

type GraphRepository struct {
	driver neo4j.DriverWithContext
}

func NewGraphRepository(driver neo4j.DriverWithContext) *GraphRepository {
	return &GraphRepository{driver: driver}
}

func (r *GraphRepository) UpsertUser(ctx context.Context, user entity.User) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)
	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MERGE (u:User {id: $id})
			ON CREATE SET
				u.display_name = $display_name,
				u.created_at = datetime(),
				u.last_active = datetime(),
				u.session_count = 0,
				u.onboarding_complete = false
			ON MATCH SET
				u.display_name = coalesce($display_name, u.display_name),
				u.last_active = datetime()
		`, map[string]any{
			"id":           user.ID,
			"display_name": user.DisplayName,
		})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("neo4j upsert user: %w", err)
	}
	return nil
}

func (r *GraphRepository) GetUser(ctx context.Context, userID string) (*entity.User, error) {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)
	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, `
			MATCH (u:User {id: $id})
			RETURN u.id AS id,
			       u.display_name AS display_name,
			       u.session_count AS session_count,
			       u.onboarding_complete AS onboarding_complete
		`, map[string]any{"id": userID})
		if err != nil {
			return nil, err
		}
		if !res.Next(ctx) {
			return nil, nil
		}
		rec := res.Record()
		return &entity.User{
			ID:                 stringValue(rec, "id"),
			DisplayName:        stringValue(rec, "display_name"),
			SessionCount:       intValue(rec, "session_count"),
			OnboardingComplete: boolValue(rec, "onboarding_complete"),
		}, nil
	})
	if err != nil {
		return nil, fmt.Errorf("neo4j get user: %w", err)
	}
	if result == nil {
		return nil, nil
	}
	return result.(*entity.User), nil
}

func (r *GraphRepository) MarkOnboardingComplete(ctx context.Context, userID string) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)
	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MATCH (u:User {id: $id})
			SET u.onboarding_complete = true
		`, map[string]any{"id": userID})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("neo4j mark onboarding complete: %w", err)
	}
	return nil
}

func (r *GraphRepository) OpenSession(ctx context.Context, sessionNode entity.Session) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)
	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MERGE (u:User {id: $user_id})
			ON CREATE SET
				u.created_at   = datetime(),
				u.last_active  = datetime(),
				u.session_count = 0,
				u.onboarding_complete = false
			MERGE (s:Session {id: $session_id})
			ON CREATE SET
				s.started_at        = datetime(),
				s.ended_at          = null,
				s.channel           = $channel,
				s.summary           = null,
				s.sentiment_avg     = null,
				s.phq9_administered = false
			MERGE (u)-[rel:HAD_SESSION]->(s)
			ON CREATE SET
				rel.t_valid        = datetime(),
				rel.t_invalid      = null,
				rel.confidence     = 1.0,
				rel.source_session = $session_id
			SET u.session_count = coalesce(u.session_count, 0) + 1,
			    u.last_active   = datetime()
		`, map[string]any{
			"user_id":    sessionNode.UserID,
			"session_id": sessionNode.ID,
			"channel":    sessionNode.Channel,
		})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("neo4j open session: %w", err)
	}
	return nil
}

func (r *GraphRepository) CloseSession(ctx context.Context, sessionID string, summary string, sentimentAvg float64) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)
	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MATCH (s:Session {id: $session_id})
			SET s.ended_at = datetime(),
			    s.summary = $summary,
			    s.sentiment_avg = $sentiment_avg
		`, map[string]any{
			"session_id":    sessionID,
			"summary":       summary,
			"sentiment_avg": sentimentAvg,
		})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("neo4j close session: %w", err)
	}
	return nil
}

func (r *GraphRepository) MarkPHQ9Administered(ctx context.Context, sessionID string) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)
	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MATCH (s:Session {id: $session_id})
			SET s.phq9_administered = true
		`, map[string]any{"session_id": sessionID})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("neo4j mark phq9 administered: %w", err)
	}
	return nil
}

func (r *GraphRepository) WriteAssessment(ctx context.Context, assessment entity.Assessment) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)
	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})
			OPTIONAL MATCH (s:Session {id: $session_id})
			CREATE (a:Assessment {
				id: $id,
				instrument: $instrument,
				score: $score,
				severity_label: $severity_label,
				delta_from_previous: $delta,
				administered_at: datetime(),
				session_id: $session_id,
				q9_score: $q9_score,
				item_responses: $item_responses,
				sensitivity_level: 'normal'
			})
			CREATE (u)-[:COMPLETED_ASSESSMENT {
				t_valid: datetime(),
				t_invalid: null,
				confidence: 1.0,
				source_session: $session_id
			}]->(a)
			FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END |
				MERGE (s)-[:RECORDED_ASSESSMENT {
					source_session: $session_id
				}]->(a)
			)
		`, map[string]any{
			"user_id":        assessment.UserID,
			"session_id":     assessment.SessionID,
			"id":             assessment.ID,
			"instrument":     assessment.Instrument,
			"score":          assessment.Score,
			"severity_label": assessment.SeverityLabel,
			"delta":          assessment.DeltaFromPrevious,
			"q9_score":       assessment.Q9Score,
			"item_responses": assessment.ItemResponsesJSON,
		})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("neo4j write assessment: %w", err)
	}
	return nil
}

func (r *GraphRepository) GetLatestAssessment(ctx context.Context, userID string, instrument string) (*entity.Assessment, error) {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)
	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})-[:COMPLETED_ASSESSMENT]->(a:Assessment)
			WHERE a.instrument = $instrument
			RETURN a.id AS id,
			       a.instrument AS instrument,
			       a.score AS score,
			       a.severity_label AS severity_label,
			       a.session_id AS session_id,
			       a.delta_from_previous AS delta_from_previous,
			       a.q9_score AS q9_score,
			       a.item_responses AS item_responses
			ORDER BY a.administered_at DESC
			LIMIT 1
		`, map[string]any{"user_id": userID, "instrument": instrument})
		if err != nil {
			return nil, err
		}
		if !res.Next(ctx) {
			return nil, nil
		}
		rec := res.Record()
		delta := nullableInt(rec, "delta_from_previous")
		return &entity.Assessment{
			ID:                stringValue(rec, "id"),
			UserID:            userID,
			SessionID:         stringValue(rec, "session_id"),
			Instrument:        stringValue(rec, "instrument"),
			Score:             intValue(rec, "score"),
			SeverityLabel:     stringValue(rec, "severity_label"),
			DeltaFromPrevious: delta,
			Q9Score:           intValue(rec, "q9_score"),
			ItemResponsesJSON: stringValue(rec, "item_responses"),
		}, nil
	})
	if err != nil {
		return nil, fmt.Errorf("neo4j latest assessment: %w", err)
	}
	if result == nil {
		return nil, nil
	}
	return result.(*entity.Assessment), nil
}

func (r *GraphRepository) UpsertTopic(ctx context.Context, topic entity.Topic) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)
	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})
			MERGE (top:Topic {name: $name})
			ON CREATE SET
				top.id = $topic_id,
				top.frequency = 1,
				top.first_seen = datetime(),
				top.last_seen = datetime(),
				top.avg_sentiment = $sentiment
			ON MATCH SET
				top.frequency = coalesce(top.frequency, 0) + 1,
				top.last_seen = datetime(),
				top.avg_sentiment = (coalesce(top.avg_sentiment, 0.0) + $sentiment) / 2.0
			MERGE (u)-[rel:HAS_RECURRING_THEME]->(top)
			ON CREATE SET
				rel.first_reinforced = datetime(),
				rel.times_reinforced = 1
			ON MATCH SET
				rel.times_reinforced = coalesce(rel.times_reinforced, 0) + 1
			SET rel.last_reinforced = datetime()
		`, map[string]any{
			"user_id":   topic.UserID,
			"topic_id":  topic.ID,
			"name":      topic.Name,
			"sentiment": topic.Sentiment,
		})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("neo4j upsert topic: %w", err)
	}
	return nil
}

func (r *GraphRepository) GetEscalationSignals(ctx context.Context, userID string) (entity.EscalationSignals, error) {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)
	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})
			OPTIONAL MATCH (u)-[:FELT]->(emo:Emotion)
			WHERE emo.active = true
			  AND emo.timestamp > datetime() - duration('PT48H')
			WITH u, emo
			ORDER BY emo.timestamp DESC
			WITH u, collect(emo)[0] AS latest_emo
			OPTIONAL MATCH (u)-[:COMPLETED_ASSESSMENT]->(a:Assessment)
			WHERE a.instrument = 'PHQ-9'
			WITH u, latest_emo, a
			ORDER BY a.administered_at DESC
			WITH u, latest_emo, collect(a)[0] AS latest_phq9
			OPTIONAL MATCH (u)-[:HAD_SESSION]->(s:Session)
			WHERE s.started_at > datetime() - duration('P7D')
			RETURN latest_emo.valence AS latest_valence,
			       latest_emo.intensity AS latest_intensity,
			       latest_phq9.score AS latest_phq9_score,
			       latest_phq9.delta_from_previous AS phq9_delta,
			       latest_phq9.q9_score AS q9_score,
			       latest_phq9.administered_at AS last_phq9_at,
			       count(s) AS sessions_this_week
		`, map[string]any{"user_id": userID})
		if err != nil {
			return nil, err
		}
		if !res.Next(ctx) {
			return entity.EscalationSignals{}, nil
		}
		rec := res.Record()
		return entity.EscalationSignals{
			LatestValence:    floatValue(rec, "latest_valence"),
			LatestIntensity:  floatValue(rec, "latest_intensity"),
			LatestPHQ9Score:  intValue(rec, "latest_phq9_score"),
			PHQ9Delta:        intValue(rec, "phq9_delta"),
			Q9Score:          intValue(rec, "q9_score"),
			SessionsThisWeek: intValue(rec, "sessions_this_week"),
			LastPHQ9At:       nullableTime(rec, "last_phq9_at"),
		}, nil
	})
	if err != nil {
		return entity.EscalationSignals{}, fmt.Errorf("neo4j escalation signals: %w", err)
	}
	return result.(entity.EscalationSignals), nil
}

func (r *GraphRepository) ListMemories(ctx context.Context, userID string, filter repository.MemoryFilter) ([]entity.Memory, error) {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)
	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory)
			WHERE coalesce(m.active, true) = true
			  AND (
			    $tag_count = 0 OR
			    any(memory_tag IN coalesce(m.tags, []) WHERE memory_tag IN $tags)
			  )
			  AND (
			    $search = '' OR
			    toLower(coalesce(m.title, '')) CONTAINS toString($search) OR
			    toLower(coalesce(m.summary, '')) CONTAINS toString($search)
			  )
			RETURN m.id AS id,
			       u.id AS user_id,
			       coalesce(m.title, '') AS title,
			       coalesce(m.summary, '') AS content,
			       coalesce(m.tags, []) AS tags,
			       coalesce(m.is_pinned, false) AS is_pinned,
			       coalesce(m.source, 'chat') AS source,
			       coalesce(m.related_conversation_id, '') AS related_conversation_id,
			       coalesce(m.emotion, '') AS emotion,
			       coalesce(m.importance, 0.5) AS importance,
			       coalesce(m.active, true) AS active,
			       coalesce(m.embedding_synced, false) AS embedding_synced,
			       m.created_at AS created_at,
			       coalesce(m.updated_at, m.created_at) AS updated_at,
			       coalesce(m.last_accessed, m.created_at) AS last_accessed
			ORDER BY is_pinned DESC, updated_at DESC
			SKIP $offset LIMIT $limit
		`, map[string]any{
			"user_id":   userID,
			"tags":      filter.Tags,
			"tag_count": len(filter.Tags),
			"search":    strings.ToLower(strings.TrimSpace(filter.SearchQuery)),
			"limit":     filter.Limit,
			"offset":    filter.Offset,
		})
		if err != nil {
			return nil, err
		}
		var memories []entity.Memory
		for res.Next(ctx) {
			memories = append(memories, memoryFromRecord(res.Record()))
		}
		if err := res.Err(); err != nil {
			return nil, err
		}
		return memories, nil
	})
	if err != nil {
		return nil, fmt.Errorf("neo4j list memories: %w", err)
	}
	return result.([]entity.Memory), nil
}

func (r *GraphRepository) GetMemory(ctx context.Context, userID string, memoryID string) (*entity.Memory, error) {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)
	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory {id: $id})
			WHERE coalesce(m.active, true) = true
			RETURN m.id AS id,
			       u.id AS user_id,
			       coalesce(m.title, '') AS title,
			       coalesce(m.summary, '') AS content,
			       coalesce(m.tags, []) AS tags,
			       coalesce(m.is_pinned, false) AS is_pinned,
			       coalesce(m.source, 'chat') AS source,
			       coalesce(m.related_conversation_id, '') AS related_conversation_id,
			       coalesce(m.emotion, '') AS emotion,
			       coalesce(m.importance, 0.5) AS importance,
			       coalesce(m.active, true) AS active,
			       coalesce(m.embedding_synced, false) AS embedding_synced,
			       m.created_at AS created_at,
			       coalesce(m.updated_at, m.created_at) AS updated_at,
			       coalesce(m.last_accessed, m.created_at) AS last_accessed
		`, map[string]any{"user_id": userID, "id": memoryID})
		if err != nil {
			return nil, err
		}
		if !res.Next(ctx) {
			return nil, nil
		}
		memory := memoryFromRecord(res.Record())
		return &memory, nil
	})
	if err != nil {
		return nil, fmt.Errorf("neo4j get memory: %w", err)
	}
	if result == nil {
		return nil, nil
	}
	return result.(*entity.Memory), nil
}

func (r *GraphRepository) CreateMemory(ctx context.Context, memory entity.Memory) (entity.Memory, error) {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)
	result, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})
			CREATE (m:Memory {
				id: $id,
				title: $title,
				summary: $content,
				tags: $tags,
				is_pinned: $is_pinned,
				source: $source,
				related_conversation_id: $related_conversation_id,
				emotion: $emotion,
				importance: $importance,
				active: true,
				embedding_synced: false,
				created_at: datetime(),
				updated_at: datetime(),
				last_accessed: datetime()
			})
			MERGE (u)-[rel:HAS_MEMORY]->(m)
			ON CREATE SET
				rel.t_valid = datetime(),
				rel.t_invalid = null,
				rel.confidence = 1.0,
				rel.source_session = $related_conversation_id
			RETURN m.id AS id,
			       u.id AS user_id,
			       m.title AS title,
			       m.summary AS content,
			       m.tags AS tags,
			       m.is_pinned AS is_pinned,
			       m.source AS source,
			       coalesce(m.related_conversation_id, '') AS related_conversation_id,
			       coalesce(m.emotion, '') AS emotion,
			       m.importance AS importance,
			       m.active AS active,
			       m.embedding_synced AS embedding_synced,
			       m.created_at AS created_at,
			       m.updated_at AS updated_at,
			       m.last_accessed AS last_accessed
		`, memoryParams(memory))
		if err != nil {
			return nil, err
		}
		if !res.Next(ctx) {
			return nil, apperrors.NotFound("user not found")
		}
		created := memoryFromRecord(res.Record())
		return created, nil
	})
	if err != nil {
		return entity.Memory{}, fmt.Errorf("neo4j create memory: %w", err)
	}
	return result.(entity.Memory), nil
}

func (r *GraphRepository) UpdateMemory(ctx context.Context, memory entity.Memory) (entity.Memory, error) {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)
	result, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory {id: $id})
			WHERE coalesce(m.active, true) = true
			SET m.title = $title,
			    m.summary = $content,
			    m.tags = $tags,
			    m.is_pinned = $is_pinned,
			    m.embedding_synced = $embedding_synced,
			    m.updated_at = datetime()
			RETURN m.id AS id,
			       u.id AS user_id,
			       m.title AS title,
			       m.summary AS content,
			       coalesce(m.tags, []) AS tags,
			       coalesce(m.is_pinned, false) AS is_pinned,
			       coalesce(m.source, 'manual') AS source,
			       coalesce(m.related_conversation_id, '') AS related_conversation_id,
			       coalesce(m.emotion, '') AS emotion,
			       coalesce(m.importance, 0.5) AS importance,
			       coalesce(m.active, true) AS active,
			       coalesce(m.embedding_synced, false) AS embedding_synced,
			       m.created_at AS created_at,
			       m.updated_at AS updated_at,
			       coalesce(m.last_accessed, m.updated_at) AS last_accessed
		`, memoryParams(memory))
		if err != nil {
			return nil, err
		}
		if !res.Next(ctx) {
			return nil, apperrors.NotFound("memory not found")
		}
		updated := memoryFromRecord(res.Record())
		return updated, nil
	})
	if err != nil {
		return entity.Memory{}, fmt.Errorf("neo4j update memory: %w", err)
	}
	return result.(entity.Memory), nil
}

func (r *GraphRepository) DeleteMemory(ctx context.Context, userID string, memoryID string) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)
	result, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, `
			MATCH (:User {id: $user_id})-[rel:HAS_MEMORY]->(m:Memory {id: $id})
			WHERE coalesce(m.active, true) = true
			SET m.active = false,
			    m.updated_at = datetime(),
			    rel.t_invalid = datetime()
			RETURN count(m) AS count
		`, map[string]any{"user_id": userID, "id": memoryID})
		if err != nil {
			return nil, err
		}
		if !res.Next(ctx) {
			return int64(0), nil
		}
		return intValue(res.Record(), "count"), nil
	})
	if err != nil {
		return fmt.Errorf("neo4j delete memory: %w", err)
	}
	if result.(int) == 0 {
		return apperrors.NotFound("memory not found")
	}
	return nil
}

func (r *GraphRepository) ArchiveUserMemory(ctx context.Context, userID string) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)
	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory)
			SET m.active = false,
			    m.privacy_cleared_at = datetime()
		`, map[string]any{"user_id": userID})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("neo4j archive user memory: %w", err)
	}
	return nil
}

func stringValue(rec *neo4j.Record, key string) string {
	v, ok := rec.Get(key)
	if !ok || v == nil {
		return ""
	}
	return fmt.Sprint(v)
}

func intValue(rec *neo4j.Record, key string) int {
	v, ok := rec.Get(key)
	if !ok || v == nil {
		return 0
	}
	switch n := v.(type) {
	case int:
		return n
	case int64:
		return int(n)
	case float64:
		return int(n)
	default:
		return 0
	}
}

func floatValue(rec *neo4j.Record, key string) float64 {
	v, ok := rec.Get(key)
	if !ok || v == nil {
		return 0
	}
	switch n := v.(type) {
	case float64:
		return n
	case int64:
		return float64(n)
	case int:
		return float64(n)
	default:
		return 0
	}
}

func boolValue(rec *neo4j.Record, key string) bool {
	v, ok := rec.Get(key)
	if !ok || v == nil {
		return false
	}
	b, _ := v.(bool)
	return b
}

func nullableInt(rec *neo4j.Record, key string) *int {
	v := intValue(rec, key)
	raw, ok := rec.Get(key)
	if !ok || raw == nil {
		return nil
	}
	return &v
}

func nullableTime(rec *neo4j.Record, key string) *time.Time {
	v, ok := rec.Get(key)
	if !ok || v == nil {
		return nil
	}
	t, ok := v.(time.Time)
	if !ok {
		return nil
	}
	return &t
}

func timeValue(rec *neo4j.Record, key string) time.Time {
	v, ok := rec.Get(key)
	if !ok || v == nil {
		return time.Time{}
	}
	switch t := v.(type) {
	case time.Time:
		return t
	default:
		return time.Time{}
	}
}

func stringSliceValue(rec *neo4j.Record, key string) []entity.MemoryTag {
	v, ok := rec.Get(key)
	if !ok || v == nil {
		return nil
	}
	switch values := v.(type) {
	case []any:
		out := make([]entity.MemoryTag, 0, len(values))
		for _, value := range values {
			if s := strings.TrimSpace(fmt.Sprint(value)); s != "" {
				out = append(out, entity.MemoryTag(s))
			}
		}
		return out
	case []string:
		out := make([]entity.MemoryTag, 0, len(values))
		for _, value := range values {
			if s := strings.TrimSpace(value); s != "" {
				out = append(out, entity.MemoryTag(s))
			}
		}
		return out
	default:
		return nil
	}
}

func memoryFromRecord(rec *neo4j.Record) entity.Memory {
	return entity.Memory{
		ID:                    stringValue(rec, "id"),
		UserID:                stringValue(rec, "user_id"),
		Title:                 stringValue(rec, "title"),
		Content:               stringValue(rec, "content"),
		Tags:                  stringSliceValue(rec, "tags"),
		IsPinned:              boolValue(rec, "is_pinned"),
		Source:                stringValue(rec, "source"),
		RelatedConversationID: stringValue(rec, "related_conversation_id"),
		Emotion:               stringValue(rec, "emotion"),
		Importance:            floatValue(rec, "importance"),
		Active:                boolValue(rec, "active"),
		EmbeddingSynced:       boolValue(rec, "embedding_synced"),
		CreatedAt:             timeValue(rec, "created_at"),
		UpdatedAt:             timeValue(rec, "updated_at"),
		LastAccessed:          timeValue(rec, "last_accessed"),
	}
}

func memoryParams(memory entity.Memory) map[string]any {
	tags := make([]string, 0, len(memory.Tags))
	for _, tag := range memory.Tags {
		tags = append(tags, string(tag))
	}
	return map[string]any{
		"id":                      memory.ID,
		"user_id":                 memory.UserID,
		"title":                   memory.Title,
		"content":                 memory.Content,
		"tags":                    tags,
		"is_pinned":               memory.IsPinned,
		"source":                  memory.Source,
		"related_conversation_id": memory.RelatedConversationID,
		"emotion":                 memory.Emotion,
		"importance":              memory.Importance,
		"embedding_synced":        memory.EmbeddingSynced,
	}
}
