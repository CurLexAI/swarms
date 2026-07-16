# Licensed under MIT
#!/usr/bin/env python3
"""Dependency-free fail-closed validation for the Lex node registry."""
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, NoReturn

ENV = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")
NODE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}$")
ROOT_FIELDS = {"schema_version", "node_id", "display_name", "role", "network", "attestation", "heartbeat", "status"}


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def require_fields(value: object, expected: "set[str]", label: str) -> None:
    if not isinstance(value, dict):
        fail(f"{label} must be an object")
    if set(value) != expected:
        fail(f"{label} fields do not match contract")


def require_text(
    value: object,
    label: str,
    pattern: "re.Pattern[str] | None" = None,
    maximum: "int | None" = None,
) -> None:
    if not isinstance(value, str) or not value.strip():
        fail(f"invalid {label}")
    if maximum is not None and len(value) > maximum:
        fail(f"invalid {label}")
    if pattern is not None and not pattern.fullmatch(value):
        fail(f"invalid {label}")


def validate_identity(data: "dict[str, Any]") -> None:
    if data["schema_version"] != 1:
        fail("unsupported schema version")
    require_text(data["node_id"], "node_id", NODE)
    require_text(data["display_name"], "display_name", maximum=120)
    if data["role"] != "lex-sovereign-node":
        fail("invalid role")


def validate_network(value: "dict[str, Any]") -> None:
    require_fields(value, {"tailscale_tag", "control_plane_dns_name"}, "network")
    if value["tailscale_tag"] != "tag:lex-sovereign-node":
        fail("invalid network tag")
    require_text(value["control_plane_dns_name"], "control plane name")


def validate_key(value: "dict[str, Any]", label: str, requires_ttl: bool) -> None:
    fields = {"algorithm", "key_env"}
    if requires_ttl:
        fields.add("ttl_seconds")
    require_fields(value, fields, label)
    if value["algorithm"] != "HMAC-SHA256":
        fail(f"invalid {label} algorithm")
    require_text(value["key_env"], f"{label} key environment", ENV)


def validate_heartbeat(value: "dict[str, Any]") -> None:
    validate_key(value, "heartbeat", True)
    ttl = value["ttl_seconds"]
    if not isinstance(ttl, int):
        fail("invalid heartbeat ttl")
    if ttl < 30 or ttl > 900:
        fail("invalid heartbeat ttl")


def verify(data: "dict[str, Any]") -> bool:
    require_fields(data, ROOT_FIELDS, "registry")
    validate_identity(data)
    validate_network(data["network"])
    validate_key(data["attestation"], "attestation", False)
    validate_heartbeat(data["heartbeat"])
    if data["attestation"]["key_env"] == data["heartbeat"]["key_env"]:
        fail("attestation and heartbeat keys must be distinct")
    if data["status"] not in {"pending-enrollment", "active", "revoked", "retired"}:
        fail("invalid status")
    return True


def _confine_registry_path(path_value: "str | Path") -> Path:
    """Normalize the operator-supplied registry path and confine it.

    Permitted roots: the current working directory (validating a candidate
    registry from a checkout), the installed node state directory, and the
    system temp directory (test fixtures). Anything else fails closed.
    """
    real = os.path.realpath(
        os.path.join(os.getcwd(), os.path.expanduser(str(path_value)))
    )
    permitted_roots = (
        os.path.realpath(os.getcwd()),
        os.path.realpath("/var/lib/lex-sovereign-node"),
        os.path.realpath(tempfile.gettempdir()),
    )
    for root in permitted_roots:
        if real == root or real.startswith(root + os.sep):
            return Path(real)
    fail(
        "registry path must be under the working directory, "
        "/var/lib/lex-sovereign-node, or the system temp directory"
    )


def load_registry(path_value: "str | Path") -> "dict[str, Any]":
    path = _confine_registry_path(path_value)
    if path.suffix.lower() != ".json" or not path.is_file():
        fail("registry must be a JSON file")
    with path.open(encoding="utf-8") as handle:
        value: "dict[str, Any]" = json.load(handle)
    verify(value)
    return value


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_registry.py REGISTRY.json")
    try:
        load_registry(sys.argv[1])
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print("registry validation failed: " + str(error), file=sys.stderr)
        return 2
    print("registry validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
