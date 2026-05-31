# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Validator package.

Exposes the data classification validator. Other validators in this
package (bayyinah_validation_gate, qala_*) are loaded directly by their
callers and gates.
"""

from .classification_validator import (
    ClassificationResult,
    DataClassification,
    classify_content,
)

__all__ = [
    "DataClassification",
    "ClassificationResult",
    "classify_content",
]
