# SPDX-License-Identifier: MIT
# Licensed under MIT
"""
CurLexAI Coding Agents — Modal Deployment
==========================================
Two private coding agents deployed on Modal using vLLM.

Agent 1 — Mihwar:  DeepSeek-Coder-V2-Instruct (236B MoE) on 2x A100-80GB
Agent 2 — Bayyinah: Qwen2.5-Coder-32B-Instruct (32B) on 1x A100-80GB

Usage:
    modal deploy .agents/modal_app.py          # deploy both agents
    modal run .agents/modal_app.py             # smoke test both endpoints

Web endpoints (after deploy):
    POST <BAYYINAH_ENDPOINT>/review            # called by GitHub Actions
    POST <MIHWAR_ENDPOINT>/generate            # called by GitHub Actions

Environment secrets required in Modal dashboard:
    huggingface-secret  →  HF_TOKEN
    agent-api-secret    →  AGENT_API_TOKEN   (shared token for GitHub Actions auth)
"""

from __future__ import annotations

import hmac
import json
import os
import uuid
from typing import Optional

import modal
from fastapi import Header, HTTPException

# ── Shared base image ──────────────────────────────────────────────────────

vllm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "vllm>=0.6.0,<1.0.0",
        "transformers>=4.44.0",
        "accelerate>=0.33.0",
        "huggingface_hub>=0.24.0",
        "scipy>=1.11.0",
    )
)

# Lightweight image for web endpoint routing (no GPU/vLLM needed)
gateway_image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "fastapi>=0.110.0",
)

hf_secret = modal.Secret.from_name("huggingface-secret")
MAX_REVIEW_PAYLOAD_BYTES = 40000
MAX_GENERATE_PAYLOAD_BYTES = 120000
MAX_CONTEXT_BYTES = 8000

# ── Agent 1: MIHWAR ───────────────────────────────────────────────────────
# DeepSeek-Coder-V2-Instruct — strongest open-source coding model
# 236B MoE (21B parameters active per token)
# Requires 2x A100-80GB for tensor parallel inference

MIHWAR_MODEL = "deepseek-ai/DeepSeek-Coder-V2-Instruct"
MIHWAR_SYSTEM = (
    "You are Mihwar (المحور), a senior software architect agent. "
    "You plan, design, and generate production-quality code. "
    "Think step-by-step. Never truncate output. "
    "Declare which files you create or modify before generating them. "
    "Label every claim: VERIFIED / INFERRED / UNVERIFIED."
)

app = modal.App("curlexai-agents")


@app.cls(
    gpu="A100-80GB:2",
    image=vllm_image,
    secrets=[hf_secret],
    timeout=300,
    max_containers=1,
    min_containers=0,
)
class MihwarAgent:
    model_id: str = MIHWAR_MODEL

    @modal.enter()
    def load_model(self):
        from vllm import LLM, SamplingParams  # noqa: F401

        self.llm = LLM(
            model=self.model_id,
            tensor_parallel_size=2,
            max_model_len=32768,
            trust_remote_code=True,
            gpu_memory_utilization=0.92,
        )
        self.default_params = SamplingParams(
            temperature=0.1,
            top_p=0.95,
            max_tokens=8192,
        )

    @modal.method()
    def generate(self, user_message: str, max_tokens: int = 8192) -> dict:
        from vllm import SamplingParams

        params = (
            self.default_params
            if max_tokens == self.default_params.max_tokens
            else SamplingParams(
                temperature=self.default_params.temperature,
                top_p=self.default_params.top_p,
                max_tokens=max_tokens,
            )
        )

        prompt = _build_chat_prompt(
            system=MIHWAR_SYSTEM,
            user=user_message,
            model_family="deepseek",
        )

        outputs = self.llm.generate([prompt], params)
        text = outputs[0].outputs[0].text.strip()

        return {
            "agent": "mihwar",
            "model": self.model_id,
            "response": text,
            "finish_reason": outputs[0].outputs[0].finish_reason,
            "tokens_generated": len(outputs[0].outputs[0].token_ids),
        }

    @modal.method()
    def review_and_generate(
        self, task: str, context_files=None
    ) -> dict:
        """
        Full coding task: receive task description + optional file context,
        return implementation plan and generated code.
        """
        file_block = ""
        if context_files:
            file_block = "\n\nEXISTING FILES:\n"
            for path, content in context_files.items():
                file_block += f"\n--- {path} ---\n{content}\n"

        message = f"TASK:\n{task}{file_block}"
        return self.generate(message)


