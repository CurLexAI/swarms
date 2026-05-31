# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Fail-closed Google Drive exporter for Qarar public artifacts.

The Drive service agent is intentionally scoped to PUBLIC operational
artifacts only. It validates classification, path ownership, file size,
magic bytes, archive member safety, PII, and secret-like material before
calling an injected uploader port. It never prints credentials or Drive
links and records only sanitized audit events.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import mimetypes
import os
import posixpath
import re
import tarfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Mapping, Protocol


DRIVE_FILE_SCOPE = "https://" "www.googleapis.com/auth/drive.file"
DEFAULT_CHUNK_SIZE = 1024 * 1024
TEXT_SAMPLE_BYTES = 1024 * 1024
ARCHIVE_TEXT_SAMPLE_BYTES = 256 * 1024
ALLOWED_CLASSIFICATION = "PUBLIC"
BLOCKED_CLASSIFICATIONS = frozenset({"INTERNAL", "CONFIDENTIAL", "RESTRICTED"})


class DriveAgentErrorCode(str, Enum):
    """Stable error codes returned by the fail-closed validator."""

    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
    CLASSIFICATION_BLOCKED = "CLASSIFICATION_BLOCKED"
    PATH_NOT_ALLOWED = "PATH_NOT_ALLOWED"
    UNSAFE_PATH = "UNSAFE_PATH"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    ARCHIVE_UNSAFE = "ARCHIVE_UNSAFE"
    SENSITIVE_CONTENT = "SENSITIVE_CONTENT"
    UPLOAD_FAILED = "UPLOAD_FAILED"


class DriveAgentError(Exception):
    """Typed exception raised for blocked Drive export attempts.

    Args:
        code: Stable machine-readable error code.
        message: Human-safe error message with no credentials or Drive links.
    """

    def __init__(self, code: DriveAgentErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ValidationResult:
    """Sanitized validation evidence for an upload candidate."""

    file_path: str
    sha256: str
    size_bytes: int
    classification: str
    mime_type: str
    archive_members_scanned: int


@dataclass(frozen=True)
class DriveUploadResult:
    """Structured result returned after a validated Drive upload.

    The Drive web link is intentionally omitted to avoid leaking sharing URLs
    into stdout, CI logs, or chat transcripts.
    """

    ok: bool
    file_id: str
    validation: ValidationResult
    audit_path: str


@dataclass(frozen=True)
class SensitiveFinding:
    """Represents a sensitive-content detector hit without raw value leakage."""

    kind: str
    location: str


class DriveUploader(Protocol):
    """Port implemented by Google Drive adapters or tests."""

    def upload(self, file_path: Path, *, mime_type: str) -> Mapping[str, str]:
        """Upload a validated file and return provider metadata.

        Args:
            file_path: Canonical path to the validated file.
            mime_type: Magic-byte-derived MIME type.

        Returns:
            Provider metadata. Only ``id`` is consumed by this module.
        """


class GoogleDriveUploader:
    """Google Drive adapter using a mounted service-account JSON secret file."""

    def __init__(self, service_account_file: Path, folder_id: str | None = None) -> None:
        """Initialize the Google Drive adapter.

        Args:
            service_account_file: Path to a mounted secret file containing the
                Google service-account JSON. Environment-variable key splitting
                is intentionally not supported.
            folder_id: Optional destination folder ID.
        """
        self.service_account_file = service_account_file
        self.folder_id = folder_id

    def upload(self, file_path: Path, *, mime_type: str) -> Mapping[str, str]:
        """Upload a file with the narrow ``drive.file`` scope.

        Args:
            file_path: Canonical path to the validated file.
            mime_type: Magic-byte-derived MIME type.

        Returns:
            Google Drive file metadata containing at least ``id``.
        """
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        credentials = service_account.Credentials.from_service_account_file(
            str(self.service_account_file), scopes=[DRIVE_FILE_SCOPE]
        )
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        metadata: dict[str, object] = {"name": file_path.name}
        if self.folder_id:
            metadata["parents"] = [self.folder_id]
        media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=True)
        return (
            service.files()
            .create(body=metadata, media_body=media, fields="id")
            .execute()
        )


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b", re.IGNORECASE)),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("generic_api_key", re.compile(r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token)\b\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{20,}")),
    ("google_service_account", re.compile(r'"type"\s*:\s*"service_account"|"private_key_id"\s*:', re.IGNORECASE)),
)

