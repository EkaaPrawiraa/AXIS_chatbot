package agentic

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	apperrors "github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/errors"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/memory/internal/usecase"
)

type Client struct {
	baseURL    string
	privateKey string
	httpClient *http.Client
}

func New(baseURL, privateKey string) *Client {
	return &Client{
		baseURL:    strings.TrimRight(baseURL, "/"),
		privateKey: privateKey,
		httpClient: &http.Client{Timeout: 60 * time.Second},
	}
}

type MemoryNode struct {
	ID              string              `json:"id"`
	Type            string              `json:"type"`
	Label           string              `json:"label"`
	Title           string              `json:"title"`
	Preview         string              `json:"preview"`
	Properties      map[string]any      `json:"properties"`
	EditableFields  []string            `json:"editable_fields"`
	EnumFields      map[string][]string `json:"enum_fields"`
	EmbeddingSynced *bool               `json:"embedding_synced,omitempty"`
	UpdatedAt       string              `json:"updated_at,omitempty"`
}

type ListMemoryNodesResponse struct {
	Nodes    []MemoryNode `json:"nodes"`
	NodeType string       `json:"node_type"`
	Total    int          `json:"total"`
}

type MemoryGraphRelation struct {
	ID           string   `json:"id"`
	SourceID     string   `json:"source_id"`
	SourceType   string   `json:"source_type"`
	SourceTitle  string   `json:"source_title"`
	TargetID     string   `json:"target_id"`
	TargetType   string   `json:"target_type"`
	TargetTitle  string   `json:"target_title"`
	RelationType string   `json:"relation_type"`
	Label        string   `json:"label"`
	Confidence   *float64 `json:"confidence,omitempty"`
}

type ListMemoryRelationsResponse struct {
	Relations []MemoryGraphRelation `json:"relations"`
	Total     int                   `json:"total"`
}

type UpdateMemoryNodeRequest struct {
	UserID     string         `json:"user_id"`
	Properties map[string]any `json:"properties"`
}

type UpdateMemoryNodeResponse struct {
	Node           MemoryNode `json:"node"`
	Updated        bool       `json:"updated"`
	PGVectorSynced *bool      `json:"pgvector_synced,omitempty"`
}

type DeleteMemoryNodeResponse struct {
	Deleted          bool `json:"deleted"`
	Archived         bool `json:"archived"`
	PGVectorArchived int  `json:"pgvector_archived"`
}

type ResetUserMemoryResponse struct {
	Reset                    bool `json:"reset"`
	NodesDeleted             int  `json:"nodes_deleted"`
	SessionsDeleted          int  `json:"sessions_deleted"`
	UserRelationshipsDeleted int  `json:"user_relationships_deleted"`
	PGVectorRowsDeleted      int  `json:"pgvector_rows_deleted"`
	UserDeleted              int  `json:"user_deleted"`
}

type PurgeUserAccountResponse struct {
	Purged              bool `json:"purged"`
	NodesDeleted        int  `json:"nodes_deleted"`
	SessionsDeleted     int  `json:"sessions_deleted"`
	UserDeleted         int  `json:"user_deleted"`
	PGVectorRowsDeleted int  `json:"pgvector_rows_deleted"`
}

func (c *Client) ListMemoryNodes(ctx context.Context, userID, nodeType, query string, limit, offset int) (usecase.MemoryNodeListDTO, error) {
	values := url.Values{}
	values.Set("user_id", userID)
	values.Set("node_type", nodeType)
	values.Set("q", query)
	values.Set("limit", fmt.Sprintf("%d", limit))
	values.Set("offset", fmt.Sprintf("%d", offset))
	var out ListMemoryNodesResponse
	if err := c.do(ctx, http.MethodGet, "/memory-nodes?"+values.Encode(), nil, &out); err != nil {
		return usecase.MemoryNodeListDTO{}, err
	}
	return mapList(out), nil
}

func (c *Client) ListMemoryRelations(ctx context.Context, userID string, limit int) (usecase.MemoryGraphRelationListDTO, error) {
	values := url.Values{}
	values.Set("user_id", userID)
	values.Set("limit", fmt.Sprintf("%d", limit))
	var out ListMemoryRelationsResponse
	if err := c.do(ctx, http.MethodGet, "/memory-nodes/relations?"+values.Encode(), nil, &out); err != nil {
		return usecase.MemoryGraphRelationListDTO{}, err
	}
	return mapRelations(out), nil
}

func (c *Client) UpdateMemoryNode(ctx context.Context, userID, nodeType, nodeID string, properties map[string]any) (usecase.MemoryNodeUpdateDTO, error) {
	var out UpdateMemoryNodeResponse
	err := c.do(ctx, http.MethodPatch, "/memory-nodes/"+url.PathEscape(nodeType)+"/"+url.PathEscape(nodeID), UpdateMemoryNodeRequest{
		UserID:     userID,
		Properties: properties,
	}, &out)
	if err != nil {
		return usecase.MemoryNodeUpdateDTO{}, err
	}
	return usecase.MemoryNodeUpdateDTO{
		Node:           mapNode(out.Node),
		Updated:        out.Updated,
		PGVectorSynced: out.PGVectorSynced,
	}, nil
}

func (c *Client) DeleteMemoryNode(ctx context.Context, userID, nodeType, nodeID string) (usecase.MemoryNodeDeleteDTO, error) {
	values := url.Values{}
	values.Set("user_id", userID)
	var out DeleteMemoryNodeResponse
	err := c.do(ctx, http.MethodDelete, "/memory-nodes/"+url.PathEscape(nodeType)+"/"+url.PathEscape(nodeID)+"?"+values.Encode(), nil, &out)
	if err != nil {
		return usecase.MemoryNodeDeleteDTO{}, err
	}
	return usecase.MemoryNodeDeleteDTO{
		Deleted:          out.Deleted,
		Archived:         out.Archived,
		PGVectorArchived: out.PGVectorArchived,
	}, nil
}

