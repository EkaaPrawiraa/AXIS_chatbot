package agentic

import (
	"bytes"
	"io"
	"net/http"
	"strings"
	"time"
)

type Proxy struct {
	baseURL    string
	privateKey string
	httpClient *http.Client
}

func NewProxy(baseURL, privateKey string) *Proxy {
	return &Proxy{
		baseURL:    strings.TrimRight(baseURL, "/"),
		privateKey: privateKey,
		httpClient: &http.Client{Timeout: 60 * time.Second},
	}
}

func (p *Proxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "read request body", http.StatusBadRequest)
		return
	}
	target := p.baseURL + strings.TrimPrefix(r.URL.Path, "/agentic")
	if r.URL.RawQuery != "" {
		target += "?" + r.URL.RawQuery
	}
	req, err := http.NewRequestWithContext(r.Context(), r.Method, target, bytes.NewReader(body))
	if err != nil {
		http.Error(w, "build upstream request", http.StatusBadGateway)
		return
	}
	req.Header = r.Header.Clone()
	req.Header.Set("Content-Type", "application/json")
	if p.privateKey != "" {
		req.Header.Set("X-Agentic-Private-Key", p.privateKey)
	}
	resp, err := p.httpClient.Do(req)
	if err != nil {
		http.Error(w, "agentic upstream unavailable", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	for key, values := range resp.Header {
		for _, value := range values {
			w.Header().Add(key, value)
		}
	}
	w.WriteHeader(resp.StatusCode)
	_, _ = io.Copy(w, resp.Body)
}
