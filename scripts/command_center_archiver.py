#!/usr/bin/env python3
"""Command Center archive builder for safe offline handoff.

The archiver uses a default-deny policy: it copies only explicitly allowed file
extensions, excludes sensitive/runtime directories, rejects risky filenames, and
performs a lightweight secret-pattern scan before any file is added to the
archive. It never uploads data to external services; operators may move the
resulting ``.tar.gz`` manually after review.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import tarfile
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_ALLOWED_EXTENSIONS = frozenset({".md", ".py", ".yml", ".yaml", ".txt", ".json"})
DEFAULT_BLOCKED_KEYWORDS = frozenset(
    {
        "card",
        "credential",
        "history",
        "password",
        "payment",
        "secret",
        "token",
        "سجل التاريخ",
        "كلمات السر",
    }
)
DEFAULT_BLOCKED_DIRS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".venv",
        ".venv-modal",
        "__pycache__",
        "artifacts",
        "build",
        "certs",
        "dist",
        "node_modules",
    }
)
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{80,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    re.compile(r"password\s*[:=]\s*[\"'][^\"'\n]{8,}[\"']", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class ArchivePolicy:
    """Default-deny policy for command-center archiving.

    Attributes:
        allowed_extensions: File extensions eligible for copy.
        blocked_keywords: Case-insensitive keywords rejected in path names.
        blocked_dirs: Directory names that must never be traversed.
        max_file_size_bytes: Maximum file size per copied file.
    """

    allowed_extensions: frozenset[str] = DEFAULT_ALLOWED_EXTENSIONS
    blocked_keywords: frozenset[str] = DEFAULT_BLOCKED_KEYWORDS
    blocked_dirs: frozenset[str] = DEFAULT_BLOCKED_DIRS
    max_file_size_bytes: int = 1_000_000


@dataclass(slots=True)
class ArchiveResult:
    """Result summary for an archive run."""

    archive_path: Path | None
    copied_files: list[Path] = field(default_factory=list)
    blocked_files: list[Path] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)


class CommandCenterArchiver:
    """Build a safe local tarball for command-center evidence handoff.

    Args:
        source_dir: Repository or folder to inspect.
        output_dir: Directory where the archive tarball will be written.
        archive_prefix: Stable prefix for generated archive names.
        policy: Optional injected archive policy.
        clock: Optional injected clock for deterministic tests.
    """

    def __init__(
        self,
        source_dir: Path | str = ".",
        output_dir: Path | str | None = None,
        archive_prefix: str = "Command_Center_Archive",
        policy: ArchivePolicy | None = None,
        clock: datetime | None = None,
    ) -> None:
        self.source_dir = Path(source_dir).resolve()
        self.output_dir = Path(output_dir).resolve() if output_dir else self.source_dir
        self.archive_prefix = archive_prefix
        self.policy = policy or ArchivePolicy()
        self.clock = clock

    def build(self) -> ArchiveResult:
        """Collect safe files into a temporary folder and compress them.

        Returns:
            ArchiveResult containing the created archive path and file summary.

        Raises:
            ValueError: If the configured source directory is invalid.
        """

        if not self.source_dir.is_dir():
            raise ValueError(f"source_dir is not a directory: {self.source_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        result = ArchiveResult(archive_path=None)
        archive_name = self._archive_name()
        with tempfile.TemporaryDirectory(prefix=f"{archive_name}_") as temp_root:
            staging_dir = Path(temp_root) / archive_name
            staging_dir.mkdir(parents=True, exist_ok=False)
            self._collect_into(staging_dir, result)
            if not result.copied_files:
                return result
            archive_path = self.output_dir / f"{archive_name}.tar.gz"
            self._compress(staging_dir, archive_path)
            result.archive_path = archive_path
        return result

    def is_safe_file(self, path: Path) -> bool:
        """Return whether a source file is allowed to be archived.

        Args:
            path: Candidate source file path.

        Returns:
            True when the file passes extension, path, size, and content checks.
        """

        if not path.is_file():
            return False
        relative_path = self._relative_path(path)
        if self._path_has_blocked_part(relative_path):
            return False
        if path.suffix.lower() not in self.policy.allowed_extensions:
            return False
        if path.stat().st_size > self.policy.max_file_size_bytes:
            return False
        return not self._contains_secret_pattern(path)

    def _collect_into(self, staging_dir: Path, result: ArchiveResult) -> None:
        for path in sorted(self.source_dir.rglob("*")):
            if path.is_dir():
                continue
            relative_path = self._relative_path(path)
            if self._is_output_archive(path):
                result.skipped_files.append(relative_path)
                continue
            if not self.is_safe_file(path):
                result.blocked_files.append(relative_path)
                continue
            destination = staging_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            result.copied_files.append(relative_path)

    def _compress(self, staging_dir: Path, archive_path: Path) -> None:
        with tarfile.open(archive_path, "w:gz") as tar:
            for path in sorted(staging_dir.rglob("*")):
                if path.is_file():
                    tar.add(path, arcname=path.relative_to(staging_dir.parent))

    def _archive_name(self) -> str:
        now = self.clock or datetime.now(timezone.utc)
        return f"{self.archive_prefix}_{now.strftime('%Y_%m_%d')}"

    def _relative_path(self, path: Path) -> Path:
        return path.resolve().relative_to(self.source_dir)

    def _path_has_blocked_part(self, relative_path: Path) -> bool:
        lowered_parts = [part.lower() for part in relative_path.parts]
        if any(part in self.policy.blocked_dirs for part in lowered_parts):
            return True
        lowered_path = str(relative_path).lower()
        return any(keyword.lower() in lowered_path for keyword in self.policy.blocked_keywords)

    def _contains_secret_pattern(self, path: Path) -> bool:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return True
        return any(pattern.search(content) for pattern in SECRET_PATTERNS)

    def _is_output_archive(self, path: Path) -> bool:
        if path.suffixes[-2:] != [".tar", ".gz"]:
            return False
        try:
            path.resolve().relative_to(self.output_dir)
        except ValueError:
            return False
        return path.name.startswith(self.archive_prefix)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Build a safe local command-center archive.")
    parser.add_argument("--source-dir", default=".", help="Directory to archive from.")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for the generated .tar.gz file. Defaults to source-dir.",
    )
    parser.add_argument(
        "--archive-prefix",
        default="Command_Center_Archive",
        help="Prefix for generated archive names.",
    )
    return parser.parse_args(argv)


def print_result(result: ArchiveResult) -> None:
    """Print a non-sensitive archive summary."""

    print(f"COPIED: {len(result.copied_files)}")
    print(f"BLOCKED_OR_SKIPPED_BY_POLICY: {len(result.blocked_files)}")
    if result.archive_path is None:
        print("ARCHIVE: NOT_CREATED")
        return
    print(f"ARCHIVE: {result.archive_path}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-center archiver CLI."""

    args = parse_args(argv)
    archiver = CommandCenterArchiver(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        archive_prefix=args.archive_prefix,
    )
    result = archiver.build()
    print_result(result)
    return 0 if result.archive_path is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
