package usecase

import (
	"context"
	"strings"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/domain/entity"
	"github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/domain/repository"
	apperrors "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/errors"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/id"
	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/validator"
)

type MemoryUsecase struct {
	graph   repository.GraphRepository
	agentic AgenticMemoryClient
	now     func() time.Time
}

func NewMemoryUsecase(graph repository.GraphRepository) *MemoryUsecase {
	return &MemoryUsecase{graph: graph, now: time.Now}
}

func NewMemoryUsecaseWithAgentic(graph repository.GraphRepository, agentic AgenticMemoryClient) *MemoryUsecase {
	return &MemoryUsecase{graph: graph, agentic: agentic, now: time.Now}
}

type AgenticMemoryClient interface {
	ListMemoryNodes(ctx context.Context, userID, nodeType, query string, limit, offset int) (MemoryNodeListDTO, error)
	ListMemoryRelations(ctx context.Context, userID string, limit int) (MemoryGraphRelationListDTO, error)
	UpdateMemoryNode(ctx context.Context, userID, nodeType, nodeID string, properties map[string]any) (MemoryNodeUpdateDTO, error)
	DeleteMemoryNode(ctx context.Context, userID, nodeType, nodeID string) (MemoryNodeDeleteDTO, error)
	ResetUserMemory(ctx context.Context, userID string) (MemoryResetDTO, error)
	PurgeUserAccount(ctx context.Context, userID string) (PurgeUserAccountDTO, error)
}

func (u *MemoryUsecase) UpsertUser(ctx context.Context, user entity.User) error {
	return u.graph.UpsertUser(ctx, user)
}

func (u *MemoryUsecase) OpenSession(ctx context.Context, session entity.Session) error {
	return u.graph.OpenSession(ctx, session)
}

func (u *MemoryUsecase) WriteAssessment(ctx context.Context, assessment entity.Assessment) error {
	return u.graph.WriteAssessment(ctx, assessment)
}

func (u *MemoryUsecase) UpsertTopic(ctx context.Context, topic entity.Topic) error {
	return u.graph.UpsertTopic(ctx, topic)
}

type MemoryDTO struct {
	ID                    string   `json:"id"`
	UserID                string   `json:"userId"`
	Title                 string   `json:"title"`
	Content               string   `json:"content"`
	Tags                  []string `json:"tags"`
	IsPinned              bool     `json:"isPinned"`
	Source                string   `json:"source,omitempty"`
	RelatedConversationID string   `json:"relatedConversationId,omitempty"`
	Emotion               string   `json:"emotion,omitempty"`
	CreatedAt             int64    `json:"createdAt"`
	UpdatedAt             int64    `json:"updatedAt"`
}

type MemoryFilter struct {
	Tags        []string
	SearchQuery string
	Limit       int
	Offset      int
}

type MemoryNodeDTO struct {
	ID              string              `json:"id"`
	Type            string              `json:"type"`
	Label           string              `json:"label"`
	Title           string              `json:"title"`
	Preview         string              `json:"preview"`
	Properties      map[string]any      `json:"properties"`
	EditableFields  []string            `json:"editableFields"`
	EnumFields      map[string][]string `json:"enumFields"`
	EmbeddingSynced *bool               `json:"embeddingSynced,omitempty"`
	UpdatedAt       string              `json:"updatedAt,omitempty"`
}

type MemoryNodeListDTO struct {
	Nodes    []MemoryNodeDTO `json:"nodes"`
	NodeType string          `json:"nodeType"`
	Total    int             `json:"total"`
}

type MemoryGraphRelationDTO struct {
	ID           string   `json:"id"`
	SourceID     string   `json:"sourceId"`
	SourceType   string   `json:"sourceType"`
	SourceTitle  string   `json:"sourceTitle"`
	TargetID     string   `json:"targetId"`
	TargetType   string   `json:"targetType"`
	TargetTitle  string   `json:"targetTitle"`
	RelationType string   `json:"relationType"`
	Label        string   `json:"label"`
	Confidence   *float64 `json:"confidence,omitempty"`
}

type MemoryGraphRelationListDTO struct {
	Relations []MemoryGraphRelationDTO `json:"relations"`
	Total     int                      `json:"total"`
}

