# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for `.agents/validators/qala_trace.py`.

Contracts under test (per ADR-0003 §Q6):

1. Generated trace_id and span_id are UUID v4.
2. child_span inherits trace_id and tenant_id; generates fresh span_id;
   parent_span_id is set to the parent's span_id.
3. to_headers / from_headers round-trip without loss.
4. from_headers is fail-closed — returns None on any missing/malformed
   field rather than raising.
5. to_headers never emits Authorization / Bearer / secret-shaped values.
6. Phase enum is closed; unknown phases are rejected.
7. tenant_id is required, length-bounded, and pattern-bounded.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import qala_trace  # noqa: E402

new_trace = qala_trace.new_trace
child_span = qala_trace.child_span
to_headers = qala_trace.to_headers
from_headers = qala_trace.from_headers
QalaTraceError = qala_trace.QalaTraceError


UUID_V4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class NewTraceTests(unittest.TestCase):
    def test_generates_uuid_v4_ids(self):
        ctx = new_trace("tenant-A", "input_validation")
        self.assertRegex(ctx.trace_id, UUID_V4_RE)
        self.assertRegex(ctx.span_id, UUID_V4_RE)
        self.assertNotEqual(ctx.trace_id, ctx.span_id)
        self.assertIsNone(ctx.parent_span_id)
        self.assertEqual(ctx.tenant_id, "tenant-A")
        self.assertEqual(ctx.phase, "input_validation")

    def test_distinct_traces_have_distinct_ids(self):
        a = new_trace("tenant-A", "input_validation")
        b = new_trace("tenant-A", "input_validation")
        self.assertNotEqual(a.trace_id, b.trace_id)
        self.assertNotEqual(a.span_id, b.span_id)

    def test_rejects_unknown_phase(self):
        with self.assertRaises(QalaTraceError) as cm:
            new_trace("tenant-A", "not_a_phase")
        self.assertEqual(cm.exception.code, "INVALID_PHASE")

    def test_rejects_empty_tenant(self):
        with self.assertRaises(QalaTraceError) as cm:
            new_trace("", "input_validation")
        self.assertEqual(cm.exception.code, "INVALID_TENANT_ID")

    def test_rejects_oversize_tenant(self):
        with self.assertRaises(QalaTraceError) as cm:
            new_trace("t" * 200, "input_validation")
        self.assertEqual(cm.exception.code, "INVALID_TENANT_ID")

    def test_rejects_tenant_with_disallowed_chars(self):
        with self.assertRaises(QalaTraceError) as cm:
            new_trace("tenant A", "input_validation")
        self.assertEqual(cm.exception.code, "INVALID_TENANT_ID")


class ChildSpanTests(unittest.TestCase):
    def test_inherits_trace_and_tenant(self):
        parent = new_trace("tenant-A", "input_validation")
        child = child_span(parent, "model_call")
        self.assertEqual(child.trace_id, parent.trace_id)
        self.assertEqual(child.tenant_id, parent.tenant_id)
        self.assertEqual(child.parent_span_id, parent.span_id)
        self.assertNotEqual(child.span_id, parent.span_id)
        self.assertEqual(child.phase, "model_call")

    def test_rejects_unknown_phase_on_child(self):
        parent = new_trace("tenant-A", "input_validation")
        with self.assertRaises(QalaTraceError) as cm:
            child_span(parent, "garbage")
        self.assertEqual(cm.exception.code, "INVALID_PHASE")


class HeaderRoundTripTests(unittest.TestCase):
    def test_round_trip_root_span(self):
        ctx = new_trace("tenant-A", "policy_check")
        headers = to_headers(ctx)
        restored = from_headers(headers)
        self.assertIsNotNone(restored)
        assert restored is not None  # for type narrowing
        self.assertEqual(restored.trace_id, ctx.trace_id)
        self.assertEqual(restored.span_id, ctx.span_id)
        self.assertIsNone(restored.parent_span_id)
        self.assertEqual(restored.tenant_id, ctx.tenant_id)
        self.assertEqual(restored.phase, ctx.phase)
        self.assertEqual(restored.started_at, ctx.started_at)

    def test_round_trip_child_span(self):
        parent = new_trace("tenant-A", "input_validation")
        child = child_span(parent, "audit_emit")
        restored = from_headers(to_headers(child))
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored.parent_span_id, parent.span_id)
        self.assertEqual(restored.trace_id, parent.trace_id)

    def test_case_insensitive_header_read(self):
        ctx = new_trace("tenant-A", "audit_emit")
        headers = to_headers(ctx)
        upper = {k.upper(): v for k, v in headers.items()}
        restored = from_headers(upper)
        self.assertIsNotNone(restored)


