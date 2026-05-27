# SPDX-License-Identifier: MIT
# Licensed under MIT
from __future__ import annotations

from pathlib import Path

REQUIRED_FILES = [
    Path('.agents/config/agents.yaml'),
    Path('.agents/modal_app.py'),
    Path('.agents/pr_review.py'),
    Path('.agents/invoke.py'),
    Path('.agents/policies/secrets-boundary.md'),
    Path('.agents/policies/network-boundary.md'),
    Path('.agents/policies/dependency-build-safety.md'),
]


def main() -> int:
    missing = [str(p) for p in REQUIRED_FILES if not p.exists()]
    if missing:
        print('VALIDATION: FAIL')
        print('Missing required files:')
        for item in missing:
            print(f' - {item}')
        return 1

    print('VALIDATION: PASS')
    print(f'Checked {len(REQUIRED_FILES)} required agent files.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
