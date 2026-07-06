package database

import (
	"github.com/redis/go-redis/v9"
)

// RedisConfig holds connection parameters for a Redis instance.
type RedisConfig struct {
	Addr     string
	Password string
	DB       int
}

// NewRedisClient constructs a lazy go-redis client.
func NewRedisClient(cfg RedisConfig) *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr:     cfg.Addr,
		Password: cfg.Password,
		DB:       cfg.DB,
	})
}
