package policy

import (
	"log"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
	"mihwar.qarar.sa/core/internal/audit"
)

// Engine loads YAML policies from disk and evaluates them against device posture.
type Engine struct {
	policies []policyDef
	ledger   *audit.Ledger
}

type policyDef struct {
	Name     string     `yaml:"policy"`
	Version  string     `yaml:"version"`
	Priority int        `yaml:"priority"`
	When     whenClause `yaml:"when"`
	Then     actionDef  `yaml:"then"`
	Else     actionDef  `yaml:"else"`
}

type whenClause struct {
	DeviceAttestation string `yaml:"device_attestation"`
	CountryCode       string `yaml:"country_code"`
	RiskScoreLT       int    `yaml:"risk_score_lt"`
	NetworkType       string `yaml:"network_type"`
}

type actionDef struct {
	Allow    *allowAction    `yaml:"allow,omitempty"`
	Restrict *restrictAction `yaml:"restrict,omitempty"`
}

type allowAction struct {
	Apn   string `yaml:"apn"`
	Vpn   string `yaml:"vpn"`
	DNS   string `yaml:"dns"`
	Proxy string `yaml:"proxy"`
}

type restrictAction struct {
	Network       string `yaml:"network"`
	TelemetryOnly bool   `yaml:"telemetry_only"`
	AlertSecurity bool   `yaml:"alert_security_team"`
}

// NewEngine loads all YAML policy files from policyDir.
func NewEngine(policyDir string, ledger *audit.Ledger) (*Engine, error) {
	e := &Engine{ledger: ledger}

	entries, err := os.ReadDir(policyDir)
	if os.IsNotExist(err) {
		log.Printf("policy dir %s not found — using built-in defaults", policyDir)
		return e, nil
	}
	if err != nil {
		return nil, err
	}

	for _, entry := range entries {
		if filepath.Ext(entry.Name()) != ".yaml" {
			continue
		}
		data, err := os.ReadFile(filepath.Join(policyDir, entry.Name()))
		if err != nil {
			log.Printf("warn: cannot read policy %s: %v", entry.Name(), err)
			continue
		}
		var p policyDef
		if err := yaml.Unmarshal(data, &p); err != nil {
			log.Printf("warn: cannot parse policy %s: %v", entry.Name(), err)
			continue
		}
		e.policies = append(e.policies, p)
		log.Printf("loaded policy: %s v%s (priority %d)", p.Name, p.Version, p.Priority)
	}

	return e, nil
}

// Evaluate returns a network decision map for the given posture and cellular state.
func (e *Engine) Evaluate(posture, _ map[string]any) map[string]any {
	deviceID, _ := posture["device_id"].(string)
	country, _  := posture["country_code"].(string)
	riskF, _    := posture["risk_score"].(float64)
	risk        := int(riskF)
	attest, _   := posture["attestation_valid"].(bool)

	// Fail-secure default: quarantine
	decision := map[string]any{
		"allow_connection": false,
		"quarantine_mode":  true,
		"telemetry_only":   true,
	}

	// Walk loaded policies (highest priority wins)
	for _, p := range e.policies {
		w := p.When
		match := (w.DeviceAttestation == "" || (w.DeviceAttestation == "valid") == attest) &&
			(w.CountryCode == "" || w.CountryCode == country) &&
			(w.RiskScoreLT == 0 || risk < w.RiskScoreLT)

		var action *actionDef
		if match {
			action = &p.Then
		} else {
			action = &p.Else
		}

		if action.Allow != nil {
			decision = map[string]any{
				"allow_connection": true,
				"required_apn":     action.Allow.Apn,
				"force_vpn":        action.Allow.Vpn != "",
				"vpn_endpoint":     action.Allow.Vpn,
				"quarantine_mode":  false,
				"telemetry_only":   false,
			}
		} else if action.Restrict != nil {
			decision = map[string]any{
				"allow_connection": false,
				"quarantine_mode":  action.Restrict.Network == "quarantine",
				"telemetry_only":   action.Restrict.TelemetryOnly,
			}
		}
		break
	}

	// Fallback built-in rule when no policies loaded
	if len(e.policies) == 0 && attest && country == "SA" && risk < 40 {
		decision = map[string]any{
			"allow_connection": true,
			"required_apn":     "qarar-sovereign",
			"force_vpn":        true,
			"vpn_endpoint":     "mihwar.qarar.sa",
			"quarantine_mode":  false,
			"telemetry_only":   false,
		}
	}

	e.ledger.Record("policy_decision", deviceID, decision)
	return decision
}
