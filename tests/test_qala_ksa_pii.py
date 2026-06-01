# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for `.agents/validators/qala_ksa_pii.py`.

Contracts under test (per ADR-0003 §Q5):

1. National ID, Iqama, CR, IBAN, Mobile, Ambiguous-10-digit are each
   detected by their documented shape.
2. Raw match values NEVER appear in the result — only masked.
3. Word-boundary discipline: a 12-digit number does not match as a
   10-digit ID inside it; an IBAN does not double-match as a 10-digit
   shape.
4. Anti-collision: 10-digit shape with leading 1 is National ID, with
   leading 2 is Iqama, with leading 7 is CR, otherwise Ambiguous.
5. ``redact_ksa_pii`` returns text with every span masked.
6. Empty / non-string input is handled fail-closed (empty result).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import _load_module, AGENTS_DIR  # noqa: E402

qala_ksa_pii = _load_module(
    "_agents_pkg.validators.qala_ksa_pii",
    AGENTS_DIR / "validators" / "qala_ksa_pii.py",
)
detect_ksa_pii = qala_ksa_pii.detect_ksa_pii
has_ksa_pii = qala_ksa_pii.has_ksa_pii
redact_ksa_pii = qala_ksa_pii.redact_ksa_pii


class CategoryDetectionTests(unittest.TestCase):
    def test_national_id(self) -> None:
        hits = detect_ksa_pii("الهوية: 1234567890")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].category, "KSA_NATIONAL_ID")
        self.assertEqual(hits[0].masked_value, "12…90")

    def test_iqama(self) -> None:
        hits = detect_ksa_pii("Iqama: 2345678901")
        self.assertEqual(hits[0].category, "KSA_IQAMA")

    def test_commercial_registration(self) -> None:
        hits = detect_ksa_pii("CR No. 7012345678")
        self.assertEqual(hits[0].category, "KSA_COMMERCIAL_REGISTRATION")

    def test_iban(self) -> None:
        hits = detect_ksa_pii("IBAN SA4420000001234567891234.")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].category, "KSA_IBAN")
        self.assertTrue(hits[0].masked_value.startswith("SA"))

    def test_mobile_plus966(self) -> None:
        hits = detect_ksa_pii("Mobile: +966512345678")
        self.assertEqual(hits[0].category, "KSA_MOBILE")

    def test_mobile_966_no_plus(self) -> None:
        hits = detect_ksa_pii("Mobile: 966512345678")
        self.assertEqual(hits[0].category, "KSA_MOBILE")

    def test_mobile_local_05(self) -> None:
        hits = detect_ksa_pii("Mobile: 0512345678")
        self.assertEqual(hits[0].category, "KSA_MOBILE")

    def test_ambiguous_10digit_leading_5(self) -> None:
        hits = detect_ksa_pii("ID: 5123456789")
        self.assertEqual(hits[0].category, "KSA_ID_AMBIGUOUS_10DIGIT")


class MaskingTests(unittest.TestCase):
    def test_raw_value_never_in_masked(self) -> None:
        raw = "1234567890"
        hit = detect_ksa_pii(f"X {raw} Y")[0]
        self.assertNotIn(raw, hit.masked_value)
        self.assertIn("…", hit.masked_value)
        self.assertEqual(hit.masked_value, "12…90")

    def test_redact_replaces_raw_value(self) -> None:
        text = "Patient national id 1234567890 was processed."
        redacted = redact_ksa_pii(text)
        self.assertNotIn("1234567890", redacted)
        self.assertIn("[KSA_NATIONAL_ID:12…90]", redacted)

    def test_redact_preserves_non_pii_text(self) -> None:
        text = "Hello world."
        self.assertEqual(redact_ksa_pii(text), "Hello world.")


class WordBoundaryTests(unittest.TestCase):
    def test_eleven_digits_does_not_match_ten_digit_id(self) -> None:
        # 12345678901 — 11 digits. Should NOT match as 10-digit National ID.
        hits = detect_ksa_pii("Number 12345678901")
        national_id_hits = [h for h in hits if h.category == "KSA_NATIONAL_ID"]
        self.assertEqual(national_id_hits, [])

    def test_iban_does_not_double_match_as_10_digit(self) -> None:
        # IBAN has 22 digits after "SA" — the 10-digit anchors require
        # (?<!\d), so the digit stream inside the IBAN must not be
        # interpreted as a 10-digit ID.
        hits = detect_ksa_pii("SA4420000001234567891234")
        categories = {h.category for h in hits}
        self.assertEqual(categories, {"KSA_IBAN"})

    def test_short_digit_run_does_not_match(self) -> None:
        self.assertEqual(detect_ksa_pii("Number 12345"), ())

    def test_word_boundary_inside_alpha(self) -> None:
        # 10 digits embedded inside an alphanumeric blob — the (?<!\d)
        # anchors do not look for letters, so the match WOULD fire.
        # This documents current behavior; surrounding word-boundary
        # discipline is the caller's responsibility for free-form text.
        hits = detect_ksa_pii("ID:1234567890.")
        self.assertEqual(len(hits), 1)


class AntiCollisionTests(unittest.TestCase):
    def test_iban_is_returned_when_both_iban_and_digits_present(self) -> None:
        hits = detect_ksa_pii(
            "IBAN: SA4420000001234567891234 and ID 1234567890"
        )
        categories = [h.category for h in hits]
        self.assertIn("KSA_IBAN", categories)
        self.assertIn("KSA_NATIONAL_ID", categories)

    def test_mobile_and_national_id_distinct(self) -> None:
        hits = detect_ksa_pii("Mobile +966512345678 and ID 1234567890.")
        categories = [h.category for h in hits]
        self.assertIn("KSA_MOBILE", categories)
        self.assertIn("KSA_NATIONAL_ID", categories)
        self.assertEqual(len(hits), 2)


class EdgeCaseTests(unittest.TestCase):
    def test_empty_string(self) -> None:
        self.assertEqual(detect_ksa_pii(""), ())
        self.assertFalse(has_ksa_pii(""))

    def test_non_string_returns_empty(self) -> None:
        # The type hint is str, but defensive behavior protects callers.
        self.assertEqual(detect_ksa_pii(None), ())
        self.assertEqual(detect_ksa_pii(12345), ())

    def test_no_pii_text(self) -> None:
        self.assertFalse(has_ksa_pii("This is benign text."))

    def test_has_ksa_pii_truthy(self) -> None:
        self.assertTrue(has_ksa_pii("Iqama 2345678901."))


if __name__ == "__main__":
    unittest.main()
