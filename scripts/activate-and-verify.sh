#!/usr/bin/env bash
set -euo pipefail

# ----------------- CONFIG (عدل أو عيّن كـ env vars قبل التشغيل) -----------------
GITHUB_REPO="${GITHUB_REPO:-CurLexAI/swarms}"
WORKFLOW_FILE="${WORKFLOW_FILE:-modal-runtime-auto-activation.yml}"
REF_BRANCH="${REF_BRANCH:-main}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
MODEL_NAME="${MODEL_NAME:-qwen2.5:0.5b}"
RETRY_SLEEP="${RETRY_SLEEP:-5}"
MAX_POLL_MINUTES="${MAX_POLL_MINUTES:-10}"
# Optional: modal deploy command (set MODAL_DEPLOY_CMD env to override)
MODAL_DEPLOY_CMD="${MODAL_DEPLOY_CMD:-modal deploy .agents/modal_app.py}"

# Secrets required for unattended smoke (repo-level or runtime-smoke env)
REQUIRED_SECRETS=(BAYYINAH_ENDPOINT MIHWAR_ENDPOINT BAYYINAH_API_TOKEN MIHWAR_API_TOKEN)

# ----------------- HELPERS -----------------
err() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "INFO: $*"; }
job_field() {
  local jobs_json="$1"
  local job_name="$2"
  local field="$3"
  echo "$jobs_json" | jq -r --arg job "$job_name" --arg field "$field" \
    '.jobs[]? | select(.name == $job) | .[$field] // empty' | tail -n1
}
step_conclusion() {
  local jobs_json="$1"
  local job_name="$2"
  local step_name="$3"
  echo "$jobs_json" | jq -r --arg job "$job_name" --arg step "$step_name" \
    '.jobs[]? | select(.name == $job) | .steps[]? | select(.name == $step) | .conclusion // empty' | tail -n1
}

# ----------------- PRECHECKS -----------------
command -v gh >/dev/null 2>&1 || err "gh CLI not found. ثبت gh وسجّل الدخول (gh auth login)."
command -v curl >/dev/null 2>&1 || err "curl غير موجود."
command -v jq >/dev/null 2>&1 || err "jq CLI not found. ثبّت jq لأن السكربت يعتمد عليه لتحليل مخرجات gh."

# Ensure gh auth — exit immediately if not authenticated
if ! gh auth status >/dev/null 2>&1; then
  err "gh غير مسجّل. نفّذ 'gh auth login' أو عيّن GITHUB_TOKEN/GH_TOKEN قبل التشغيل."
fi

# ----------------- 1) تحقق من Ollama ووجود النموذج (اختياري — عيّن SKIP_OLLAMA=1 للتخطّي) -----------------
if [[ "${SKIP_OLLAMA:-0}" == "1" ]]; then
  info "SKIP_OLLAMA=1 — تخطّي فحص Ollama المحلي."
else
  info "التحقق من Ollama على $OLLAMA_URL (عيّن SKIP_OLLAMA=1 للتخطّي)..."
  set +e
  models_json="$(curl -sS --max-time 10 "${OLLAMA_URL}/api/tags" 2>/dev/null)"
  curl_rc=$?
  set -e
  if [[ $curl_rc -ne 0 || -z "$models_json" ]]; then
    info "تعذر الوصول إلى Ollama على ${OLLAMA_URL}. إذا لم تكن بحاجة لفحص Ollama، عيّن SKIP_OLLAMA=1."
  else
    if echo "$models_json" | jq -e --arg m "$MODEL_NAME" 'any(.models[]?; .name == $m or (.name | startswith($m)))' >/dev/null 2>&1; then
      info "النموذج $MODEL_NAME موجود في Ollama."
    else
      info "النموذج $MODEL_NAME غير موجود. النماذج المتاحة:"
      echo "$models_json" | jq -r '.models[]?.name // empty'
      info "إذا كان النموذج مفقودًا، حمّله إلى Ollama أو عدّل MODEL_NAME."
    fi
  fi
fi

# ----------------- 2) تأكد من وجود الأسرار في المستودع (فحص فقط؛ عيّن SET_SECRETS=1 لإنشائها) -----------------
info "التحقق من أسرار المستودع المطلوبة..."
missing_secrets=()
for s in "${REQUIRED_SECRETS[@]}"; do
  if gh secret list --repo "$GITHUB_REPO" --json name --jq '.[].name' 2>/dev/null | grep -Fxq "$s"; then
    info "Secret $s موجود في $GITHUB_REPO."
  else
    missing_secrets+=("$s")
  fi
done

