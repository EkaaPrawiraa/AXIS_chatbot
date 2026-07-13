package middleware

import (
	"context"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
)

// buat nyimpen config
type RateLimitConfig struct {
	MaxTurnsPerHour        int
	MaxMessagesPerDay      int
	MaxSessionsPerDay      int
	MaxAuthAttemptsPerHour int
}

// DefaultRateLimitConfig returns limits from input_validation.yaml. MaxMessagesPerDay is thesis-scope (not abuse prevention). LLM caps daily msgs.
func DefaultRateLimitConfig() RateLimitConfig {
	return RateLimitConfig{
		MaxTurnsPerHour:        30,
		MaxMessagesPerDay:      100,
		MaxSessionsPerDay:      10,
		MaxAuthAttemptsPerHour: 20,
	}
}

// limit redis
type RateLimiter struct {
	rdb    *redis.Client
	cfg    RateLimitConfig
	prefix string // key namespace prefix, default "rl"
}

// rate lim.
func NewRateLimiter(rdb *redis.Client, cfg RateLimitConfig) *RateLimiter {
	return &RateLimiter{
		rdb:    rdb,
		cfg:    cfg,
		prefix: "rl",
	}
}

// turn limit, fail open, redis errors
func (rl *RateLimiter) TurnLimit(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			next.ServeHTTP(w, r)
			return
		}

		key := rl.clientKey(r)
		hourWindow := time.Now().UTC().Format("2006-01-02-15")
		redisKey := fmt.Sprintf("%s:turns:%s:%s", rl.prefix, key, hourWindow)

		allowed, remaining := rl.checkLimit(r.Context(), redisKey, rl.cfg.MaxTurnsPerHour, time.Hour)
		w.Header().Set("X-RateLimit-Limit-Turns", fmt.Sprintf("%d", rl.cfg.MaxTurnsPerHour))
		w.Header().Set("X-RateLimit-Remaining-Turns", fmt.Sprintf("%d", remaining))

		if !allowed {
			slog.Warn("rate limit: turns exceeded",
				"key", key,
				"limit", rl.cfg.MaxTurnsPerHour,
				"window", hourWindow,
			)
			http.Error(w,
				`{"error":"rate_limit_exceeded","message":"Too many messages. Please wait before sending more."}`,
				http.StatusTooManyRequests,
			)
			return
		}

		dayWindow := time.Now().UTC().Format("2006-01-02")
		dailyKey := fmt.Sprintf("%s:messages_daily:%s:%s", rl.prefix, key, dayWindow)
		dailyAllowed, dailyRemaining := rl.checkLimit(r.Context(), dailyKey, rl.cfg.MaxMessagesPerDay, 24*time.Hour)
		w.Header().Set("X-RateLimit-Limit-MessagesDaily", fmt.Sprintf("%d", rl.cfg.MaxMessagesPerDay))
		w.Header().Set("X-RateLimit-Remaining-MessagesDaily", fmt.Sprintf("%d", dailyRemaining))

		if !dailyAllowed {
			slog.Warn("rate limit: daily messages exceeded",
				"key", key,
				"limit", rl.cfg.MaxMessagesPerDay,
				"window", dayWindow,
			)
			http.Error(w,
				`{"error":"daily_message_limit_reached","message":"Kamu sudah mencapai batas pesan harian untuk riset TA ini. Coba lagi besok ya."}`,
				http.StatusTooManyRequests,
			)
			return
		}

		next.ServeHTTP(w, r)
	})
}

// skip on err
func (rl *RateLimiter) SessionLimit(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			next.ServeHTTP(w, r)
			return
		}

		key := rl.clientKey(r)
		window := time.Now().UTC().Format("2006-01-02")
		redisKey := fmt.Sprintf("%s:sessions:%s:%s", rl.prefix, key, window)

		allowed, remaining := rl.checkLimit(r.Context(), redisKey, rl.cfg.MaxSessionsPerDay, 24*time.Hour)
		w.Header().Set("X-RateLimit-Limit-Sessions", fmt.Sprintf("%d", rl.cfg.MaxSessionsPerDay))
		w.Header().Set("X-RateLimit-Remaining-Sessions", fmt.Sprintf("%d", remaining))

		if !allowed {
			slog.Warn("rate limit: sessions/day exceeded",
				"key", key,
				"limit", rl.cfg.MaxSessionsPerDay,
				"window", window,
			)
			http.Error(w,
				`{"error":"rate_limit_exceeded","message":"Daily session limit reached. Please continue in an existing conversation."}`,
				http.StatusTooManyRequests,
			)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func (rl *RateLimiter) AuthLimit(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			next.ServeHTTP(w, r)
			return
		}

		key := rl.clientKey(r)
		window := time.Now().UTC().Format("2006-01-02-15")
		redisKey := fmt.Sprintf("%s:auth:%s:%s", rl.prefix, key, window)

		allowed, remaining := rl.checkLimit(r.Context(), redisKey, rl.cfg.MaxAuthAttemptsPerHour, time.Hour)
		w.Header().Set("X-RateLimit-Limit-Auth", fmt.Sprintf("%d", rl.cfg.MaxAuthAttemptsPerHour))
		w.Header().Set("X-RateLimit-Remaining-Auth", fmt.Sprintf("%d", remaining))

		if !allowed {
			slog.Warn("rate limit: auth attempts exceeded",
				"key", key,
				"limit", rl.cfg.MaxAuthAttemptsPerHour,
				"window", window,
			)
			http.Error(w,
				`{"error":"rate_limit_exceeded","message":"Too many auth attempts. Please wait before trying again."}`,
				http.StatusTooManyRequests,
			)
			return
		}

		next.ServeHTTP(w, r)
	})
}

// checkLimit, ttl, EXPIRE.
func (rl *RateLimiter) checkLimit(
	ctx context.Context,
	redisKey string,
	limit int,
	window time.Duration,
) (allowed bool, remaining int) {
	pipe := rl.rdb.Pipeline()
	incrCmd := pipe.Incr(ctx, redisKey)
	pipe.ExpireNX(ctx, redisKey, window)

	if _, err := pipe.Exec(ctx); err != nil {
		slog.Warn("rate limiter: redis pipeline failed (fail-open)", "err", err)
		return true, limit
	}

	count := int(incrCmd.Val())
	if count > limit {
		return false, 0
	}
	return true, limit - count
}

// use token or ip.
func (rl *RateLimiter) clientKey(r *http.Request) string {
	auth := r.Header.Get("Authorization")
	if strings.HasPrefix(auth, "Bearer ") {
		token := strings.TrimPrefix(auth, "Bearer ")
		if len(token) > 8 {
			// skip klo nggak pake id
			if len(token) > 32 {
				token = token[:32]
			}
			return token
		}
	}

	// `skip fallback`
	ip, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		ip = r.RemoteAddr
	}
	// prefer x-forwarded-for
	if forwarded := r.Header.Get("X-Forwarded-For"); forwarded != "" {
		parts := strings.Split(forwarded, ",")
		if len(parts) > 0 {
			ip = strings.TrimSpace(parts[0])
		}
	}
	return ip
}