func (c *Client) ResetUserMemory(ctx context.Context, userID string) (usecase.MemoryResetDTO, error) {
	var out ResetUserMemoryResponse
	err := c.do(ctx, http.MethodDelete, "/memory-nodes/users/"+url.PathEscape(userID)+"/reset", nil, &out)
	if err != nil {
		return usecase.MemoryResetDTO{}, err
	}
	return usecase.MemoryResetDTO{
		Reset:                    out.Reset,
		NodesDeleted:             out.NodesDeleted,
		SessionsDeleted:          out.SessionsDeleted,
		UserRelationshipsDeleted: out.UserRelationshipsDeleted,
		PGVectorRowsDeleted:      out.PGVectorRowsDeleted,
		UserDeleted:              out.UserDeleted,
	}, nil
}

func (c *Client) PurgeUserAccount(ctx context.Context, userID string) (usecase.PurgeUserAccountDTO, error) {
	var out PurgeUserAccountResponse
	err := c.do(ctx, http.MethodDelete, "/memory-nodes/users/"+url.PathEscape(userID)+"/purge", nil, &out)
	if err != nil {
		return usecase.PurgeUserAccountDTO{}, err
	}
	return usecase.PurgeUserAccountDTO{
		Purged:              out.Purged,
		NodesDeleted:        out.NodesDeleted,
		SessionsDeleted:     out.SessionsDeleted,
		UserDeleted:         out.UserDeleted,
		PGVectorRowsDeleted: out.PGVectorRowsDeleted,
	}, nil
}

func (c *Client) do(ctx context.Context, method string, path string, in any, out any) error {
	var body bytes.Buffer
	if in != nil {
		if err := json.NewEncoder(&body).Encode(in); err != nil {
			return fmt.Errorf("agentic memory marshal request: %w", err)
		}
	}
	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, &body)
	if err != nil {
		return fmt.Errorf("agentic memory build request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if c.privateKey != "" {
		req.Header.Set("X-Agentic-Private-Key", c.privateKey)
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("agentic memory request: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return agenticError(resp)
	}
	if out == nil {
		return nil
	}
	if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
		return fmt.Errorf("agentic memory decode response: %w", err)
	}
	return nil
}

// agenticError turns a non-2xx agentic response into a typed apperrors.Error
// so response.FromError maps it to the RIGHT HTTP status for the caller.
// Previously every non-2xx response (400 validation failures included --
// e.g. the memory-edit content-safety gate, or "must be one of {allowed}"
// enum checks) collapsed into a bare fmt.Errorf that response.FromError
// couldn't classify, so it fell through to a generic 500 -- the frontend
// could never tell "your edit was rejected, try different content" apart
// from "the server crashed."
func agenticError(resp *http.Response) error {
	var body struct {
		Detail string `json:"detail"`
	}
	raw, readErr := io.ReadAll(resp.Body)
	if readErr == nil {
		_ = json.Unmarshal(raw, &body)
	}
	message := strings.TrimSpace(body.Detail)
	if message == "" {
		message = fmt.Sprintf("agentic memory request failed with status %d", resp.StatusCode)
	}
	switch resp.StatusCode {
	case http.StatusBadRequest, http.StatusUnprocessableEntity:
		return apperrors.Invalid(message)
	case http.StatusNotFound:
		return apperrors.NotFound(message)
	case http.StatusConflict:
		return apperrors.Conflict(message)
	default:
		return fmt.Errorf("agentic memory request: status %d: %s", resp.StatusCode, message)
	}
}

func mapList(in ListMemoryNodesResponse) usecase.MemoryNodeListDTO {
	nodes := make([]usecase.MemoryNodeDTO, 0, len(in.Nodes))
	for _, node := range in.Nodes {
		nodes = append(nodes, mapNode(node))
	}
	return usecase.MemoryNodeListDTO{Nodes: nodes, NodeType: in.NodeType, Total: in.Total}
}

func mapNode(in MemoryNode) usecase.MemoryNodeDTO {
	return usecase.MemoryNodeDTO{
		ID:              in.ID,
		Type:            in.Type,
		Label:           in.Label,
		Title:           in.Title,
		Preview:         in.Preview,
		Properties:      in.Properties,
		EditableFields:  in.EditableFields,
		EnumFields:      in.EnumFields,
		EmbeddingSynced: in.EmbeddingSynced,
		UpdatedAt:       in.UpdatedAt,
	}
}

func mapRelations(in ListMemoryRelationsResponse) usecase.MemoryGraphRelationListDTO {
	relations := make([]usecase.MemoryGraphRelationDTO, 0, len(in.Relations))
	for _, relation := range in.Relations {
		relations = append(relations, usecase.MemoryGraphRelationDTO{
			ID:           relation.ID,
			SourceID:     relation.SourceID,
			SourceType:   relation.SourceType,
			SourceTitle:  relation.SourceTitle,
			TargetID:     relation.TargetID,
			TargetType:   relation.TargetType,
			TargetTitle:  relation.TargetTitle,
			RelationType: relation.RelationType,
			Label:        relation.Label,
			Confidence:   relation.Confidence,
		})
	}
	return usecase.MemoryGraphRelationListDTO{Relations: relations, Total: in.Total}
}
