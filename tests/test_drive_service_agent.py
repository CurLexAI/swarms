# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Tests for the fail-closed Qarar Drive service agent."""

from __future__ import annotations

import io
import os
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from typing import Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _agents_loader import _load_module, AGENTS_DIR  # noqa: E402


drive_service_agent = _load_module(
    "_agents_pkg.drive_service_agent",
    AGENTS_DIR / "drive_service_agent.py",
)
DriveAgentError = drive_service_agent.DriveAgentError
DriveAgentErrorCode = drive_service_agent.DriveAgentErrorCode
export_public_artifact = drive_service_agent.export_public_artifact


class FakeUploader:
    """Test uploader that records calls without external network access."""

    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []

    def upload(self, file_path: Path, *, mime_type: str) -> Mapping[str, str]:
        self.calls.append((file_path, mime_type))
        return {"id": "drive-file-id"}


class DriveServiceAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.audit = self.root / "audit" / "drive.jsonl"
        self._old_env = os.environ.copy()
        os.environ.update(
            {
                "QARAR_UPLOAD_CLASSIFICATION": "PUBLIC",
                "QARAR_MAX_UPLOAD_BYTES": "1048576",
                "QARAR_AUDIT_LOG_PATH": str(self.audit),
                "QARAR_UPLOAD_ALLOWLIST_DIRS": str(self.root),
            }
        )

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._old_env)
        self.tmp.cleanup()

    def test_clean_markdown_upload_succeeds(self) -> None:
        artifact = self.root / "public.md"
        artifact.write_text("# Public operational artifact\nNo sensitive data here.\n", encoding="utf-8")
        uploader = FakeUploader()

        result = export_public_artifact(artifact, uploader)

        self.assertTrue(result.ok)
        self.assertEqual(result.file_id, "drive-file-id")
        self.assertEqual(result.validation.classification, "PUBLIC")
        self.assertEqual(result.validation.mime_type, "text/markdown")
        self.assertEqual(len(result.validation.sha256), 64)
        self.assertEqual(len(uploader.calls), 1)
        self.assertTrue(self.audit.read_text(encoding="utf-8").strip())

    def test_pii_in_text_is_blocked(self) -> None:
        artifact = self.root / "pii.txt"
        artifact.write_text("Contact person: user@example.com\n", encoding="utf-8")

        with self.assertRaises(DriveAgentError) as ctx:
            export_public_artifact(artifact, FakeUploader())

        self.assertEqual(ctx.exception.code, DriveAgentErrorCode.SENSITIVE_CONTENT)

    def test_secret_key_is_blocked(self) -> None:
        artifact = self.root / "secret.txt"
        artifact.write_text("api_key = 'abcdefghijklmnopqrstuvwxyz123456'\n", encoding="utf-8")

        with self.assertRaises(DriveAgentError) as ctx:
            export_public_artifact(artifact, FakeUploader())

        self.assertEqual(ctx.exception.code, DriveAgentErrorCode.SENSITIVE_CONTENT)

    def test_tar_gz_with_hidden_pii_is_blocked(self) -> None:
        artifact = self.root / "bundle.tar.gz"
        self._write_tar_gz(artifact, {"nested/notes.txt": b"owner=user@example.com\n"})

        with self.assertRaises(DriveAgentError) as ctx:
            export_public_artifact(artifact, FakeUploader())

        self.assertEqual(ctx.exception.code, DriveAgentErrorCode.SENSITIVE_CONTENT)

    def test_path_traversal_archive_is_blocked(self) -> None:
        artifact = self.root / "traversal.tar.gz"
        self._write_tar_gz(artifact, {"../escape.txt": b"safe words\n"})

        with self.assertRaises(DriveAgentError) as ctx:
            export_public_artifact(artifact, FakeUploader())

        self.assertEqual(ctx.exception.code, DriveAgentErrorCode.ARCHIVE_UNSAFE)

    def test_oversized_file_is_blocked(self) -> None:
        os.environ["QARAR_MAX_UPLOAD_BYTES"] = "4"
        artifact = self.root / "large.md"
        artifact.write_text("larger than four bytes\n", encoding="utf-8")

        with self.assertRaises(DriveAgentError) as ctx:
            export_public_artifact(artifact, FakeUploader())

        self.assertEqual(ctx.exception.code, DriveAgentErrorCode.FILE_TOO_LARGE)

    def test_symlink_upload_is_blocked(self) -> None:
        target = self.root / "target.md"
        target.write_text("# Public\n", encoding="utf-8")
        artifact = self.root / "link.md"
        artifact.symlink_to(target)

        with self.assertRaises(DriveAgentError) as ctx:
            export_public_artifact(artifact, FakeUploader())

        self.assertEqual(ctx.exception.code, DriveAgentErrorCode.UNSAFE_PATH)

    def test_binary_spoofed_as_markdown_is_blocked(self) -> None:
        artifact = self.root / "binary.md"
        artifact.write_bytes(b"# title\n\x00not text\n")

        with self.assertRaises(DriveAgentError) as ctx:
            export_public_artifact(artifact, FakeUploader())

        self.assertEqual(ctx.exception.code, DriveAgentErrorCode.UNSUPPORTED_FILE_TYPE)

    def test_missing_env_vars_are_blocked(self) -> None:
        os.environ.pop("QARAR_UPLOAD_CLASSIFICATION")
        artifact = self.root / "public.md"
        artifact.write_text("# Public\n", encoding="utf-8")

        with self.assertRaises(DriveAgentError) as ctx:
            export_public_artifact(artifact, FakeUploader())

        self.assertEqual(ctx.exception.code, DriveAgentErrorCode.CONFIG_NOT_FOUND)

    def test_non_public_classification_is_blocked(self) -> None:
        os.environ["QARAR_UPLOAD_CLASSIFICATION"] = "CONFIDENTIAL"
        artifact = self.root / "confidential.md"
        artifact.write_text("# Not for Drive\n", encoding="utf-8")

        with self.assertRaises(DriveAgentError) as ctx:
            export_public_artifact(artifact, FakeUploader())

        self.assertEqual(ctx.exception.code, DriveAgentErrorCode.CLASSIFICATION_BLOCKED)

    def _write_tar_gz(self, path: Path, members: dict[str, bytes]) -> None:
        with tarfile.open(path, "w:gz") as archive:
            for name, data in members.items():
                info = tarfile.TarInfo(name=name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))


if __name__ == "__main__":
    unittest.main()
