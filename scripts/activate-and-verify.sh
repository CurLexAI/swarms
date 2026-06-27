#!/usr/bin/env bash
set -euo pipefail

# ----------------- CONFIG (عدل أو عيّن كـ env vars قبل التشغيل) -----------------
GITHUB_REPO="${GITHUB_REPO:-CurLexAI/swarms}"
WORKFLOW_FILE="${WORKFLOW_FILE:-modal-runtime-auto-activation.yml}"
REF_BRANCH="${REF_BRANCH:-main}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
MODEL_NAME="${MODEL_NAME:-qwen2.5:0.5b}"
RETRY_SLEEP="${RETRY_SLEEP:-5}"
MAX_POLL_MINUTES="${MAX_POLL_MINUTES:-10}"
# Optional: modal deploy command (set MODAL_DEPLOY_CMD env to override)
MODAL_DEPLOY_CMD="${MODAL_DEPLOY_CMD:-modal deploy}"

# Secrets required for unattended smoke (repo-level or runtime-smoke env)
REQUIRED_SECRETS=(BAYYINAH_ENDPOINT MIHWAR_ENDPOINT BAYYINAH_API_TOKEN MIHWAR_API_TOKEN)

# ----------------- HELPERS -----------------
err() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "INFO: $*"; }

# ----------------- PRECHECKS -----------------
command -v gh >/dev/null 2>&1 || err "gh CLI not found. ثبت gh وسجّل الدخول (gh auth login)."
command -v curl >/dev/null 2>&1 || err "curl غير موجود."
command -v jq >/dev/null 2>&1 || info "jq غير مثبت؛ المخرجات ستكون نصية."

# Ensure gh auth
if ! gh auth status >/dev/null 2>&1; then
  info "gh غير مسجّل. حاول gh auth login أو عيّن GITHUB_TOKEN env."
fi

# ----------------- 1) تحقق من Ollama ووجود النموذج -----------------
info "التحقق من Ollama على $OLLAMA_URL ..."
set +e
models_json="$(curl -sS --max-time 10 "${OLLAMA_URL}/v1/models" 2>/dev/null || true)"
curl_rc=$?
set -e
if [[ $curl_rc -ne 0 || -z "$models_json" ]]; then
  err "تعذر الوصول إلى Ollama على ${OLLAMA_URL}. شغّل 'ollama serve' ثم أعد المحاولة."
fi

if command -v jq >/dev/null 2>&1; then
  if echo "$models_json" | jq -e --arg m "$MODEL_NAME" 'index($m) | . >= 0' >/dev/null 2>&1; then
    info "النموذج $MODEL_NAME موجود في Ollama."
  else
    info "النموذج $MODEL_NAME غير موجود. النماذج المتاحة:"
    echo "$models_json" | jq .
    info "إذا كان النموذج مفقودًا، حمّله إلى Ollama أو عدّل MODEL_NAME."
  fi
else
  echo "$models_json"
fi

# ----------------- 2) تأكد من وجود الأسرار في المستودع (أو أنشئها) -----------------
info "التحقق من أسرار المستودع المطلوبة..."
for s in "${REQUIRED_SECRETS[@]}"; do
  if gh secret list --repo "$GITHUB_REPO" 2>/dev/null | grep -q "^$s$"; then
    info "Secret $s موجود في $GITHUB_REPO."
  else
    info "Secret $s غير موجود في $GITHUB_REPO."
    # حاول قراءة من env محلي أولاً
    val="${!s:-}"
    if [[ -z "$val" ]]; then
      read -r -p "أدخل قيمة $s (لن تُعرض): " -s val
      echo
    fi
    if [[ -n "$val" ]]; then
      echo "$val" | gh secret set "$s" --repo "$GITHUB_REPO" --body-file - >/dev/null
      info "تم تعيين Secret $s في repo."
    else
      err "لم تُقدّم قيمة لـ $s؛ لا يمكن المتابعة."
    fi
  fi
done

# ----------------- 3) (اختياري) نشر Modal إذا كان CLI متوفر -----------------
if command -v modal >/dev/null 2>&1; then
  info "Modal CLI موجود. محاولة تشغيل: $MODAL_DEPLOY_CMD"
  set +e
  $MODAL_DEPLOY_CMD
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    info "أمر Modal أعاد $rc — تابع يدويًا إذا لزم."
  else
    info "Modal deploy انتهى بنجاح."
  fi
