"""Shared typed contracts for Qarar agent routing.

The router is deterministic policy code. It is not a prompt and must not make
network calls while classifying or choosing a route.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal


class TaskKind(str, Enum):
    CODING = "coding"
    CODE_REVIEW = "code_review"
    LONG_CONTEXT_ANALYSIS = "long_context_analysis"
    LEGAL_ANALYSIS = "legal_analysis"
    AGENT_CREATION = "agent_creation"
    MULTIMODAL = "multimodal"
    FAST_DRAFT = "fast_draft"
    CRITICAL_DECISION = "critical_decision"


RiskLevel = Literal["low", "medium", "high", "critical"]
ProviderKind = Literal["openai", "anthropic", "modal_vllm", "router"]
ValidationVerdict = Literal["APPROVE", "REQUEST_CHANGES", "BLOCKED"]
FindingSeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
FindingCategory = Literal[
    "SECURITY",
    "TENANT_ISOLATION",
    "LEGAL_ACCURACY",
    "CITATION",
    "CODE_CORRECTNESS",
    "PROMPT_INJECTION",
    "POLICY",
]


@dataclass(frozen=True)
class TaskProfile:
    kind: TaskKind
    risk: RiskLevel
    requires_long_context: bool
    requires_arabic_legal_precision: bool
    requires_code_execution: bool
    requires_multimodal: bool
    estimated_context_tokens: int
    requires_citations: bool
    tenant_id: str | None = None


@dataclass(frozen=True)
class ModelRoute:
    provider: ProviderKind
    model: str
    reason: str
    requires_reviewer: bool
    reviewer_agent_id: str | None = None


@dataclass(frozen=True)
class ExecutionPlan:
    primary_agent_id: str
    route: ModelRoute
    validation_required: bool
    steps: tuple[str, ...]


@dataclass(frozen=True)
class ValidationFinding:
    severity: FindingSeverity
    category: FindingCategory
    message: str


@dataclass(frozen=True)
class ValidationReport:
    verdict: ValidationVerdict
    severity: RiskLevel | Literal["none"]
    findings: tuple[ValidationFinding, ...]
    safe_output: Any
