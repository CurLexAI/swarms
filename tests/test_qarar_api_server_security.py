"""Security regression tests for the Qarar workspace gateway."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import anyio
import pytest
from fastapi import HTTPException


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / ".agents" / "mcp" / "qarar_api_server.py"
)


class StubInferencePort:
    """Inference stub that records payloads without external calls."""

    def __init__(self, result: Any | None = None) -> None:
        """Initialize the stub.

        Args:
            result: Response returned from ``infer``.
        """

        self.result = "stubbed" if result is None else result
        self.payloads: list[dict[str, Any]] = []

    async def infer(self, payload: dict[str, Any]) -> Any:
        """Record and return a deterministic response.

        Args:
            payload: Gateway payload.

        Returns:
            Configured stub result.
        """

        self.payloads.append(payload)
        return self.result


def load_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    environment: str = "development",
    allow_origins: str = "http://localhost:3000",
    token: str | None = None,
    max_read_bytes: int | None = None,
    max_write_bytes: int | None = None,
) -> ModuleType:
    """Load the gateway module under isolated environment settings.

    Args:
        tmp_path: Temporary directory from pytest.
        monkeypatch: Pytest monkeypatch helper.
        environment: ENVIRONMENT value for module import.
        allow_origins: ALLOW_ORIGINS value for module import.
        token: Optional QARAR_API_TOKEN value.
        max_read_bytes: Optional small read limit for regression tests.
        max_write_bytes: Optional small write limit for regression tests.

    Returns:
        Imported gateway module.
    """

    module_name = f"qarar_api_server_security_{len(sys.modules)}"
    monkeypatch.setenv("ENVIRONMENT", environment)
    monkeypatch.setenv("QARAR_WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.setenv("ALLOW_ORIGINS", allow_origins)
    monkeypatch.delenv("QARAR_ENABLE_WORKSPACE_WRITE", raising=False)
    if token is None:
        monkeypatch.delenv("QARAR_API_TOKEN", raising=False)
    else:
        monkeypatch.setenv("QARAR_API_TOKEN", token)
    if max_read_bytes is None:
        monkeypatch.delenv("QARAR_MAX_READ_BYTES", raising=False)
    else:
        monkeypatch.setenv("QARAR_MAX_READ_BYTES", str(max_read_bytes))
    if max_write_bytes is None:
        monkeypatch.delenv("QARAR_MAX_WRITE_BYTES", raising=False)
    else:
        monkeypatch.setenv("QARAR_MAX_WRITE_BYTES", str(max_write_bytes))

    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def qarar_module(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load a development-mode gateway module with an isolated workspace."""

    return load_module(tmp_path, monkeypatch)


def test_traversal_blocked(qarar_module: ModuleType) -> None:
    """The gateway must reject parent-directory traversal."""

    with pytest.raises(HTTPException) as exc_info:
        qarar_module.resolve_workspace_path("../outside.txt")

    assert exc_info.value.status_code == 403


