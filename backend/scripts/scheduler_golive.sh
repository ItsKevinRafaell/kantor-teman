#!/usr/bin/env bash
# scheduler_golive.sh — eksekutor one-shot runbook go-live scheduler prod Kantor Teman.
#
# Sumber kanonis urutan: PRODUCTION.md § "Runbook Go-Live Scheduler Prod"
# dan § "Runbook aktivasi worker scheduler". Skrip ini HANYA membungkus urutan
# itu persis — tidak menambah langkah, tidak mengubah urutan.
#
# GATE (anti-eksekusi-kecelakaan):
#   Semua perintah yang MENGGANTI state prod (deploy-code, activate, rollback)
#   MENOLAK jalan kecuali env  KT_SCHED_GOLIVE_ACK=deploy  — memaksa operator
#   (Kevin / agent dengan ACC Kevin) menuliskan kata "deploy" secara eksplisit,
#   sama seperti runbook. Cron/agent tanpa ACC = exit 3, zero mutasi.
#
# Perintah:
 #   status      read-only penuh (SSH cat/ls/crontab -l + health HTTPS)
 #   check       cocokkan konstanta crontab vs preflight_scheduler_deploy.py (lokal)
#   upload      [GATE] jalur upload first-enable (PRODUCTION.md § Jalur Upload
#               First-Enable): 3 file kanonis via deploy_kantorteman.sh
#               --file <abs> --no-restart (berhenti di kegagalan pertama),
#               lalu verifikasi ukuran remote == lokal per file.
 #   deploy-code [GATE] git-pull kanonis di server (bash deploy.sh) + health + --probe
#   activate    [GATE] pasang crontab kanonis --once (idempotent) + 1x run manual
#               --once via flock → bukti log segera, tanpa nunggu menit :20
#   verify      read-only: tail scheduler-worker.log + cek entry crontab
#   rollback    [GATE] hapus entry crontab scheduler (1 baris). .env/Passenger tak disentuh.
#
# Pemakaian contoh (SAAT Kevin menulis "deploy"):
#   KT_SCHED_GOLIVE_ACK=deploy bash scripts/scheduler_golive.sh deploy-code
#   KT_SCHED_GOLIVE_ACK=deploy bash scripts/scheduler_golive.sh activate
#   bash scripts/scheduler_golive.sh status
#   bash scripts/scheduler_golive.sh verify
set -euo pipefail

SSH_HOST="deploy-kantorteman"
SERVER_DIR="/home/qqwtlphb/backend"
VENV_PY="/home/qqwtlphb/virtualenv/backend/3.13/bin/python"
WORKER="${SERVER_DIR}/scripts/run_scheduler_worker.py"
LOG="${SERVER_DIR}/scheduler-worker.log"
CRON_MARKER="run_scheduler_worker.py --safe-first --once"
# Mirror kanonik dari preflight_scheduler_deploy.py (CRONTAB_LINE). `check`
# membandingkan otomatis — JANGAN ubah salah satu saja.
CRONTAB_LINE="20 * * * * flock -n /tmp/kt-sched.lock ${VENV_PY} ${WORKER} --safe-first --once >> ${LOG} 2>&1"
#
# Jalur upload first-enable: 3 file kanonis (urutan & mapping persis runbook).
# Deps: deploy_kantorteman.sh (ACK-gate + anti nested-trap + size-verify).
UPLOAD_FILES=(
  "app/schedulers/flags.py"
  "scripts/run_scheduler_worker.py"
  "scripts/__init__.py"
)
DEPLOY_SCRIPT="${GOLIVE_DEPLOY_SCRIPT:-/root/.hermes/shared/scripts/deploy_kantorteman.sh}"

 SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log()  { echo "[GOLIVE] $*"; }
die()  { echo "[GOLIVE] ERROR: $*" >&2; exit 1; }

sshq() {
  # GOLIVE_SSH_CMD: seam test lokal SAJA (default 'ssh'). Prod tak pernah diset.
  "${GOLIVE_SSH_CMD:-ssh}" -o ConnectTimeout=15 -o BatchMode=yes "$SSH_HOST" "$@"
}

gate() {
  if [[ "${KT_SCHED_GOLIVE_ACK:-}" != "deploy" ]]; then
    echo "[GATE] DITOLAK (exit 3): '$1' mengubah state prod. Jalankan hanya dengan" >&2
    echo "       KT_SCHED_GOLIVE_ACK=deploy — dan hanya SETELAH Kevin menulis \"deploy\"." >&2
    exit 3
  fi
  log "ACK 'deploy' diterima — melanjutkan '$1'"
}

