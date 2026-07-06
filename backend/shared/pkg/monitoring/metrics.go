package monitoring

import (
	"expvar"
	"fmt"
	"net/http"
	"sync"
	"time"
)

var (
	httpRequests = expvar.NewMap("axis_http_requests_total")
	httpErrors   = expvar.NewMap("axis_http_errors_total")
	httpLatency  = expvar.NewMap("axis_http_latency_ms_total")
	mu           sync.Mutex
)

func ObserveHTTPRequest(method string, path string, status int, duration time.Duration) {
	key := fmt.Sprintf("%s %s %d", method, path, status)
	mu.Lock()
	defer mu.Unlock()
	httpRequests.Add(key, 1)
	httpLatency.Add(key, duration.Milliseconds())
	if status >= http.StatusBadRequest {
		httpErrors.Add(key, 1)
	}
}

func Handler() http.Handler {
	return expvar.Handler()
}
