# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Tests for the sovereign local Ollama activation manifest and script."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "config" / "ollama.local.models.json"
SCRIPT_PATH = REPO_ROOT / "scripts" / "ollama" / "activate-local-models.sh"


def test_ollama_manifest_declares_exactly_18_required_local_models() -> None:
    """The local activation manifest must stay explicit and non-empty."""

    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    models = data["models"]
    model_names = [entry["model"] for entry in models]
    model_ids = [entry["id"] for entry in models]

    assert data["provider"] == "ollama"
    assert data["policy"]["trustBoundary"] == "LOCAL_CONTROL_PLANE"
    assert data["policy"]["pullRequiresExplicitFlag"] == "OLLAMA_PULL=1"
    assert data["policy"]["requiredModelCount"] == 18
    assert len(models) == 18
    assert len(set(model_ids)) == 18
    assert len(set(model_names)) == 18
    assert all(entry["required"] is True for entry in models)
    assert "deepseek-coder-v2:16b" in model_names
    assert "qwen2.5-coder:32b" in model_names
    assert "nomic-embed-text:latest" in model_names
    assert "bge-m3:latest" in model_names


def test_ollama_activation_script_rejects_non_local_base_url() -> None:
    """The activation command must not target external Ollama endpoints."""

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "OLLAMA_BASE_URL": "https://example.com:11434",
            "OLLAMA_MODEL_MANIFEST": str(MANIFEST_PATH),
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "OLLAMA_BASE_URL must point to localhost" in result.stderr


def test_ollama_activation_script_fails_closed_when_runtime_is_absent() -> None:
    """Without a local Ollama runtime, verification must fail instead of passing."""

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        env={
            "PATH": "/usr/bin:/bin",
            "OLLAMA_BASE_URL": "http://localhost:9",
            "OLLAMA_MODEL_MANIFEST": str(MANIFEST_PATH),
            "OLLAMA_PULL": "0",
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Ollama is not reachable" in result.stderr


def test_ollama_activation_script_verifies_models_from_local_runtime(tmp_path: Path) -> None:
    """A local /api/tags response with all 18 models should verify successfully."""

    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    model_names = [entry["model"] for entry in data["models"]]
    server_script = tmp_path / "ollama_tags_server.py"
    server_script.write_text(
        """
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

models = json.loads(sys.argv[1])

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/tags":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({"models": [{"name": model} for model in models]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        return

server = HTTPServer(("127.0.0.1", 0), Handler)
print(server.server_port, flush=True)
server.serve_forever()
""".lstrip(),
        encoding="utf-8",
    )
    proc = subprocess.Popen(
        ["python3", str(server_script), json.dumps(model_names)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        assert proc.stdout is not None
        port = proc.stdout.readline().strip()
        result = subprocess.run(
            ["bash", str(SCRIPT_PATH)],
            cwd=REPO_ROOT,
            env={
                "PATH": "/usr/bin:/bin",
                "OLLAMA_BASE_URL": f"http://127.0.0.1:{port}",
                "OLLAMA_MODEL_MANIFEST": str(MANIFEST_PATH),
                "OLLAMA_PULL": "0",
            },
            text=True,
            capture_output=True,
            check=False,
        )
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    assert result.returncode == 0
    assert "VERIFIED: all 18 sovereign local Ollama models are installed" in result.stdout
