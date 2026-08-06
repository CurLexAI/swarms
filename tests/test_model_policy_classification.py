# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Unit tests for classification-based provider selection (PAT-003).

Contracts under test:

1. DataClassification enum exposes PUBLIC/INTERNAL/CONFIDENTIAL/SOVEREIGN
   (with the claim-language alias DATA_CLASSIFICATION).
2. SOVEREIGN/CONFIDENTIAL data never routes to an external provider.
3. PERMANENTLY_BLOCKED_PROVIDERS are excluded for every classification,
   even when explicitly passed as candidates.
4. selectProviderByClassification (claim-language alias) is the same
   callable as select_provider_by_classification.
5. Fail-closed: unknown classifications raise; a candidate set with no
   permitted provider raises.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import model_policy_engine as mpe  # noqa: E402

DataClassification = mpe.DataClassification
select = mpe.select_provider_by_classification


class TestClassificationEnum(unittest.TestCase):
    def test_enum_members(self) -> None:
        self.assertEqual(DataClassification.PUBLIC.value, "public")
        self.assertEqual(DataClassification.INTERNAL.value, "internal")
        self.assertEqual(DataClassification.CONFIDENTIAL.value, "confidential")
        self.assertEqual(DataClassification.SOVEREIGN.value, "sovereign")

    def test_claim_language_aliases(self) -> None:
        self.assertIs(mpe.DATA_CLASSIFICATION, DataClassification)
        self.assertIs(mpe.selectProviderByClassification, select)


class TestSovereignFirstSelection(unittest.TestCase):
    def test_sovereign_never_routes_external(self) -> None:
        for classification in (
            DataClassification.SOVEREIGN,
            DataClassification.CONFIDENTIAL,
        ):
            selection = select(classification)
            self.assertNotIn("openai", selection.allowed)
            self.assertNotIn("anthropic", selection.allowed)
            self.assertIn(selection.provider, selection.allowed)
            self.assertEqual(selection.provider, "local_ollama")

    def test_public_allows_external_but_sovereign_first(self) -> None:
        selection = select("public")
        self.assertIn("openai", selection.allowed)
        self.assertIn("anthropic", selection.allowed)
        # Sovereign-first: local runtimes outrank external even for PUBLIC.
        self.assertEqual(selection.provider, "local_ollama")

    def test_internal_excludes_openai(self) -> None:
        selection = select(DataClassification.INTERNAL)
        self.assertNotIn("openai", selection.allowed)
        self.assertIn("anthropic", selection.allowed)

    def test_candidate_filtering(self) -> None:
        selection = select(
            DataClassification.PUBLIC, candidates=("anthropic", "openai")
        )
        self.assertEqual(selection.provider, "anthropic")


class TestPermanentBlocking(unittest.TestCase):
    def test_blocked_providers_never_selected(self) -> None:
        for classification in DataClassification:
            for blocked in mpe.PERMANENTLY_BLOCKED_PROVIDERS:
                selection = select(
                    classification,
                    candidates=(blocked, "local_ollama"),
                )
                self.assertNotEqual(selection.provider, blocked)
                self.assertNotIn(blocked, selection.allowed)
                self.assertIn(blocked, selection.blocked)

    def test_only_blocked_candidates_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            select(
                DataClassification.PUBLIC,
                candidates=tuple(mpe.PERMANENTLY_BLOCKED_PROVIDERS),
            )

    def test_unknown_classification_raises(self) -> None:
        with self.assertRaises(ValueError):
            select("top-secret-nonsense")


if __name__ == "__main__":
    unittest.main()
