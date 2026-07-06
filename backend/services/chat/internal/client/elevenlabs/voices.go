package elevenlabs

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/usecase"
)

type Client struct {
	apiKey     string
	httpClient *http.Client
}

func New(apiKey string) *Client {
	return &Client{
		apiKey:     apiKey,
		httpClient: &http.Client{Timeout: 15 * time.Second},
	}
}

func (c *Client) ListVoices(ctx context.Context) ([]usecase.VoiceOptionDTO, error) {
	if c.apiKey == "" {
		return []usecase.VoiceOptionDTO{}, nil
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, "https://api.elevenlabs.io/v1/voices", nil)
	if err != nil {
		return nil, fmt.Errorf("elevenlabs build voices request: %w", err)
	}
	req.Header.Set("xi-api-key", c.apiKey)
	req.Header.Set("Accept", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("elevenlabs voices: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("elevenlabs voices: status %d", resp.StatusCode)
	}

	var payload struct {
		Voices []struct {
			VoiceID     string `json:"voice_id"`
			Name        string `json:"name"`
			Category    string `json:"category"`
			Description string `json:"description"`
			PreviewURL  string `json:"preview_url"`
		} `json:"voices"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return nil, fmt.Errorf("elevenlabs decode voices: %w", err)
	}
	out := make([]usecase.VoiceOptionDTO, 0, len(payload.Voices))
	for _, voice := range payload.Voices {
		if voice.VoiceID == "" {
			continue
		}
		name := voice.Name
		if name == "" {
			name = voice.VoiceID
		}
		out = append(out, usecase.VoiceOptionDTO{
			ID:          voice.VoiceID,
			Name:        name,
			Provider:    "elevenlabs",
			ProviderID:  voice.VoiceID,
			Category:    voice.Category,
			PreviewURL:  voice.PreviewURL,
			Description: voice.Description,
		})
	}
	return out, nil
}