# ── Agent 2: BAYYINAH ─────────────────────────────────────────────────────
# Qwen2.5-Coder-32B-Instruct — top open-source model for code review
# 32B dense model, Apache 2.0, 131K context
# Requires 1x A100-80GB

BAYYINAH_MODEL = "Qwen/Qwen2.5-Coder-32B-Instruct"
BAYYINAH_SYSTEM = (
    "You are Bayyinah (البيّنة), a code review and validation agent. "
    "You find bugs, security issues, and logical errors with precision. "
    "Review every line. Cite exact file:line for every finding. "
    "Use severity: CRITICAL / HIGH / MEDIUM / LOW / INFO. "
    "Output format:\n"
    "VERDICT: APPROVE | REQUEST_CHANGES\n"
    "FINDINGS: [severity] file:line — description\n"
    "BLOCKERS: [list or NONE]"
)

@app.cls(
    gpu="A100-80GB",
    image=vllm_image,
    secrets=[hf_secret],
    timeout=120,
    max_containers=4,
    min_containers=0,
)
class BayyinahAgent:
    model_id: str = BAYYINAH_MODEL

    @modal.enter()
    def load_model(self):
        from vllm import LLM, SamplingParams  # noqa: F401

        self.llm = LLM(
            model=self.model_id,
            tensor_parallel_size=1,
            max_model_len=32768,
            trust_remote_code=True,
            gpu_memory_utilization=0.90,
        )

    @modal.method()
    def review(self, code_or_diff: str, context: str = "") -> dict:
        """
        Review a code snippet, full file, or git diff.
        Returns structured findings with severity labels.
        """
        from vllm import SamplingParams

        params = SamplingParams(
            temperature=0.0,
            top_p=1.0,
            max_tokens=4096,
        )

        review_prompt = (
            f"Review the following code for bugs, security issues, "
            f"and correctness.\n\n"
        )
        if context:
            review_prompt += f"CONTEXT:\n{context}\n\n"
        review_prompt += f"CODE TO REVIEW:\n{code_or_diff}"

        prompt = _build_chat_prompt(
            system=BAYYINAH_SYSTEM,
            user=review_prompt,
            model_family="qwen",
        )

        outputs = self.llm.generate([prompt], params)
        text = outputs[0].outputs[0].text.strip()

        verdict = "REQUEST_CHANGES"
        if "VERDICT: APPROVE" in text.upper():
            verdict = "APPROVE"

        return {
            "agent": "bayyinah",
            "model": self.model_id,
            "verdict": verdict,
            "report": text,
            "finish_reason": outputs[0].outputs[0].finish_reason,
            "tokens_generated": len(outputs[0].outputs[0].token_ids),
        }

# ── Prompt builders ────────────────────────────────────────────────────────

def _build_chat_prompt(system: str, user: str, model_family: str) -> str:
    """
    Build a chat-formatted prompt for the given model family.
    Uses the correct chat template for each model.
    """
    if model_family == "deepseek":
        return (
            f"<｜begin▁of▁sentence｜>{system}\n"
            f"<｜User｜>{user}"
            f"<｜Assistant｜>"
        )
    elif model_family == "qwen":
        return (
            f"<|im_start|>system\n{system}<|im_end|>\n"
            f"<|im_start|>user\n{user}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
    else:
        return f"### System:\n{system}\n\n### User:\n{user}\n\n### Assistant:\n"


def _make_request_id(header_value: str | None) -> str:
    if header_value:
        trimmed = header_value.strip()[:128]
        if trimmed:
            return trimmed
    return str(uuid.uuid4())


def _verify_bearer_token(authorization: str | None) -> None:
    expected_token = os.environ.get("AGENT_API_TOKEN", "")
    if not expected_token:
        raise HTTPException(status_code=503, detail="agent_api_token_missing")

    if not authorization:
        raise HTTPException(status_code=401, detail="missing_authorization")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="invalid_authorization_scheme")

    if not hmac.compare_digest(token, expected_token):
        raise HTTPException(status_code=401, detail="invalid_token")


def _limit_payload_bytes(payload: dict, max_bytes: int) -> None:
    raw = json.dumps(payload, ensure_ascii=False)
    if len(raw.encode("utf-8")) > max_bytes:
        raise HTTPException(status_code=413, detail="payload_too_large")


