package database

import (
	"github.com/redis/go-redis/v9"
)

// init redis
type RedisConfig struct {
	Addr     string
	Password string
	DB       int
}

// redis client lazy
func NewRedisClient(cfg RedisConfig) *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr:     cfg.Addr,
		Password: cfg.Password,
		DB:       cfg.DB,
	})
}
