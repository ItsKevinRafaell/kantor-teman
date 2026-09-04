#!/usr/bin/env bash
# ============================================================================
# Test harness 0-SSH untuk scheduler_golive.sh — Kantorteman backend
#
# Membuktikan perilaku gerbang & mode read-only TANPA menyentuh prod:
#   - GATE: upload/deploy-code/activate/rollback TANPA KT_SCHED_GOLIVE_ACK=deploy
#     harus exit 3 dengan NOL panggilan SSH (zero mutasi).
#   - check: konstanta crontab golive SINKRON dengan preflight_scheduler_deploy.py.
#   - status/verify: hanya perintah read-only (grep/ls/crontab -l/tail/git).
#   - deploy-code: layout-trap nested DITOLAK sebelum deploy.sh terpanggil.
#   - activate: baris crontab kanonis --once + flock persis runbook.
#   - upload: 3 file kanonis berurutan --no-restart + stop-on-first-failure
#     + verifikasi ukuran remote == lokal (mock stat via ukuran file lokal).
#
# Semua jaringan di-mock: GOLIVE_SSH_CMD (ssh), PATH shim curl, GOLIVE_DEPLOY_SCRIPT.
# Jalankan:  bash backend/scripts/test_scheduler_golive_sh.sh
# Output:    "TEST n: <nama> — PASS/FAIL" + ringkasan N/N. Exit 0 = semua pass.
# ============================================================================
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GOLIVE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scheduler_golive.sh"

PASS=0; FAIL=0; N=0
SBX="" BIN="" SSHLOG="" CURLLOG="" UPLOADLOG=""
OUT=""; RC=0

report() { # $1=nama $2=ok(0 pass) $3=detail
  N=$((N+1))
  if [ "$2" = "0" ]; then
    PASS=$((PASS+1)); echo "TEST $N: $1 — PASS"
  else
    FAIL=$((FAIL+1))
    echo "TEST $N: $1 — FAIL: ${3:-}"
    echo "   [debug] rc=$RC out_tail=$(printf '%s' "$OUT" | tail -3 | tr '\n' '|')"
  fi
}
ssh_calls() { [ -f "$SSHLOG" ] && wc -l < "$SSHLOG" | tr -d ' ' || echo 0; }

cleanup_sbx() { [ -n "${SBX:-}" ] && [ -d "$SBX" ] && rm -rf "$SBX"; }
trap 'cleanup_sbx' EXIT

new_sbx() {
  cleanup_sbx
  SBX="$(mktemp -d /tmp/kt-golivetest-XXXXXX)"
  BIN="$SBX/bin"; mkdir -p "$BIN"
  SSHLOG="$SBX/ssh.log"; CURLLOG="$SBX/curl.log"; UPLOADLOG="$SBX/upload.log"
  : > "$SSHLOG"

  # --- mock ssh: log + respon sesuai KT_SSH_* ---
  cat > "$BIN/mockssh" <<'SH'
#!/bin/bash
cmd="${@: -1}"   # argumen terakhir = command string (setelah host)
{ printf 'CMD::%s\n' "$cmd"; } >> "${KT_SSH_LOG:?}"
case "$cmd" in
  *rev-parse*--show-toplevel*) echo "${KT_SSH_TOPLEVEL:-}"; exit 0 ;;
  *ls-tree*)                   echo "${KT_SSH_NESTED:-NO}";  exit 0 ;;
  *stat\ -c%s*)
    rel="$(printf '%s' "$cmd" | sed -n "s|^stat -c%s '\?${KT_SERVER_DIR:-/home/qqwtlphb/backend}/\([^']*\)'.*|\1|p")"
    if [ -n "$rel" ] && [ -f "${KT_REPO_BACKEND:?}/$rel" ]; then
      wc -c < "${KT_REPO_BACKEND}/$rel"
    else
      echo MISSING
    fi
    exit 0 ;;
  *) echo MOCK_OK; exit 0 ;;
esac
SH
  chmod +x "$BIN/mockssh"

  # --- mock curl: log + echo 200 ---
  cat > "$BIN/curl" <<'SH'
#!/bin/bash
printf 'CURL::%s\n' "$*" >> "${KT_CURL_LOG:?}"
echo 200
exit 0
SH
  chmod +x "$BIN/curl"

  ENVBASE=(env PATH="$BIN:$PATH" \
    KT_SSH_LOG="$SSHLOG" KT_CURL_LOG="$CURLLOG" KT_REPO_BACKEND="$REPO_ROOT/backend" \
    GOLIVE_SSH_CMD="$BIN/mockssh" GOLIVE_DEPLOY_SCRIPT="$SBX/mockdeploy.sh")
  : > "$UPLOADLOG"
}

run_golive() { # "$@" = env-modifier tambahan; GOLIVE_ARGS = command
  OUT="$("${ENVBASE[@]}" "$@" bash "$GOLIVE" "${GOLIVE_ARGS[@]}" 2>&1)"
  RC=$?
}

