"""Tests for the Qarar sovereign workspace API helpers and handlers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import anyio
import pytest
from fastapi import HTTPException


class StubInferencePort:
    """Inference port stub that records payloads without external calls."""

    def __init__(self) -> None:
        """Initialize an empty payload log."""

        self.payloads: list[dict[str, Any]] = []

    async def infer(self, payload: dict[str, Any]) -> dict[str, str]:
        """Return a deterministic response for chat route tests.

        Args:
            payload: Payload sent by the route.

        Returns:
            Deterministic response payload.
        """

        self.payloads.append(payload)
        return {"response": "stubbed"}


@pytest.fixture()
def qarar_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load the API module with an isolated workspace.

    Args:
        tmp_path: Temporary directory provided by pytest.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        Imported API module configured for the temporary workspace.
    """

    module_name = "qarar_api_server_under_test"
    module_path = (
        Path(__file__).resolve().parents[1]
        / ".agents"
        / "mcp"
        / "qarar_api_server.py"
    )
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("QARAR_WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.setenv("ALLOW_ORIGINS", "http://localhost:3000")
    monkeypatch.delenv("QARAR_API_TOKEN", raising=False)
    monkeypatch.delenv("QARAR_ENABLE_WORKSPACE_WRITE", raising=False)
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_workspace_path_blocks_traversal(qarar_module: ModuleType) -> None:
    """Path resolution must reject traversal outside the workspace."""

    with pytest.raises(HTTPException) as exc_info:
        qarar_module.resolve_workspace_path("../outside.txt")

    assert exc_info.value.status_code == 403


def test_read_workspace_text_blocks_secret_like_content(qarar_module: ModuleType) -> None:
    """Workspace reads must not return literal-looking secrets."""

    target = qarar_module.WORKSPACE_DIR / "safe.txt"
    target.write_text("api_key = '" + "a" * 32 + "'", encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        qarar_module.read_workspace_text(target)

    assert exc_info.value.status_code == 403


def test_read_workspace_text_enforces_extension_allowlist(qarar_module: ModuleType) -> None:
    """Workspace reads must reject non-allow-listed extensions."""

    target = qarar_module.WORKSPACE_DIR / "archive.bin"
    target.write_text("not secret", encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        qarar_module.read_workspace_text(target)

    assert exc_info.value.status_code == 403


def test_chat_uses_only_allowed_context_files(qarar_module: ModuleType) -> None:
    """Chat should inject safe context and skip forbidden workspace files."""

    async def run_case() -> dict[str, Any]:
        safe = qarar_module.WORKSPACE_DIR / "safe.md"
        unsafe = qarar_module.WORKSPACE_DIR / ".env"
        safe.write_text("Safe context", encoding="utf-8")
        unsafe.write_text("TOKEN=" + "b" * 32, encoding="utf-8")
        stub = StubInferencePort()

        response = await qarar_module.chat(
            qarar_module.ChatRequest(message="Summarize", files=["safe.md", ".env"]),
            inference_port=stub,
        )
        return {"response": response, "payloads": stub.payloads}

    result = anyio.run(run_case)

    assert result["response"] == {
        "status": "success",
        "response": "stubbed",
        "modal": {},
        "files_used": ["safe.md"],
    }
    assert len(result["payloads"]) == 1
    assert "Safe context" in result["payloads"][0]["prompt"]
    assert ".env" not in result["payloads"][0]["files_used"]


def test_write_file_disabled_by_default(qarar_module: ModuleType) -> None:
    """Workspace writes must be disabled unless explicitly enabled."""

    with pytest.raises(HTTPException) as exc_info:
        anyio.run(
            qarar_module.write_file,
            qarar_module.FileOperationRequest(file_path="draft.md", content="draft"),
        )

    assert exc_info.value.status_code == 403


def test_write_file_blocks_secret_when_enabled(
    qarar_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enabled writes must still reject literal-looking secrets."""

    monkeypatch.setenv("QARAR_ENABLE_WORKSPACE_WRITE", "true")

    with pytest.raises(HTTPException) as exc_info:
        anyio.run(
            qarar_module.write_file,
            qarar_module.FileOperationRequest(
                file_path="draft.md",
                content="password = " + "c" * 32,
            ),
        )

    assert exc_info.value.status_code == 403
    assert not (qarar_module.WORKSPACE_DIR / "draft.md").exists()


def test_require_optional_api_token_rejects_invalid_token(
    qarar_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured API tokens must be compared and enforced."""

    monkeypatch.setattr(qarar_module, "QARAR_API_TOKEN", "expected-token")

    with pytest.raises(HTTPException) as exc_info:
        anyio.run(qarar_module.require_optional_api_token, "wrong-token")

    assert exc_info.value.status_code == 401
