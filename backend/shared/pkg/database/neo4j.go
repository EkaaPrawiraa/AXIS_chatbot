// db conn
package database

import (
	"context"
	"fmt"
	"time"

	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

// Neo4jConfig holds conn params.
type Neo4jConfig struct {
	URI      string // e.g. bolt://localhost:7687  or  neo4j://neo4j:7687
	Username string
	Password string

	// pool settings
	MaxConnectionPoolSize        int           // default: 50
	ConnectionAcquisitionTimeout time.Duration // default: 60s
	MaxTransactionRetryTime      time.Duration // default: 30s
}

// skip defaults, override fields.
func DefaultNeo4jConfig() Neo4jConfig {
	return Neo4jConfig{
		URI:                          "bolt://localhost:7687",
		Username:                     "neo4j",
		Password:                     "devpassword",
		MaxConnectionPoolSize:        50,
		ConnectionAcquisitionTimeout: 60 * time.Second,
		MaxTransactionRetryTime:      30 * time.Second,
	}
}

// creates shared driver, verifys conn.
func NewNeo4jDriver(cfg Neo4jConfig) (neo4j.DriverWithContext, error) {
	driver, err := neo4j.NewDriverWithContext(
		cfg.URI,
		neo4j.BasicAuth(cfg.Username, cfg.Password, ""),
		func(c *neo4j.Config) {
			c.MaxConnectionPoolSize = cfg.MaxConnectionPoolSize
			c.ConnectionAcquisitionTimeout = cfg.ConnectionAcquisitionTimeout
			c.MaxTransactionRetryTime = cfg.MaxTransactionRetryTime
		},
	)
	if err != nil {
		return nil, fmt.Errorf("neo4j: failed to create driver: %w", err)
	}

	// verify conn
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := driver.VerifyConnectivity(ctx); err != nil {
		_ = driver.Close(ctx)
		return nil, fmt.Errorf("neo4j: connectivity check failed (is Neo4j running?): %w", err)
	}

	return driver, nil
}

// opens session
func NewNeo4jSession(
	ctx context.Context,
	driver neo4j.DriverWithContext,
	mode neo4j.AccessMode,
) neo4j.SessionWithContext {
	return driver.NewSession(ctx, neo4j.SessionConfig{
		AccessMode: mode,
	})
}
