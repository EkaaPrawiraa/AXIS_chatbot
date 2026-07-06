package agentic

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/services/chat/internal/usecase"
)

type Client struct {
	baseURL      string
	privateKey   string
	httpClient   *http.Client
	streamClient *http.Client
}

func New(baseURL, privateKey string) *Client {
	return &Client{
		baseURL:    strings.TrimRight(baseURL, "/"),
		privateKey: privateKey,
		httpClient: &http.Client{Timeout: 60 * time.Second},
		// http.Client.Timeout bounds the ENTIRE round trip, including
		// reading the response body -- for a streaming SSE response that
		// means the whole turn (retrieval + guardrails + CBT/PHQ judges +
		// token-by-token LLM generation), not just connecting. A turn that
		// legitimately runs past 60s (slower model, heavier turn) got its
		// connection killed mid-stream, surfacing as "agentic read stream:
		// unexpected EOF" downstream. Neither the Go server (plain
		// ListenAndServe, no ReadTimeout/WriteTimeout) nor Caddy in front
		// of it enforce a shorter bound, so the request's real lifecycle is
		// governed by the browser staying connected (propagated via ctx).
		// Keep a generous bound here only as a safety net against a truly
		// hung connection, not as a turn-latency budget.
		streamClient: &http.Client{Timeout: 5 * time.Minute},
	}
}

func (c *Client) Invoke(ctx context.Context, req usecase.AgenticChatRequest) (usecase.AgenticChatResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return usecase.AgenticChatResponse{}, fmt.Errorf("agentic marshal request: %w", err)
	}
	httpReq, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.baseURL+"/chat/invoke",
		bytes.NewReader(body),
	)
	if err != nil {
		return usecase.AgenticChatResponse{}, fmt.Errorf("agentic build request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	if c.privateKey != "" {
		httpReq.Header.Set("X-Agentic-Private-Key", c.privateKey)
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return usecase.AgenticChatResponse{}, fmt.Errorf("agentic invoke: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return usecase.AgenticChatResponse{}, fmt.Errorf("agentic invoke: status %d", resp.StatusCode)
	}
	var out usecase.AgenticChatResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return usecase.AgenticChatResponse{}, fmt.Errorf("agentic decode response: %w", err)
	}
	return out, nil
}

func (c *Client) Stream(
	ctx context.Context,
	req usecase.AgenticChatRequest,
	onEvent func(usecase.AgenticStreamEvent) error,
) (usecase.AgenticChatResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return usecase.AgenticChatResponse{}, fmt.Errorf("agentic marshal stream request: %w", err)
	}
	httpReq, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.baseURL+"/chat/stream",
		bytes.NewReader(body),
	)
	if err != nil {
		return usecase.AgenticChatResponse{}, fmt.Errorf("agentic build stream request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Accept", "text/event-stream")
	if c.privateKey != "" {
		httpReq.Header.Set("X-Agentic-Private-Key", c.privateKey)
	}

	resp, err := c.streamClient.Do(httpReq)
	if err != nil {
		return usecase.AgenticChatResponse{}, fmt.Errorf("agentic stream: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return usecase.AgenticChatResponse{}, fmt.Errorf("agentic stream: status %d", resp.StatusCode)
	}
	return readAgenticStream(resp.Body, onEvent)
}

func readAgenticStream(body io.Reader, onEvent func(usecase.AgenticStreamEvent) error) (usecase.AgenticChatResponse, error) {
	scanner := bufio.NewScanner(body)
	scanner.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	eventName := "message"
	var dataLines []string

	flush := func() (usecase.AgenticChatResponse, bool, error) {
		if len(dataLines) == 0 {
			eventName = "message"
			return usecase.AgenticChatResponse{}, false, nil
		}
		data := strings.Join(dataLines, "\n")
		ev := usecase.AgenticStreamEvent{Event: eventName, Data: data}
		eventName = "message"
		dataLines = nil

		switch ev.Event {
		case "token":
			if onEvent != nil {
				if err := onEvent(ev); err != nil {
					return usecase.AgenticChatResponse{}, false, err
				}
			}
		case "done":
			var out usecase.AgenticChatResponse
			if err := json.Unmarshal([]byte(ev.Data), &out); err != nil {
				return usecase.AgenticChatResponse{}, false, fmt.Errorf("agentic decode stream done: %w", err)
			}
			return out, true, nil
		case "error":
			return usecase.AgenticChatResponse{}, false, fmt.Errorf("agentic stream error: %s", ev.Data)
		default:
			if onEvent != nil {
				if err := onEvent(ev); err != nil {
					return usecase.AgenticChatResponse{}, false, err
				}
			}
		}
		return usecase.AgenticChatResponse{}, false, nil
	}

	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			if out, done, err := flush(); done || err != nil {
				return out, err
			}
			continue
		}
		if strings.HasPrefix(line, ":") {
			continue
		}
		if strings.HasPrefix(line, "event:") {
			eventName = strings.TrimSpace(strings.TrimPrefix(line, "event:"))
			continue
		}
		if strings.HasPrefix(line, "data:") {
			data := strings.TrimPrefix(line, "data:")
			if strings.HasPrefix(data, " ") {
				data = strings.TrimPrefix(data, " ")
			}
			dataLines = append(dataLines, data)
		}
	}
	if err := scanner.Err(); err != nil {
		return usecase.AgenticChatResponse{}, fmt.Errorf("agentic read stream: %w", err)
	}
	if out, done, err := flush(); done || err != nil {
		return out, err
	}
	return usecase.AgenticChatResponse{}, fmt.Errorf("agentic stream ended without done event")
}