else
  info "Modal CLI غير موجود؛ تخطّي خطوة النشر."
fi

# ----------------- 4) شغّل الـ workflow: أولاً unattended smoke (بدون ACTIVATE) ثم (اختياري) ACTIVATE deploy -----------------
info "Dispatch: تشغيل smoke unattended (push/schedule يعتمدان على إعدادات workflow)."
gh workflow run "$WORKFLOW_FILE" --repo "$GITHUB_REPO" --ref "$REF_BRANCH"
info "تم إرسال طلب smoke unattended. الآن سننتظر ظهور run يحتوي FINAL_STATUS=VERIFIED_ENDPOINT_SMOKE."

# Polling: نبحث عن أحدث run للـ workflow ونفحص الـ logs حتى يظهر FINAL_STATUS أو ينتهي الوقت
end_time=$(( $(date +%s) + MAX_POLL_MINUTES*60 ))
info "مراقبة آخر run لمدة أقصاها ${MAX_POLL_MINUTES} دقيقة..."

while true; do
  # احصل آخر run id للـ workflow
  run_info="$(gh run list --repo "$GITHUB_REPO" --workflow "$WORKFLOW_FILE" --limit 1 --json databaseId,event,conclusion,createdAt 2>/dev/null || true)"
  if [[ -z "$run_info" ]]; then
    info "لم يتم العثور على run بعد. الانتظار ${RETRY_SLEEP}s..."
    sleep "$RETRY_SLEEP"
  else
    run_id="$(echo "$run_info" | jq -r '.[0].databaseId')"
    run_conclusion="$(echo "$run_info" | jq -r '.[0].conclusion')"
    run_event="$(echo "$run_info" | jq -r '.[0].event')"
    info "أحدث run: id=$run_id event=$run_event conclusion=$run_conclusion"
    if [[ "$run_id" != "null" && -n "$run_id" ]]; then
      # جلب الـ logs والبحث عن FINAL_STATUS
      info "جلب logs للـ run $run_id ..."
      # gh run view <id> --log يطبع logs؛ نبحث عن FINAL_STATUS
      if gh run view "$run_id" --repo "$GITHUB_REPO" --log 2>/dev/null | grep -q "FINAL_STATUS="; then
        final_line="$(gh run view "$run_id" --repo "$GITHUB_REPO" --log 2>/dev/null | grep "FINAL_STATUS=" | tail -n1)"
        info "Found: $final_line"
        if echo "$final_line" | grep -q "VERIFIED_ENDPOINT_SMOKE"; then
          echo "FINAL_STATUS=VERIFIED_ENDPOINT_SMOKE"
          info "التحقق ناجح: الوكلاء والنماذج live."
          exit 0
        else
          info "حالة نهائية مختلفة: $final_line"
          # إذا كانت UNVERIFIED_SECRET_MISSING أو UNVERIFIED_HTTP_* نخرج برمز خطأ
          if echo "$final_line" | grep -qE "UNVERIFIED_"; then
            err "Smoke انتهى بحالة غير VERIFIED: $final_line"
          fi
        fi
      else
        info "لم يُكتب FINAL_STATUS بعد في logs. الانتظار ${RETRY_SLEEP}s..."
      fi
    fi
  fi

  if (( $(date +%s) > end_time )); then
    err "انتهى وقت الانتظار (${MAX_POLL_MINUTES} دقيقة) دون ظهور FINAL_STATUS=VERIFIED_ENDPOINT_SMOKE."
  fi
  sleep "$RETRY_SLEEP"
done

# ----------------- 5) (اختياري) شغّل الـ deploy المحمي عبر workflow_dispatch مع ACTIVATE -----------------
# ملاحظة: هذا الجزء لن يُنفّذ تلقائيًا في نفس run أعلاه؛ نفّذه يدويًا عند التأكد من readiness.
# مثال:
# gh workflow run "$WORKFLOW_FILE" --repo "$GITHUB_REPO" --ref "$REF_BRANCH" -f ACTIVATE=ACTIVATE