_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)),
    ("phone", re.compile(r"(?<!\d)(?:\+?966|0)?5\d{8}(?!\d)")),
    ("ksa_national_id", re.compile(r"(?<!\d)[12]\d{9}(?!\d)")),
    ("iban", re.compile(r"\bSA\d{2}[A-Z0-9]{18}\b", re.IGNORECASE)),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
)

_TEXT_MIME_TYPES = frozenset(
    {
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
        "application/x-ndjson",
        "application/xml",
        "text/xml",
        "application/yaml",
        "text/yaml",
    }
)

_ALLOWED_MIME_TYPES = _TEXT_MIME_TYPES | frozenset({"application/gzip"})

_EXTENSION_MIME_HINTS = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".xml": "application/xml",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".tar.gz": "application/gzip",
    ".tgz": "application/gzip",
}


def export_public_artifact(file_path: str | Path, uploader: DriveUploader) -> DriveUploadResult:
    """Validate and upload a PUBLIC Qarar artifact to Google Drive.

    Args:
        file_path: Candidate artifact path.
        uploader: Injected Drive uploader adapter.

    Returns:
        Structured upload result without a Drive web link.

    Raises:
        DriveAgentError: If configuration, validation, or upload fails.
    """
    config = _load_config_from_env()
    candidate = _canonical_candidate(file_path)
    validation = validate_public_artifact(candidate, config=config)
    try:
        provider_result = uploader.upload(candidate, mime_type=validation.mime_type)
    except Exception as exc:  # noqa: BLE001 - fail closed with typed public error.
        _write_audit_event(config.audit_log_path, "drive_upload_blocked", validation, "UPLOAD_FAILED")
        raise DriveAgentError(DriveAgentErrorCode.UPLOAD_FAILED, "Drive upload failed") from exc

    file_id = str(provider_result.get("id") or "").strip()
    if not file_id:
        _write_audit_event(config.audit_log_path, "drive_upload_blocked", validation, "UPLOAD_FAILED")
        raise DriveAgentError(DriveAgentErrorCode.UPLOAD_FAILED, "Drive upload did not return a file id")

    _write_audit_event(config.audit_log_path, "drive_upload_succeeded", validation, None)
    return DriveUploadResult(
        ok=True,
        file_id=file_id,
        validation=validation,
        audit_path=str(config.audit_log_path),
    )


def validate_public_artifact(file_path: Path, *, config: "DriveAgentConfig") -> ValidationResult:
    """Validate a PUBLIC artifact without uploading it.

    Args:
        file_path: Canonical candidate path.
        config: Fail-closed runtime configuration.

    Returns:
        Sanitized validation result.

    Raises:
        DriveAgentError: If any security gate fails.
    """
    if config.classification != ALLOWED_CLASSIFICATION:
        raise DriveAgentError(
            DriveAgentErrorCode.CLASSIFICATION_BLOCKED,
            "Only explicitly PUBLIC artifacts may be uploaded",
        )
    if file_path.is_symlink():
        raise DriveAgentError(DriveAgentErrorCode.UNSAFE_PATH, "Symlink uploads are blocked")
    if not file_path.is_file():
        raise DriveAgentError(DriveAgentErrorCode.FILE_NOT_FOUND, "Upload candidate is not a regular file")
    if not _is_under_allowlist(file_path, config.allowlist_dirs):
        raise DriveAgentError(DriveAgentErrorCode.PATH_NOT_ALLOWED, "Upload path is outside the allowlist")

    size_bytes = file_path.stat().st_size
    if size_bytes > config.max_upload_bytes:
        raise DriveAgentError(DriveAgentErrorCode.FILE_TOO_LARGE, "Upload candidate exceeds size limit")

    mime_type = _detect_mime_type(file_path)
    if mime_type not in _ALLOWED_MIME_TYPES:
        raise DriveAgentError(DriveAgentErrorCode.UNSUPPORTED_FILE_TYPE, "Unsupported file type")

    archive_members_scanned = 0
    if mime_type == "application/gzip":
        archive_members_scanned = _inspect_tar_gz(file_path)
    else:
        _inspect_text_stream(file_path, location=file_path.name, sample_limit=TEXT_SAMPLE_BYTES)

    return ValidationResult(
        file_path=str(file_path),
        sha256=_stream_sha256(file_path),
        size_bytes=size_bytes,
        classification=config.classification,
        mime_type=mime_type,
        archive_members_scanned=archive_members_scanned,
    )