type MemoryNodeUpdateDTO struct {
	Node           MemoryNodeDTO `json:"node"`
	Updated        bool          `json:"updated"`
	PGVectorSynced *bool         `json:"pgvectorSynced,omitempty"`
}

type MemoryNodeDeleteDTO struct {
	Deleted          bool `json:"deleted"`
	Archived         bool `json:"archived"`
	PGVectorArchived int  `json:"pgvectorArchived"`
}

type MemoryResetDTO struct {
	Reset                    bool `json:"reset"`
	NodesDeleted             int  `json:"nodesDeleted"`
	SessionsDeleted          int  `json:"sessionsDeleted"`
	UserRelationshipsDeleted int  `json:"userRelationshipsDeleted"`
	PGVectorRowsDeleted      int  `json:"pgvectorRowsDeleted"`
	UserDeleted              int  `json:"userDeleted"`
}

type PurgeUserAccountDTO struct {
	Purged              bool `json:"purged"`
	NodesDeleted        int  `json:"nodesDeleted"`
	SessionsDeleted     int  `json:"sessionsDeleted"`
	UserDeleted         int  `json:"userDeleted"`
	PGVectorRowsDeleted int  `json:"pgvectorRowsDeleted"`
}

type CreateMemoryInput struct {
	UserID                string
	Title                 string
	Content               string
	Tags                  []string
	RelatedConversationID string
	Source                string
	Emotion               string
}

type UpdateMemoryInput struct {
	UserID   string
	ID       string
	Title    *string
	Content  *string
	Tags     []string
	HasTags  bool
	IsPinned *bool
}

func (u *MemoryUsecase) ListMemories(ctx context.Context, userID string, filter MemoryFilter) ([]MemoryDTO, error) {
	if err := validateUUID("userId", userID); err != nil {
		return nil, err
	}
	memories, err := u.graph.ListMemories(ctx, userID, repository.MemoryFilter{
		Tags:        filter.Tags,
		SearchQuery: strings.TrimSpace(filter.SearchQuery),
		Limit:       validator.ClampInt(filter.Limit, 1, 100),
		Offset:      max(filter.Offset, 0),
	})
	if err != nil {
		return nil, err
	}
	out := make([]MemoryDTO, 0, len(memories))
	for _, memory := range memories {
		out = append(out, memoryDTO(memory))
	}
	return out, nil
}

func (u *MemoryUsecase) GetMemory(ctx context.Context, userID string, memoryID string) (MemoryDTO, error) {
	if err := validateUUID("userId", userID); err != nil {
		return MemoryDTO{}, err
	}
	if err := validateUUID("memoryId", memoryID); err != nil {
		return MemoryDTO{}, err
	}
	memory, err := u.graph.GetMemory(ctx, userID, memoryID)
	if err != nil {
		return MemoryDTO{}, err
	}
	if memory == nil {
		return MemoryDTO{}, apperrors.NotFound("memory not found")
	}
	return memoryDTO(*memory), nil
}

func (u *MemoryUsecase) CreateMemory(ctx context.Context, input CreateMemoryInput) (MemoryDTO, error) {
	if err := validateUUID("userId", input.UserID); err != nil {
		return MemoryDTO{}, err
	}
	title, content, err := validateMemoryText(input.Title, input.Content)
	if err != nil {
		return MemoryDTO{}, err
	}
	memoryID, err := id.NewUUID()
	if err != nil {
		return MemoryDTO{}, err
	}
	source := strings.TrimSpace(input.Source)
	if source == "" {
		source = "manual"
	}
	now := u.now()
	memory, err := u.graph.CreateMemory(ctx, entity.Memory{
		ID:                    memoryID,
		UserID:                input.UserID,
		Title:                 title,
		Content:               content,
		Tags:                  toMemoryTags(input.Tags),
		IsPinned:              false,
		Source:                source,
		RelatedConversationID: strings.TrimSpace(input.RelatedConversationID),
		Emotion:               strings.TrimSpace(input.Emotion),
		Importance:            0.7,
		Active:                true,
		EmbeddingSynced:       false,
		CreatedAt:             now,
		UpdatedAt:             now,
		LastAccessed:          now,
	})
	if err != nil {
		return MemoryDTO{}, err
	}
	return memoryDTO(memory), nil
}

