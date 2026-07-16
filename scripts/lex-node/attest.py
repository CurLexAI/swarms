# Licensed under MIT
#!/usr/bin/env python3
"""Create a deterministic HMAC-SHA256 node attestation without exposing its key."""
import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timezone

from verify_registry import load_registry


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--registry", required=True)
    p.add_argument("--key-env", default="LEX_NODE_ATTESTATION_KEY")
    args = p.parse_args()
    key = os.environ.get(args.key_env)
    if not key:
        raise SystemExit("missing attestation key environment value")
    registry = load_registry(args.registry)
    payload = {
        "kind": "lex-node-attestation",
        "node_id": registry["node_id"],
        "issued_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "nonce": secrets.token_urlsafe(18),
        "registry_sha256": hashlib.sha256(canonical(registry)).hexdigest(),
    }
    signature = base64.b64encode(
        hmac.new(key.encode(), canonical(payload), hashlib.sha256).digest()
    ).decode()
    print(
        json.dumps(
            {"payload": payload, "signature": signature, "algorithm": "HMAC-SHA256"},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