# mock deploy script dibuat per-skenario
make_mockdeploy() { # $1 = "0" | "fail2" (gagal di file ke-2)
  cat > "$SBX/mockdeploy.sh" <<SH
#!/bin/bash
printf 'DEPLOY::%s::ACK=%s\n' "\$*" "\${KT_DEPLOY_ACK-}" >> "\${KT_UPLOAD_LOG:?}"
case "${1:-0}" in
  fail2) n=\$(grep -c . "\${KT_UPLOAD_LOG:?}"); [ "\$n" -ge 2 ] && exit 1 ;;
esac
exit 0
SH
  chmod +x "$SBX/mockdeploy.sh"
}

# ============================================================================
# TEST 1-4: GATE default-deny — 4 perintah pengubah state tanpa ACK
# ============================================================================
for cmdname in upload deploy-code activate rollback; do
  new_sbx
  GOLIVE_ARGS=("$cmdname")
  run_golive env -u KT_SCHED_GOLIVE_ACK
  ok=0
  [ "$RC" = "3" ] || ok=1
  printf '%s' "$OUT" | grep -qF "[GATE] DITOLAK" || ok=1
  [ "$(ssh_calls)" = "0" ] || ok=1
  report "gate default-deny: $cmdname (exit 3, 0 panggilan ssh)" "$ok"
done

# ============================================================================
# TEST 5: check — konstanta crontab sinkron dengan preflight
# ============================================================================
new_sbx
GOLIVE_ARGS=(check); run_golive
ok=0
[ "$RC" = "0" ] || ok=1
printf '%s' "$OUT" | grep -qF "SINKRON" || ok=1
report "check: konstanta crontab golive == preflight" "$ok"

# ============================================================================
# TEST 6: status — read-only penuh (ssh hanya grep/ls/crontab -l/tail/git)
# ============================================================================
new_sbx
GOLIVE_ARGS=(status); run_golive
ok=0
[ "$RC" = "0" ] || ok=1
S="$(cat "$SSHLOG" 2>/dev/null)"
printf '%s' "$S" | grep -qF "ENABLE_BACKGROUND_SCHEDULER" || ok=1
printf '%s' "$S" | grep -qF "crontab -l" || ok=1
printf '%s' "$S" | grep -qF "tail -n 5" || ok=1
printf '%s' "$S" | grep -qF "rev-parse --show-toplevel" || ok=1
# anti-mutasi: tidak ada flock/worker/deploy.sh/redirect crontab di panggilan ssh
printf '%s' "$S" | grep -qF "flock" && ok=1
printf '%s' "$S" | grep -qF "deploy.sh" && ok=1
printf '%s' "$S" | grep -q "| crontab -" && ok=1
# health via curl mock ke URL kanonis
printf '%s' "$(cat "$CURLLOG" 2>/dev/null)" | grep -qF "api.kantorteman.my.id/api/health" || ok=1
report "status: ssh read-only + health URL kanonis, 0 mutasi" "$ok"

# ============================================================================
# TEST 7: deploy-code — layout nested DITOLAK sebelum deploy.sh terpanggil
# ============================================================================
new_sbx
GOLIVE_ARGS=(deploy-code)
OUT="$("${ENVBASE[@]}" KT_SCHED_GOLIVE_ACK=deploy \
  KT_SSH_TOPLEVEL="/home/qqwtlphb/backend" KT_SSH_NESTED=YES \
  bash "$GOLIVE" deploy-code 2>&1)"; RC=$?
ok=0
[ "$RC" != "0" ] || ok=1
printf '%s' "$OUT" | grep -qF "NESTED" || ok=1
printf '%s' "$(cat "$SSHLOG")" | grep -qF "bash deploy.sh" && ok=1
report "deploy-code: nested-layout guard menolak sebelum deploy.sh" "$ok"

# ============================================================================
# TEST 8: activate — ACK lolos, baris crontab kanonis persis runbook
# ============================================================================
new_sbx
GOLIVE_ARGS=(activate)
OUT="$("${ENVBASE[@]}" KT_SCHED_GOLIVE_ACK=deploy \
  bash "$GOLIVE" activate 2>&1)"; RC=$?
CANON="20 * * * * flock -n /tmp/kt-sched.lock /home/qqwtlphb/virtualenv/backend/3.13/bin/python /home/qqwtlphb/backend/scripts/run_scheduler_worker.py --safe-first --once >> /home/qqwtlphb/backend/scheduler-worker.log 2>&1"
ok=0
[ "$RC" = "0" ] || ok=1
S="$(cat "$SSHLOG")"
printf '%s' "$S" | grep -qF "run_scheduler_worker.py --safe-first --once" || ok=1
printf '%s' "$S" | grep -qF "$CANON" || ok=1
printf '%s' "$S" | grep -qF "flock -n /tmp/kt-sched.lock" || ok=1
[ "$(ssh_calls)" -ge 2 ] || ok=1
report "activate: ACK lolos + baris crontab kanonis --once + flock" "$ok"

