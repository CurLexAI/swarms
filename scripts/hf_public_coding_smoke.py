#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Public-only Hugging Face coding model smoke test.

This harness must only send synthetic/public snippets.
It must not read repository source code, legal corpora, customer data, or secrets
other than the Hugging Face read token needed to call the public smoke endpoint.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct:fastest"

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


def read_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required but not configured.")
    return value


def load_yaml(path: Path) -> dict[str, Any]:
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
        if pattern and pattern in serialized:
            raise RuntimeError(
                f"Synthetic fixture contains forbidden term: {pattern}"
            )


def call_hf(token: str, model: str, task: dict[str, Any], max_tokens: int) -> str:
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a safe code reviewer. "
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

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "Unexpected Hugging Face chat completion response shape."
        ) from exc

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Empty model response.")

    return content.strip()


def check_response(text: str, allowlist: dict[str, Any]) -> None:
    lowered = text.lower()

    configured_forbidden = allowlist.get("smoke", {}).get("forbidden_terms", [])
    forbidden_terms = set(FORBIDDEN_PATTERNS)
    if isinstance(configured_forbidden, list):
        forbidden_terms.update(str(item).lower() for item in configured_forbidden)

    for pattern in forbidden_terms:
        if pattern and pattern in lowered:
            raise RuntimeError(f"Forbidden response pattern detected: {pattern}")

    allowed_topics = allowlist.get("smoke", {}).get("allowed_topics", [])
    if not isinstance(allowed_topics, list) or not allowed_topics:
        raise RuntimeError("Allowlist must define smoke.allowed_topics.")

    if not any(str(topic).lower() in lowered for topic in allowed_topics):
        raise RuntimeError("Response did not mention any allowed topic.")


def main() -> int:
    token = read_required_env("HF_READ_TOKEN")
    model = os.environ.get("HF_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL

    allowlist = load_yaml(Path(".github/smoke_allowlist.yml"))
    max_tokens = int(allowlist.get("smoke", {}).get("max_tokens", 150))

    task = load_json(Path("tests/fixtures/synthetic_public_task.json"))
    assert_public_fixture(task)

    print("HF public coding smoke: starting")
    print(f"model: {model}")

    response = call_hf(token=token, model=model, task=task, max_tokens=max_tokens)
    check_response(response, allowlist)

    print("response_preview:", response[:220].replace("\n", " "))
    print("VERIFIED_HF_PUBLIC_SMOKE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
