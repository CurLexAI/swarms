# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for `.agents/validators/classification_validator.py`.

Contracts under test:

1. Allowlisted public source (e.g. SAMA) -> PUBLIC.
2. Unrecognized source -> INTERNAL (fail-safe default).
3. KSA-PII present -> escalates to at least INTERNAL (never downgrades a
   public source below INTERNAL when PII is found).
4. A `metadata["classification_floor"]` escalates monotonically.
5. When an audit sink + trace identifiers are supplied, a
   `classification_decision` record is sealed and the chain verifies;
   the payload carries only PII category names, never raw values.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import _load_module, AGENTS_DIR  # noqa: E402

classification_validator = _load_module(
    "_agents_pkg.validators.classification_validator",
    AGENTS_DIR / "validators" / "classification_validator.py",
)
qala_audit_sink = _load_module(
    "_agents_pkg.validators.qala_audit_sink",
    AGENTS_DIR / "validators" / "qala_audit_sink.py",
)

DataClassification = classification_validator.DataClassification
classify_content = classification_validator.classify_content
QalaAuditSink = qala_audit_sink.QalaAuditSink

# A KSA National ID shape (leading 1, ten digits) — synthetic, not real.
_PII_TEXT = "Customer national id 1234567890 on file."


class ClassificationRulesTests(unittest.TestCase):
    def test_sama_source_is_public(self) -> None:
        result = classify_content("SAMA", "Public circular on open banking.")
        self.assertEqual(result.classification, DataClassification.PUBLIC)
        self.assertIn("allowlisted_public_source", result.reasons)
        self.assertEqual(result.pii_categories, ())

    def test_public_source_token_match_is_case_insensitive(self) -> None:
        result = classify_content("laws.boe.gov.sa", "Royal decree text.")
        self.assertEqual(result.classification, DataClassification.PUBLIC)

    def test_unknown_source_defaults_internal(self) -> None:
        result = classify_content("random-blog", "Some commentary.")
        self.assertEqual(result.classification, DataClassification.INTERNAL)
        self.assertIn("unrecognized_source_default_internal", result.reasons)

    def test_pii_detected_escalates_to_internal(self) -> None:
        result = classify_content("random-blog", _PII_TEXT)
        self.assertEqual(result.classification, DataClassification.INTERNAL)
        self.assertIn("ksa_pii_detected", result.reasons)
        self.assertIn("KSA_NATIONAL_ID", result.pii_categories)

    def test_pii_in_public_source_escalates_above_public(self) -> None:
        result = classify_content("SAMA", _PII_TEXT)
        self.assertEqual(result.classification, DataClassification.INTERNAL)
        self.assertIn("ksa_pii_detected", result.reasons)

    def test_metadata_floor_escalates(self) -> None:
        result = classify_content(
            "SAMA", "no pii here", {"classification_floor": "RESTRICTED"}
        )
        self.assertEqual(result.classification, DataClassification.RESTRICTED)

    def test_invalid_metadata_floor_is_ignored(self) -> None:
        result = classify_content(
            "SAMA", "no pii here", {"classification_floor": "BOGUS"}
        )
        self.assertEqual(result.classification, DataClassification.PUBLIC)


class ClassificationAuditTests(unittest.TestCase):
    def test_decision_is_sealed_and_chain_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # The `classification_decision` event ships in PR #242, not yet
            # on `main`. Probe support so this assertion auto-activates the
            # moment #242 lands the event, without staying skipped forever.
            probe = QalaAuditSink(Path(tmp) / "probe.jsonl").append(
                event="classification_decision",
                trace_id="t",
                span_id="s",
                tenant_id="x",
                payload={},
            )
            if not probe.ok:
                self.skipTest(
                    "audit-seal requires classification_decision event from "
                    "PR #242; forward-compatible and auto-activates post-merge"
                )
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            result = classify_content(
                "random-blog",
                _PII_TEXT,
                audit_sink=sink,
                trace_id="trace-1",
                span_id="span-1",
                tenant_id="tenant-A",
            )
            self.assertEqual(result.classification, DataClassification.INTERNAL)
            verify = sink.verify_chain()
            self.assertTrue(verify.ok)
            self.assertEqual(verify.records_verified, 1)

            # The sealed record must carry category names only — never the
            # raw or masked identifier value.
            content = (Path(tmp) / "audit.jsonl").read_text(encoding="utf-8")
            self.assertIn("classification_decision", content)
            self.assertIn("KSA_NATIONAL_ID", content)
            self.assertNotIn("1234567890", content)

    def test_no_audit_when_trace_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sink = QalaAuditSink(Path(tmp) / "audit.jsonl")
            classify_content("SAMA", "no pii", audit_sink=sink)
            self.assertEqual(sink.verify_chain().records_verified, 0)


if __name__ == "__main__":
    unittest.main()