@dataclass(frozen=True)
class DriveAgentConfig:
    """Environment-derived configuration for the Drive exporter."""

    classification: str
    max_upload_bytes: int
    audit_log_path: Path
    allowlist_dirs: tuple[Path, ...]


def _load_config_from_env() -> DriveAgentConfig:
    classification = os.environ.get("QARAR_UPLOAD_CLASSIFICATION", "").strip().upper()
    if not classification:
        raise DriveAgentError(DriveAgentErrorCode.CONFIG_NOT_FOUND, "Missing QARAR_UPLOAD_CLASSIFICATION")
    if classification in BLOCKED_CLASSIFICATIONS or classification != ALLOWED_CLASSIFICATION:
        raise DriveAgentError(DriveAgentErrorCode.CLASSIFICATION_BLOCKED, "Upload classification is blocked")

    max_raw = os.environ.get("QARAR_MAX_UPLOAD_BYTES", "").strip()
    audit_raw = os.environ.get("QARAR_AUDIT_LOG_PATH", "").strip()
    allowlist_raw = os.environ.get("QARAR_UPLOAD_ALLOWLIST_DIRS", "").strip()
    if not max_raw or not audit_raw or not allowlist_raw:
        raise DriveAgentError(
            DriveAgentErrorCode.CONFIG_NOT_FOUND,
            "Missing required Drive agent environment configuration",
        )
    try:
        max_upload_bytes = int(max_raw)
    except ValueError as exc:
        raise DriveAgentError(DriveAgentErrorCode.CONFIG_NOT_FOUND, "Invalid QARAR_MAX_UPLOAD_BYTES") from exc
    if max_upload_bytes <= 0:
        raise DriveAgentError(DriveAgentErrorCode.CONFIG_NOT_FOUND, "QARAR_MAX_UPLOAD_BYTES must be positive")

    validated_allowlist_dirs: list[Path] = []
    for part in allowlist_raw.split(os.pathsep):
        raw_part = part.strip()
        if not raw_part:
            continue
        candidate = Path(raw_part)
        if not candidate.is_absolute():
            raise DriveAgentError(
                DriveAgentErrorCode.CONFIG_NOT_FOUND,
                "QARAR_UPLOAD_ALLOWLIST_DIRS entries must be absolute paths",
            )
        try:
            resolved = candidate.expanduser().resolve(strict=True)
        except OSError as exc:
            raise DriveAgentError(
                DriveAgentErrorCode.CONFIG_NOT_FOUND,
                "Invalid QARAR_UPLOAD_ALLOWLIST_DIRS entry",
            ) from exc
        validated_allowlist_dirs.append(resolved)

    allowlist_dirs = tuple(validated_allowlist_dirs)
    if not allowlist_dirs:
        raise DriveAgentError(DriveAgentErrorCode.CONFIG_NOT_FOUND, "Upload allowlist is empty")

    return DriveAgentConfig(
        classification=classification,
        max_upload_bytes=max_upload_bytes,
        audit_log_path=Path(audit_raw).expanduser(),
        allowlist_dirs=allowlist_dirs,
    )


def _canonical_candidate(file_path: str | Path) -> Path:
    raw_path = Path(file_path).expanduser()
    if raw_path.is_symlink():
        raise DriveAgentError(DriveAgentErrorCode.UNSAFE_PATH, "Symlink uploads are blocked")
    try:
        return raw_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise DriveAgentError(DriveAgentErrorCode.FILE_NOT_FOUND, "Upload candidate does not exist") from exc


def _is_under_allowlist(candidate: Path, allowlist_dirs: tuple[Path, ...]) -> bool:
    return any(candidate == allowed or candidate.is_relative_to(allowed) for allowed in allowlist_dirs)


def _detect_mime_type(file_path: Path) -> str:
    with file_path.open("rb") as handle:
        header = handle.read(512)
    lower_name = file_path.name.lower()
    if header.startswith(b"\x1f\x8b"):
        if lower_name.endswith((".tar.gz", ".tgz")) and _is_gzip_tar(file_path):
            return "application/gzip"
        raise DriveAgentError(DriveAgentErrorCode.UNSUPPORTED_FILE_TYPE, "Gzip payload is not a tar archive")
    if b"\x00" in header:
        raise DriveAgentError(DriveAgentErrorCode.UNSUPPORTED_FILE_TYPE, "Binary payloads are blocked")
    hinted = _extension_hint(file_path)
    guessed = mimetypes.guess_type(file_path.name)[0]
    return hinted or guessed or "text/plain"


