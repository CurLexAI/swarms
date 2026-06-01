# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Qarar sovereign workspace API.

This module exposes a guarded FastAPI surface for reading bounded workspace
context and forwarding prompts to a protected Modal inference function. The API
is intentionally conservative: writes are disabled by default, paths are scoped
to one workspace root, literal-looking secrets are blocked, and production mode
requires an API token plus explicit CORS origins.
"""

from __future__ import annotations

import hmac
import importlib
import json
import os
import re
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

import anyio
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
WORKSPACE_DIR = Path(os.getenv("QARAR_WORKSPACE_DIR", "./workspace")).resolve()
MODAL_APP_NAME = os.getenv("QARAR_MODAL_APP_NAME", "qarar-sovereign-vllm-backend")
MODAL_FUNCTION_NAME = os.getenv("QARAR_MODAL_FUNCTION_NAME", "protected_vllm_inference")
ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOW_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
QARAR_API_TOKEN = os.getenv("QARAR_API_TOKEN", "").strip()

MAX_CONTEXT_FILES = int(os.getenv("QARAR_MAX_CONTEXT_FILES", "8"))
MAX_READ_BYTES = int(os.getenv("QARAR_MAX_READ_BYTES", str(256 * 1024)))
MAX_WRITE_BYTES = int(os.getenv("QARAR_MAX_WRITE_BYTES", str(512 * 1024)))
MAX_TOTAL_CONTEXT_BYTES = int(os.getenv("QARAR_MAX_TOTAL_CONTEXT_BYTES", str(512 * 1024)))

ALLOWED_READ_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".css",
    ".html",
    ".env.example",
}
ALLOWED_WRITE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".css",
    ".html",
}
FORBIDDEN_PATH_PARTS = {
    ".git",
    ".modal",
    ".ssh",
    "vault",
    "secrets",
    "secret",
    "private",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}
FORBIDDEN_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_ed25519",
    "known_hosts",
}
SECRET_LIKE_PATTERN = re.compile(
    r"""(?ix)
    (
        api[_-]?key|
        secret|
        access[_-]?token|
        refresh[_-]?token|
        private[_-]?key|
        password
    )
    \s*[:=]\s*
    ['"]?
    [A-Za-z0-9_\-./+=]{24,}
    ['"]?
    """
)

def is_production() -> bool:
    """Return whether the gateway is running in a production environment.

    Returns:
        True when ``ENVIRONMENT`` is ``prod`` or ``production``.
    """

    return ENVIRONMENT in {"prod", "production"}


if "*" in ALLOW_ORIGINS and is_production():
    raise RuntimeError(
        'Refusing to start in production with ALLOW_ORIGINS="*". '
        "Set explicit origins instead."
    )

if is_production() and not QARAR_API_TOKEN:
    raise RuntimeError("QARAR_API_TOKEN is required in production")

WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)


class ChatRequest(BaseModel):
    """Validated chat request with bounded file context.

    Attributes:
        message: User message to send to the protected inference adapter.
        files: Relative workspace file paths to include as context.
        temperature: Low-temperature generation setting for deterministic output.
        max_tokens: Upper bound for generated tokens requested from inference.
    """

    message: str = Field(..., min_length=1, max_length=20_000)
    files: list[str] = Field(default_factory=list, max_length=MAX_CONTEXT_FILES)
    temperature: float = Field(default=0.2, ge=0.0, le=0.2)
    max_tokens: int = Field(default=2048, ge=1, le=8192)

    @field_validator("files")
    @classmethod
    def validate_file_count(cls, files: list[str]) -> list[str]:
        """Validate the number of requested context files.

        Args:
            files: Relative workspace file paths supplied by the caller.

        Returns:
            The original list when it is within the configured limit.

        Raises:
            ValueError: If too many file paths are supplied.
        """

        if len(files) > MAX_CONTEXT_FILES:
            raise ValueError(f"Too many files. Max allowed: {MAX_CONTEXT_FILES}")
        return files


class FileOperationRequest(BaseModel):
    """Validated request for workspace file read or write operations.

    Attributes:
        file_path: Relative path inside the configured workspace root.
        content: Optional content for write operations.
    """

    file_path: str = Field(..., min_length=1, max_length=500)
    content: str | None = Field(default=None, max_length=MAX_WRITE_BYTES)

    @field_validator("file_path")
    @classmethod
    def validate_file_path_text(cls, value: str) -> str:
        """Reject NUL bytes before path resolution.

        Args:
            value: User-supplied relative path string.

        Returns:
            The original path string when it is syntactically safe.

        Raises:
            ValueError: If the path contains a NUL byte.
        """

        if "\x00" in value:
            raise ValueError("NUL byte is not allowed in file path")
        return value


class ModalInferencePort(Protocol):
    """Port for protected inference adapters."""

    async def infer(self, payload: dict[str, Any]) -> Any:
        """Run protected inference.

        Args:
            payload: Prompt and generation options to send to the adapter.

        Returns:
            Adapter-specific inference response.
        """


class ModalInferenceAdapter:
    """Modal-backed inference adapter for Qarar.

    The adapter is intentionally isolated behind ``ModalInferencePort`` so tests
    and future local backends can inject a mock implementation without changing
    route logic.
    """

    async def infer(self, payload: dict[str, Any]) -> Any:
        """Call the configured Modal function in a worker thread.

        Args:
            payload: Prompt and generation settings.

        Returns:
            Response returned by the Modal function.
        """

        return await anyio.to_thread.run_sync(
            lambda: get_modal_function().remote(payload)
        )


@lru_cache(maxsize=1)
def get_modal_function() -> Any:
    """Resolve and cache the configured Modal function reference.

    Returns:
        Modal function handle resolved from the configured app and function name.
    """

    modal_module = importlib.import_module("modal")
    if hasattr(modal_module.Function, "from_name"):
        return modal_module.Function.from_name(MODAL_APP_NAME, MODAL_FUNCTION_NAME)
    return modal_module.Function.lookup(MODAL_APP_NAME, MODAL_FUNCTION_NAME)


async def require_optional_api_token(
    x_qarar_api_key: str | None = Header(default=None),
) -> None:
    """Enforce the API token when one is configured.

    Args:
        x_qarar_api_key: Caller-provided API key header.

    Raises:
        HTTPException: If a token is configured and the supplied value is
            missing or invalid.
    """

    if not QARAR_API_TOKEN:
        return
    if not x_qarar_api_key or not hmac.compare_digest(
        x_qarar_api_key, QARAR_API_TOKEN
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Qarar API token",
        )


def resolve_workspace_path(user_path: str) -> Path:
    """Resolve a relative workspace path and enforce path boundaries.

    Args:
        user_path: Caller-supplied path relative to ``WORKSPACE_DIR``.

    Returns:
        Absolute resolved path inside ``WORKSPACE_DIR``.

    Raises:
        HTTPException: If the path is absolute, traverses outside the workspace,
            or targets a forbidden name or path component.
    """

    raw_path = Path(user_path)
    if raw_path.is_absolute():
        raise HTTPException(status_code=403, detail="Absolute paths are not allowed")

    candidate = (WORKSPACE_DIR / raw_path).resolve()
    try:
        relative = candidate.relative_to(WORKSPACE_DIR)
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail="Path traversal outside workspace is forbidden",
        ) from exc

    lower_parts = [part.lower() for part in relative.parts]
    lower_name = candidate.name.lower()
    if lower_name in FORBIDDEN_FILE_NAMES:
        raise HTTPException(status_code=403, detail="Access to this file is forbidden")
    if any(part in FORBIDDEN_PATH_PARTS for part in lower_parts):
        raise HTTPException(status_code=403, detail="Access to this path is forbidden")
    if lower_name.startswith(".env") and lower_name != ".env.example":
        raise HTTPException(status_code=403, detail="Environment files are forbidden")
    return candidate


def extension_of(path: Path) -> str:
    """Return the effective extension used by workspace allow-lists.

    Args:
        path: Path to classify.

    Returns:
        ``.env.example`` for that special allow-listed file, otherwise the
        lowercase suffix.
    """

    if path.name.lower() == ".env.example":
        return ".env.example"
    return path.suffix.lower()


def assert_read_allowed(path: Path) -> None:
    """Ensure a resolved workspace path is safe to read as bounded text.

    Args:
        path: Resolved target path inside ``WORKSPACE_DIR``.

    Raises:
        HTTPException: If the extension, existence, file type, or size check fails.
    """

    ext = extension_of(path)
    if ext not in ALLOWED_READ_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Reading files with extension '{ext or '[none]'}' is not allowed",
        )
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File does not exist",
        )
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Path is not a file",
        )
    size = path.stat().st_size
    if size > MAX_READ_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File is too large to read: {size} bytes",
        )


def assert_write_allowed(path: Path, content: str) -> None:
    """Ensure a resolved workspace path and content are safe to write.

    Args:
        path: Resolved target path inside ``WORKSPACE_DIR``.
        content: UTF-8 text content requested by the caller.

    Raises:
        HTTPException: If the extension, content size, or secret scan fails.
    """

    ext = extension_of(path)
    if ext not in ALLOWED_WRITE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Writing files with extension '{ext or '[none]'}' is not allowed",
        )
    content_size = len(content.encode("utf-8"))
    if content_size > MAX_WRITE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Content is too large to write: {content_size} bytes",
        )
    assert_no_secret_like_content(content)


def assert_allowed_extension(path: Path, allowed_extensions: set[str]) -> None:
    """Ensure a file extension is explicitly allowed.

    Args:
        path: Target file path.
        allowed_extensions: Set of accepted effective extensions.

    Raises:
        HTTPException: If the extension is not allow-listed.
    """

    if extension_of(path) not in allowed_extensions:
        raise HTTPException(status_code=403, detail="File extension is not allowed")


def assert_no_secret_like_content(content: str) -> None:
    """Block content that appears to contain literal credentials.

    Args:
        content: Text to scan.

    Raises:
        HTTPException: If a literal-looking secret, token, or password is found.
    """

    if SECRET_LIKE_PATTERN.search(content):
        raise HTTPException(
            status_code=403,
            detail="File appears to contain a literal secret/token/password",
        )


def read_text_file_safely(path: Path) -> str:
    """Read a resolved workspace file after all file gates pass.

    Args:
        path: Resolved workspace file path.

    Returns:
        UTF-8 text content.

    Raises:
        HTTPException: If the read gates fail, the file is not UTF-8 text, or
            the content appears to contain a secret.
    """

    assert_read_allowed(path)
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only UTF-8 text files are supported",
        ) from exc
    assert_no_secret_like_content(content)
    return content


def read_workspace_text(path: Path) -> str:
    """Backward-compatible wrapper for safe workspace text reads.

    Args:
        path: Resolved workspace file path.

    Returns:
        UTF-8 text content.
    """

    return read_text_file_safely(path)


def write_text_file_atomically(path: Path, content: str) -> None:
    """Atomically write UTF-8 text after all write gates pass.

    Args:
        path: Resolved workspace file path.
        content: UTF-8 text content to persist.

    Raises:
        HTTPException: If extension, size, or secret-content validation fails.
    """

    assert_write_allowed(path, content)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(path.parent),
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def normalize_modal_response(result: Any) -> dict[str, Any]:
    """Normalize Modal adapter output into the public chat response shape.

    Args:
        result: Adapter output, either a mapping or any plain value.

    Returns:
        A success response dictionary with a string ``response`` field.
    """

    if isinstance(result, dict):
        text = (
            result.get("answer")
            or result.get("response")
            or result.get("text")
            or result.get("content")
        )
        if text is not None:
            return {
                "status": "success",
                "response": str(text),
                "modal": {
                    key: value
                    for key, value in result.items()
                    if key not in {"answer", "response", "text", "content"}
                },
            }
        return {
            "status": "success",
            "response": json.dumps(result, ensure_ascii=False),
        }
    return {
        "status": "success",
        "response": str(result),
    }


def get_inference_port() -> ModalInferencePort:
    """Provide the default inference adapter dependency.

    Returns:
        Modal-backed inference adapter.
    """

    return ModalInferenceAdapter()


app = FastAPI(
    title="Qarar Sovereign Workspace API",
    version="1.0.0",
    docs_url=None if is_production() else "/docs",
    redoc_url=None if is_production() else "/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Qarar-API-Key"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return a local health response without touching external services.

    Returns:
        Service status metadata.
    """

    return {
        "status": "ok",
        "service": "qarar-workspace-api",
        "environment": ENVIRONMENT,
    }


@app.post("/api/chat", dependencies=[Depends(require_optional_api_token)])
async def chat(
    req: ChatRequest,
    inference_port: ModalInferencePort = Depends(get_inference_port),
) -> dict[str, Any]:
    """Send a bounded prompt and optional workspace context to inference.

    Args:
        req: Validated chat request.
        inference_port: Injected protected inference port.

    Returns:
        Normalized response payload with the relative files used.

    Raises:
        HTTPException: If the protected inference adapter fails.
    """

    context_parts: list[str] = []
    used_files: list[str] = []
    total_bytes = 0
    for file_path in req.files[:MAX_CONTEXT_FILES]:
        try:
            target = resolve_workspace_path(file_path)
            content = read_text_file_safely(target)
            size = len(content.encode("utf-8"))
            if total_bytes + size > MAX_TOTAL_CONTEXT_BYTES:
                break
            rel_path = target.relative_to(WORKSPACE_DIR).as_posix()
            used_files.append(rel_path)
            context_parts.append(f"\n--- FILE: {rel_path} ---\n{content}")
            total_bytes += size
        except HTTPException:
            continue

    context_text = "\n".join(context_parts) if context_parts else ""
    system_prompt = "You are Qarar, a sovereign Saudi legal and regulatory AI assistant."
    final_prompt = (
        f"{system_prompt}\n{context_text}\n\nUser: {req.message}"
        if context_text
        else f"{system_prompt}\n\nUser: {req.message}"
    )
    payload = {
        "prompt": final_prompt,
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
        "files_used": used_files,
    }

    try:
        result = await inference_port.infer(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Modal inference failed: {type(exc).__name__}",
        ) from exc

    response = normalize_modal_response(result)
    response["files_used"] = used_files
    return response


@app.get("/api/workspace/files", dependencies=[Depends(require_optional_api_token)])
async def list_files() -> dict[str, list[dict[str, int | str]]]:
    """List allowed workspace files without reading their contents.

    Returns:
        Sorted list of relative file paths and byte sizes.
    """

    files: list[dict[str, int | str]] = []
    for path in WORKSPACE_DIR.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(WORKSPACE_DIR).as_posix()
            target = resolve_workspace_path(rel)
            assert_read_allowed(target)
        except HTTPException:
            continue
        files.append({"path": rel, "size": path.stat().st_size})
    return {"files": sorted(files, key=lambda file_info: str(file_info["path"]))}


@app.post("/api/workspace/file/read", dependencies=[Depends(require_optional_api_token)])
async def read_file(req: FileOperationRequest) -> dict[str, str]:
    """Read one allowed workspace file.

    Args:
        req: Validated file operation request.

    Returns:
        Relative file path and UTF-8 content.
    """

    target = resolve_workspace_path(req.file_path)
    content = read_text_file_safely(target)
    return {"file_path": req.file_path, "content": content}


@app.post("/api/workspace/file/write", dependencies=[Depends(require_optional_api_token)])
async def write_file(req: FileOperationRequest) -> dict[str, str]:
    """Atomically write one allowed workspace file when explicitly enabled.

    Args:
        req: Validated file operation request.

    Returns:
        Write status and localized message.

    Raises:
        HTTPException: If workspace writes are disabled or content/path checks
            fail.
    """

    if os.getenv("QARAR_ENABLE_WORKSPACE_WRITE", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Workspace write API is disabled")

    target = resolve_workspace_path(req.file_path)
    content = req.content or ""
    write_text_file_atomically(target, content)

    return {"status": "success", "message": f"Updated {req.file_path}"}
