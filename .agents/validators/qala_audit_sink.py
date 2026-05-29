# SPDX-License-Identifier: MIT
# Licensed under MIT
"""Qal'a (قلعة) — Q7 Sealed Audit Sink (Python side).

Append-only, tamper-evident JSONL log. Each record carries a chained
SHA-256 hash; tampering with any prior record invalidates the chain.

No external persistence. No background workers. No network calls.
Payloads MUST be sanitized by the caller (Q5 KSA-PII + adapter audit
redaction) before being passed to ``append`` — this module does not
redact, because the gate pipeline needs to keep redaction explicit.

Mirror of ``src/security/qalaAuditSink.ts``. See
``docs/decisions/ADR-0003-qala-security-architecture.md`` §Q7.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Literal, Mapping

QALA_GENESIS_HASH: Final[str] = "GENESIS"

QalaAuditEvent = Literal[
    "input_validation_blocked",
    "input_validation_request_changes",
    "input_validation_approved",
    "output_validation_blocked",
    "output_validation_request_changes",
    "output_validation_approved",
    "ksa_pii_detected",
    "policy_decision",
    "egress_check_blocked",
    "egress_check_approved",
    "auth_check_blocked",
    "auth_check_approved",
    # Qarar router decisions (audited via build_audited_execution_plan).
    "classification_decision",
    "route_decision",
    "route_blocked",
]

_QALA_AUDIT_EVENTS: Final[frozenset[str]] = frozenset(
    {
        "input_validation_blocked",
        "input_validation_request_changes",
        "input_validation_approved",
        "output_validation_blocked",
        "output_validation_request_changes",
        "output_validation_approved",
        "ksa_pii_detected",
        "policy_decision",
        "egress_check_blocked",
        "egress_check_approved",
        "auth_check_blocked",
        "auth_check_approved",
        # Qarar router decisions (audited via build_audited_execution_plan).
        "classification_decision",
        "route_decision",
        "route_blocked",
    }
)


@dataclass(frozen=True)
class QalaAuditRecord:
    record_id: str
    prev_hash: str
    record_hash: str
    event: QalaAuditEvent
    trace_id: str
    span_id: str
    tenant_id: str
    occurred_at: str
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class QalaAuditAppendOk:
    ok: Literal[True]
    value: QalaAuditRecord


@dataclass(frozen=True)
class QalaAuditAppendErr:
    ok: Literal[False]
    error: Literal["AUDIT_WRITE_FAILED", "AUDIT_INVALID_EVENT", "AUDIT_INVALID_INPUT"]
    message: str


QalaAuditAppendResult = QalaAuditAppendOk | QalaAuditAppendErr


@dataclass(frozen=True)
class QalaAuditVerifyOk:
    ok: Literal[True]
    records_verified: int


@dataclass(frozen=True)
class QalaAuditVerifyErr:
    ok: Literal[False]
    error: Literal["AUDIT_CHAIN_BROKEN", "AUDIT_READ_FAILED"]
    message: str
    at_record: int | None = None


QalaAuditVerifyResult = QalaAuditVerifyOk | QalaAuditVerifyErr


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _default_sink_path() -> Path:
    return Path(
        os.environ.get("QALA_AUDIT_SINK_PATH", "artifacts/security/qala-audit.jsonl")
    )


def _canonicalize(
    *,
    event: str,
    occurred_at: str,
    payload: Mapping[str, Any],
    span_id: str,
    tenant_id: str,
    trace_id: str,
) -> str:
    # Deterministic, key-sorted JSON (sort_keys=True) so the hash is
    # reproducible regardless of dict insertion order. Matches the TS
    # mirror, which key-sorts via Object.keys(obj).sort().
    return json.dumps(
        {
            "event": event,
            "occurredAt": occurred_at,
            "payload": payload,
            "spanId": span_id,
            "tenantId": tenant_id,
            "traceId": trace_id,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class QalaAuditSink:
    def __init__(self, sink_path: str | os.PathLike[str] | None = None) -> None:
        path = Path(sink_path) if sink_path is not None else _default_sink_path()
        self._path = path.resolve()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def sink_path(self) -> Path:
        return self._path

    def append(
        self,
        *,
        event: str,
        trace_id: str,
        span_id: str,
        tenant_id: str,
        payload: Mapping[str, Any] | None = None,
        occurred_at: str | None = None,
    ) -> QalaAuditAppendResult:
        if event not in _QALA_AUDIT_EVENTS:
            return QalaAuditAppendErr(
                ok=False, error="AUDIT_INVALID_EVENT", message=f"unknown event: {event!r}"
            )
        if (
            not isinstance(trace_id, str)
            or not isinstance(span_id, str)
            or not isinstance(tenant_id, str)
            or len(trace_id) == 0
            or len(span_id) == 0
            or len(tenant_id) == 0
        ):
            return QalaAuditAppendErr(
                ok=False,
                error="AUDIT_INVALID_INPUT",
                message="trace_id, span_id, and tenant_id are required",
            )

        payload_normalized: Mapping[str, Any] = payload if payload is not None else {}
        occurred_at_normalized = occurred_at if occurred_at is not None else _now_iso()
        prev_hash = self._read_last_hash()
        canonical = _canonicalize(
            event=event,
            occurred_at=occurred_at_normalized,
            payload=payload_normalized,
            span_id=span_id,
            tenant_id=tenant_id,
            trace_id=trace_id,
        )
        record_hash = _sha256(f"{prev_hash}\n{canonical}")

        record = QalaAuditRecord(
            record_id=str(uuid.uuid4()),
            prev_hash=prev_hash,
            record_hash=record_hash,
            event=event,  # type: ignore[arg-type]
            trace_id=trace_id,
            span_id=span_id,
            tenant_id=tenant_id,
            occurred_at=occurred_at_normalized,
            payload=payload_normalized,
        )

        # Serialize using camelCase keys to match the TS mirror. The
        # canonical-for-hash form already uses camelCase; the on-disk
        # record matches so verifyChain can re-canonicalize from disk.
        on_disk = {
            "recordId": record.record_id,
            "prevHash": record.prev_hash,
            "recordHash": record.record_hash,
            "event": record.event,
            "traceId": record.trace_id,
            "spanId": record.span_id,
            "tenantId": record.tenant_id,
            "occurredAt": record.occurred_at,
            "payload": dict(record.payload),
        }

        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(on_disk, ensure_ascii=False) + "\n")
        except OSError as exc:
            return QalaAuditAppendErr(
                ok=False, error="AUDIT_WRITE_FAILED", message=str(exc)
            )

        return QalaAuditAppendOk(ok=True, value=record)

    def verify_chain(self) -> QalaAuditVerifyResult:
        if not self._path.exists():
            return QalaAuditVerifyOk(ok=True, records_verified=0)
        try:
            content = self._path.read_text(encoding="utf-8")
        except OSError as exc:
            return QalaAuditVerifyErr(
                ok=False, error="AUDIT_READ_FAILED", message=str(exc)
            )

        expected_prev = QALA_GENESIS_HASH
        index = 0
        for line in content.splitlines():
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                return QalaAuditVerifyErr(
                    ok=False,
                    error="AUDIT_CHAIN_BROKEN",
                    message="record is not valid JSON",
                    at_record=index,
                )
            if not isinstance(parsed, dict):
                return QalaAuditVerifyErr(
                    ok=False,
                    error="AUDIT_CHAIN_BROKEN",
                    message="record is not a JSON object",
                    at_record=index,
                )
            if parsed.get("prevHash") != expected_prev:
                return QalaAuditVerifyErr(
                    ok=False,
                    error="AUDIT_CHAIN_BROKEN",
                    message=f"prev_hash mismatch at record {index}",
                    at_record=index,
                )
            # A record may be valid JSON yet missing required fields. Treat
            # that as a broken chain (tamper/corruption), never a traceback,
            # so the CLI keeps its documented exit-code contract.
            try:
                canonical = _canonicalize(
                    event=parsed["event"],
                    occurred_at=parsed["occurredAt"],
                    payload=parsed.get("payload") or {},
                    span_id=parsed["spanId"],
                    tenant_id=parsed["tenantId"],
                    trace_id=parsed["traceId"],
                )
            except KeyError as exc:
                return QalaAuditVerifyErr(
                    ok=False,
                    error="AUDIT_CHAIN_BROKEN",
                    message=f"record missing required field: {exc.args[0]}",
                    at_record=index,
                )
            recomputed = _sha256(f"{expected_prev}\n{canonical}")
            if recomputed != parsed.get("recordHash"):
                return QalaAuditVerifyErr(
                    ok=False,
                    error="AUDIT_CHAIN_BROKEN",
                    message=f"record_hash mismatch at record {index}",
                    at_record=index,
                )
            expected_prev = parsed["recordHash"]
            index += 1

        return QalaAuditVerifyOk(ok=True, records_verified=index)

    def _read_last_hash(self) -> str:
        if not self._path.exists():
            return QALA_GENESIS_HASH
        try:
            content = self._path.read_text(encoding="utf-8").rstrip()
        except OSError:
            return QALA_GENESIS_HASH
        if not content:
            return QALA_GENESIS_HASH
        last = content.splitlines()[-1]
        try:
            parsed = json.loads(last)
        except json.JSONDecodeError:
            return QALA_GENESIS_HASH
        value = parsed.get("recordHash")
        return value if isinstance(value, str) else QALA_GENESIS_HASH


def _resolve_verify_path(path_arg: str | None) -> Path:
    if path_arg:
        return Path(path_arg)
    return _default_sink_path()


def _main(argv: list[str] | None = None) -> int:
    """CLI verifier for the sealed audit chain (Q7).

    Reuses ``QalaAuditSink.verify_chain`` — it does not re-implement the
    chain logic. Exit codes are stable so a shell gate can branch on them:

      0  -> chain intact (or empty/absent log)
      10 -> AUDIT_CHAIN_BROKEN (tamper, insertion, truncation, gap)
      2  -> AUDIT_READ_FAILED (I/O failure) — fail-closed for the gate
    """
    parser = argparse.ArgumentParser(
        prog="qala_audit_sink",
        description="Verify the tamper-evident Qal'a audit chain (Q7).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    verify_p = sub.add_parser("verify", help="Verify the on-disk audit chain.")
    verify_p.add_argument(
        "--path",
        default=None,
        help=(
            "Audit sink JSONL path (default: $QALA_AUDIT_SINK_PATH or "
            "artifacts/security/qala-audit.jsonl)."
        ),
    )
    args = parser.parse_args(argv)

    if args.command == "verify":
        sink = QalaAuditSink(_resolve_verify_path(args.path))
        print(f"AUDIT_SINK_PATH: {sink.sink_path}")
        result = sink.verify_chain()
        if result.ok:
            print(f"AUDIT_CHAIN_OK records_verified={result.records_verified}")
            return 0
        if result.error == "AUDIT_CHAIN_BROKEN":
            print(
                f"AUDIT_CHAIN_BROKEN at_record={result.at_record} "
                f"message={result.message}"
            )
            return 10
        print(f"AUDIT_READ_FAILED message={result.message}")
        return 2

    parser.error(f"unknown command: {args.command}")  # pragma: no cover
    return 2  # pragma: no cover — parser.error exits before this


__all__ = [
    "QalaAuditEvent",
    "QalaAuditRecord",
    "QalaAuditSink",
    "QalaAuditAppendOk",
    "QalaAuditAppendErr",
    "QalaAuditAppendResult",
    "QalaAuditVerifyOk",
    "QalaAuditVerifyErr",
    "QalaAuditVerifyResult",
    "QALA_GENESIS_HASH",
]


if __name__ == "__main__":
    sys.exit(_main())
