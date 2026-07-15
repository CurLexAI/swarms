# Licensed under MIT
#!/usr/bin/env python3
"""Dependency-free fail-closed validation for the Lex node registry."""
import json
import re
import sys
from pathlib import Path

ENV = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")
NODE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}$")
ROOT_FIELDS = {"schema_version", "node_id", "display_name", "role", "network", "attestation", "heartbeat", "status"}

def fail(message):
    raise ValueError(message)

def require_fields(value, expected, label):
    if not isinstance(value, dict):
        fail(f"{label} must be an object")
    if set(value) != expected:
        fail(f"{label} fields do not match contract")

def require_text(value, label, pattern=None, maximum=None):
    if not isinstance(value, str) or not value.strip():
        fail(f"invalid {label}")
    if maximum is not None and len(value) > maximum:
        fail(f"invalid {label}")
    if pattern is not None and not pattern.fullmatch(value):
        fail(f"invalid {label}")

def validate_identity(data):
    if data["schema_version"] != 1:
        fail("unsupported schema version")
    require_text(data["node_id"], "node_id", NODE)
    require_text(data["display_name"], "display_name", maximum=120)
    if data["role"] != "lex-sovereign-node":
        fail("invalid role")

def validate_network(value):
    require_fields(value, {"tailscale_tag", "control_plane_dns_name"}, "network")
    if value["tailscale_tag"] != "tag:lex-sovereign-node":
        fail("invalid network tag")
    require_text(value["control_plane_dns_name"], "control plane name")

def validate_key(value, label, requires_ttl):
    fields = {"algorithm", "key_env"}
    if requires_ttl:
        fields.add("ttl_seconds")
    require_fields(value, fields, label)
    if value["algorithm"] != "HMAC-SHA256":
        fail(f"invalid {label} algorithm")
    require_text(value["key_env"], f"{label} key environment", ENV)

def validate_heartbeat(value):
    validate_key(value, "heartbeat", True)
    ttl = value["ttl_seconds"]
    if not isinstance(ttl, int):
        fail("invalid heartbeat ttl")
    if ttl < 30 or ttl > 900:
        fail("invalid heartbeat ttl")

def verify(data):
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

def load_registry(path_value):
    path = Path(path_value).expanduser().resolve(strict=True)
    if path.suffix.lower() != ".json" or not path.is_file():
        fail("registry must be a JSON file")
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    verify(value)
    return value

def main():
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
