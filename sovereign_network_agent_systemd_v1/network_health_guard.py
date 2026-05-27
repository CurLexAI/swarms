#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Qarar Sovereign Network Health Guard.

Raspberry Pi first. Safe by default. Decision flow:
Sense -> Analyze -> Decide -> Act.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

ProbeStatus = Literal["pass", "fail"]
DecisionAction = Literal["observe", "continue_monitoring", "request_human_review", "reboot_router"]


def _read_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _read_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= minimum else default


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ProbeTarget:
    host: str
    port: int
    label: str


@dataclass(frozen=True)
class GuardConfig:
    app_id: str
    dry_run: bool
    reboot_enabled: bool
    interval_seconds: int
    log_path: Path
    targets: Tuple[ProbeTarget, ...]
    connect_timeout_seconds: float
    failure_threshold: int
    router_reboot_command: Optional[str]
    log_max_bytes: int
    ping_fallback_enabled: bool
    ping_binary: str

    @staticmethod
    def from_env() -> "GuardConfig":
        log_path_value = os.getenv("QARAR_LOG_PATH") or os.getenv("QARAR_NETWORK_AUDIT_LOG") or "./logs/network-health.jsonl"
        return GuardConfig(
            app_id=os.getenv("QARAR_APP_ID", "sovereign-agent-v2"),
            dry_run=_read_bool("QARAR_NETWORK_DRY_RUN", True),
            reboot_enabled=_read_bool("QARAR_ENABLE_ROUTER_REBOOT", False),
            interval_seconds=_read_int("QARAR_INTERVAL", 60, minimum=5),
            log_path=Path(log_path_value).expanduser().resolve(),
            targets=_parse_targets(os.getenv("QARAR_TARGETS", "1.1.1.1:53,8.8.8.8:53,192.168.3.1:80")),
            connect_timeout_seconds=float(os.getenv("QARAR_CONNECT_TIMEOUT", "2.0")),
            failure_threshold=_read_int("QARAR_FAILURE_THRESHOLD", 3, minimum=1),
            router_reboot_command=os.getenv("QARAR_ROUTER_REBOOT_COMMAND"),
            log_max_bytes=_read_int("QARAR_LOG_MAX_BYTES", 5 * 1024 * 1024, minimum=1024),
            ping_fallback_enabled=_read_bool("QARAR_ENABLE_PING_FALLBACK", True),
            ping_binary=os.getenv("QARAR_PING_BINARY", "ping"),
        )


def _parse_targets(raw: str) -> Tuple[ProbeTarget, ...]:
    targets: List[ProbeTarget] = []
    for item in raw.split(","):
        text = item.strip()
        if not text:
            continue
        if ":" not in text:
            continue
        host, port_text = text.rsplit(":", 1)
        try:
            port = int(port_text)
        except ValueError:
            continue
        if host and 1 <= port <= 65535:
            targets.append(ProbeTarget(host=host, port=port, label=text))
    if not targets:
        targets.append(ProbeTarget(host="1.1.1.1", port=53, label="1.1.1.1:53"))
    return tuple(targets)


