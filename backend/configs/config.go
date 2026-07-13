package configs

import (
	"bufio"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/EkaaPrawiraa/companionshipchatbot/shared/pkg/database"
)

var loadEnvOnce sync.Once

// buat nyimpan config
type Config struct {
	HTTPPortMain   string
	HTTPPortAuth   string
	HTTPPortChat   string
	HTTPPortMemory string

	Postgres database.PostgresConfig
	Neo4j    database.Neo4jConfig
	Redis    database.RedisConfig

	AgenticBaseURL     string
	AgenticPrivateKey  string
	ElevenLabsAPIKey   string
	ChatServiceURL     string
	MemoryServiceURL   string
	AuthServiceURL     string
	CORSAllowedOrigins []string
	JWTSecret          string
	PublicAgenticProxy bool
}

// load config from env with local-dev defaults
func Load() Config {
	loadEnvOnce.Do(loadDotEnv)
	return Config{
		HTTPPortMain:   envAny([]string{"HTTP_PORT_MAIN", "HTTP_PORT_GATEWAY", "HTTP_PORT"}, "3001"),
		HTTPPortAuth:   envAny([]string{"HTTP_PORT_AUTH", "AUTH_HTTP_PORT"}, "8083"),
		HTTPPortChat:   envAny([]string{"HTTP_PORT_CHAT", "CHAT_HTTP_PORT"}, "8081"),
		HTTPPortMemory: envAny([]string{"HTTP_PORT_MEMORY", "MEMORY_HTTP_PORT"}, "8082"),
		Postgres: database.PostgresConfig{
			DSN:             env("POSTGRES_DSN", "postgres://postgres:postgres@localhost:5432/companionship?sslmode=disable"),
			MaxOpenConns:    envInt("POSTGRES_MAX_OPEN_CONNS", 20),
			MaxIdleConns:    envInt("POSTGRES_MAX_IDLE_CONNS", 5),
			ConnMaxLifetime: envDuration("POSTGRES_CONN_MAX_LIFETIME", 30*time.Minute),
		},
		Neo4j: database.Neo4jConfig{
			URI:                          env("NEO4J_URI", "bolt://localhost:7687"),
			Username:                     env("NEO4J_USERNAME", "neo4j"),
			Password:                     env("NEO4J_PASSWORD", "devpassword"),
			MaxConnectionPoolSize:        envInt("NEO4J_MAX_POOL_SIZE", 50),
			ConnectionAcquisitionTimeout: envDuration("NEO4J_ACQUIRE_TIMEOUT", 60*time.Second),
			MaxTransactionRetryTime:      envDuration("NEO4J_TX_RETRY_TIME", 30*time.Second),
		},
		Redis: database.RedisConfig{
			Addr:     env("REDIS_ADDR", "localhost:6379"),
			Password: env("REDIS_PASSWORD", ""),
			DB:       envInt("REDIS_DB", 0),
		},
		AgenticBaseURL:    env("AGENTIC_BASE_URL", "http://localhost:8000"),
		AgenticPrivateKey: env("AGENTIC_GATEWAY_PRIVATE_KEY", ""),
		ElevenLabsAPIKey:  env("ELEVENLABS_API_KEY", ""),
		ChatServiceURL:    env("CHAT_SERVICE_URL", "http://localhost:8081"),
		MemoryServiceURL:  env("MEMORY_SERVICE_URL", "http://localhost:8082"),
		AuthServiceURL:    env("AUTH_SERVICE_URL", "http://localhost:8083"),
		CORSAllowedOrigins: envCSV("CORS_ALLOWED_ORIGINS", []string{
			"http://localhost:3000",
			"http://127.0.0.1:3000",
		}),
		JWTSecret:          envAny([]string{"JWT_SECRET", "AUTH_JWT_SECRET", "AGENTIC_GATEWAY_PRIVATE_KEY"}, "dev-secret"),
		PublicAgenticProxy: envBool("PUBLIC_AGENTIC_PROXY_ENABLED", false),
	}
}

func loadDotEnv() {
	// loads first, vals take prec.
	loadDotEnvFile(".env.local")
	loadDotEnvFile("backend/.env.local")
	for _, path := range []string{".env", "backend/.env"} {
		if loadDotEnvFile(path) {
			return
		}
	}
}

func loadDotEnvFile(path string) bool {
	file, err := os.Open(path)
	if err != nil {
		return false
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		key, value, ok := strings.Cut(line, "=")
		if !ok {
			continue
		}
		key = strings.TrimSpace(key)
		if key == "" || os.Getenv(key) != "" {
			continue
		}
		value = strings.TrimSpace(value)
		value = strings.Trim(value, `"'`)
		_ = os.Setenv(key, value)
	}
	return true
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envAny(keys []string, fallback string) string {
	for _, key := range keys {
		if v := os.Getenv(key); v != "" {
			return v
		}
	}
	return fallback
}

func envInt(key string, fallback int) int {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return fallback
	}
	return n
}

func envBool(key string, fallback bool) bool {
	value := strings.ToLower(strings.TrimSpace(os.Getenv(key)))
	if value == "" {
		return fallback
	}
	return value == "1" || value == "true" || value == "yes" || value == "on"
}

func envCSV(key string, fallback []string) []string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	parts := strings.Split(value, ",")
	out := make([]string, 0, len(parts))
	for _, part := range parts {
		if part = strings.TrimSpace(part); part != "" {
			out = append(out, part)
		}
	}
	if len(out) == 0 {
		return fallback
	}
	return out
}

func envDuration(key string, fallback time.Duration) time.Duration {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	d, err := time.ParseDuration(v)
	if err != nil {
		return fallback
	}
	return d
}
