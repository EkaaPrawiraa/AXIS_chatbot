package middleware

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/redis/go-redis/v9"
)

// Regression test for AGENTIC #6 / BACKEND #2: checkLimit used a plain
// EXPIRE on every call (including rejected ones), which resets the TTL
// to a fresh `window` duration on every single request instead of only
// when the counter key is first created. A user sending requests faster
// than the window -- or a client retrying after a 429 -- would keep
// pushing the TTL out, so the window never actually expired on schedule.
//
// Requires a real Redis reachable at TEST_REDIS_ADDR (defaults to
// 127.0.0.1:16399, matching the throwaway local instance used to verify
// this fix) -- skips if unreachable.

func testRedisClient(t *testing.T) *redis.Client {
	t.Helper()
	addr := os.Getenv("TEST_REDIS_ADDR")
	if addr == "" {
		addr = "127.0.0.1:16399"
	}
	rdb := redis.NewClient(&redis.Options{Addr: addr})
	if err := rdb.Ping(context.Background()).Err(); err != nil {
		t.Skipf("redis not reachable at %s: %v", addr, err)
	}
	return rdb
}

func TestCheckLimit_TTLNotResetOnSubsequentCalls(t *testing.T) {
	rdb := testRedisClient(t)
	defer rdb.Close()

	ctx := context.Background()
	key := "rl-test:ttl-not-reset:" + time.Now().Format(time.RFC3339Nano)
	defer rdb.Del(ctx, key)

	rl := &RateLimiter{rdb: rdb, prefix: "rl-test"}

	// First call creates the key and must set a TTL close to `window`.
	// PTTL (millisecond precision) instead of TTL (whole-second, rounds
	// away the ~1.2s gap this test relies on) -- with TTL's 1-second
	// granularity, "2s window minus 1.2s elapsed" and "reset to a fresh
	// 2s" are both indistinguishable from an observed value of 1s.
	allowed, _ := rl.checkLimit(ctx, key, 100, 2*time.Second)
	if !allowed {
		t.Fatalf("expected first call to be allowed")
	}
	ttl1, err := rdb.PTTL(ctx, key).Result()
	if err != nil {
		t.Fatalf("PTTL after first call: %v", err)
	}
	if ttl1 <= 0 {
		t.Fatalf("expected a positive TTL after key creation, got %v", ttl1)
	}

	// Let some of the window elapse, then call again -- the TTL must
	// keep counting down from the ORIGINAL window, not reset to a fresh
	// `window` duration on this second call.
	time.Sleep(1200 * time.Millisecond)
	allowed, _ = rl.checkLimit(ctx, key, 100, 2*time.Second)
	if !allowed {
		t.Fatalf("expected second call to be allowed")
	}
	ttl2, err := rdb.PTTL(ctx, key).Result()
	if err != nil {
		t.Fatalf("PTTL after second call: %v", err)
	}

	if ttl2 > ttl1 {
		t.Fatalf(
			"TTL was reset instead of counting down: ttl1=%v ttl2=%v "+
				"(second call happened ~1.2s after the first, so ttl2 "+
				"should be ~1.2s lower, not higher)",
			ttl1, ttl2,
		)
	}
	if ttl2 > 900*time.Millisecond {
		t.Fatalf(
			"expected TTL to have counted down close to ~0.8s remaining "+
				"(2s window minus ~1.2s elapsed), got %v -- TTL looks reset",
			ttl2,
		)
	}
}

func TestCheckLimit_StillBlocksOverLimit(t *testing.T) {
	rdb := testRedisClient(t)
	defer rdb.Close()

	ctx := context.Background()
	key := "rl-test:blocks-over-limit:" + time.Now().Format(time.RFC3339Nano)
	defer rdb.Del(ctx, key)

	rl := &RateLimiter{rdb: rdb, prefix: "rl-test"}

	for i := 0; i < 3; i++ {
		allowed, _ := rl.checkLimit(ctx, key, 3, time.Minute)
		if !allowed {
			t.Fatalf("call %d: expected allowed within limit", i+1)
		}
	}

	allowed, remaining := rl.checkLimit(ctx, key, 3, time.Minute)
	if allowed {
		t.Fatalf("expected 4th call to exceed limit of 3, got allowed=true remaining=%d", remaining)
	}
}