cmd_check() {
  local py
  py="$(command -v python3 || command -v python)"
  local got
  got="$(GOLIVE_PF_DIR="$SCRIPT_DIR" "$py" - <<'PYEOF'
import importlib.util, os, pathlib
pf = pathlib.Path(os.environ["GOLIVE_PF_DIR"]) / "preflight_scheduler_deploy.py"
if not pf.is_file():
    raise SystemExit(f"preflight tidak ditemukan: {pf}")
spec = importlib.util.spec_from_file_location("pf_mod", str(pf.resolve()))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(m.CRONTAB_LINE)
PYEOF
)" || die "gagal baca CRONTAB_LINE dari preflight_scheduler_deploy.py"
  if [[ "$got" == "$CRONTAB_LINE" ]]; then
    log "check: konstanta crontab SINKRON dengan preflight_scheduler_deploy.py"
  else
    echo "[GOLIVE] check: GAGAL — konstanta BEDA!" >&2
    echo "  golive:    $CRONTAB_LINE" >&2
    echo "  preflight: $got" >&2
    exit 1
  fi
}

cmd_status() {
  log "status prod (read-only) — $(date '+%F %T %Z')"
  sshq "grep -E 'ENABLE_BACKGROUND_SCHEDULER' ${SERVER_DIR}/.env 2>/dev/null || echo NO_ENV_LINE;
        ls ${SERVER_DIR}/app/schedulers/flags.py ${SERVER_DIR}/scripts/run_scheduler_worker.py ${SERVER_DIR}/scripts/__init__.py 2>&1;
        echo '--- crontab ---'; crontab -l 2>/dev/null | grep -F '${CRON_MARKER}' || echo 'CRON_BELUM_TERPASANG';
        echo '--- log tail ---'; tail -n 5 ${LOG} 2>/dev/null || echo 'LOG_BELUM_ADA';
        echo '--- layout ---';
        echo T=\$(git -C ${SERVER_DIR} rev-parse --show-toplevel 2>/dev/null);
        echo N=\$(git -C ${SERVER_DIR} ls-tree -d --name-only HEAD 2>/dev/null | grep -qx '^backend$' && echo YES || echo NO)"
  curl -s -o /dev/null -w "[GOLIVE] health api.kantorteman.my.id: HTTP %{http_code}\n" \
       --max-time 20 https://api.kantorteman.my.id/api/health
}

cmd_deploy_code() {
  gate deploy-code
  # Layout-trap guard (bukti read-only 1 Sep 2026 ~23:1x WIB): git toplevel di
  # server = /home/qqwtlphb/backend (live root), TAPI tracked tree ber-prefix
  # `backend/` → `git pull` hanya update ~/backend/backend/* (folder nested),
  # BUKAN file live di ~/backend/* (live main.py bahkan untracked). deploy.sh
  # live juga masih panggil `python migrate.py` — python TIDAK ada di jailshell
  # → set -e mati sebelum restart. deploy-code di layout ini = no-op untuk file
  # live → DITOLAK. First-enable kanonis = jalur upload (PRODUCTION.md).
  local toplevel="" nested=""
  toplevel="$(sshq "cd ${SERVER_DIR} && git rev-parse --show-toplevel 2>/dev/null" | grep -v '^\[HERMES-SAFETY\]' | tail -n1 || true)"
  # Deteksi nested layout: cek apakah tracked tree punya folder `backend/` SENDIRI
  # (grep -qx, BUKAN head -n1 — ls-tree diurut alfabetis, entry pertama bisa .claude).
  nested="$(sshq "cd ${SERVER_DIR} && git ls-tree -d --name-only HEAD 2>/dev/null | grep -qx '^backend$' && echo YES || echo NO" | grep -v '^\[HERMES-SAFETY\]' | tail -n1 || true)"
  if [[ "$toplevel" == "$SERVER_DIR" && "$nested" == "YES" \
        && "${KT_SCHED_GOLIVE_FORCE_DEPLOY_CODE:-}" != "1" ]]; then
    die "layout server NESTED (toplevel=${toplevel}, tracked tree punya folder 'backend/'): git pull hanya update ${SERVER_DIR}/backend/* — file live TIDAK ter-update, deploy-code = no-op. First-enable = jalur upload 3 file (PRODUCTION.md § Jalur Upload First-Enable). deploy.sh live juga masih pakai 'python' (absen di jailshell). Kalau deploy.sh sudah diperbaiki (venv python + sync live root) DAN dites, jalankan ulang dengan KT_SCHED_GOLIVE_FORCE_DEPLOY_CODE=1."
  fi
  [[ "${KT_SCHED_GOLIVE_FORCE_DEPLOY_CODE:-}" == "1" ]] && \
    log "PERINGATAN: layout nested terdeteksi, lanjut karena KT_SCHED_GOLIVE_FORCE_DEPLOY_CODE=1"
  log "deploy kanonis: bash deploy.sh di server (git pull + protect .env + migrate + restart)"
  sshq "cd ${SERVER_DIR} && bash deploy.sh"
  log "tunggu health 200 (maks 60s)..."
  local ok=0 i
  for i in $(seq 1 12); do
    if curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://api.kantorteman.my.id/api/health | grep -q 200; then
      ok=1; break
    fi
    sleep 5
  done
  [[ "$ok" == "1" ]] || die "health TIDAK 200 dalam 60s — cek stderr.log di server, rollback = git reset --hard HEAD@{1} + restart"
  log "health 200 OK. Probe worker (read-only, tidak start job):"
  sshq "cd ${SERVER_DIR} && ${VENV_PY} ${WORKER} --probe"
  log "deploy-code SELESAI. Lanjut 'activate' (crontab --once) bila probe exit 0."
}

