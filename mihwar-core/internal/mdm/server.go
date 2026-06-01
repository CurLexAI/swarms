package mdm

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"mihwar.qarar.sa/core/internal/audit"
)

// Server handles Apple MDM protocol endpoints (Check-in, Connect, SCEP).
type Server struct {
	ledger *audit.Ledger
}

// NewServer returns an MDM Server bound to the given audit ledger.
func NewServer(ledger *audit.Ledger) *Server {
	return &Server{ledger: ledger}
}

// CheckIn handles MDM Check-in messages (TokenUpdate, Authenticate, CheckOut).
func (s *Server) CheckIn(c *gin.Context) {
	// Real: parse plist body, validate device cert, update enrollment record.
	s.ledger.Record("mdm_checkin", c.ClientIP(), map[string]any{
		"user_agent": c.Request.UserAgent(),
	})
	c.Status(http.StatusOK)
}

// Connect handles MDM Connect (command + response) messages.
func (s *Server) Connect(c *gin.Context) {
	// Real: dispatch MDM commands (InstallProfile, LockDevice, EraseDevice, etc.)
	s.ledger.Record("mdm_connect", c.ClientIP(), map[string]any{})
	c.Status(http.StatusOK)
}

// SCEP serves the SCEP CA certificate for device identity provisioning.
func (s *Server) SCEP(c *gin.Context) {
	// Real: return DER-encoded CA cert for Apple's SCEP enrollment flow.
	c.JSON(http.StatusNotImplemented, gin.H{
		"status": "scep_pending",
		"note":   "SCEP CA provisioning requires HSM integration",
	})
}