func (c *Client) SynthesizeSpeech(ctx context.Context, req usecase.SynthesizeSpeechRequest) (usecase.SynthesizeSpeechResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return usecase.SynthesizeSpeechResponse{}, fmt.Errorf("agentic marshal synthesize request: %w", err)
	}
	httpReq, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.baseURL+"/voice/synthesize",
		bytes.NewReader(body),
	)
	if err != nil {
		return usecase.SynthesizeSpeechResponse{}, fmt.Errorf("agentic build synthesize request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	if c.privateKey != "" {
		httpReq.Header.Set("X-Agentic-Private-Key", c.privateKey)
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return usecase.SynthesizeSpeechResponse{}, fmt.Errorf("agentic synthesize: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return usecase.SynthesizeSpeechResponse{}, fmt.Errorf("agentic synthesize: status %d", resp.StatusCode)
	}
	var out usecase.SynthesizeSpeechResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return usecase.SynthesizeSpeechResponse{}, fmt.Errorf("agentic decode synthesize response: %w", err)
	}
	return out, nil
}

func (c *Client) TranscribeSpeech(ctx context.Context, req usecase.TranscribeSpeechRequest) (usecase.TranscribeSpeechResponse, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return usecase.TranscribeSpeechResponse{}, fmt.Errorf("agentic marshal transcribe request: %w", err)
	}
	httpReq, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.baseURL+"/voice/transcribe",
		bytes.NewReader(body),
	)
	if err != nil {
		return usecase.TranscribeSpeechResponse{}, fmt.Errorf("agentic build transcribe request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	if c.privateKey != "" {
		httpReq.Header.Set("X-Agentic-Private-Key", c.privateKey)
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return usecase.TranscribeSpeechResponse{}, fmt.Errorf("agentic transcribe: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return usecase.TranscribeSpeechResponse{}, fmt.Errorf("agentic transcribe: status %d", resp.StatusCode)
	}
	var out usecase.TranscribeSpeechResponse
	if err := json.NewDecoder(resp.Body).Decode(&out); err != nil {
		return usecase.TranscribeSpeechResponse{}, fmt.Errorf("agentic decode transcribe response: %w", err)
	}
	return out, nil
}

func (c *Client) PurgeSessionMemory(ctx context.Context, sessionID string, messageIDs []string) error {
	if messageIDs == nil {
		messageIDs = []string{}
	}
	body, err := json.Marshal(struct {
		MessageIDs []string `json:"message_ids"`
	}{MessageIDs: messageIDs})
	if err != nil {
		return fmt.Errorf("agentic marshal purge session memory: %w", err)
	}
	httpReq, err := http.NewRequestWithContext(
		ctx,
		http.MethodDelete,
		c.baseURL+"/memory-nodes/sessions/"+url.PathEscape(sessionID)+"/purge",
		bytes.NewReader(body),
	)
	if err != nil {
		return fmt.Errorf("agentic build purge session memory: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	if c.privateKey != "" {
		httpReq.Header.Set("X-Agentic-Private-Key", c.privateKey)
	}

	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		return fmt.Errorf("agentic purge session memory: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("agentic purge session memory: status %d", resp.StatusCode)
	}
	return nil
}
