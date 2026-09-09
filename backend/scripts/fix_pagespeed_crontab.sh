#!/usr/bin/env bash
# fix_pagespeed_crontab.sh — perbaiki 1 baris crontab pagespeed prod Kantor Teman.
#
# Latar (PRODUCTION.md § PageSpeed Scoring Lead): baris live masih versi rusak
#   `flock -n /tmp/kt-pagespeed.lock cd /home/... && python ...`
# `cd` adalah shell BUILTIN — flock exec gagal exit 69 → cron Senin 09:07 no-op
# diam-diam (bukti 7 Sep: lock mtime 09:07, logs/ kosong, 0/148 lead berskor).
# Kanonis (PRODUCTION.md 293): TANPA cd — run_pagespeed_recheck.py chdir sendiri.
#
# Perintah:
#   status   read-only: baris pagespeed di crontab prod + verdict (CANONICAL/BUGGY/ABSENT)
#            + lock mtime + log tail. Zero mutasi.
#   fix      [GATE] backup crontab lalu ganti SEMUA baris pagespeed non-kanonis
#            dengan 1 baris kanonis (idempotent: kanonis yang sudah ada dipelihara,
#            duplikat dirapikan). Tanpa KT_PAGESPEED_FIX_ACK=deploy → exit 3, zero mutasi.
#   verify   read-only: baris kanonis ada & buggy absen + tail log.
#
# GATE (anti-eksekusi-kecelakaan, pola scheduler_golive.sh):
#   'fix' MENOLAK jalan kecuali KT_PAGESPEED_FIX_ACK=deploy — memaksa kata
#   "deploy" ditulis eksplisit oleh operator (Kevin / agent dgn ACC Kevin).
#
# Seam test lokal: PAGESPEED_FIX_SSH_CMD (pola GOLIVE_SSH_CMD). Prod tak pernah diset.
#
# Catatan operasional (JANGAN dihapus): setelah fix, cron JALAN tapi skor tetap
# NULL sampai PageSpeed Insights API di-ENABLE di project Google yang pegang key
# prod (PSI call = HTTP 403, fail-open). Backfill pertama juga belum pernah jalan:
#   ${VENV_PY} ${SERVER_DIR}/scripts/run_pagespeed_recheck.py --dry-run   (dulu)
#   ... tanpa --dry-run                                                   (lalu)
set -euo pipefail

SSH_HOST="deploy-kantorteman"
SERVER_DIR="/home/qqwtlphb/backend"
VENV_PY="/home/qqwtlphb/virtualenv/backend/3.13/bin/python"
LOCK="/tmp/kt-pagespeed.lock"
LOG="${SERVER_DIR}/logs/pagespeed_recheck.log"
# Mirror kanonik PRODUCTION.md baris 293 — satu-satunya sumber kebenaran baris ini.
CANONICAL="7 9 * * 1 flock -n ${LOCK} ${VENV_PY} ${SERVER_DIR}/scripts/run_pagespeed_recheck.py >> ${LOG} 2>&1"
MARKER="kt-pagespeed.lock"

log() { echo "[PSFIX] $*"; }
die() { echo "[PSFIX] ERROR: $*" >&2; exit 1; }

sshq() {
  # PAGESPEED_FIX_SSH_CMD: seam test lokal SAJA (default 'ssh').
  "${PAGESPEED_FIX_SSH_CMD:-ssh}" -o ConnectTimeout=15 -o BatchMode=yes "$SSH_HOST" "$@"
}

gate() {
  if [[ "${KT_PAGESPEED_FIX_ACK:-}" != "deploy" ]]; then
    echo "[GATE] DITOLAK (exit 3): '$1' mengubah crontab prod. Jalankan hanya dengan" >&2
    echo "       KT_PAGESPEED_FIX_ACK=deploy — dan hanya SETELAH Kevin menulis \"deploy\"." >&2
    exit 3
  fi
  log "ACK 'deploy' diterima — melanjutkan '$1'"
}

# Read-only: nilai + verdict. stdout = isi klasifikasi (CONSUMED via PAGESPEED_FIX_FACTS mode)
crontab_lines() {
  sshq "crontab -l 2>/dev/null || true"
}