def test_prefix_bypass_blocked(tmp_path: Path, qarar_module: ModuleType) -> None:
    """A sibling path with a workspace-like prefix must not pass containment."""

    evil_dir = tmp_path / "workspace_evil"
    evil_dir.mkdir()
    (evil_dir / "file.txt").write_text("evil", encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        qarar_module.resolve_workspace_path("../workspace_evil/file.txt")

    assert exc_info.value.status_code == 403


def test_symlink_escape_blocked(tmp_path: Path, qarar_module: ModuleType) -> None:
    """Symlinks that resolve outside the workspace must be rejected."""

    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    link = qarar_module.WORKSPACE_DIR / "link.md"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink unavailable in this environment: {exc}")

    with pytest.raises(HTTPException) as exc_info:
        qarar_module.resolve_workspace_path("link.md")

    assert exc_info.value.status_code == 403


def test_env_file_blocked(qarar_module: ModuleType) -> None:
    """Real environment files must be blocked even when they exist."""

    (qarar_module.WORKSPACE_DIR / ".env").write_text("SAFE=value", encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        qarar_module.resolve_workspace_path(".env")

    assert exc_info.value.status_code == 403


def test_disallowed_read_extension_blocked(qarar_module: ModuleType) -> None:
    """Reads must enforce ALLOWED_READ_EXTENSIONS."""

    target = qarar_module.WORKSPACE_DIR / "payload.bin"
    target.write_text("payload", encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        qarar_module.read_text_file_safely(target)

    assert exc_info.value.status_code == 403


def test_disallowed_write_extension_blocked(
    qarar_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enabled writes must still enforce ALLOWED_WRITE_EXTENSIONS."""

    monkeypatch.setenv("QARAR_ENABLE_WORKSPACE_WRITE", "true")

    with pytest.raises(HTTPException) as exc_info:
        anyio.run(
            qarar_module.write_file,
            qarar_module.FileOperationRequest(file_path="payload.bin", content="payload"),
        )

    assert exc_info.value.status_code == 403
    assert not (qarar_module.WORKSPACE_DIR / "payload.bin").exists()


def test_max_read_bytes_enforced_before_read_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oversized files must be rejected before attempting read_text."""

    module = load_module(tmp_path, monkeypatch, max_read_bytes=3)
    target = module.WORKSPACE_DIR / "large.txt"
    target.write_text("four", encoding="utf-8")

    def fail_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        raise AssertionError("read_text should not be called for oversized files")

    monkeypatch.setattr(Path, "read_text", fail_read_text)

    with pytest.raises(HTTPException) as exc_info:
        module.read_text_file_safely(target)

    assert exc_info.value.status_code == 413


def test_non_utf8_read_blocked(qarar_module: ModuleType) -> None:
    """Binary or non-UTF-8 content must not be returned as text."""

    target = qarar_module.WORKSPACE_DIR / "binary.txt"
    target.write_bytes(b"\xff\xfe\x00")

    with pytest.raises(HTTPException) as exc_info:
        qarar_module.read_text_file_safely(target)

    assert exc_info.value.status_code == 415


def test_secret_like_content_blocked_before_modal_context(
    qarar_module: ModuleType,
) -> None:
    """Secret-like file content must not be injected into the Modal prompt."""

    secret_value = "a" * 32
    target = qarar_module.WORKSPACE_DIR / "secret.md"
    target.write_text(f"api_key = {secret_value}", encoding="utf-8")
    stub = StubInferencePort(result={"response": "ok"})

    response = anyio.run(
        qarar_module.chat,
        qarar_module.ChatRequest(message="Summarize", files=["secret.md"]),
        stub,
    )

    assert response["status"] == "success"
    assert response["files_used"] == []
    assert len(stub.payloads) == 1
    assert secret_value not in stub.payloads[0]["prompt"]
    assert "secret.md" not in stub.payloads[0]["files_used"]


def test_modal_plain_string_response_handled(qarar_module: ModuleType) -> None:
    """Plain string Modal responses must be normalized safely."""

    stub = StubInferencePort(result="plain response")

    response = anyio.run(
        qarar_module.chat,
        qarar_module.ChatRequest(message="Hello", files=[]),
        stub,
    )

    assert response == {
        "status": "success",
        "response": "plain response",
        "files_used": [],
    }


def test_prod_token_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Production aliases must fail closed without QARAR_API_TOKEN."""

    with pytest.raises(RuntimeError, match="QARAR_API_TOKEN is required"):
        load_module(tmp_path, monkeypatch, environment="prod")


def test_docs_disabled_in_prod_and_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both production aliases must disable interactive docs."""

    prod_module = load_module(tmp_path, monkeypatch, environment="prod", token="token")
    assert prod_module.app.docs_url is None
    assert prod_module.app.redoc_url is None

    production_module = load_module(
        tmp_path,
        monkeypatch,
        environment="production",
        token="token",
    )
    assert production_module.app.docs_url is None
    assert production_module.app.redoc_url is None


@pytest.mark.parametrize("environment", ["prod", "production"])
def test_cors_wildcard_rejected_in_prod_and_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    """Production aliases must reject wildcard CORS origins."""

    with pytest.raises(RuntimeError, match="ALLOW_ORIGINS"):
        load_module(
            tmp_path,
            monkeypatch,
            environment=environment,
            allow_origins="*",
            token="token",
        )


def test_max_write_bytes_enforced_when_write_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enabled writes must still enforce the byte-size write limit."""

    module = load_module(tmp_path, monkeypatch, max_write_bytes=3)
    monkeypatch.setenv("QARAR_ENABLE_WORKSPACE_WRITE", "true")

    with pytest.raises(HTTPException) as exc_info:
        anyio.run(
            module.write_file,
            module.FileOperationRequest(file_path="large.md", content="üü"),
        )

    assert exc_info.value.status_code == 413
    assert not (module.WORKSPACE_DIR / "large.md").exists()
