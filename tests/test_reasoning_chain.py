# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for `.agents/validators/reasoning_chain.py` (PAT-014).

Contracts under test:

1. build_certificate seals the full chain with a SHA-256 chain_hash.
2. verify_certificate detects step tampering, reordering, truncation,
   and decision substitution.
3. The builder is append-only and one-way sealed (no steps after seal).
4. The middleware form records outcome classes, not raw return values.
5. Fail-closed: empty chains and blank decisions cannot certify.
6. The audit payload carries hashes/counts only (no rationale text).
"""

from __future__ import annotations

import dataclasses
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import AGENTS_DIR, _load_module  # noqa: E402

rc = _load_module(
    "_agents_pkg.validators.reasoning_chain",
    AGENTS_DIR / "validators" / "reasoning_chain.py",
)


def _builder() -> "rc.ReasoningChainBuilder":
    return rc.ReasoningChainBuilder(tenant_id="tenant-A", trace_id="trace-1")


class TestCertificate(unittest.TestCase):
    def test_certificate_covers_full_chain(self) -> None:
        b = _builder()
        b.add_step(actor="mihwar", action="plan", rationale="draft produced")
        b.add_step(actor="bayyinah", action="review", rationale="approved")
        cert = b.build_certificate(decision="APPROVE")
        self.assertEqual(cert.step_count, 2)
        self.assertEqual(len(cert.chain_hash), 64)
        self.assertEqual(cert.algorithm, rc.CHAIN_ALGORITHM)
        self.assertTrue(rc.verify_certificate(cert, b.steps))

    def test_deterministic_hash_for_same_chain(self) -> None:
        def build() -> tuple:
            b = _builder()
            b.add_step(
                actor="a",
                action="x",
                rationale="r",
                occurred_at="2026-08-06T00:00:00Z",
            )
            return b.build_certificate(decision="APPROVE"), b.steps

        cert_a, _ = build()
        cert_b, _ = build()
        self.assertEqual(cert_a.chain_hash, cert_b.chain_hash)


class TestTamperDetection(unittest.TestCase):
    def _sealed(self) -> tuple:
        b = _builder()
        b.add_step(actor="mihwar", action="plan", rationale="draft")
        b.add_step(actor="bayyinah", action="review", rationale="ok")
        return b.build_certificate(decision="APPROVE"), list(b.steps)

    def test_step_mutation_detected(self) -> None:
        cert, steps = self._sealed()
        steps[0] = dataclasses.replace(steps[0], rationale="ALTERED")
        self.assertFalse(rc.verify_certificate(cert, steps))

    def test_reorder_detected(self) -> None:
        cert, steps = self._sealed()
        self.assertFalse(rc.verify_certificate(cert, list(reversed(steps))))

    def test_truncation_detected(self) -> None:
        cert, steps = self._sealed()
        self.assertFalse(rc.verify_certificate(cert, steps[:1]))

    def test_decision_substitution_detected(self) -> None:
        cert, steps = self._sealed()
        forged = dataclasses.replace(cert, decision="BLOCKED")
        self.assertFalse(rc.verify_certificate(forged, steps))


class TestBuilderDiscipline(unittest.TestCase):
    def test_sealed_chain_rejects_new_steps(self) -> None:
        b = _builder()
        b.add_step(actor="a", action="x", rationale="r")
        b.build_certificate(decision="APPROVE")
        with self.assertRaises(RuntimeError):
            b.add_step(actor="a", action="y", rationale="late")

    def test_empty_chain_cannot_certify(self) -> None:
        with self.assertRaises(ValueError):
            _builder().build_certificate(decision="APPROVE")

    def test_blank_decision_rejected(self) -> None:
        b = _builder()
        b.add_step(actor="a", action="x", rationale="r")
        with self.assertRaises(ValueError):
            b.build_certificate(decision="  ")

    def test_required_identifiers(self) -> None:
        with self.assertRaises(ValueError):
            rc.ReasoningChainBuilder(tenant_id="", trace_id="t")


class TestMiddlewareForm(unittest.TestCase):
    def test_record_success_hides_return_value(self) -> None:
        b = _builder()
        result = b.record(
            lambda: "raw-secret-output", actor="runner", action="execute"
        )
        self.assertEqual(result, "raw-secret-output")
        self.assertEqual(b.steps[0].rationale, "ok")
        self.assertNotIn("raw-secret-output", b.steps[0].rationale)

    def test_record_failure_records_exception_class(self) -> None:
        b = _builder()

        def boom() -> None:
            raise KeyError("secret-key-name")

        with self.assertRaises(KeyError):
            b.record(boom, actor="runner", action="execute")
        self.assertEqual(b.steps[0].rationale, "raised KeyError")


class TestAuditPayload(unittest.TestCase):
    def test_payload_is_sanitized(self) -> None:
        b = _builder()
        b.add_step(actor="a", action="x", rationale="sensitive rationale")
        cert = b.build_certificate(decision="APPROVE")
        payload = rc.certificate_audit_payload(cert)
        self.assertEqual(payload["stepCount"], 1)
        self.assertEqual(payload["chainHash"], cert.chain_hash)
        self.assertNotIn("sensitive rationale", str(payload))


if __name__ == "__main__":
    unittest.main()