def _extension_hint(file_path: Path) -> str | None:
    lower_name = file_path.name.lower()
    for suffix, mime_type in _EXTENSION_MIME_HINTS.items():
        if lower_name.endswith(suffix):
            return mime_type
    return None


def _is_gzip_tar(file_path: Path) -> bool:
    with gzip.open(file_path, "rb") as handle:
        block = handle.read(262)
    return len(block) >= 262 and block[257:262] == b"ustar"


def _stream_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(DEFAULT_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inspect_tar_gz(file_path: Path) -> int:
    members_scanned = 0
    with tarfile.open(file_path, mode="r:gz") as archive:
        for member in archive.getmembers():
            _validate_archive_member(member)
            if member.isfile() and _archive_member_is_text_like(member.name):
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise DriveAgentError(DriveAgentErrorCode.ARCHIVE_UNSAFE, "Archive member could not be inspected")
                _inspect_binary_stream(extracted, location=member.name, sample_limit=ARCHIVE_TEXT_SAMPLE_BYTES)
                members_scanned += 1
            elif member.isfile() and member.size > 0:
                raise DriveAgentError(DriveAgentErrorCode.UNSUPPORTED_FILE_TYPE, "Archive contains unsupported binary-like member")
    return members_scanned


def _validate_archive_member(member: tarfile.TarInfo) -> None:
    normalized = member.name.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if member.issym() or member.islnk():
        raise DriveAgentError(DriveAgentErrorCode.ARCHIVE_UNSAFE, "Archive links are blocked")
    if pure.is_absolute() or normalized.startswith("/"):
        raise DriveAgentError(DriveAgentErrorCode.ARCHIVE_UNSAFE, "Archive absolute paths are blocked")
    collapsed = posixpath.normpath(normalized)
    if collapsed == ".." or collapsed.startswith("../") or "/../" in f"/{collapsed}/":
        raise DriveAgentError(DriveAgentErrorCode.ARCHIVE_UNSAFE, "Archive path traversal is blocked")
    if member.isdev():
        raise DriveAgentError(DriveAgentErrorCode.ARCHIVE_UNSAFE, "Archive device entries are blocked")


def _archive_member_is_text_like(name: str) -> bool:
    suffix = _extension_hint(Path(name))
    guessed = mimetypes.guess_type(name)[0]
    return (suffix or guessed or "text/plain") in _TEXT_MIME_TYPES


def _inspect_text_stream(file_path: Path, *, location: str, sample_limit: int) -> None:
    with file_path.open("rb") as handle:
        _inspect_binary_stream(handle, location=location, sample_limit=sample_limit)


def _inspect_binary_stream(handle: BinaryIO, *, location: str, sample_limit: int) -> None:
    payload = handle.read(sample_limit + 1)
    if b"\x00" in payload:
        raise DriveAgentError(DriveAgentErrorCode.UNSUPPORTED_FILE_TYPE, "Binary content is blocked")
    text = payload[:sample_limit].decode("utf-8", errors="ignore")
    finding = _detect_sensitive_content(text, location=location)
    if finding is not None:
        raise DriveAgentError(
            DriveAgentErrorCode.SENSITIVE_CONTENT,
            f"Sensitive content detected: {finding.kind} at {finding.location}",
        )


def _detect_sensitive_content(text: str, *, location: str) -> SensitiveFinding | None:
    for kind, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            return SensitiveFinding(kind=kind, location=location)
    for kind, pattern in _PII_PATTERNS:
        if pattern.search(text):
            return SensitiveFinding(kind=kind, location=location)
    return None


def _write_audit_event(
    audit_log_path: Path,
    event: str,
    validation: ValidationResult,
    error_code: str | None,
) -> None:
    audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "validation": asdict(validation),
        "error_code": error_code,
    }
    with audit_log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


__all__ = [
    "ALLOWED_CLASSIFICATION",
    "BLOCKED_CLASSIFICATIONS",
    "DRIVE_FILE_SCOPE",
    "DriveAgentConfig",
    "DriveAgentError",
    "DriveAgentErrorCode",
    "DriveUploadResult",
    "DriveUploader",
    "GoogleDriveUploader",
    "ValidationResult",
    "export_public_artifact",
    "validate_public_artifact",
]
