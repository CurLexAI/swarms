# SPDX-License-Identifier: MIT
# Licensed under MIT
from __future__ import annotations

import re
import sys
from pathlib import Path

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("openai", re.compile(r"sk-(proj|admin)?-[A-Za-z0-9_-]{20,}")),
    ("anthropic", re.compile(r"sk-ant-api\d{2}-[A-Za-z0-9_-]{20,}")),
    ("github", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("telegram", re.compile(r"\d{8,12}:[A-Za-z0-9_-]{30,}")),
    ("google", re.compile(r"AIza[0-9A-Za-z_-]{20,}")),
    ("private-key", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)?PRIVATE KEY-----")),
    ("bcrypt", re.compile(r"\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}")),
]

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
}
TEXT_EXTS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
    ".rs",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".env",
    ".md",
    ".txt",
    ".sh",
}


def should_scan(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if path.name == ".env" or path.name.startswith(".env."):
        return True
    return path.suffix in TEXT_EXTS


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or not should_scan(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name, pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path}:{line}: possible {name} secret")
    if findings:
        print(f"Potential secrets detected: {len(findings)} finding(s).")
        return 1
    print("No obvious secrets found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
