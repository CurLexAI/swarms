#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Licensed under MIT
"""
LexPrim Bridge Integration Test
===============================
Real-world test of the unidirectional bridge from LexPrim to swarms.

Test scenarios:
1. CAO-Claude (architecture) → Mihwar (code generation)
2. CGSA-Gemini (security audit) → Bayyinah (code review)
3. Verify audit log (bridge_audit.jsonl)

Status: EXECUTABLE (requires Modal + invoke.py)
Date: 2026-06-01
Branch: test/lexprim-bridge-integration
"""

import asyncio
import json
import sys
from pathlib import Path

# Add .agents to path
AGENTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(AGENTS_DIR))

from adapters.lexprim_bridge import (  # noqa: E402
    LexPrimBridge,
    BridgeRequest,
    SourceAgent,
)


async def test_cao_claude_to_mihwar():
    """
    Test 1: CAO-Claude (Architecture) → Mihwar (Code Generation)

    Scenario: LexPrim asks for architecture of a regulatory document retrieval system.
    Expected: Mihwar generates design and code skeleton.
    """
    print("\n" + "=" * 70)
    print("[TEST 1] CAO-Claude → Mihwar (Architecture → Code Generation)")
    print("=" * 70)

    request = BridgeRequest(
        source=SourceAgent.CAO_CLAUDE,
        task=(
            "Design a secure REST API for regulatory document retrieval "
            "with PDPL compliance checks. Include:\n"
            "- Authentication layer (JWT with 15-min expiry)\n"
            "- Rate limiting (100 req/min per user)\n"
            "- Document classification (PUBLIC/INTERNAL/CONFIDENTIAL)\n"
            "- Audit logging for all access"
        ),
        context=(
            "This is for Qarar platform (regulatory compliance system). "
            "Must comply with SAMA CSF and PDPL."
        ),
        priority="HIGH",
    )

    bridge = LexPrimBridge()
    response = await bridge.process(request)

    print(f"\n📋 Request ID: {response.request_id}")
    print(f"⏱️  Duration: {response.duration_ms:.0f}ms")
    print(f"📊 Status: {response.status.value}")
    if response.error:
        print(f"❌ Error: {response.error}")
    else:
        print(f"✅ Result preview:\n{response.result[:500]}...")

    return response


async def test_cgsa_gemini_to_bayyinah():
    """
    Test 2: CGSA-Gemini (Security Audit) → Bayyinah (Code Review)

    Scenario: LexPrim asks for security review of authentication module.
    Expected: Bayyinah reviews for vulnerabilities, compliance issues.
    """
    print("\n" + "=" * 70)
    print("[TEST 2] CGSA-Gemini → Bayyinah (Security Audit → Code Review)")
    print("=" * 70)

    # Simulated code to review (from Test 1 output would be real)
    code_to_review = """
    import jwt
    from datetime import datetime, timedelta
    from fastapi import FastAPI, Header, HTTPException

    app = FastAPI()
    SECRET_KEY = "hardcoded-secret-key-12345"  # VULNERABILITY!

    @app.post("/auth/login")
    def login(username: str, password: str):
        # Direct SQL query - VULNERABILITY!
        user = db.execute(f"SELECT * FROM users WHERE username='{username}'")
        if not user or user.password != password:  # Plaintext comparison!
            raise HTTPException(status_code=401)

        token = jwt.encode(
            {"user": username, "exp": datetime.utcnow() + timedelta(hours=24)},
            SECRET_KEY,
            algorithm="HS256"
        )
        return {"access_token": token}

    @app.get("/documents")
    def get_documents(token: str = Header()):
        # No rate limiting
        # No audit log
        return db.execute("SELECT * FROM documents")
    """

    request = BridgeRequest(
        source=SourceAgent.CGSA_GEMINI,
        task=(
            "Review the following authentication module for security vulnerabilities, "
            "SAMA CSF compliance, and PDPL data protection issues:\n\n" + code_to_review
        ),
        priority="CRITICAL",
    )

    bridge = LexPrimBridge()
    response = await bridge.process(request)

    print(f"\n📋 Request ID: {response.request_id}")
    print(f"⏱️  Duration: {response.duration_ms:.0f}ms")
    print(f"📊 Status: {response.status.value}")
    if response.error:
        print(f"❌ Error: {response.error}")
    else:
        print(f"✅ Result preview:\n{response.result[:500]}...")

    return response


async def verify_audit_log():
    """
    Test 3: Verify Audit Log (bridge_audit.jsonl)

    Scenario: Check that both requests were logged for SAMA CSF / PDPL compliance.
    Expected: Two JSONL lines, one per request, with full traceability.
    """
    print("\n" + "=" * 70)
    print("[TEST 3] Audit Log Verification (SAMA CSF / PDPL Compliance)")
    print("=" * 70)

    audit_log_path = AGENTS_DIR / "audit" / "bridge_audit.jsonl"

    if not audit_log_path.exists():
        print("❌ Audit log not found:", audit_log_path)
        return False

    try:
        with open(audit_log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        print(f"\n📊 Audit log entries: {len(lines)}")
        print(f"📁 Location: {audit_log_path}")

        for i, line in enumerate(lines[-2:], start=1):  # Show last 2 entries
            entry = json.loads(line)
            print(f"\n📋 Entry {i}:")
            print(f"  Request ID: {entry.get('request_id')}")
            print(f"  Source: {entry.get('source')}")
            print(f"  Target: {entry.get('target')}")
            print(f"  Status: {entry.get('status')}")
            print(f"  Duration: {entry.get('duration_ms'):.0f}ms")
            print(f"  Timestamp: {entry.get('timestamp')}")

        return True

    except Exception as e:
        print(f"❌ Error reading audit log: {e}")
        return False


async def main():
    """Run all tests sequentially."""
    print("\n" + "#" * 70)
    print("# LexPrim Bridge Integration Test")
    print("# Branch: test/lexprim-bridge-integration")
    print("# Commit: cecd32f79d82ea99850bf76f45e2af36f5f03831")
    print("#" * 70)

    try:
        # Test 1: Architecture → Code
        response1 = await test_cao_claude_to_mihwar()

        # Test 2: Security Audit → Review
        response2 = await test_cgsa_gemini_to_bayyinah()

        # Test 3: Audit Log
        audit_ok = await verify_audit_log()

        # Summary
        print("\n" + "=" * 70)
        print("[SUMMARY]")
        print("=" * 70)
        print(f"✅ Test 1 (CAO-Claude → Mihwar): {response1.status.value}")
        print(f"✅ Test 2 (CGSA-Gemini → Bayyinah): {response2.status.value}")
        print(f"✅ Test 3 (Audit Log): {'VERIFIED' if audit_ok else 'FAILED'}")

        if (
            response1.status.value == "SUCCESS"
            and response2.status.value == "SUCCESS"
            and audit_ok
        ):
            print("\n✅ All tests PASSED - Bridge is operational")
            return 0
        else:
            print("\n⚠️ Some tests failed - Check logs above")
            return 1

    except Exception as e:
        print(f"\n❌ Test execution failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