cmd_upload() {
  gate upload
  [[ -f "$DEPLOY_SCRIPT" ]] || die "deploy_kantorteman.sh tidak ditemukan: $DEPLOY_SCRIPT (set GOLIVE_DEPLOY_SCRIPT atau sinkronkan shared/scripts)"
  local repo_backend
  repo_backend="$(cd "${SCRIPT_DIR}/.." && pwd)"
  local f abs
  for f in "${UPLOAD_FILES[@]}"; do
    abs="${repo_backend}/${f}"
    [[ -f "$abs" ]] || die "file repo tidak ada: $abs (jalankan dari clone kanonis)"
    log "upload kanonis (TANPA restart Passenger): $f"
    KT_DEPLOY_ACK=deploy bash "$DEPLOY_SCRIPT" --file "$abs" --no-restart \
      || die "upload GAGAL pada '$f' — BERHENTI di sini (urutan runbook). Perbaiki dulu, JANGAN lanjut file berikutnya."
  done
  log "verifikasi remote per file (ukuran byte remote == lokal, bukti file utuh):"
  local lsize rsize ok_all=1
  for f in "${UPLOAD_FILES[@]}"; do
    abs="${repo_backend}/${f}"
    lsize="$(wc -c < "$abs")"
    rsize="$(sshq "stat -c%s '${SERVER_DIR}/${f}' 2>/dev/null || echo MISSING" | grep -v '^\[HERMES-SAFETY\]' | tail -n1)"
    if [[ -z "$rsize" || "$rsize" == "MISSING" ]]; then
      echo "[GOLIVE] verify: FAIL — $f TIDAK ADA di server" >&2
      ok_all=0
    elif [[ "$rsize" != "$lsize" ]]; then
      echo "[GOLIVE] verify: FAIL — $f ukuran remote (${rsize}B) != lokal (${lsize}B)" >&2
      ok_all=0
    else
      log "verify OK: $f (${rsize}B remote == lokal)"
    fi
  done
  [[ "$ok_all" == "1" ]] || die "verifikasi remote GAGAL — jangan lanjut activate. Cek output di atas."
  log "upload SELESAI (3/3 terverifikasi). Lanjut: status → activate (ACK) → verify."
}

cmd_activate() {
  gate activate
  log "pasang crontab kanonis (idempotent)..."
  sshq "crontab -l 2>/dev/null | grep -Fq '${CRON_MARKER}' && echo CRONTAB_SUDAH_ADA || \
        { { crontab -l 2>/dev/null; echo '${CRONTAB_LINE}'; } | crontab -; echo CRONTAB_TERPASANG; }"
  log "run 1x manual --once via flock (bukti log segera, process-local, .env tak disentuh)..."
  sshq "flock -n /tmp/kt-sched.lock ${VENV_PY} ${WORKER} --safe-first --once >> ${LOG} 2>&1; tail -n 10 ${LOG}"
  log "activate SELESAI. Verifikasi: bash scripts/scheduler_golive.sh verify"
}

cmd_verify() {
  log "verifikasi bukti jalan (read-only)"
  sshq "echo '--- crontab ---'; crontab -l 2>/dev/null | grep -F '${CRON_MARKER}' || echo CRON_BELUM_TERPASANG;
        echo '--- log ---'; grep -E 'SCHEDULER|once selesai' ${LOG} 2>/dev/null | tail -n 15 || echo LOG_BELUM_ADA"
}

cmd_rollback() {
  gate rollback
  log "rollback: hapus entry crontab scheduler (satu-satunya state yang diubah runbook ini)"
  sshq "crontab -l 2>/dev/null | grep -Fv '${CRON_MARKER}' | crontab - && echo CRONTAB_SCHEDULER_DIHAPUS"
}

case "${1:-}" in
  status)     cmd_status ;;
  check)      cmd_check ;;
  upload)     cmd_upload ;;
  deploy-code) cmd_deploy_code ;;
  activate)   cmd_activate ;;
  verify)     cmd_verify ;;
  rollback)   cmd_rollback ;;
  ""|-h|--help)
    grep '^#   ' "$0" | sed 's/^#   //'
    ;;
  *) die "perintah tidak dikenal: $1 (lihat: bash scripts/scheduler_golive.sh)" ;;
esac