class FailClosedReaderTests(unittest.TestCase):
    """from_headers returns None — never raises — on malformed input."""

    def _valid_headers(self) -> dict[str, str]:
        return to_headers(new_trace("tenant-A", "input_validation"))

    def test_missing_trace_id_returns_none(self):
        h = self._valid_headers()
        del h["x-qala-trace-id"]
        self.assertIsNone(from_headers(h))

    def test_missing_span_id_returns_none(self):
        h = self._valid_headers()
        del h["x-qala-span-id"]
        self.assertIsNone(from_headers(h))

    def test_missing_tenant_returns_none(self):
        h = self._valid_headers()
        del h["x-qala-tenant-id"]
        self.assertIsNone(from_headers(h))

    def test_missing_phase_returns_none(self):
        h = self._valid_headers()
        del h["x-qala-phase"]
        self.assertIsNone(from_headers(h))

    def test_malformed_trace_id_returns_none(self):
        h = self._valid_headers()
        h["x-qala-trace-id"] = "not-a-uuid"
        self.assertIsNone(from_headers(h))

    def test_malformed_parent_span_id_returns_none(self):
        parent = new_trace("tenant-A", "input_validation")
        child = child_span(parent, "model_call")
        h = to_headers(child)
        h["x-qala-parent-span-id"] = "not-a-uuid"
        self.assertIsNone(from_headers(h))

    def test_unknown_phase_returns_none(self):
        h = self._valid_headers()
        h["x-qala-phase"] = "unknown_phase"
        self.assertIsNone(from_headers(h))

    def test_malformed_tenant_returns_none(self):
        h = self._valid_headers()
        h["x-qala-tenant-id"] = "bad tenant id with spaces"
        self.assertIsNone(from_headers(h))

    def test_empty_headers_returns_none(self):
        self.assertIsNone(from_headers({}))

    def test_malformed_started_at_returns_none(self):
        h = self._valid_headers()
        h["x-qala-started-at"] = "not-a-date"
        self.assertIsNone(from_headers(h))


class NoSecretsInHeadersTests(unittest.TestCase):
    """to_headers MUST NOT emit any value that looks like an auth credential.

    The full secret-shape pattern matrix is enforced by
    sovereignCyberRadar / unifiedAgentAdapter. Here we sample the
    highest-frequency leak shapes to keep the trace surface clean.
    """

    SECRET_SHAPES = [
        re.compile(r"Bearer\s+", re.IGNORECASE),
        re.compile(r"\bsk-[A-Za-z0-9_-]{8,}", re.IGNORECASE),
        re.compile(r"\bghp_[A-Za-z0-9_]{8,}"),
        re.compile(r"\bAKIA[0-9A-Z]{8,}"),
        re.compile(r"\.modal\.run", re.IGNORECASE),
    ]

    def test_no_secret_shapes_in_headers(self):
        ctx = new_trace("tenant-A", "model_call")
        for value in to_headers(ctx).values():
            for pattern in self.SECRET_SHAPES:
                self.assertIsNone(
                    pattern.search(value),
                    f"trace header value leaked a secret-shaped pattern: {value!r}",
                )

    def test_no_authorization_header_emitted(self):
        ctx = new_trace("tenant-A", "model_call")
        headers = {k.lower(): v for k, v in to_headers(ctx).items()}
        self.assertNotIn("authorization", headers)
        self.assertNotIn("x-api-key", headers)
        self.assertNotIn("cookie", headers)


if __name__ == "__main__":
    unittest.main()
