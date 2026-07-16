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


def _default_events_path() -> Path:
    return Path(
        os.environ.get(
            "QALA_AUDIT_EVENTS_PATH", "artifacts/security/qala-audit.events.json"
        )
    )


def _default_anchor_path() -> Path:
    return Path(
        os.environ.get(
            "QALA_AUDIT_ANCHOR_PATH", "artifacts/security/qala-audit.anchor.json"
        )
    )


def _confine_cli_path(raw: str, *, kind: str) -> Path:
    """Resolve and confine an operator-supplied CLI path.

    The path may come from argv or an environment override. After symlink
    resolution (wrapping any OSError or RuntimeError in a ValueError), the
    path must live under the permitted root: the ``artifacts/security``
    directory below the current working directory. Test suites that need
    scratch space run from a private workspace containing its own
    ``artifacts/security`` instead of widening this boundary. Anything
    outside fails closed.
    """
    try:
        expanded = Path(os.path.expanduser(raw))
        cwd = Path.cwd()
        try:
            candidate = expanded if expanded.is_absolute() else (cwd / expanded)
            resolved = candidate.resolve(strict=False)
            artifacts_root = (cwd / "artifacts" / "security").resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            raise ValueError(f"Failed to resolve {kind} path {raw}: {exc}") from exc

        try:
            resolved.relative_to(artifacts_root)
        except ValueError:
            raise ValueError(
                f"{kind} path must be within artifacts/security, got: {resolved}"
            ) from None
        return resolved
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"Path verification error for {raw}: {exc}") from exc


