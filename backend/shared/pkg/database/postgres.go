package database

import (
	"database/sql"
	"fmt"
	"time"
)

// PostgresConfig holds connection and pool settings for PostgreSQL.
type PostgresConfig struct {
	DSN             string
	MaxOpenConns    int
	MaxIdleConns    int
	ConnMaxLifetime time.Duration
}

// OpenPostgres configures a database/sql pool. The caller must import the
// concrete driver in its main package when enabling a real database connection.
func OpenPostgres(cfg PostgresConfig) (*sql.DB, error) {
	db, err := sql.Open("postgres", cfg.DSN)
	if err != nil {
		return nil, fmt.Errorf("postgres open: %w", err)
	}
	db.SetMaxOpenConns(cfg.MaxOpenConns)
	db.SetMaxIdleConns(cfg.MaxIdleConns)
	db.SetConnMaxLifetime(cfg.ConnMaxLifetime)
	return db, nil
}
