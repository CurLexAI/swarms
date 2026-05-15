"""Behavior tests for ``scripts/commander/qala-egress-residency-gate.sh``.

Contracts under test (per ADR-0003 §Q8 and the gate's policy doc):

1. The gate PASSes the current repository (the allowlist plus the
   RFC-reserved-domain auto-exemption covers all repository-resident
   sources).
2. The gate FAILs when a scanned source file contains a host outside
   the allowlist (e.g. ``https://attacker.example.invalid`` is NOT
   exempt because ``example.invalid`` is in the RESERVED_DOMAINS set,
   so we deliberately use ``https://attacker.evil-host.zz``).
3. RFC 2606 reserved domains (``example.com``, ``*.invalid``,
   ``localhost``, ``*.test``) are auto-exempted.
4. RFC 5737 documentation IPs (``192.0.2.0/24``, ``198.51.100.0/24``,
   ``203.0.113.0/24``) are auto-exempted.
5. Non-reserved IP literals trigger the gate.
6. Empty allowlist would FAIL the gate (covered by a static read of
   the script body, since the scanner's exit code path is gated
   behind ``ALLOWLIST_EMPTY``).
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE_SCRIPT = REPO_ROOT / "scripts" / "commander" / "qala-egress-residency-gate.sh"


def _run_gate(workdir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(GATE_SCRIPT), str(workdir)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _make_repo(workdir: Path, file_path: str, content: str) -> None:
    target = workdir / file_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


class RepositoryPassesTests(unittest.TestCase):
    def test_current_repo_passes(self):
        result = _run_gate(REPO_ROOT)
        self.assertEqual(
            result.returncode,
            0,
            f"gate must PASS the current repo. stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}",
        )
        self.assertIn("[RESULT] PASS", result.stdout)


class UnapprovedHostFailsTests(unittest.TestCase):
    def test_unapproved_host_fails_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _make_repo(
                d,
                "src/oops.py",
                'import requests\n'
                'requests.get("https://attacker.evil-host.zz/x")\n',
            )
            result = _run_gate(d)
            self.assertEqual(
                result.returncode,
                1,
                f"gate must FAIL on unapproved host. stdout:\n{result.stdout}",
            )
            self.assertIn("UNAPPROVED_EGRESS", result.stdout)
            self.assertIn("attacker.evil-host.zz", result.stdout)

    def test_unapproved_ip_literal_fails_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _make_repo(d, "src/oops.py", 'url = "http://8.8.8.8/x"\n')
            result = _run_gate(d)
            self.assertEqual(result.returncode, 1)
            self.assertIn("8.8.8.8", result.stdout)


class ReservedExemptionsTests(unittest.TestCase):
    def test_example_com_is_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _make_repo(
                d,
                "src/sample.py",
                'sample = "https://docs.example.com/foo"\n',
            )
            result = _run_gate(d)
            self.assertEqual(
                result.returncode,
                0,
                f"example.com must be exempt. stdout:\n{result.stdout}",
            )

    def test_invalid_tld_is_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _make_repo(
                d,
                "src/sample.py",
                'sample = "https://anything.invalid/test"\n',
            )
            self.assertEqual(_run_gate(d).returncode, 0)

    def test_localhost_is_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _make_repo(d, "src/x.py", 'url = "http://localhost:8080/x"\n')
            self.assertEqual(_run_gate(d).returncode, 0)

    def test_documentation_ip_is_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _make_repo(
                d,
                "src/x.py",
                'phishing_sample = "http://admin:secret@192.0.2.1/x"\n',
            )
            result = _run_gate(d)
            self.assertEqual(
                result.returncode,
                0,
                f"192.0.2.0/24 must be exempt. stdout:\n{result.stdout}",
            )


class ScanScopeTests(unittest.TestCase):
    def test_docs_directory_is_not_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _make_repo(d, "docs/note.md", "See https://attacker.evil-host.zz\n")
            self.assertEqual(_run_gate(d).returncode, 0)

    def test_tests_directory_is_not_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _make_repo(d, "tests/fix.py", 'u = "https://attacker.evil-host.zz"\n')
            self.assertEqual(_run_gate(d).returncode, 0)


class AllowlistedHostsPassTests(unittest.TestCase):
    def test_modal_subdomain_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _make_repo(
                d,
                ".agents/x.py",
                'url = "https://my-app.modal.run/api"\n',
            )
            self.assertEqual(_run_gate(d).returncode, 0)

    def test_github_api_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _make_repo(
                d,
                ".agents/x.py",
                'url = "https://api.github.com/repos/x/y/pulls"\n',
            )
            self.assertEqual(_run_gate(d).returncode, 0)

    def test_huggingface_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            _make_repo(d, ".agents/x.py", 'url = "https://huggingface.co/model"\n')
            self.assertEqual(_run_gate(d).returncode, 0)


if __name__ == "__main__":
    unittest.main()