func (u *MemoryUsecase) UpdateMemory(ctx context.Context, input UpdateMemoryInput) (MemoryDTO, error) {
	if err := validateUUID("userId", input.UserID); err != nil {
		return MemoryDTO{}, err
	}
	if err := validateUUID("memoryId", input.ID); err != nil {
		return MemoryDTO{}, err
	}
	current, err := u.graph.GetMemory(ctx, input.UserID, input.ID)
	if err != nil {
		return MemoryDTO{}, err
	}
	if current == nil {
		return MemoryDTO{}, apperrors.NotFound("memory not found")
	}
	updated := *current
	updated.UserID = input.UserID
	if input.Title != nil {
		updated.Title = strings.TrimSpace(*input.Title)
	}
	if input.Content != nil {
		updated.Content = strings.TrimSpace(*input.Content)
		updated.EmbeddingSynced = false
	}
	if _, _, err := validateMemoryText(updated.Title, updated.Content); err != nil {
		return MemoryDTO{}, err
	}
	if input.HasTags {
		updated.Tags = toMemoryTags(input.Tags)
	}
	if input.IsPinned != nil {
		updated.IsPinned = *input.IsPinned
	}
	updated.UpdatedAt = u.now()
	memory, err := u.graph.UpdateMemory(ctx, updated)
	if err != nil {
		return MemoryDTO{}, err
	}
	return memoryDTO(memory), nil
}

func (u *MemoryUsecase) DeleteMemory(ctx context.Context, userID string, memoryID string) error {
	if err := validateUUID("userId", userID); err != nil {
		return err
	}
	if err := validateUUID("memoryId", memoryID); err != nil {
		return err
	}
	return u.graph.DeleteMemory(ctx, userID, memoryID)
}

func (u *MemoryUsecase) ListMemoryNodes(ctx context.Context, userID string, nodeType string, query string, limit int, offset int) (MemoryNodeListDTO, error) {
	if u.agentic == nil {
		return MemoryNodeListDTO{}, apperrors.Invalid("agentic memory service is not configured")
	}
	if err := validateUUID("userId", userID); err != nil {
		return MemoryNodeListDTO{}, err
	}
	return u.agentic.ListMemoryNodes(
		ctx,
		userID,
		strings.TrimSpace(nodeType),
		strings.TrimSpace(query),
		validator.ClampInt(limit, 1, 100),
		max(offset, 0),
	)
}

func (u *MemoryUsecase) ListMemoryRelations(ctx context.Context, userID string, limit int) (MemoryGraphRelationListDTO, error) {
	if u.agentic == nil {
		return MemoryGraphRelationListDTO{}, apperrors.Invalid("agentic memory service is not configured")
	}
	if err := validateUUID("userId", userID); err != nil {
		return MemoryGraphRelationListDTO{}, err
	}
	return u.agentic.ListMemoryRelations(ctx, userID, validator.ClampInt(limit, 1, 300))
}

func (u *MemoryUsecase) UpdateMemoryNode(ctx context.Context, userID string, nodeType string, nodeID string, properties map[string]any) (MemoryNodeUpdateDTO, error) {
	if u.agentic == nil {
		return MemoryNodeUpdateDTO{}, apperrors.Invalid("agentic memory service is not configured")
	}
	if err := validateUUID("userId", userID); err != nil {
		return MemoryNodeUpdateDTO{}, err
	}
	if strings.TrimSpace(nodeID) == "" {
		return MemoryNodeUpdateDTO{}, apperrors.InvalidField("nodeId", "nodeId is required")
	}
	return u.agentic.UpdateMemoryNode(ctx, userID, strings.TrimSpace(nodeType), strings.TrimSpace(nodeID), properties)
}

func (u *MemoryUsecase) DeleteMemoryNode(ctx context.Context, userID string, nodeType string, nodeID string) (MemoryNodeDeleteDTO, error) {
	if u.agentic == nil {
		return MemoryNodeDeleteDTO{}, apperrors.Invalid("agentic memory service is not configured")
	}
	if err := validateUUID("userId", userID); err != nil {
		return MemoryNodeDeleteDTO{}, err
	}
	if strings.TrimSpace(nodeID) == "" {
		return MemoryNodeDeleteDTO{}, apperrors.InvalidField("nodeId", "nodeId is required")
	}
	return u.agentic.DeleteMemoryNode(ctx, userID, strings.TrimSpace(nodeType), strings.TrimSpace(nodeID))
}