def _trimmed_text(value: object, max_bytes: int) -> str:
    text = str(value or "")
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


# ── Web endpoints (called by GitHub Actions) ───────────────────────────────
#
# After `modal deploy .agents/modal_app.py`, Modal provides stable HTTPS URLs.
# Copy those URLs into GitHub repository secrets:
#   BAYYINAH_ENDPOINT  →  the URL for bayyinah-review
#   MIHWAR_ENDPOINT    →  the URL for mihwar-generate
#   AGENT_API_TOKEN    →  any strong random string (openssl rand -hex 32)

api_secret = modal.Secret.from_name("agent-api-secret")


@app.function(
    image=gateway_image,
    secrets=[hf_secret, api_secret],
    timeout=180,
    min_containers=0,
)
@modal.fastapi_endpoint(method="POST", label="bayyinah-review")
def bayyinah_review_web(
    payload: dict,
    authorization: Optional[str] = Header(default=None),
    x_request_id: Optional[str] = Header(default=None),
) -> dict:
    """
    HTTP POST endpoint for Bayyinah.
    Called by GitHub Actions on every PR using Authorization: Bearer.
    """
    request_id = _make_request_id(x_request_id)
    _verify_bearer_token(authorization)
    _limit_payload_bytes(payload, MAX_REVIEW_PAYLOAD_BYTES)

    result = BayyinahAgent().review.remote(
        _trimmed_text(payload.get("code"), MAX_REVIEW_PAYLOAD_BYTES),
        _trimmed_text(payload.get("context"), MAX_CONTEXT_BYTES),
    )
    result["request_id"] = request_id
    return result


@app.function(
    image=gateway_image,
    secrets=[hf_secret, api_secret],
    timeout=360,
    min_containers=0,
)
@modal.fastapi_endpoint(method="POST", label="mihwar-generate")
def mihwar_generate_web(
    payload: dict,
    authorization: Optional[str] = Header(default=None),
    x_request_id: Optional[str] = Header(default=None),
) -> dict:
    """
    HTTP POST endpoint for Mihwar.
    Called by GitHub Actions using Authorization: Bearer.
    """
    request_id = _make_request_id(x_request_id)
    _verify_bearer_token(authorization)
    _limit_payload_bytes(payload, MAX_GENERATE_PAYLOAD_BYTES)

    context_files = payload.get("context_files")
    if not isinstance(context_files, dict):
        context_files = {}

    sanitized_context_files = {
        str(path): _trimmed_text(content, MAX_CONTEXT_BYTES)
        for path, content in context_files.items()
    }

    result = MihwarAgent().review_and_generate.remote(
        _trimmed_text(payload.get("task"), MAX_GENERATE_PAYLOAD_BYTES),
        sanitized_context_files,
    )
    result["request_id"] = request_id
    return result


# ── Smoke test ─────────────────────────────────────────────────────────────

@app.local_entrypoint()
def test():
    """
    Smoke test for Mihwar.
    Usage: modal run .agents/modal_app.py
    """
    print("=== Testing Mihwar (DeepSeek-Coder-V2-Instruct) ===")
    mihwar = MihwarAgent()
    result = mihwar.generate.remote(
        "Write a Python function that checks if a string is a valid Arabic name. "
        "Include type hints and a brief docstring."
    )
    print(f"Agent:  {result['agent']}")
    print(f"Tokens: {result['tokens_generated']}")
    print(f"Output:\n{result['response'][:500]}")


@app.local_entrypoint()
def test_bayyinah():
    """
    Smoke test for Bayyinah.
    Usage: modal run .agents/modal_app.py::test_bayyinah
    """
    print("=== Testing Bayyinah (Qwen2.5-Coder-32B-Instruct) ===")
    bayyinah = BayyinahAgent()
    sample_code = """
def is_valid_arabic_name(name: str) -> bool:
    import re
    pattern = r'^[\\u0600-\\u06FF\\s]{2,50}$'
    return bool(re.match(pattern, name))
"""
    review = bayyinah.review.remote(sample_code)
    print(f"Agent:   {review['agent']}")
    print(f"Verdict: {review['verdict']}")
    print(f"Report:\n{review['report'][:500]}")


@app.local_entrypoint()
def test_mihwar():
    """
    Alias smoke test for Mihwar.
    Usage: modal run .agents/modal_app.py::test_mihwar
    """
    test()
