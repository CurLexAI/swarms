# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for `.agents/validators/bayyinah_truth_gate.py` (PAT-001).

Contracts under test:

1. TruthGate verdict contract is APPROVE | REQUEST_CHANGES | BLOCKED.
2. VERIFIED claims without a citable source are CRITICAL → BLOCKED.
3. Material UNVERIFIED claims can never APPROVE (REQUEST_CHANGES).
4. Empty/malformed claim sets fail closed (BLOCKED).
5. The offline LLM bridge challenges absolute assertions.
6. resolve_bridge refuses to run when ALLOW_EXTERNAL_AI=true.
7. evaluate_and_audit appends a sanitized record to the Qal'a sink
   (labels/counts/hash only — no claim text).
8. chain_hash is deterministic for identical claim sets.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import AGENTS_DIR, _load_module  # noqa: E402

truth_gate = _load_module(
    "_agents_pkg.validators.bayyinah_truth_gate",
    AGENTS_DIR / "validators" / "bayyinah_truth_gate.py",
)
qala_audit_sink = _load_module(
    "_agents_pkg.validators.qala_audit_sink",
    AGENTS_DIR / "validators" / "qala_audit_sink.py",
)

EvidenceClaim = truth_gate.EvidenceClaim
TruthGate = truth_gate.TruthGate


def _verified(statement: str = "tests pass") -> "truth_gate.EvidenceClaim":
    return EvidenceClaim(
        statement=statement,
        label="VERIFIED",
        source="tests/test_bayyinah_truth_gate.py",
    )


class TestTruthGateVerdicts(unittest.TestCase):
    def test_all_verified_with_sources_approves(self) -> None:
        report = TruthGate().evaluate([_verified(), _verified("gate ran")])
        self.assertEqual(report.verdict, "APPROVE")
        self.assertEqual(report.verified_count, 2)
        self.assertEqual(report.unverified_count, 0)

    def test_verified_without_source_blocks(self) -> None:
        claim = EvidenceClaim(statement="deployed", label="VERIFIED", source="")
        report = TruthGate().evaluate([claim])
        self.assertEqual(report.verdict, "BLOCKED")
        self.assertTrue(
            any(f.severity == "CRITICAL" for f in report.findings)
        )

    def test_material_unverified_requests_changes(self) -> None:
        claims = [
            _verified(),
            EvidenceClaim(statement="runtime is live", label="UNVERIFIED"),
        ]
        report = TruthGate().evaluate(claims)
        self.assertEqual(report.verdict, "REQUEST_CHANGES")

    def test_immaterial_unverified_can_approve(self) -> None:
        claims = [
            _verified(),
            EvidenceClaim(
                statement="minor note", label="UNVERIFIED", material=False
            ),
        ]
        report = TruthGate().evaluate(claims)
        self.assertEqual(report.verdict, "APPROVE")

    def test_empty_claim_set_blocks(self) -> None:
        self.assertEqual(TruthGate().evaluate([]).verdict, "BLOCKED")

    def test_unknown_label_blocks(self) -> None:
        claim = EvidenceClaim(statement="x", label="PROBABLY")
        self.assertEqual(TruthGate().evaluate([claim]).verdict, "BLOCKED")

    def test_blank_statement_blocks(self) -> None:
        claim = EvidenceClaim(statement="   ", label="INFERRED")
        self.assertEqual(TruthGate().evaluate([claim]).verdict, "BLOCKED")


class TestOfflineBridge(unittest.TestCase):
    def test_bridge_challenges_absolute_assertions(self) -> None:
        claims = [
            EvidenceClaim(
                statement="System is production ready",
                label="INFERRED",
            )
        ]
        report = TruthGate().evaluate(claims)
        self.assertEqual(report.verdict, "REQUEST_CHANGES")
        self.assertTrue(
            any("absolute assertion" in f.message for f in report.findings)
        )
        self.assertEqual(report.bridge_name, "offline-deterministic-v1")

    def test_resolve_bridge_refuses_external_ai(self) -> None:
        os.environ["ALLOW_EXTERNAL_AI"] = "true"
        try:
            with self.assertRaises(RuntimeError):
                truth_gate.resolve_bridge()
            with self.assertRaises(RuntimeError):
                TruthGate()
        finally:
            del os.environ["ALLOW_EXTERNAL_AI"]


class TestChainHashAndAudit(unittest.TestCase):
    def test_chain_hash_deterministic(self) -> None:
        claims = [_verified(), _verified("gate ran")]
        a = TruthGate().evaluate(claims)
        b = TruthGate().evaluate(list(claims))
        self.assertEqual(a.chain_hash, b.chain_hash)
        self.assertEqual(len(a.chain_hash), 64)

    def test_chain_hash_changes_with_claims(self) -> None:
        a = TruthGate().evaluate([_verified("one")])
        b = TruthGate().evaluate([_verified("two")])
        self.assertNotEqual(a.chain_hash, b.chain_hash)

    def test_evaluate_and_audit_appends_sanitized_record(self) -> None:
        with tempfile.TemporaryDirectory(prefix="truth-gate-") as tmp:
            sink = qala_audit_sink.QalaAuditSink(
                Path(tmp) / "qala-audit.jsonl"
            )
            secret_statement = "national id 1234567890 was processed"
            report = TruthGate().evaluate_and_audit(
                [
                    EvidenceClaim(
                        statement=secret_statement,
                        label="VERIFIED",
                        source="tests/x",
                    )
                ],
                sink=sink,
                trace_id="trace-1",
                span_id="span-1",
                tenant_id="tenant-A",
            )
            content = sink.sink_path.read_text(encoding="utf-8")
            self.assertIn(report.chain_hash, content)
            self.assertIn('"verdict": "APPROVE"', content)
            # Claim text must never reach the audit trail.
            self.assertNotIn(secret_statement, content)
            verify = sink.verify_chain()
            self.assertTrue(verify.ok)
            self.assertEqual(verify.records_verified, 1)


if __name__ == "__main__":
    unittest.main()
