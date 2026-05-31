# SPDX-License-Identifier: MIT
# Licensed under MIT
from __future__ import annotations

import tarfile
from datetime import datetime, timezone
from pathlib import Path

from scripts.command_center_archiver import ArchivePolicy, CommandCenterArchiver


def test_archiver_copies_only_safe_allowed_files(tmp_path: Path) -> None:
    source = tmp_path / "repo"
    output = tmp_path / "out"
    source.mkdir()
    (source / "README.md").write_text("safe evidence", encoding="utf-8")
    (source / "script.py").write_text("print('safe')\n", encoding="utf-8")
    (source / "image.png").write_bytes(b"not allowed")
    (source / "passwords.txt").write_text("not copied", encoding="utf-8")
    nested = source / "docs"
    nested.mkdir()
    (nested / "policy.yaml").write_text("name: safe\n", encoding="utf-8")

    archiver = CommandCenterArchiver(
        source_dir=source,
        output_dir=output,
        clock=datetime(2026, 5, 29, tzinfo=timezone.utc),
    )

    result = archiver.build()

    assert result.archive_path == output / "Command_Center_Archive_2026_05_29.tar.gz"
    assert sorted(str(path) for path in result.copied_files) == [
        "README.md",
        "docs/policy.yaml",
        "script.py",
    ]
    assert Path("image.png") in result.blocked_files
    assert Path("passwords.txt") in result.blocked_files

    with tarfile.open(result.archive_path, "r:gz") as archive:
        names = sorted(archive.getnames())

    assert names == [
        "Command_Center_Archive_2026_05_29/README.md",
        "Command_Center_Archive_2026_05_29/docs/policy.yaml",
        "Command_Center_Archive_2026_05_29/script.py",
    ]


def test_archiver_blocks_secret_content_and_sensitive_dirs(tmp_path: Path) -> None:
    source = tmp_path / "repo"
    output = tmp_path / "out"
    source.mkdir()
    (source / "safe.json").write_text('{"ok": true}\n', encoding="utf-8")
    (source / "leak.py").write_text("API_KEY = 'sk-" + "A" * 40 + "'\n", encoding="utf-8")
    git_dir = source / ".git"
    git_dir.mkdir()
    (git_dir / "config.txt").write_text("must not archive", encoding="utf-8")
    cert_dir = source / "certs"
    cert_dir.mkdir()
    (cert_dir / "server.key.txt").write_text("must not archive", encoding="utf-8")

    archiver = CommandCenterArchiver(
        source_dir=source,
        output_dir=output,
        clock=datetime(2026, 5, 29, tzinfo=timezone.utc),
    )

    result = archiver.build()

    assert result.archive_path is not None
    assert result.copied_files == [Path("safe.json")]
    assert Path("leak.py") in result.blocked_files
    assert Path(".git/config.txt") in result.blocked_files
    assert Path("certs/server.key.txt") in result.blocked_files


def test_archiver_returns_no_archive_when_no_safe_files(tmp_path: Path) -> None:
    source = tmp_path / "repo"
    output = tmp_path / "out"
    source.mkdir()
    (source / "payment.json").write_text("{}", encoding="utf-8")

    archiver = CommandCenterArchiver(source_dir=source, output_dir=output)

    result = archiver.build()

    assert result.archive_path is None
    assert result.copied_files == []
    assert result.blocked_files == [Path("payment.json")]


def test_archiver_honors_injected_policy(tmp_path: Path) -> None:
    source = tmp_path / "repo"
    output = tmp_path / "out"
    source.mkdir()
    (source / "small.md").write_text("ok", encoding="utf-8")
    (source / "large.md").write_text("too large", encoding="utf-8")

    policy = ArchivePolicy(max_file_size_bytes=3)
    archiver = CommandCenterArchiver(source_dir=source, output_dir=output, policy=policy)

    result = archiver.build()

    assert result.copied_files == [Path("small.md")]
    assert result.blocked_files == [Path("large.md")]