func (u *MemoryUsecase) ResetUserMemory(ctx context.Context, userID string) (MemoryResetDTO, error) {
	if u.agentic == nil {
		return MemoryResetDTO{}, apperrors.Invalid("agentic memory service is not configured")
	}
	if err := validateUUID("userId", userID); err != nil {
		return MemoryResetDTO{}, err
	}
	return u.agentic.ResetUserMemory(ctx, userID)
}

func (u *MemoryUsecase) PurgeUserAccount(ctx context.Context, userID string) (PurgeUserAccountDTO, error) {
	if u.agentic == nil {
		return PurgeUserAccountDTO{}, apperrors.Invalid("agentic memory service is not configured")
	}
	if err := validateUUID("userId", userID); err != nil {
		return PurgeUserAccountDTO{}, err
	}
	return u.agentic.PurgeUserAccount(ctx, userID)
}

func (u *MemoryUsecase) EscalationPolicy(ctx context.Context, userID string) (EscalationPolicy, error) {
	signals, err := u.graph.GetEscalationSignals(ctx, userID)
	if err != nil {
		return EscalationPolicy{}, err
	}
	return EscalationPolicy{
		Signals:               signals,
		SuppressReminder:      signals.ShouldSuppressReminder(),
		SuppressPHQ9:          signals.ShouldSuppressPHQ9(u.now()),
		Crisis:                signals.IsCrisis(),
		NudgeSocialConnection: signals.ShouldNudgeSocialConnection(),
	}, nil
}

func (u *MemoryUsecase) ArchiveUserMemory(ctx context.Context, userID string) error {
	return u.graph.ArchiveUserMemory(ctx, userID)
}

type EscalationPolicy struct {
	Signals               entity.EscalationSignals `json:"signals"`
	SuppressReminder      bool                     `json:"suppress_reminder"`
	SuppressPHQ9          bool                     `json:"suppress_phq9"`
	Crisis                bool                     `json:"crisis"`
	NudgeSocialConnection bool                     `json:"nudge_social_connection"`
}

func validateMemoryText(title string, content string) (string, string, error) {
	title = strings.TrimSpace(title)
	content = strings.TrimSpace(content)
	if title == "" {
		return "", "", apperrors.InvalidField("title", "title is required")
	}
	if len(title) > 200 {
		return "", "", apperrors.InvalidField("title", "title must be at most 200 characters")
	}
	if content == "" {
		return "", "", apperrors.InvalidField("content", "content is required")
	}
	if len(content) > 10000 {
		return "", "", apperrors.InvalidField("content", "content must be at most 10000 characters")
	}
	return title, content, nil
}

func validateUUID(field string, value string) error {
	value = strings.TrimSpace(value)
	if value == "" {
		return apperrors.InvalidField(field, field+" is required")
	}
	if !validator.UUID(value) {
		return apperrors.InvalidField(field, field+" must be a UUID")
	}
	return nil
}

func memoryDTO(memory entity.Memory) MemoryDTO {
	tags := make([]string, 0, len(memory.Tags))
	for _, tag := range memory.Tags {
		tags = append(tags, string(tag))
	}
	return MemoryDTO{
		ID:                    memory.ID,
		UserID:                memory.UserID,
		Title:                 memory.Title,
		Content:               memory.Content,
		Tags:                  tags,
		IsPinned:              memory.IsPinned,
		Source:                memory.Source,
		RelatedConversationID: memory.RelatedConversationID,
		Emotion:               memory.Emotion,
		CreatedAt:             millis(memory.CreatedAt),
		UpdatedAt:             millis(memory.UpdatedAt),
	}
}

func toMemoryTags(tags []string) []entity.MemoryTag {
	out := make([]entity.MemoryTag, 0, len(tags))
	seen := map[string]bool{}
	for _, tag := range tags {
		tag = strings.ToLower(strings.TrimSpace(tag))
		if tag == "" || seen[tag] {
			continue
		}
		seen[tag] = true
		out = append(out, entity.MemoryTag(tag))
	}
	return out
}

func millis(t time.Time) int64 {
	if t.IsZero() {
		return 0
	}
	return t.UnixMilli()
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
