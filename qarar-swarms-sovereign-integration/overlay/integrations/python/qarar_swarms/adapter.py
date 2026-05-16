from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional, Sequence

import requests
from dotenv import load_dotenv

SOVEREIGN_MODEL_IDS = {"deepseek-r1-32b", "allam-7b", "qwen-72b-arabic"}
TASK_MODEL_MAP = {
    "LEGAL_REASONING": "deepseek-r1-32b",
    "LOCAL_CONTEXT": "allam-7b",
    "ARABIC_DRAFTING": "qwen-72b-arabic",
    "CONSENSUS_REVIEW": "deepseek-r1-32b",
}


@dataclass(frozen=True)
class DataContext:
    trace_id: str
    jurisdiction: str = "KSA"
    environment: str = "production"
    data_class: str = "INTERNAL"
    contains_pii: bool = False

    def to_api(self) -> dict[str, object]:
        if not self.trace_id.strip():
            raise ValueError("trace_id must not be empty")
        if self.jurisdiction != "KSA":
            raise ValueError("only KSA jurisdiction is allowed for this adapter")
        if self.contains_pii and self.data_class == "PUBLIC":
            raise ValueError("PII cannot be classified as PUBLIC")
        return {
            "traceId": self.trace_id,
            "jurisdiction": self.jurisdiction,
            "environment": self.environment,
            "dataClass": self.data_class,
            "containsPII": self.contains_pii,
        }


@dataclass(frozen=True)
class QararToolRequest:
    prompt: str
    task_type: str
    agent_id: str
    model_id: str
    data_context: DataContext
    context: Mapping[str, str] = field(default_factory=dict)
    architecture: str = "DIRECT_TOOL_CALL"
    preferred_protocol: Optional[str] = None

    def to_api(self) -> dict[str, object]:
        if self.task_type not in TASK_MODEL_MAP:
            raise ValueError(f"unsupported task_type: {self.task_type}")
        if self.model_id not in SOVEREIGN_MODEL_IDS:
            raise ValueError(f"unsupported model_id: {self.model_id}")
        if TASK_MODEL_MAP[self.task_type] != self.model_id and self.task_type != "CONSENSUS_REVIEW":
            raise ValueError(f"{self.model_id} is not approved for {self.task_type}")
        if not self.prompt.strip():
            raise ValueError("prompt must not be empty")
        if not self.agent_id.strip():
            raise ValueError("agent_id must not be empty")

        payload: dict[str, object] = {
            "traceId": self.data_context.trace_id,
            "agentId": self.agent_id,
            "taskType": self.task_type,
            "modelId": self.model_id,
            "architecture": self.architecture,
            "prompt": self.prompt,
            "context": [
                {"key": key, "value": value}
                for key, value in sorted(self.context.items(), key=lambda item: item[0])
            ],
            "dataContext": self.data_context.to_api(),
        }
        if self.preferred_protocol is not None:
            payload["preferredProtocol"] = self.preferred_protocol
        return payload


@dataclass(frozen=True)
class QararToolResponse:
    text: str
    confidence: float
    trace_id: str
    model_id: str
    protocol: str
    escalated: bool
    sources: Sequence[Mapping[str, object]]

    @classmethod
    def from_api(cls, raw: Mapping[str, object], fallback_trace_id: str, fallback_model_id: str) -> "QararToolResponse":
        text = raw.get("text")
        confidence = raw.get("confidence")
        protocol = raw.get("protocol", "ACP")
        escalated = raw.get("escalated", False)
        sources = raw.get("sources", [])

        if not isinstance(text, str):
            raise ValueError("Qarar response text must be a string")
        if not isinstance(confidence, (int, float)):
            raise ValueError("Qarar response confidence must be numeric")
        if not isinstance(protocol, str):
            raise ValueError("Qarar response protocol must be a string")
        if not isinstance(escalated, bool):
            raise ValueError("Qarar response escalated must be a boolean")
        if not isinstance(sources, list):
            raise ValueError("Qarar response sources must be a list")

        return cls(
            text=text,
            confidence=float(confidence),
            trace_id=str(raw.get("traceId", fallback_trace_id)),
            model_id=str(raw.get("modelId", fallback_model_id)),
            protocol=protocol,
            escalated=escalated,
            sources=[item for item in sources if isinstance(item, Mapping)],
        )


class QararSovereignToolClient:
    def __init__(self, base_url: str, token: Optional[str], timeout_seconds: float = 30.0) -> None:
        normalized = base_url.rstrip("/")
        if not normalized:
            raise ValueError("QARAR_API_BASE_URL is required")
        self._base_url = normalized
        self._token = token
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "QararSovereignToolClient":
        load_dotenv()
        return cls(
            base_url=os.getenv("QARAR_API_BASE_URL", ""),
            token=os.getenv("QARAR_API_TOKEN"),
            timeout_seconds=float(os.getenv("QARAR_API_TIMEOUT_SECONDS", "30")),
        )

    def complete(self, request: QararToolRequest) -> QararToolResponse:
        endpoint = f"{self._base_url}/api/sovereign/swarms/complete"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
        }
        if self._token:
            headers["authorization"] = f"Bearer {self._token}"

        response = requests.post(
            endpoint,
            data=json.dumps(request.to_api(), ensure_ascii=False),
            headers=headers,
            timeout=self._timeout_seconds,
        )
        response.raise_for_status()
        raw = response.json()
        if not isinstance(raw, Mapping):
            raise ValueError("Qarar API response must be an object")
        return QararToolResponse.from_api(
            raw=raw,
            fallback_trace_id=request.data_context.trace_id,
            fallback_model_id=request.model_id,
        )


def create_qarar_tool(
    task_type: str,
    agent_id: str,
    data_class: str = "INTERNAL",
    contains_pii: bool = False,
    environment: str = "production",
    context: Optional[Mapping[str, str]] = None,
) -> Callable[[str], str]:
    client = QararSovereignToolClient.from_environment()
    model_id = TASK_MODEL_MAP.get(task_type)
    if model_id is None:
        raise ValueError(f"unsupported task_type: {task_type}")

    def tool(prompt: str) -> str:
        trace_id = f"swarms-{uuid.uuid4().hex}"
        data_context = DataContext(
            trace_id=trace_id,
            environment=environment,
            data_class=data_class,
            contains_pii=contains_pii,
        )
        response = client.complete(
            QararToolRequest(
                prompt=prompt,
                task_type=task_type,
                agent_id=agent_id,
                model_id=model_id,
                data_context=data_context,
                context=context or {},
            )
        )
        return response.text

    tool.__name__ = f"qarar_{task_type.lower()}"
    tool.__doc__ = f"Qarar sovereign model tool for {task_type}."
    return tool
