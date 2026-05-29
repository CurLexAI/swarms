#!/usr/bin/env bash
set -euo pipefail

: "${QARAR_RAG_URL:?Set QARAR_RAG_URL}"
: "${QARAR_RAG_HMAC_SECRET:?Set QARAR_RAG_HMAC_SECRET}"

BODY='[{"doc_id":"pdpl-001","text":"تجربة إدخال مادة تنظيمية عامة دون أسرار.","source":"manual","authority":"SDAIA","article":"1","section":"definitions"}]'
SIGNED="$(python scripts/sign_request.py --secret "$QARAR_RAG_HMAC_SECRET" --body "$BODY")"
TS="$(printf '%s' "$SIGNED" | python -c 'import json,sys; print(json.load(sys.stdin)["x-qarar-timestamp"])')"
SIG="$(printf '%s' "$SIGNED" | python -c 'import json,sys; print(json.load(sys.stdin)["x-qarar-signature"])')"

curl -fsS "$QARAR_RAG_URL/health"
echo
curl -fsS \
  -X POST "$QARAR_RAG_URL/ingest" \
  -H "content-type: application/json" \
  -H "x-qarar-timestamp: $TS" \
  -H "x-qarar-signature: $SIG" \
  --data "$BODY"
echo