class SovereignAgent:
    def __init__(self, config: GuardConfig) -> None:
        self.config = config
        self.running = True
        self.consecutive_failures = 0
        self.config.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._register_signal_handlers()

    def _register_signal_handlers(self) -> None:
        def handle_stop(signum: int, _frame: object) -> None:
            self.running = False
            self.log_event("info", "Shutdown requested", {"signal": signum})

        signal.signal(signal.SIGTERM, handle_stop)
        signal.signal(signal.SIGINT, handle_stop)

    def _rotate_log_if_needed(self) -> None:
        path = self.config.log_path
        try:
            if path.exists() and path.stat().st_size >= self.config.log_max_bytes:
                rotated = path.with_suffix(path.suffix + ".1")
                if rotated.exists():
                    rotated.unlink()
                path.rename(rotated)
        except OSError as exc:
            print(f"[WARN] log rotation failed: {exc}", file=sys.stderr)

    def log_event(self, status: str, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        self._rotate_log_if_needed()
        event: Dict[str, Any] = {
            "timestamp": _utc_now(),
            "app_id": self.config.app_id,
            "status": status,
            "message": message,
            "dry_run": self.config.dry_run,
        }
        if extra is not None:
            event["extra"] = extra
        with self.config.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
        print(f"[{status.upper()}] {message}", flush=True)

    def sense(self) -> Dict[str, Any]:
        probes = [self._probe_target(target) for target in self.config.targets]
        passed = sum(1 for probe in probes if probe["status"] == "pass")
        failed = len(probes) - passed
        return {
            "observed_at": _utc_now(),
            "probes": probes,
            "passed": passed,
            "failed": failed,
            "total": len(probes),
        }

    def _probe_target(self, target: ProbeTarget) -> Dict[str, Any]:
        started = time.monotonic()
        try:
            with socket.create_connection((target.host, target.port), timeout=self.config.connect_timeout_seconds):
                latency_ms = int((time.monotonic() - started) * 1000)
                return {"target": target.label, "status": "pass", "latency_ms": latency_ms, "method": "tcp", "error": None}
        except OSError as socket_error:
            if self.config.ping_fallback_enabled and self._ping_host(target.host):
                latency_ms = int((time.monotonic() - started) * 1000)
                return {"target": target.label, "status": "pass", "latency_ms": latency_ms, "method": "ping-fallback", "error": None}
            latency_ms = int((time.monotonic() - started) * 1000)
            return {"target": target.label, "status": "fail", "latency_ms": latency_ms, "method": "tcp", "error": str(socket_error)}

    def _ping_host(self, host: str) -> bool:
        try:
            completed = subprocess.run(
                [self.config.ping_binary, "-c", "1", "-W", str(max(1, int(self.config.connect_timeout_seconds))), host],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=max(2, int(self.config.connect_timeout_seconds) + 1),
            )
            return completed.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def analyze(self, sensed: Dict[str, Any]) -> Dict[str, Any]:
        failed = int(sensed["failed"])
        total = int(sensed["total"])
        if failed == 0:
            severity = "LOW"
            self.consecutive_failures = 0
        elif failed < total:
            severity = "MEDIUM"
            self.consecutive_failures += 1
        else:
            severity = "HIGH"
            self.consecutive_failures += 1
        return {
            "severity": severity,
            "consecutive_failures": self.consecutive_failures,
            "failure_threshold": self.config.failure_threshold,
            "network_available": failed < total,
        }

    def decide(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        severity = str(analysis["severity"])
        consecutive_failures = int(analysis["consecutive_failures"])
        if severity == "LOW":
            action: DecisionAction = "continue_monitoring"
            reason = "All configured probes passed."
        elif consecutive_failures < self.config.failure_threshold:
            action = "observe"
            reason = "Failure threshold not reached."
        elif self.config.dry_run:
            action = "request_human_review"
            reason = "Dry run is enabled; router actuation is blocked."
        elif not self.config.reboot_enabled:
            action = "request_human_review"
            reason = "Router reboot flag is disabled."
        else:
            action = "reboot_router"
            reason = "High-severity failure threshold reached and actuation is explicitly enabled."
        return {"action": action, "reason": reason}

    def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        action = str(decision["action"])
        if action != "reboot_router":
            return {"executed": False, "action": action, "result": "No unsafe actuation performed."}
        command = self.config.router_reboot_command
        if command is None or command.strip() == "":
            return {"executed": False, "action": action, "result": "Missing QARAR_ROUTER_REBOOT_COMMAND; fail-closed."}
        argv = shlex.split(command)
        if not argv:
            return {"executed": False, "action": action, "result": "Empty router reboot command; fail-closed."}
        completed = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=30)
        return {
            "executed": completed.returncode == 0,
            "action": action,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-500:],
            "stderr": completed.stderr[-500:],
        }

    def run_once(self) -> None:
        sensed = self.sense()
        analysis = self.analyze(sensed)
        decision = self.decide(analysis)
        actuation = self.act(decision)
        status = "healthy" if analysis["severity"] == "LOW" else "warning" if analysis["severity"] == "MEDIUM" else "failed"
        self.log_event(status, "Sense -> Analyze -> Decide -> Act completed", {
            "sense": sensed,
            "analysis": analysis,
            "decision": decision,
            "act": actuation,
        })

    def run(self, *, once: bool = False) -> None:
        self.log_event("info", "Starting Sovereign Agent Engine", {
            "interval_seconds": self.config.interval_seconds,
            "targets": [target.label for target in self.config.targets],
            "reboot_enabled": self.config.reboot_enabled,
        })
        while self.running:
            self.run_once()
            if once:
                break
            time.sleep(self.config.interval_seconds)
        self.log_event("info", "Sovereign Agent Engine stopped")


def main() -> int:
    parser = argparse.ArgumentParser(description="Qarar Sovereign Network Health Guard")
    parser.add_argument("--once", action="store_true", help="run one Sense -> Analyze -> Decide -> Act cycle and exit")
    args = parser.parse_args()
    agent = SovereignAgent(GuardConfig.from_env())
    agent.run(once=args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
