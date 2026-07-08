// mem service queries
package repository

import (
	"context"
	"fmt"
	"time"

	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

// neo4j_repo_handles_graph_operations
type Neo4jRepo struct {
	driver neo4j.DriverWithContext
}

// ```go NewRepo(NewNeo4jDriver) ```
func New(driver neo4j.DriverWithContext) *Neo4jRepo {
	return &Neo4jRepo{driver: driver}
}

// user.

// UpsertUser checks if user exists, then updates last_active.
func (r *Neo4jRepo) UpsertUser(ctx context.Context, userID, displayName string) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MERGE (u:User {id: $id})
			ON CREATE SET
				u.display_name        = $display_name,
				u.created_at          = datetime(),
				u.last_active         = datetime(),
				u.session_count       = 0,
				u.onboarding_complete = false
			ON MATCH SET
				u.last_active = datetime()
		`, map[string]any{
			"id":           userID,
			"display_name": displayName,
		})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("UpsertUser: %w", err)
	}
	return nil
}

// get user returns nil if not found.
func (r *Neo4jRepo) GetUser(ctx context.Context, userID string) (map[string]any, error) {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)

	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, `
			MATCH (u:User {id: $id})
			RETURN u.id              AS id,
			       u.display_name   AS display_name,
			       u.created_at     AS created_at,
			       u.last_active    AS last_active,
			       u.session_count  AS session_count,
			       u.onboarding_complete AS onboarding_complete
		`, map[string]any{"id": userID})
		if err != nil {
			return nil, err
		}
		if res.Next(ctx) {
			return res.Record().AsMap(), nil
		}
		return nil, nil
	})
	if err != nil {
		return nil, fmt.Errorf("GetUser: %w", err)
	}
	if result == nil {
		return nil, nil
	}
	return result.(map[string]any), nil
}

// set_onboarding_complete=true
func (r *Neo4jRepo) MarkOnboardingComplete(ctx context.Context, userID string) error {
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
		return fmt.Errorf("MarkOnboardingComplete: %w", err)
	}
	return nil
}

// ses.

// open session, link to user, get session id.
func (r *Neo4jRepo) OpenSession(ctx context.Context, sessionID, userID, channel string) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})
			CREATE (s:Session {
				id:                $session_id,
				started_at:        datetime(),
				ended_at:          null,
				channel:           $channel,
				summary:           null,
				sentiment_avg:     null,
				phq9_administered: false
			})
			CREATE (u)-[:HAD_SESSION {
				t_valid:        datetime(),
				t_invalid:      null,
				confidence:     1.0,
				source_session: $session_id
			}]->(s)
			SET u.session_count = u.session_count + 1
		`, map[string]any{
			"user_id":    userID,
			"session_id": sessionID,
			"channel":    channel,
		})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("OpenSession: %w", err)
	}
	return nil
}

// set ended_at, llm_summary, senti_avg
func (r *Neo4jRepo) CloseSession(
	ctx context.Context,
	sessionID, summary string,
	sentimentAvg float64,
) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MATCH (s:Session {id: $session_id})
			SET s.ended_at     = datetime(),
			    s.summary      = $summary,
			    s.sentiment_avg = $sentiment_avg
		`, map[string]any{
			"session_id":    sessionID,
			"summary":       summary,
			"sentiment_avg": sentimentAvg,
		})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("CloseSession: %w", err)
	}
	return nil
}

// set phq9_administered=true
func (r *Neo4jRepo) MarkPHQ9Administered(ctx context.Context, sessionID string) error {
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
		return fmt.Errorf("MarkPHQ9Administered: %w", err)
	}
	return nil
}

// assess.

// Assessment node, User, Session, PHQ-9, GAD-7, IPIP.
func (r *Neo4jRepo) WriteAssessment(ctx context.Context, a AssessmentInput) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MATCH (u:User    {id: $user_id})
			MATCH (s:Session {id: $session_id})
			CREATE (a:Assessment {
				id:                  $id,
				instrument:          $instrument,
				score:               $score,
				severity_label:      $severity_label,
				delta_from_previous: $delta,
				administered_at:     datetime(),
				q9_score:            $q9_score,
				item_responses:      $item_responses,
				sensitivity_level:   'normal'
			})
			CREATE (s)-[:PRODUCED_ASSESSMENT {
				t_valid:        datetime(),
				t_invalid:      null,
				confidence:     1.0,
				source_session: $session_id
			}]->(a)
			CREATE (u)-[:COMPLETED_ASSESSMENT {
				t_valid:        datetime(),
				t_invalid:      null,
				source_session: $session_id
			}]->(a)
		`, map[string]any{
			"user_id":        a.UserID,
			"session_id":     a.SessionID,
			"id":             a.ID,
			"instrument":     a.Instrument,
			"score":          a.Score,
			"severity_label": a.SeverityLabel,
			"delta":          a.DeltaFromPrevious,
			"q9_score":       a.Q9Score,
			"item_responses": a.ItemResponsesJSON,
		})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("WriteAssessment: %w", err)
	}
	return nil
}

