#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Public-only Hugging Face coding model smoke test.

This harness must only send synthetic/public snippets.
It must not read repository source code, legal corpora, customer data, or secrets
other than the Hugging Face read token needed to call the public smoke endpoint.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_CONFIGS = (
    (
        "mihwar",
        "MIHWAR_HF_MODEL_ID",
        "MIHWAR_HF_PROVIDER",
        "deepseek-ai/DeepSeek-Coder-V2-Instruct",
    ),
    (
        "bayyinah",
        "BAYYINAH_HF_MODEL_ID",
        "BAYYINAH_HF_PROVIDER",
        "Qwen/Qwen2.5-Coder-32B-Instruct",
    ),
)

FORBIDDEN_PATTERNS = (
    "sk-",
    "api_key",
    "bearer ",
    "begin rsa",
    "private key",
    "password",
    "token",
    "contract",
    "confidential",
    "customer",
    "client",
    "عميل",
    "سري",
    "سر",
    "قانون",
    "محامي",
)


def load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a YAML object.")
    return data


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a JSON object.")
    return data


def assert_public_fixture(task: dict[str, Any]) -> None:
    serialized = json.dumps(task, ensure_ascii=False).lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in serialized:
            raise RuntimeError(f"Synthetic fixture contains forbidden term: {pattern}")


def model_id(env_name: str, provider_env_name: str, default: str) -> str:
    model = os.environ.get(env_name, default).strip() or default
    provider = os.environ.get(provider_env_name, "").strip()
    if provider and ":" not in model:
        return f"{model}:{provider}"
    return model


def call_hf(
    token: str, model: str, task: dict[str, Any], max_tokens: int, agent: str
) -> str:
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    f"You are the {agent} coding agent. "
                    "Only discuss style, type hints, correctness, or basic security. "
                    "Do not mention legal, customer, confidential, or secret material."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(task, ensure_ascii=False),
            },
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": False,
    }
    request = urllib.request.Request(
        HF_ROUTER_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(
            f"Hugging Face request failed: HTTP {exc.code}: {body_text}"
        ) from exc

    return _extract_content(payload)


def _extract_content(payload: Any) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "Unexpected Hugging Face chat completion response shape."
        ) from exc

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Empty model response.")
    return content.strip()


def _forbidden_terms(allowlist: dict[str, Any]) -> list[str]:
    terms = set(FORBIDDEN_PATTERNS)
    configured = allowlist.get("smoke", {}).get("forbidden_terms", [])
    terms.update(str(item).lower() for item in configured)
    return sorted(filter(None, terms))


def _assert_topic_present(lowered: str, allowlist: dict[str, Any]) -> None:
    allowed_topics = allowlist.get("smoke", {}).get("allowed_topics", [])
    if not isinstance(allowed_topics, list) or not allowed_topics:
        raise RuntimeError("Allowlist must define smoke.allowed_topics.")
    if not any(str(topic).lower() in lowered for topic in allowed_topics):
        raise RuntimeError("Response did not mention any allowed topic.")


def check_response(text: str, allowlist: dict[str, Any]) -> None:
    lowered = text.lower()
    for term in _forbidden_terms(allowlist):
        if term in lowered:
            raise RuntimeError(f"Forbidden response pattern detected: {term}")
    _assert_topic_present(lowered, allowlist)


def main() -> int:
    token = os.environ.get("HF_TOKEN", "").strip() or os.environ.get(
        "HF_READ_TOKEN", ""
    ).strip()
    if not token:
        # Missing secret is not a code defect: degrade to SKIPPED, never to a
        # false pass. Matches agent-review.yml's SKIPPED_UNVERIFIED convention.
        print("HF_TOKEN is not configured — skipping live calls.")
        print("SKIPPED_UNVERIFIED")
        return 0

    allowlist = load_yaml(Path(".github/smoke_allowlist.yml"))
    max_tokens = int(allowlist.get("smoke", {}).get("max_tokens", 150))

    task = load_json(Path("tests/fixtures/synthetic_public_task.json"))
    assert_public_fixture(task)

    print("HF public coding smoke: starting")

    verified: list[str] = []
    for agent, env_name, provider_env_name, default in MODEL_CONFIGS:
        model = model_id(env_name, provider_env_name, default)
        print(f"agent: {agent}")
        print(f"model: {model}")
        response = call_hf(
            token=token,
            model=model,
            task=task,
            max_tokens=max_tokens,
            agent=agent,
        )
        check_response(response, allowlist)
        print(f"{agent}_response_preview:", response[:220].replace("\n", " "))
        verified.append(agent)

    print(f"VERIFIED_HF_PUBLIC_SMOKE agents={','.join(verified)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
