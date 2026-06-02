# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Validate the sovereign security controls registry.

The validator is intentionally deterministic, offline, and dependency-free. It
verifies that the architecture registry remains a governance artifact rather
than a runtime activation file, and that ECC references are traceability mappings
instead of unverified compliance claims.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

EXPECTED_CONTROL_CATEGORIES = {
    "AV",
    "EDR",
    "SIEM",
    "IDS_IPS",
    "DLP",
    "WAF",
    "NAC",
    "MTLS",
}

REQUIRED_CONTROL_KEYS = {
    "id",
    "name",
    "category",
    "layer",
    "role",
    "integration_points",
    "least_privilege",
    "audit_events",
    "ecc_mappings",
    "activation",
}

SECRET_OR_ENDPOINT_PATTERN = re.compile(
    r"(https?://|bearer\s+|api[_-]?key\s*=|token\s*=|password\s*=|secret\s*=|AKIA|sk-|ghp_|github_pat_)",
    re.IGNORECASE,
)


class RegistryValidationError(ValueError):
    """Raised when the controls registry violates offline governance rules."""


def load_registry(path: Path) -> Mapping[str, Any]:
    """Load a JSON controls registry from disk.

    Args:
        path: Path to the JSON registry file.

    Returns:
        Parsed registry mapping.

    Raises:
        RegistryValidationError: If the file is missing, invalid JSON, or does
            not parse to a mapping.
    """
    if not path.exists():
        raise RegistryValidationError(f"registry not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RegistryValidationError(f"registry JSON is invalid: {exc}") from exc
    if not isinstance(data, Mapping):
        raise RegistryValidationError("registry root must be a mapping")
    return data


def _string_values(value: Any) -> Iterable[str]:
    """Yield every string contained in a nested YAML value.

    Args:
        value: Arbitrary parsed YAML value.

    Yields:
        String values found at any nesting level.
    """
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for nested in value.values():
            yield from _string_values(nested)
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for nested in value:
            yield from _string_values(nested)


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    """Return a value as mapping or raise a validation error.

    Args:
        value: Value to inspect.
        label: Human-readable label used in the error message.

    Returns:
        The input value typed as a mapping.

    Raises:
        RegistryValidationError: If the value is not a mapping.
    """
    if not isinstance(value, Mapping):
        raise RegistryValidationError(f"{label} must be a mapping")
    return value


def _require_sequence(value: Any, label: str) -> Sequence[Any]:
    """Return a value as sequence or raise a validation error.

    Args:
        value: Value to inspect.
        label: Human-readable label used in the error message.

    Returns:
        The input value typed as a sequence.

    Raises:
        RegistryValidationError: If the value is not a list-like sequence.
    """
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise RegistryValidationError(f"{label} must be a sequence")
    return value


def _validate_no_secrets_or_endpoints(registry: Mapping[str, Any]) -> None:
    """Ensure the registry does not contain secrets or live endpoint URLs.

    Args:
        registry: Parsed registry mapping.

    Raises:
        RegistryValidationError: If a secret-like or endpoint-like value exists.
    """
    for value in _string_values(registry):
        if SECRET_OR_ENDPOINT_PATTERN.search(value):
            raise RegistryValidationError(
                "registry must not contain secret-like material or live endpoint URLs"
            )


def _validate_metadata(registry: Mapping[str, Any]) -> None:
    """Validate offline metadata and safety constraints.

    Args:
        registry: Parsed registry mapping.

    Raises:
        RegistryValidationError: If required metadata or constraints are unsafe.
    """
    metadata = _require_mapping(registry.get("metadata"), "metadata")
    constraints = _require_mapping(registry.get("constraints"), "constraints")

    if metadata.get("status") != "architecture_only":
        raise RegistryValidationError("metadata.status must be architecture_only")
    if metadata.get("activation_state") != "not_active":
        raise RegistryValidationError("metadata.activation_state must be not_active")

    for key in (
        "no_runtime_activation",
        "no_external_endpoints",
        "no_secret_values",
        "fail_closed_required",
        "least_privilege_required",
        "audit_required",
        "human_review_required_for_destructive_actions",
    ):
        if constraints.get(key) is not True:
            raise RegistryValidationError(f"constraints.{key} must be true")


def _validate_ecc_mappings(mappings: Sequence[Any], label: str) -> None:
    """Validate ECC mapping entries as unverified traceability mappings.

    Args:
        mappings: Parsed mapping entries.
        label: Parent label used in error messages.

    Raises:
        RegistryValidationError: If an entry claims verified compliance.
    """
    if not mappings:
        raise RegistryValidationError(f"{label}.ecc_mappings must not be empty")

    for index, item in enumerate(mappings):
        mapping = _require_mapping(item, f"{label}.ecc_mappings[{index}]")
        if not mapping.get("control"):
            raise RegistryValidationError(f"{label}.ecc_mappings[{index}].control is required")
        if mapping.get("mapping_status") != "UNVERIFIED_MAPPING":
            raise RegistryValidationError(
                f"{label}.ecc_mappings[{index}].mapping_status must be UNVERIFIED_MAPPING"
            )


def _validate_control(control: Mapping[str, Any], index: int) -> str:
    """Validate one security control entry.

    Args:
        control: Parsed control mapping.
        index: Position of the control in the registry.

    Returns:
        The validated control category.

    Raises:
        RegistryValidationError: If the control is incomplete or unsafe.
    """
    missing = REQUIRED_CONTROL_KEYS - set(control)
    label = f"controls[{index}]"
    if missing:
        raise RegistryValidationError(f"{label} missing keys: {sorted(missing)}")

    category = control.get("category")
    if category not in EXPECTED_CONTROL_CATEGORIES:
        raise RegistryValidationError(f"{label}.category is unexpected: {category}")

    for key in ("integration_points", "audit_events"):
        values = _require_sequence(control.get(key), f"{label}.{key}")
        if not values:
            raise RegistryValidationError(f"{label}.{key} must not be empty")

    least_privilege = _require_mapping(control.get("least_privilege"), f"{label}.least_privilege")
    permissions = _require_sequence(least_privilege.get("permissions"), f"{label}.least_privilege.permissions")
    if not permissions:
        raise RegistryValidationError(f"{label}.least_privilege.permissions must not be empty")

    activation = _require_mapping(control.get("activation"), f"{label}.activation")
    if activation.get("state") != "not_active":
        raise RegistryValidationError(f"{label}.activation.state must be not_active")
    if activation.get("deployment_surface") != "none":
        raise RegistryValidationError(f"{label}.activation.deployment_surface must be none")

    mappings = _require_sequence(control.get("ecc_mappings"), f"{label}.ecc_mappings")
    _validate_ecc_mappings(mappings, label)
    return str(category)


def validate_registry(registry: Mapping[str, Any]) -> None:
    """Validate the complete sovereign security controls registry.

    Args:
        registry: Parsed registry mapping.

    Raises:
        RegistryValidationError: If any governance rule fails.
    """
    _validate_no_secrets_or_endpoints(registry)
    _validate_metadata(registry)

    controls = _require_sequence(registry.get("controls"), "controls")
    if len(controls) != len(EXPECTED_CONTROL_CATEGORIES):
        raise RegistryValidationError(
            f"controls must contain exactly {len(EXPECTED_CONTROL_CATEGORIES)} entries"
        )

    categories = set()
    ids = set()
    for index, item in enumerate(controls):
        control = _require_mapping(item, f"controls[{index}]")
        control_id = control.get("id")
        if not isinstance(control_id, str) or not control_id:
            raise RegistryValidationError(f"controls[{index}].id is required")
        if control_id in ids:
            raise RegistryValidationError(f"duplicate control id: {control_id}")
        ids.add(control_id)
        categories.add(_validate_control(control, index))

    if categories != EXPECTED_CONTROL_CATEGORIES:
        raise RegistryValidationError(
            f"control categories mismatch: expected {sorted(EXPECTED_CONTROL_CATEGORIES)}, got {sorted(categories)}"
        )

    playbooks = _require_sequence(registry.get("playbooks"), "playbooks")
    if not playbooks:
        raise RegistryValidationError("playbooks must not be empty")
    known_ids = ids
    for index, item in enumerate(playbooks):
        playbook = _require_mapping(item, f"playbooks[{index}]")
        trigger_control = playbook.get("trigger_control")
        if trigger_control not in known_ids:
            raise RegistryValidationError(
                f"playbooks[{index}].trigger_control must reference a known control"
            )
        guardrails = _require_sequence(playbook.get("guardrails"), f"playbooks[{index}].guardrails")
        if "qarar_decision_required" not in guardrails:
            raise RegistryValidationError(
                f"playbooks[{index}].guardrails must include qarar_decision_required"
            )
        mappings = _require_sequence(playbook.get("ecc_mappings"), f"playbooks[{index}].ecc_mappings")
        _validate_ecc_mappings(mappings, f"playbooks[{index}]")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI validator.

    Args:
        argv: Optional command-line arguments for tests.

    Returns:
        Process exit code: 0 on pass, 1 on validation failure.
    """
    parser = argparse.ArgumentParser(description="Validate sovereign security controls registry")
    parser.add_argument(
        "registry",
        nargs="?",
        default=".agents/config/sovereign_security_controls.json",
        help="Path to sovereign_security_controls.json",
    )
    args = parser.parse_args(argv)

    try:
        registry = load_registry(Path(args.registry))
        validate_registry(registry)
    except RegistryValidationError as exc:
        print("VALIDATION: FAIL")
        print(f"Reason: {exc}")
        return 1

    print("VALIDATION: PASS")
    print("Checked 8 sovereign security controls and offline guardrails.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