def _resolve_anchor_path(anchor_arg: str | None) -> Path:
    return _confine_cli_path(
        anchor_arg or str(_default_anchor_path()), kind="anchor"
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

    def seal_from_events(self, events: list[Mapping[str, Any]]) -> str:
        """Deterministically (re)build the sealed chain from an event source.

        The event source carries no ``prevHash``/``recordHash`` (so it cannot
        be corrupted by a git merge the way a positional hash-chain is). Each
        event MUST already provide a stable ``recordId`` and ``occurredAt`` so
        the seal is byte-reproducible across runs. Returns the head hash (the
        last record's ``recordHash``, or ``GENESIS`` for an empty source).
        """
        prev_hash = QALA_GENESIS_HASH
        lines: list[str] = []
        for idx, ev in enumerate(events):
            try:
                event = ev["event"]
                record_id = ev["recordId"]
                trace_id = ev["traceId"]
                span_id = ev["spanId"]
                tenant_id = ev["tenantId"]
                occurred_at = ev["occurredAt"]
            except (KeyError, TypeError) as exc:
                raise ValueError(
                    f"event {idx} missing required field: {exc}"
                ) from exc
            if event not in _QALA_AUDIT_EVENTS:
                raise ValueError(f"event {idx} has unknown event type: {event!r}")
            payload = ev.get("payload") or {}
            canonical = _canonicalize(
                event=event,
                occurred_at=occurred_at,
                payload=payload,
                span_id=span_id,
                tenant_id=tenant_id,
                trace_id=trace_id,
            )
            record_hash = _sha256(f"{prev_hash}\n{canonical}")
            on_disk = {
                "recordId": record_id,
                "prevHash": prev_hash,
                "recordHash": record_hash,
                "event": event,
                "traceId": trace_id,
                "spanId": span_id,
                "tenantId": tenant_id,
                "occurredAt": occurred_at,
                "payload": dict(payload),
            }
            lines.append(json.dumps(on_disk, ensure_ascii=False))
            prev_hash = record_hash
        self._path.write_text(
            ("\n".join(lines) + "\n") if lines else "", encoding="utf-8"
        )
        return prev_hash

    def verify_chain(
        self,
        *,
        expected_count: int | None = None,
        expected_head_hash: str | None = None,
    ) -> QalaAuditVerifyResult:
        # ``expected_count``/``expected_head_hash`` come from a sealed anchor.
        # Forward link-walking alone cannot detect *tail truncation* (removing
        # the last N records leaves a still-valid prefix). Pinning the total
        # record count and the head hash closes that gap.
        if not self._path.exists():
            if expected_count is not None and expected_count != 0:
                return QalaAuditVerifyErr(
                    ok=False,
                    error="AUDIT_CHAIN_BROKEN",
                    message=(
                        f"ledger absent but anchor expects {expected_count} "
                        "record(s) (tail truncation)"
                    ),
                    at_record=0,
                )
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

        if expected_count is not None and index != expected_count:
            return QalaAuditVerifyErr(
                ok=False,
                error="AUDIT_CHAIN_BROKEN",
                message=(
                    f"record count mismatch: found {index}, anchor expects "
                    f"{expected_count} (insertion or tail truncation)"
                ),
                at_record=index,
            )
        # After the walk, ``expected_prev`` holds the head hash (GENESIS if
        # empty). A truncated tail yields a different head than the anchor.
        if expected_head_hash is not None and expected_prev != expected_head_hash:
            return QalaAuditVerifyErr(
                ok=False,
                error="AUDIT_CHAIN_BROKEN",
                message=(
                    "head hash mismatch: chain head does not match the sealed "
                    "anchor (tail truncation or tamper)"
                ),
                at_record=index,
            )
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
    return _confine_cli_path(
        path_arg or str(_default_sink_path()), kind="audit sink"
    )


def _resolve_events_path(events_arg: str | None) -> Path:
    return _confine_cli_path(
        events_arg or str(_default_events_path()), kind="event source"
    )


def _load_events(events_path: Path) -> list[Mapping[str, Any]]:
    raw = json.loads(events_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("event source must be a JSON array of event objects")
    return raw


def _load_anchor(anchor_path: Path) -> tuple[int | None, str | None]:
    """Return ``(record_count, head_hash)`` from a sealed anchor, or
    ``(None, None)`` when the anchor file is absent.

    A present-but-malformed anchor raises, so the gate fails closed.
    """
    if not anchor_path.exists():
        return (None, None)
    data = json.loads(anchor_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("anchor must be a JSON object")
    count = data.get("recordCount")
    head = data.get("headHash")
    if not isinstance(count, int) or not isinstance(head, str):
        raise ValueError("anchor must contain integer recordCount and string headHash")
    return (count, head)


def _anchor_document(record_count: int, head_hash: str) -> dict[str, Any]:
    return {
        "version": 1,
        "algorithm": "sha256-chain",
        "genesis": QALA_GENESIS_HASH,
        "recordCount": record_count,
        "headHash": head_hash,
    }


def _build_parser() -> argparse.ArgumentParser:
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
            "artifacts/security/qala-audit.jsonl). Must resolve under "
            "artifacts/security below the working directory."
        ),
    )
    verify_p.add_argument(
        "--anchor",
        default=None,
        help=(
            "Sealed anchor JSON path (default: $QALA_AUDIT_ANCHOR_PATH or "
            "artifacts/security/qala-audit.anchor.json). When present, the "
            "record count and head hash are enforced to detect tail truncation. "
            "Must resolve under artifacts/security below the working directory."
        ),
    )

    seal_p = sub.add_parser(
        "seal",
        help="Deterministically build the sealed chain from the event source.",
    )
    seal_p.add_argument(
        "--events",
        default=None,
        help=(
            "Event source JSON path. Must resolve under artifacts/security "
            "below the working directory."
        ),
    )
    seal_p.add_argument(
        "--path",
        default=None,
        help=(
            "Output sealed JSONL path. Must resolve under artifacts/security "
            "below the working directory."
        ),
    )
    seal_p.add_argument(
        "--anchor",
        default=None,
        help=(
            "Anchor JSON path. With --write-anchor, (re)writes it from the "
            "seal. Must resolve under artifacts/security below the working "
            "directory."
        ),
    )
    seal_p.add_argument(
        "--write-anchor",
        action="store_true",
        help=(
            "Regenerate the anchor from the freshly sealed chain. Omit in CI "
            "so the committed anchor stays authoritative; use only when "
            "intentionally adding events."
        ),
    )

    return parser


def _main(argv: list[str] | None = None) -> int:
    """CLI verifier for the sealed audit chain (Q7).

    Reuses ``QalaAuditSink.verify_chain`` — it does not re-implement the
    chain logic. Exit codes are stable so a shell gate can branch on them:

      0  -> chain intact (or empty/absent log)
      10 -> AUDIT_CHAIN_BROKEN (tamper, insertion, truncation, gap)
      2  -> AUDIT_READ_FAILED (I/O failure) — fail-closed for the gate
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "verify":
        return _cmd_verify(args)

    if args.command == "seal":
        return _cmd_seal(args)

    parser.error(f"unknown command: {args.command}")  # pragma: no cover
    return 2  # pragma: no cover — parser.error exits before this


def _cmd_verify(args: argparse.Namespace) -> int:
    try:
        sink = QalaAuditSink(_resolve_verify_path(args.path))
        anchor_path = _resolve_anchor_path(args.anchor)
    except (OSError, ValueError) as exc:
        print(f"AUDIT_READ_FAILED message={exc}")
        return 2
    print(f"AUDIT_SINK_PATH: {sink.sink_path}")
    try:
        expected_count, expected_head = _load_anchor(anchor_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"AUDIT_READ_FAILED message=anchor unreadable: {exc}")
        return 2
    if expected_count is not None:
        print(f"AUDIT_ANCHOR recordCount={expected_count} headHash={expected_head}")
    else:
        print("AUDIT_ANCHOR absent (count/head not enforced)")
    result = sink.verify_chain(
        expected_count=expected_count, expected_head_hash=expected_head
    )
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


def _cmd_seal(args: argparse.Namespace) -> int:
    try:
        events_path = _resolve_events_path(args.events)
        sink = QalaAuditSink(_resolve_verify_path(args.path))
        anchor_path = _resolve_anchor_path(args.anchor)
    except (OSError, ValueError) as exc:
        print(f"AUDIT_SEAL_FAILED message={exc}")
        return 2
    print(f"AUDIT_EVENTS_PATH: {events_path}")
    print(f"AUDIT_SINK_PATH: {sink.sink_path}")
    try:
        events = _load_events(events_path)
        head_hash = sink.seal_from_events(events)
    except FileNotFoundError:
        print(f"AUDIT_SEAL_FAILED message=event source not found: {events_path}")
        return 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"AUDIT_SEAL_FAILED message={exc}")
        return 2
    count = len(events)
    print(f"AUDIT_SEALED records={count} headHash={head_hash}")
    if args.write_anchor:
        try:
            anchor_path.parent.mkdir(parents=True, exist_ok=True)
            anchor_path.write_text(
                json.dumps(_anchor_document(count, head_hash), indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"AUDIT_SEAL_FAILED message=anchor write failed: {exc}")
            return 2
        print(f"AUDIT_ANCHOR_WRITTEN path={anchor_path}")
    return 0


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
