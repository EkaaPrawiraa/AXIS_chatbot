// Package memory calls the memory service's own KG-purge endpoint so
// account deletion enforces "delete everything" server-side, rather than
// depending on the frontend correctly sequencing two separate API calls.
package memory

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
}

func New(baseURL string) *Client {
	return &Client{
		baseURL:    strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
}

// PurgeAccount deletes every KG/pgvector node belonging to userID. The
// memory service resolves userID from the query param when there's no
// authenticated request context to extract it from (service-to-service
// call, not a user-facing proxied request).
func (c *Client) PurgeAccount(ctx context.Context, userID string) error {
	target := c.baseURL + "/memories/kg/purge-account?userId=" + url.QueryEscape(userID)
	req, err := http.NewRequestWithContext(ctx, http.MethodDelete, target, nil)
	if err != nil {
		return fmt.Errorf("memory purge-account build request: %w", err)
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("memory purge-account: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("memory purge-account: status %d", resp.StatusCode)
	}
	return nil
}
