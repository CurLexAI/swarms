package esim

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"mihwar.qarar.sa/core/internal/audit"
)

// Orchestrator manages eSIM profile lifecycle via SM-DP+ integration.
type Orchestrator struct {
	ledger *audit.Ledger
}

// NewOrchestrator returns an eSIM Orchestrator bound to the given ledger.
func NewOrchestrator(ledger *audit.Ledger) *Orchestrator {
	return &Orchestrator{ledger: ledger}
}

// OrderProfile initiates a new eSIM profile order with the SM-DP+ server.
func (o *Orchestrator) OrderProfile(c *gin.Context) {
	var req struct {
		DeviceID string `json:"device_id" binding:"required"`
		Iccid    string `json:"iccid"`
		Plan     string `json:"plan"     binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "missing fields"})
		return
	}

	o.ledger.Record("esim_order", req.DeviceID, map[string]any{
		"plan": req.Plan, "iccid": req.Iccid,
	})

	// Real: call SM-DP+ API (GSMA SGP.02 / RSP) to allocate profile.
	c.JSON(http.StatusAccepted, gin.H{
		"status":    "ordered",
		"device_id": req.DeviceID,
		"note":      "SM-DP+ integration pending carrier agreement",
	})
}

// ActivateProfile enables a previously ordered eSIM profile on the device.
func (o *Orchestrator) ActivateProfile(c *gin.Context) {
	var req struct {
		DeviceID  string `json:"device_id"  binding:"required"`
		ProfileID string `json:"profile_id" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "missing fields"})
		return
	}

	o.ledger.Record("esim_activate", req.DeviceID, map[string]any{
		"profile_id": req.ProfileID,
	})

	c.JSON(http.StatusOK, gin.H{"status": "activated", "profile_id": req.ProfileID})
}

// RevokeProfile disables an eSIM profile (lost/stolen device, policy violation).
func (o *Orchestrator) RevokeProfile(c *gin.Context) {
	var req struct {
		DeviceID  string `json:"device_id"  binding:"required"`
		ProfileID string `json:"profile_id" binding:"required"`
		Reason    string `json:"reason"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "missing fields"})
		return
	}

	o.ledger.Record("esim_revoke", req.DeviceID, map[string]any{
		"profile_id": req.ProfileID,
		"reason":     req.Reason,
	})

	c.JSON(http.StatusOK, gin.H{"status": "revoked", "profile_id": req.ProfileID})
}