// get latest ass fetch 14-day interval
func (r *Neo4jRepo) GetLatestAssessment(
	ctx context.Context,
	userID, instrument string,
) (map[string]any, error) {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)

	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})-[:COMPLETED_ASSESSMENT]->(a:Assessment)
			WHERE a.instrument = $instrument
			RETURN a.id             AS id,
			       a.score          AS score,
			       a.severity_label AS severity_label,
			       a.administered_at AS administered_at,
			       a.q9_score       AS q9_score
			ORDER BY a.administered_at DESC
			LIMIT 1
		`, map[string]any{
			"user_id":    userID,
			"instrument": instrument,
		})
		if err != nil {
			return nil, err
		}
		if res.Next(ctx) {
			return res.Record().AsMap(), nil
		}
		return nil, nil
	})
	if err != nil {
		return nil, fmt.Errorf("GetLatestAssessment: %w", err)
	}
	if result == nil {
		return nil, nil
	}
	return result.(map[string]any), nil
}

// upsert pure freq inc Go handlers

// UpsertTopic Called from Python via gRPC.
func (r *Neo4jRepo) UpsertTopic(
	ctx context.Context,
	topicID, userID, name string,
	sentiment float64,
) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})
			MERGE (top:Topic {name: $name})
			ON CREATE SET
				top.id           = $topic_id,
				top.frequency    = 1,
				top.first_seen   = datetime(),
				top.last_seen    = datetime(),
				top.avg_sentiment = $sentiment
			ON MATCH SET
				top.frequency    = top.frequency + 1,
				top.last_seen    = datetime(),
				top.avg_sentiment = (top.avg_sentiment + $sentiment) / 2.0
			MERGE (u)-[:HAS_RECURRING_THEME]->(top)
		`, map[string]any{
			"user_id":   userID,
			"topic_id":  topicID,
			"name":      name,
			"sentiment": sentiment,
		})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("UpsertTopic: %w", err)
	}
	return nil
}

// read signal

