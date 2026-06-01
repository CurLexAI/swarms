package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"mihwar.qarar.sa/core/internal/audit"
	"mihwar.qarar.sa/core/internal/esim"
	"mihwar.qarar.sa/core/internal/mdm"
	"mihwar.qarar.sa/core/internal/policy"
	"mihwar.qarar.sa/core/internal/security"
)

// Server is the Mihwar Core HTTP/QUIC gateway.
type Server struct {
	engine *policy.Engine
	mdm    *mdm.Server
	esim   *esim.Orchestrator
	ledger *audit.Ledger
	router *gin.Engine
}

// NewServer wires up all routes and returns an idle Server.
func NewServer(
	engine *policy.Engine,
	mdm *mdm.Server,
	esim *esim.Orchestrator,
	ledger *audit.Ledger,
) *Server {
	gin.SetMode(gin.ReleaseMode)

	s := &Server{engine: engine, mdm: mdm, esim: esim, ledger: ledger}
	s.router = s.buildRouter()
	return s
}

func (s *Server) buildRouter() *gin.Engine {
	r := gin.New()
	r.Use(gin.Recovery())
	r.Use(s.auditMiddleware())

	// Health remains outside the signed control plane for load-balancer probes.
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "sovereign", "region": "SA"})
	})

	api := r.Group("/api/v1")
	api.Use(security.HMACMiddleware())
	api.POST("/policy/evaluate", s.evaluatePolicy)
	api.POST("/devices/enroll", s.enrollDevice)
	api.POST("/esim/order", s.esim.OrderProfile)
	api.POST("/esim/activate", s.esim.ActivateProfile)
	api.POST("/esim/revoke", s.esim.RevokeProfile)
	api.POST("/telemetry", s.ingestTelemetry)

	mdmGroup := r.Group("/mdm")
	mdmGroup.Use(security.HMACMiddleware())
	mdmGroup.POST("/checkin", s.mdm.CheckIn)
	mdmGroup.PUT("/connect", s.mdm.Connect)
	mdmGroup.GET("/scep", s.mdm.SCEP)

	return r
}

// StartHTTP starts the HTTP/2 listener.
func (s *Server) StartHTTP(addr string) error {
	return s.router.Run(addr)
}

// StartQUIC starts the HTTP/3 (QUIC) listener.
// Requires a TLS cert/key pair at TLS_CERT / TLS_KEY env vars.
func (s *Server) StartQUIC(addr string) error {
	// quic-go ListenAddrEarly wired in production.
	// Stub blocks until process exit so the goroutine in main doesn't
	// push nil onto errCh and terminate the server prematurely.
	select {}
}

// ── handlers ────────────────────────────────────────────────────────────────

func (s *Server) evaluatePolicy(c *gin.Context) {
	var req struct {
		Posture  map[string]any `json:"posture"`
		Cellular map[string]any `json:"cellular"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request"})
		return
	}

	deviceID, _ := req.Posture["device_id"].(string)
	decision := s.engine.Evaluate(req.Posture, req.Cellular)
	s.ledger.Record("policy_evaluated", deviceID, decision)

	c.JSON(http.StatusOK, decision)
}

func (s *Server) enrollDevice(c *gin.Context) {
	var req struct {
		DeviceID string `json:"device_id" binding:"required"`
		Platform string `json:"platform"  binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "missing fields"})
		return
	}
	s.ledger.Record("device_enrolled", req.DeviceID, map[string]any{"platform": req.Platform})
	c.JSON(http.StatusOK, gin.H{"enrolled": true, "device_id": req.DeviceID})
}

func (s *Server) ingestTelemetry(c *gin.Context) {
	var payload map[string]any
	if err := c.ShouldBindJSON(&payload); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid telemetry"})
		return
	}
	deviceID, _ := payload["device_id"].(string)
	s.ledger.Record("telemetry_received", deviceID, payload)
	c.JSON(http.StatusAccepted, gin.H{"accepted": true})
}

// ── middleware ───────────────────────────────────────────────────────────────

func (s *Server) auditMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		s.ledger.Record("http_request", c.ClientIP(), map[string]any{
			"method": c.Request.Method,
			"path":   c.Request.URL.Path,
		})
		c.Next()
	}
}

func (s *Server) authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Production: mTLS — device cert signed by sovereign CA.
		// Verify c.Request.TLS.PeerCertificates[0] against pinned CA.
		c.Next()
	}
}