if [[ ${#missing_secrets[@]} -gt 0 ]]; then
  info "أسرار مفقودة: ${missing_secrets[*]}"
  if [[ "${SET_SECRETS:-0}" == "1" ]]; then
    for s in "${missing_secrets[@]}"; do
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
    done
  else
    info "لتعيين الأسرار المفقودة تفاعليًا، أعد التشغيل مع SET_SECRETS=1."
    info "قد تكون الأسرار معرّفة على مستوى Organization — راجع docs/secrets-policy.md."
  fi
fi

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
dispatch_time="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
gh workflow run "$WORKFLOW_FILE" --repo "$GITHUB_REPO" --ref "$REF_BRANCH" -f confirm=SMOKE
info "تم إرسال طلب smoke unattended. الآن سننتظر نتيجة endpoint-smoke-verification عبر GitHub Actions API."

# Polling: نبحث عن run الخاص بالـ workflow ونفحص حالة jobs/steps حتى ينتهي الوقت
end_time=$(( $(date +%s) + MAX_POLL_MINUTES*60 ))
info "مراقبة آخر run لمدة أقصاها ${MAX_POLL_MINUTES} دقيقة..."

while true; do
  # احصل آخر run id للـ workflow
  run_info="$(gh run list --repo "$GITHUB_REPO" --workflow "$WORKFLOW_FILE" --event workflow_dispatch --branch "$REF_BRANCH" --limit 10 --json databaseId,event,status,conclusion,createdAt 2>/dev/null || true)"
  if [[ -z "$run_info" ]]; then
    info "لم يتم العثور على run بعد. الانتظار ${RETRY_SLEEP}s..."
    sleep "$RETRY_SLEEP"
  else
    run="$(echo "$run_info" | jq -c --arg since "$dispatch_time" \
      '((map(select(.createdAt >= $since)) | sort_by(.createdAt) | last) // {})')"
    run_id="$(echo "$run" | jq -r '.databaseId // empty')"
    run_status="$(echo "$run" | jq -r '.status // "unknown"')"
    run_conclusion="$(echo "$run" | jq -r '.conclusion // ""')"
    run_event="$(echo "$run" | jq -r '.event // ""')"
    info "أحدث run: id=$run_id event=$run_event status=$run_status conclusion=${run_conclusion:-pending}"
    if [[ "$run_id" == "null" || -z "$run_id" ]]; then
      info "لم يظهر run المرسل بعد. الانتظار ${RETRY_SLEEP}s..."
    else
      jobs_json="$(gh api "repos/${GITHUB_REPO}/actions/runs/${run_id}/jobs" 2>/dev/null || true)"
      if [[ -z "$jobs_json" ]]; then
        info "لم تظهر jobs للـ run بعد. الانتظار ${RETRY_SLEEP}s..."
        sleep "$RETRY_SLEEP"
        continue
      fi

      preflight_conclusion="$(job_field "$jobs_json" "activation-preflight" "conclusion")"
      smoke_status="$(job_field "$jobs_json" "endpoint-smoke-verification" "status")"
      smoke_conclusion="$(job_field "$jobs_json" "endpoint-smoke-verification" "conclusion")"
      secret_step="$(step_conclusion "$jobs_json" "endpoint-smoke-verification" "Check endpoint smoke secrets")"
      endpoint_step="$(step_conclusion "$jobs_json" "endpoint-smoke-verification" "Run endpoint smoke")"
      summary_step="$(step_conclusion "$jobs_json" "endpoint-smoke-verification" "Verification summary")"

      info "preflight=${preflight_conclusion:-pending} smoke_status=${smoke_status:-pending} smoke=${smoke_conclusion:-pending} secrets=${secret_step:-pending} endpoint=${endpoint_step:-pending} summary=${summary_step:-pending}"

      if [[ "$preflight_conclusion" == "failure" || "$preflight_conclusion" == "cancelled" || "$preflight_conclusion" == "timed_out" ]]; then
        err "Preflight فشل قبل تشغيل endpoint smoke. راجع run $run_id."
      fi

      if [[ "$smoke_status" == "completed" ]]; then
        if [[ "$smoke_conclusion" == "success" && "$endpoint_step" == "success" ]]; then
          echo "FINAL_STATUS=VERIFIED_ENDPOINT_SMOKE"
          info "التحقق ناجح: الوكلاء والنماذج live."
          exit 0
        fi
        if [[ "$smoke_conclusion" == "success" && "$endpoint_step" == "skipped" ]]; then
          err "FINAL_STATUS=UNVERIFIED_SECRET_MISSING: أسرار endpoint smoke غير مكتملة في $GITHUB_REPO."
        fi
        if [[ "$summary_step" == "failure" || "$smoke_conclusion" == "failure" ]]; then
          err "FINAL_STATUS=BLOCKED_MODAL_FAILURE: endpoint smoke فشل في run $run_id."
        fi
        if [[ "$smoke_conclusion" == "skipped" ]]; then
          err "Smoke job skipped؛ تأكد من أن confirm=SMOKE وأن preflight مر بنجاح في run $run_id."
        fi
      fi

      info "الـ run لا يزال قيد التنفيذ. الانتظار ${RETRY_SLEEP}s..."
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
# gh workflow run "$WORKFLOW_FILE" --repo "$GITHUB_REPO" --ref "$REF_BRANCH" -f confirm=ACTIVATE