classify() {
  # $1 = crontab (multi-line). echo "<verdict>\n<canonical_count>\n<buggy_count>"
  local canonical=0 buggy=0 line
  while IFS= read -r line; do
    [[ "$line" == *"$MARKER"* ]] || continue
    if [[ "$line" == "$CANONICAL" ]]; then
      canonical=$((canonical+1))
    else
      buggy=$((buggy+1))
    fi
  done <<< "$1"
  local verdict
  if (( buggy > 0 )); then verdict="BUGGY";
  elif (( canonical > 0 )); then verdict="CANONICAL";
  else verdict="ABSENT"; fi
  printf '%s %d %d\n' "$verdict" "$canonical" "$buggy"
}

cmd_status() {
  log "status prod (read-only) — $(date '+%F %T %Z')"
  local tab verdict
  tab="$(crontab_lines)"
  verdict="$(classify "$tab")"
  case "$verdict" in
    CANONICAL*) log "crontab pagespeed: CANONICAL ✔";;
    BUGGY*)     log "crontab pagespeed: BUGGY ✘ (cd di dalam flock — builtin exec gagal → no-op)";;
    ABSENT*)    log "crontab pagespeed: ABSENT (tidak ada baris $MARKER)";;
  esac
  sshq "echo '--- baris pagespeed ---'; crontab -l 2>/dev/null | grep -F '${MARKER}' || echo 'TIDAK_ADA_BARIS_PAGESPEED';
        echo '--- lock ---'; ls -l ${LOCK} 2>/dev/null || echo 'LOCK_BELUM_ADA';
        echo '--- log tail ---'; tail -n 5 ${LOG} 2>/dev/null || echo 'LOG_BELUM_ADA'"
  log "Pengingat: tanpa PSI API enabled (Google Cloud), skor tetap NULL (PSI 403 fail-open); backfill belum pernah jalan."
}

cmd_fix() {
  gate fix
  # Backup dulu — bukti restore point sebelum satu byte berubah.
  local ts backup
  ts="$(date +%Y%m%d-%H%M%S)"
  log "backup crontab → \$HOME/crontab-backup-pagespeed-${ts}.txt"
  sshq "crontab -l 2>/dev/null > \$HOME/crontab-backup-pagespeed-${ts}.txt && wc -l < \$HOME/crontab-backup-pagespeed-${ts}.txt"
  # Transform: buang SEMUA baris pagespeed, sisipkan 1 kanonis (idempotent, tanpa duplikat).
  log "replace baris pagespeed non-kanonis → kanonis (1 baris, tanpa cd)"
  sshq "crontab -l 2>/dev/null | awk -v can='${CANONICAL}' -v m='${MARKER}' '
          \$0 ~ m {
            seen=1
            if (\$0 == can) { canon_seen=1; print; next }
            dirty=1; next
          }
          { print }
          END { if (! canon_seen) { print can; dirty=1 } }' > /tmp/kt-crontab-new && cat /tmp/kt-crontab-new | crontab - && rm -f /tmp/kt-crontab-new && echo CRONTAB_DITULIS"
  log "verifikasi hasil (read-only):"
  local tab verdict
  tab="$(crontab_lines)"
  verdict="$(classify "$tab")"
  set -- $verdict
  if [[ "$1" == "CANONICAL" && "$2" == "1" && "$3" == "0" ]]; then
    log "fix OK: tepat 1 baris kanonis, 0 buggy ✔"
    log "PENTING: first-run Senin 09:07 WIB = bukti sesungguhnya (lock mtime baru + log berisi)."
    log "Masih menunggu terpisah: PSI API enable + backfill (--dry-run lalu eksekusi)."
  else
    die "verifikasi pasca-fix GAGAL (verdict='$verdict') — restore: crontab \$HOME/crontab-backup-pagespeed-${ts}.txt"
  fi
}

cmd_verify() {
  log "verify (read-only)"
  sshq "echo '--- baris kanonis ---'; crontab -l 2>/dev/null | grep -Fc '${MARKER}';
        echo '--- baris buggy (cd dalam flock) ---'; crontab -l 2>/dev/null | grep -F '${MARKER}' | grep -c 'lock cd ' || true;
        echo '--- log tail ---'; tail -n 10 ${LOG} 2>/dev/null || echo 'LOG_BELUM_ADA';
        echo '--- lock ---'; ls -l ${LOCK} 2>/dev/null || echo 'LOCK_BELUM_ADA'"
}

case "${1:-}" in
  status) cmd_status ;;
  fix)    cmd_fix ;;
  verify) cmd_verify ;;
  ""|-h|--help)
    grep '^#   ' "$0" | sed 's/^#   //'
    ;;
  *) die "perintah tidak dikenal: $1 (lihat: bash scripts/fix_pagespeed_crontab.sh)" ;;
esac
