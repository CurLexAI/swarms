# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Tests for the Qarar sovereign workspace API helpers and handlers."""

from __future__ import annotations

import importlib.util
import os
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
    module_path = os.path.abspath(".agents/mcp/qarar_api_server.py")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.chdir(tmp_path)
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


def test_gateway_file_contract_exposes_workspace_and_short_aliases(
    qarar_module: ModuleType,
) -> None:
    """Gateway file routes must expose workspace-prefixed and short aliases."""

    routes_by_path = {route.path: route for route in qarar_module.app.routes}

    assert "/api/workspace/files" in routes_by_path
    assert "/api/workspace/file/read" in routes_by_path
    assert "/api/workspace/file/write" in routes_by_path
    assert "/api/files" in routes_by_path
    assert "/api/file/read" in routes_by_path
    assert "/api/file/write" in routes_by_path
    assert routes_by_path["/api/files"].endpoint is qarar_module.list_files
    assert routes_by_path["/api/file/read"].endpoint is qarar_module.read_file
    assert routes_by_path["/api/file/write"].endpoint is qarar_module.write_file


def test_short_files_alias_uses_list_files_handler(qarar_module: ModuleType) -> None:
    """Short file-list alias must share the list_files handler logic."""

    safe = qarar_module.WORKSPACE_DIR / "safe.md"
    forbidden = qarar_module.WORKSPACE_DIR / ".env"
    safe.write_text("Safe listing", encoding="utf-8")
    forbidden.write_text("SAFE=value", encoding="utf-8")

    response = anyio.run(qarar_module.list_files)

    assert response == {"files": [{"path": "safe.md", "size": 12}]}


def test_short_read_alias_uses_safe_file_reader(
    qarar_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Short read alias must route all reads through read_text_file_safely."""

    target = qarar_module.WORKSPACE_DIR / "safe.md"
    target.write_text("Original content", encoding="utf-8")
    observed_paths: list[Path] = []

    def spy_read_text_file_safely(path: Path) -> str:
        observed_paths.append(path)
        return "guarded content"

    monkeypatch.setattr(
        qarar_module,
        "read_text_file_safely",
        spy_read_text_file_safely,
    )
    response = anyio.run(
        qarar_module.read_file,
        qarar_module.FileOperationRequest(file_path="safe.md"),
    )

    assert response == {"file_path": "safe.md", "content": "guarded content"}
    assert observed_paths == [target]


def test_short_write_alias_checks_write_enablement(qarar_module: ModuleType) -> None:
    """Short write alias must share the write_file fail-closed handler logic."""

    with pytest.raises(HTTPException) as exc_info:
        anyio.run(
            qarar_module.write_file,
            qarar_module.FileOperationRequest(file_path="draft.md", content="draft"),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Workspace write API is disabled"
    assert not (qarar_module.WORKSPACE_DIR / "draft.md").exists()


def test_short_write_alias_uses_atomic_writer_when_enabled(
    qarar_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Short write alias must persist through write_text_file_atomically."""

    observed_writes: list[tuple[Path, str]] = []

    def spy_write_text_file_atomically(path: Path, content: str) -> None:
        observed_writes.append((path, content))

    monkeypatch.setenv("QARAR_ENABLE_WORKSPACE_WRITE", "true")
    monkeypatch.setattr(
        qarar_module,
        "write_text_file_atomically",
        spy_write_text_file_atomically,
    )
    response = anyio.run(
        qarar_module.write_file,
        qarar_module.FileOperationRequest(file_path="draft.md", content="draft"),
    )

    assert response == {"status": "success", "message": "Updated draft.md"}
    assert observed_writes == [(qarar_module.WORKSPACE_DIR / "draft.md", "draft")]


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