# ============================================================================
# TEST 9: verify — read-only (crontab -l + grep log), tanpa mutasi
# ============================================================================
new_sbx
GOLIVE_ARGS=(verify)
OUT="$("${ENVBASE[@]}" bash "$GOLIVE" verify 2>&1)"; RC=$?
ok=0
[ "$RC" = "0" ] || ok=1
S="$(cat "$SSHLOG")"
printf '%s' "$S" | grep -qF "crontab -l" || ok=1
printf '%s' "$S" | grep -q "| crontab -" && ok=1
printf '%s' "$S" | grep -qF "once selesai" || ok=1
report "verify: read-only crontab+log, 0 mutasi" "$ok"

# ============================================================================
# TEST 10: rollback — hanya rewrite crontab (grep -Fv marker), .env tak disentuh
# ============================================================================
new_sbx
GOLIVE_ARGS=(rollback)
OUT="$("${ENVBASE[@]}" KT_SCHED_GOLIVE_ACK=deploy \
  bash "$GOLIVE" rollback 2>&1)"; RC=$?
ok=0
[ "$RC" = "0" ] || ok=1
S="$(cat "$SSHLOG")"
printf '%s' "$S" | grep -qF "grep -Fv" || ok=1
printf '%s' "$S" | grep -qF "run_scheduler_worker.py --safe-first --once" || ok=1
printf '%s' "$S" | grep -qF ".env" && ok=1
printf '%s' "$S" | grep -qF "rm " && ok=1
report "rollback: cuma hapus entry crontab, .env/rm tidak disentuh" "$ok"

# ============================================================================
# TEST 11: upload — 3 file kanonis berurutan --no-restart + verify ukuran OK
# ============================================================================
new_sbx
make_mockdeploy 0
GOLIVE_ARGS=(upload)
OUT="$("${ENVBASE[@]}" KT_UPLOAD_LOG="$UPLOADLOG" KT_SCHED_GOLIVE_ACK=deploy \
  bash "$GOLIVE" upload 2>&1)"; RC=$?
ok=0
[ "$RC" = "0" ] || ok=1
U="$(cat "$UPLOADLOG" 2>/dev/null)"
printf '%s' "$U" | grep -qF -e "--file $REPO_ROOT/backend/app/schedulers/flags.py" || ok=1
printf '%s' "$U" | grep -qF -e "--file $REPO_ROOT/backend/scripts/run_scheduler_worker.py" || ok=1
printf '%s' "$U" | grep -qF -e "--file $REPO_ROOT/backend/scripts/__init__.py" || ok=1
printf '%s' "$U" | grep -qF "ACK=deploy" || ok=1
printf '%s' "$U" | grep -qF "KT_DEPLOY_ACK" && ok=1   # ACK lewat env, bukan argv
# urutan kanonis: flags sebelum worker
f1="$(printf '%s' "$U" | grep -nF "flags.py" | head -1 | cut -d: -f1)"
f2="$(printf '%s' "$U" | grep -nF "run_scheduler_worker.py" | head -1 | cut -d: -f1)"
{ [ -n "$f1" ] && [ -n "$f2" ] && [ "$f1" -lt "$f2" ]; } || ok=1
printf '%s' "$OUT" | grep -qF "upload SELESAI (3/3" || ok=1
# verifikasi ukuran: mock stat pakai ukuran file lokal → semua verify OK
[ "$(printf '%s' "$OUT" | grep -cF "verify OK")" = "3" ] || ok=1
printf '%s' "$U" | grep -qF -e "--no-restart" || ok=1
report "upload: 3 file kanonis --no-restart + verify ukuran 3/3" "$ok"

# ============================================================================
# TEST 12: upload — gagal di file ke-2 BERHENTI (file ke-3 tak diuploud)
# ============================================================================
new_sbx
make_mockdeploy fail2
GOLIVE_ARGS=(upload)
OUT="$("${ENVBASE[@]}" KT_UPLOAD_LOG="$UPLOADLOG" KT_SCHED_GOLIVE_ACK=deploy \
  bash "$GOLIVE" upload 2>&1)"; RC=$?
ok=0
[ "$RC" != "0" ] || ok=1
[ "$(printf '%s' "$(cat "$UPLOADLOG")" | grep -cF "DEPLOY::")" = "2" ] || ok=1
printf '%s' "$OUT" | grep -qF "BERHENTI" || ok=1
printf '%s' "$OUT" | grep -qF "upload SELESAI" && ok=1
report "upload: stop-on-first-failure (file ke-3 tidak diuploud)" "$ok"

# ============================================================================
echo "----------------------------------------------------------------"
echo "RINGKASAN: $PASS/$N PASS, $FAIL FAIL"
[ "$FAIL" = "0" ]
