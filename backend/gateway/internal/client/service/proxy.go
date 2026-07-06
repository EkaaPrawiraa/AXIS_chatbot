package service

import (
	"bytes"
	"io"
	"net/http"
	"strings"
	"time"
)

type Proxy struct {
	baseURL     string
	stripPrefix string
	httpClient  *http.Client
}

func NewProxy(baseURL string, stripPrefix string) *Proxy {
	return &Proxy{
		baseURL:     strings.TrimRight(baseURL, "/"),
		stripPrefix: stripPrefix,
		httpClient:  &http.Client{Timeout: 60 * time.Second},
	}
}

func (p *Proxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		http.Error(w, "read request body", http.StatusBadRequest)
		return
	}
	path := r.URL.Path
	if p.stripPrefix != "" {
		path = strings.TrimPrefix(path, p.stripPrefix)
	}
	if path == "" {
		path = "/"
	}
	target := p.baseURL + path
	if r.URL.RawQuery != "" {
		target += "?" + r.URL.RawQuery
	}
	req, err := http.NewRequestWithContext(r.Context(), r.Method, target, bytes.NewReader(body))
	if err != nil {
		http.Error(w, "build upstream request", http.StatusBadGateway)
		return
	}
	req.Header = r.Header.Clone()
	resp, err := p.httpClient.Do(req)
	if err != nil {
		http.Error(w, "service upstream unavailable", http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()
	for key, values := range resp.Header {
		for _, value := range values {
			w.Header().Add(key, value)
		}
	}
	w.WriteHeader(resp.StatusCode)
	if strings.Contains(resp.Header.Get("Content-Type"), "text/event-stream") {
		flusher, _ := w.(http.Flusher)
		buf := make([]byte, 32*1024)
		for {
			n, readErr := resp.Body.Read(buf)
			if n > 0 {
				if _, writeErr := w.Write(buf[:n]); writeErr != nil {
					return
				}
				if flusher != nil {
					flusher.Flush()
				}
			}
			if readErr != nil {
				return
			}
		}
	}
	_, _ = io.Copy(w, resp.Body)
}