// get signals before session open
func (r *Neo4jRepo) GetEscalationSignals(
	ctx context.Context,
	userID string,
) (*EscalationSignals, error) {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeRead})
	defer session.Close(ctx)

	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		res, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})

			// emotenya di masa lalu 48 jam
			OPTIONAL MATCH (u)-[:FELT]->(emo:Emotion)
			WHERE emo.active = true
			  AND emo.timestamp > datetime() - duration('PT48H')
			WITH u, emo
			ORDER BY emo.timestamp DESC
			LIMIT 1

			// check phq9 score
			OPTIONAL MATCH (u)-[:COMPLETED_ASSESSMENT]->(a:Assessment)
			WHERE a.instrument = 'PHQ-9'
			WITH u, emo, a
			ORDER BY a.administered_at DESC
			LIMIT 1

			// set weekly sess cnt
			OPTIONAL MATCH (u)-[:HAD_SESSION]->(s:Session)
			WHERE s.started_at > datetime() - duration('P7D')

			RETURN
				emo.valence         AS latest_valence,
				emo.intensity       AS latest_intensity,
				a.score             AS latest_phq9_score,
				a.delta_from_previous AS phq9_delta,
				a.q9_score          AS q9_score,
				a.administered_at   AS last_phq9_at,
				count(s)            AS sessions_this_week
		`, map[string]any{"user_id": userID})
		if err != nil {
			return nil, err
		}
		if !res.Next(ctx) {
			return &EscalationSignals{}, nil
		}
		rec := res.Record()

		signals := &EscalationSignals{}
		if v, ok := rec.Get("latest_valence"); ok && v != nil {
			signals.LatestValence = v.(float64)
		}
		if v, ok := rec.Get("latest_intensity"); ok && v != nil {
			signals.LatestIntensity = v.(float64)
		}
		if v, ok := rec.Get("latest_phq9_score"); ok && v != nil {
			signals.LatestPHQ9Score = int(v.(int64))
		}
		if v, ok := rec.Get("phq9_delta"); ok && v != nil {
			signals.PHQ9Delta = int(v.(int64))
		}
		if v, ok := rec.Get("q9_score"); ok && v != nil {
			signals.Q9Score = int(v.(int64))
		}
		if v, ok := rec.Get("sessions_this_week"); ok && v != nil {
			signals.SessionsThisWeek = int(v.(int64))
		}
		if v, ok := rec.Get("last_phq9_at"); ok && v != nil {
			if t, ok := v.(time.Time); ok {
				signals.LastPHQ9At = &t
			}
		}
		return signals, nil
	})
	if err != nil {
		return nil, fmt.Errorf("GetEscalationSignals: %w", err)
	}
	return result.(*EscalationSignals), nil
}

// privacy.

// archive mem nodes, set active=false, clear privacy_cleared_at.
func (r *Neo4jRepo) ArchiveUserMemory(ctx context.Context, userID string) error {
	session := r.driver.NewSession(ctx, neo4j.SessionConfig{AccessMode: neo4j.AccessModeWrite})
	defer session.Close(ctx)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		_, err := tx.Run(ctx, `
			MATCH (u:User {id: $user_id})-[:HAS_MEMORY]->(m:Memory)
			SET m.active            = false,
			    m.privacy_cleared_at = datetime()
		`, map[string]any{"user_id": userID})
		return nil, err
	})
	if err != nil {
		return fmt.Errorf("ArchiveUserMemory: %w", err)
	}
	return nil
}

// set inputs/outputs

// assess groups fields
type AssessmentInput struct {
	ID                string
	UserID            string
	SessionID         string
	Instrument        string // "PHQ-9" | "GAD-7" | "IPIP"
	Score             int
	SeverityLabel     string
	DeltaFromPrevious *int   // nil on first assessment
	Q9Score           int    // PHQ-9 item 9 only; 0 for GAD-7 / IPIP
	ItemResponsesJSON string // raw JSON string of item_responses map
}

// EscalationSignals holds signals.
type EscalationSignals struct {
	LatestValence    float64
	LatestIntensity  float64
	LatestPHQ9Score  int
	PHQ9Delta        int
	Q9Score          int
	SessionsThisWeek int
	LastPHQ9At       *time.Time
}

// nggunin 48-hr rule
func (s *EscalationSignals) ShouldSuppressReminder() bool {
	return s.LatestValence < -0.6 && s.LatestIntensity > 0.7
}

// is crisis true q9 >= 1
func (s *EscalationSignals) IsCrisis() bool {
	return s.Q9Score >= 1
}

// `PHQ9 delta > 3` & `last 7 days`
func (s *EscalationSignals) ShouldSuppressPHQ9() bool {
	if s.LastPHQ9At == nil {
		return false
	}
	withinWindow := time.Since(*s.LastPHQ9At) < 7*24*time.Hour
	return withinWindow && s.PHQ9Delta >= 3
}

// check soc conn
func (s *EscalationSignals) ShouldNudgeSocialConnection() bool {
	return s.SessionsThisWeek > 20
}
