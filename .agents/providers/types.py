# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Provider contracts for Qarar routing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderRequest:
    task: str
    model: str
    tenant_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    model: str
    output: Any
    metadata: dict[str, Any]


class Provider(Protocol):
    name: str

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        """Execute the request or raise a clear runtime error."""
