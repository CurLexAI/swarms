# SPDX-License-Identifier: MIT
# Licensed under MIT
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / ".agents" / "validators" / "sovereign_security_controls.py"
REGISTRY_PATH = REPO_ROOT / ".agents" / "config" / "sovereign_security_controls.json"

spec = importlib.util.spec_from_file_location("sovereign_security_controls", VALIDATOR_PATH)
assert spec is not None
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


def _registry() -> dict[str, Any]:
    """Return a deep-copyable registry fixture loaded from the repository."""
    return dict(validator.load_registry(REGISTRY_PATH))


def test_registry_contains_exactly_the_eight_required_security_categories() -> None:
    """The registry must cover the eight requested control families once each."""
    registry = _registry()

    validator.validate_registry(registry)

    categories = {control["category"] for control in registry["controls"]}
    assert categories == validator.EXPECTED_CONTROL_CATEGORIES
    assert len(registry["controls"]) == 8


def test_registry_is_architecture_only_and_not_runtime_activation() -> None:
    """The registry must remain a planning artifact with no active deployment surface."""
    registry = _registry()

    assert registry["metadata"]["status"] == "architecture_only"
    assert registry["metadata"]["activation_state"] == "not_active"
    assert registry["constraints"]["no_runtime_activation"] is True
    assert registry["constraints"]["no_external_endpoints"] is True
    assert registry["constraints"]["no_secret_values"] is True

    for control in registry["controls"]:
        assert control["activation"] == {"state": "not_active", "deployment_surface": "none"}


def test_ecc_references_are_unverified_mappings_not_compliance_claims() -> None:
    """ECC entries provide traceability only and must not claim verified compliance."""
    registry = _registry()

    for control in registry["controls"]:
        assert control["ecc_mappings"]
        for mapping in control["ecc_mappings"]:
            assert mapping["mapping_status"] == "UNVERIFIED_MAPPING"

    for playbook in registry["playbooks"]:
        for mapping in playbook["ecc_mappings"]:
            assert mapping["mapping_status"] == "UNVERIFIED_MAPPING"


def test_validator_rejects_live_endpoint_or_secret_like_values() -> None:
    """Endpoint URLs and secret-like values are forbidden in the offline registry."""
    registry = copy.deepcopy(_registry())
    registry["controls"][0]["integration_points"].append("https://example.invalid/live")

    with pytest.raises(validator.RegistryValidationError, match="secret-like material|endpoint"):
        validator.validate_registry(registry)


def test_validator_requires_qarar_decision_guardrail_for_playbooks() -> None:
    """Automated response playbooks must remain gated by Qarar decisions."""
    registry = copy.deepcopy(_registry())
    registry["playbooks"][0]["guardrails"] = ["audit_before_action"]

    with pytest.raises(validator.RegistryValidationError, match="qarar_decision_required"):
        validator.validate_registry(registry)
