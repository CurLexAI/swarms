package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"mihwar.qarar.sa/core/internal/api"
	"mihwar.qarar.sa/core/internal/audit"
	"mihwar.qarar.sa/core/internal/esim"
	"mihwar.qarar.sa/core/internal/mdm"
	"mihwar.qarar.sa/core/internal/policy"
)

func main() {
	dbURL := env("DATABASE_URL", "postgresql://mihwar:sovereign@localhost/mihwar?sslmode=disable")

	ledger, err := audit.NewLedger(dbURL)
	if err != nil {
		log.Fatalf("audit ledger: %v", err)
	}
	defer ledger.Close()

	engine, err := policy.NewEngine("./policies/", ledger)
	if err != nil {
		log.Fatalf("policy engine: %v", err)
	}

	mdmServer := mdm.NewServer(ledger)
	esimOrch  := esim.NewOrchestrator(ledger)

	srv := api.NewServer(engine, mdmServer, esimOrch, ledger)

	quicAddr := env("QUIC_ADDR", ":443")
	httpAddr := env("HTTP_ADDR", ":8080")

	errCh := make(chan error, 2)
	go func() { errCh <- srv.StartQUIC(quicAddr) }()
	go func() { errCh <- srv.StartHTTP(httpAddr) }()

	log.Printf("Mihwar Core — sovereign control plane active (HTTP %s  QUIC %s)", httpAddr, quicAddr)

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)

	select {
	case <-sig:
		log.Println("shutting down")
	case err := <-errCh:
		log.Fatalf("server error: %v", err)
	}
}

func env(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
