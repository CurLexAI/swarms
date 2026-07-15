# Licensed under MIT
#!/usr/bin/env python3
"""Create a signed heartbeat payload; transport is intentionally external."""
import argparse, base64, hashlib, hmac, json, os, secrets
from verify_registry import load_registry
from datetime import datetime, timezone
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--registry", required=True)
    p.add_argument("--key-env", default="LEX_NODE_HEARTBEAT_KEY")
    args=p.parse_args()
    key=os.environ.get(args.key_env)
    if not key: raise SystemExit("missing heartbeat key environment value")
    registry=load_registry(args.registry)
    ttl=registry["heartbeat"]["ttl_seconds"]
    if not 30 <= ttl <= 900: raise SystemExit("invalid heartbeat ttl")
    payload={"kind":"lex-node-heartbeat","node_id":registry["node_id"],"issued_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),"nonce":secrets.token_urlsafe(18),"ttl_seconds":ttl,"status":registry["status"]}
    sig=base64.b64encode(hmac.new(key.encode(),canonical(payload),hashlib.sha256).digest()).decode()
    print(json.dumps({"payload":payload,"signature":sig,"algorithm":"HMAC-SHA256"},sort_keys=True))
if __name__=="__main__": main()
