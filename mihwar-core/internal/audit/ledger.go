package audit

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"log"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
)

const genesisHash = "GENESIS"

// Ledger persists immutable, append-only, hash-chained audit events to PostgreSQL.
type Ledger struct {
	db *sql.DB
}

type LedgerEntry struct {
	ID          int64           `json:"id"`
	EventType   string          `json:"event_type"`
	Actor       string          `json:"actor"`
	Payload     json.RawMessage `json:"payload"`
	PrevHash    string          `json:"prev_hash"`
	CurrentHash string          `json:"current_hash"`
	CreatedAt   time.Time       `json:"created_at"`
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

// Record writes a single hash-chained audit event. Errors are logged but never
// propagated so that a ledger write failure never blocks the critical path.
func (l *Ledger) Record(eventType, actor string, payload any) {
	if _, err := l.Append(context.Background(), eventType, actor, payload); err != nil {
		log.Printf("audit write: %v", err)
	}
}

// Append writes one append-only ledger entry and links it to the previous hash.
func (l *Ledger) Append(ctx context.Context, eventType, actor string, payload any) (*LedgerEntry, error) {
	if l.db == nil {
		return nil, nil
	}
	if eventType == "" {
		return nil, errors.New("eventType is required")
	}
	if actor == "" {
		return nil, errors.New("actor is required")
	}

	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

	tx, err := l.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()

	prevHash := genesisHash
	err = tx.QueryRowContext(ctx, `
		SELECT current_hash
		FROM audit_ledger
		ORDER BY id DESC
		LIMIT 1
		FOR UPDATE
	`).Scan(&prevHash)
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return nil, err
	}

	createdAt := time.Now().UTC()
	currentHash := computeEntryHash(eventType, actor, payloadBytes, prevHash, createdAt)

	var entry LedgerEntry
	err = tx.QueryRowContext(ctx, `
		INSERT INTO audit_ledger(event_type, actor, payload, prev_hash, current_hash, created_at)
		VALUES ($1, $2, $3, $4, $5, $6)
		RETURNING id, event_type, actor, payload, prev_hash, current_hash, created_at
	`, eventType, actor, payloadBytes, prevHash, currentHash, createdAt).Scan(
		&entry.ID,
		&entry.EventType,
		&entry.Actor,
		&entry.Payload,
		&entry.PrevHash,
		&entry.CurrentHash,
		&entry.CreatedAt,
	)
	if err != nil {
		return nil, err
	}

	if err := tx.Commit(); err != nil {
		return nil, err
	}
	return &entry, nil
}

// Close releases the database connection pool.
func (l *Ledger) Close() {
	if l.db != nil {
		_ = l.db.Close()
	}
}

func migrate(db *sql.DB) error {
	_, err := db.Exec(`
		CREATE TABLE IF NOT EXISTS audit_ledger (
			id           BIGSERIAL PRIMARY KEY,
			event_type   TEXT        NOT NULL,
			actor        TEXT        NOT NULL,
			payload      JSONB       NOT NULL DEFAULT '{}',
			prev_hash    TEXT        NOT NULL,
			current_hash TEXT        NOT NULL,
			created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
		);
		CREATE INDEX IF NOT EXISTS idx_audit_ledger_actor ON audit_ledger (actor);
		CREATE INDEX IF NOT EXISTS idx_audit_ledger_event_type ON audit_ledger (event_type);
		CREATE INDEX IF NOT EXISTS idx_audit_ledger_created_at ON audit_ledger (created_at);
	`)
	return err
}

func computeEntryHash(eventType, actor string, payload []byte, prevHash string, createdAt time.Time) string {
	h := sha256.New()
	h.Write([]byte(eventType))
	h.Write([]byte("|"))
	h.Write([]byte(actor))
	h.Write([]byte("|"))
	h.Write(payload)
	h.Write([]byte("|"))
	h.Write([]byte(prevHash))
	h.Write([]byte("|"))
	h.Write([]byte(createdAt.Format(time.RFC3339Nano)))
	return hex.EncodeToString(h.Sum(nil))
}
