# Licensed under MIT
#!/usr/bin/env python3
"""Dependency-free fail-closed validation for the Lex node registry."""
import json, re, sys
from pathlib import Path
ENV=re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")
NODE=re.compile(r"^[a-z0-9][a-z0-9-]{2,62}$")
def fail(message): raise ValueError(message)
def verify(data):
    required={"schema_version","node_id","display_name","role","network","attestation","heartbeat","status"}
    if set(data)!=required: fail("registry fields do not match contract")
    if data["schema_version"] != 1: fail("unsupported schema version")
    if not isinstance(data["node_id"],str) or not NODE.fullmatch(data["node_id"]): fail("invalid node_id")
    if not isinstance(data["display_name"],str) or not data["display_name"].strip() or len(data["display_name"])>120: fail("invalid display_name")
    if data["role"]!="lex-sovereign-node": fail("invalid role")
    n=data["network"]
    if set(n)!={"tailscale_tag","control_plane_dns_name"} or n["tailscale_tag"]!="tag:lex-sovereign-node" or not isinstance(n["control_plane_dns_name"],str) or not n["control_plane_dns_name"]: fail("invalid network")
    for name in ("attestation","heartbeat"):
        obj=data[name]
        expected={"algorithm","key_env"} | ({"ttl_seconds"} if name=="heartbeat" else set())
        if set(obj)!=expected or obj["algorithm"]!="HMAC-SHA256" or not isinstance(obj["key_env"],str) or not ENV.fullmatch(obj["key_env"]): fail("invalid "+name)
    if data["attestation"]["key_env"]==data["heartbeat"]["key_env"]: fail("attestation and heartbeat keys must be distinct")
    if not isinstance(data["heartbeat"]["ttl_seconds"],int) or not 30<=data["heartbeat"]["ttl_seconds"]<=900: fail("invalid heartbeat ttl")
    if data["status"] not in {"pending-enrollment","active","revoked","retired"}: fail("invalid status")
    return True
def main():
    if len(sys.argv)!=2: raise SystemExit("usage: verify_registry.py REGISTRY.json")
    try:
        with Path(sys.argv[1]).open(encoding="utf-8") as f: verify(json.load(f))
    except (OSError,json.JSONDecodeError,ValueError) as e:
        print("registry validation failed: "+str(e),file=sys.stderr); return 2
    print("registry validation passed"); return 0
if __name__=="__main__": raise SystemExit(main())
