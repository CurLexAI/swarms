package audit

import (
	"database/sql"
	"encoding/json"
	"log"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
)

// Ledger persists immutable audit events to PostgreSQL.
type Ledger struct {
	db *sql.DB
}

// NewLedger opens the database and runs schema migration.
func NewLedger(dsn string) (*Ledger, error) {
	db, err := sql.Open("pgx", dsn)
	if err != nil {
		return nil, err
	}
	if err := db.Ping(); err != nil {
		log.Printf("warn: audit DB unreachable (%v) — using no-op ledger", err)
		return &Ledger{db: nil}, nil
	}

	if err := migrate(db); err != nil {
		return nil, err
	}

	return &Ledger{db: db}, nil
}

// Record writes a single audit event. Errors are logged but never propagated
// so that a ledger write failure never blocks the critical path.
func (l *Ledger) Record(eventType, actor string, payload any) {
	if l.db == nil {
		return
	}

	data, err := json.Marshal(payload)
	if err != nil {
		log.Printf("audit marshal: %v", err)
		return
	}

	_, err = l.db.Exec(
		`INSERT INTO audit_events (event_type, actor, payload, created_at)
		 VALUES ($1, $2, $3, $4)`,
		eventType, actor, string(data), time.Now().UTC(),
	)
	if err != nil {
		log.Printf("audit write: %v", err)
	}
}

// Close releases the database connection pool.
func (l *Ledger) Close() {
	if l.db != nil {
		_ = l.db.Close()
	}
}

func migrate(db *sql.DB) error {
	_, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS audit_events (
			id          BIGSERIAL PRIMARY KEY,
			event_type  TEXT        NOT NULL,
			actor       TEXT        NOT NULL,
			payload     JSONB       NOT NULL DEFAULT '{}',
			created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
		);
		CREATE INDEX IF NOT EXISTS idx_audit_actor      ON audit_events (actor);
		CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events (event_type);
		CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_events (created_at);
	`)
	return err
}
