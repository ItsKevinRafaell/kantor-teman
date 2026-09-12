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
#   verify     read-only: baris kanonis ada & buggy absen + tail log.
#   firstrun   read-only PASS/FAIL: bukti cron pagespeed BARU benar-benar fire —
#              lock umur < FIRSTRUN_MAX_AGE (default 86400s) + log ada + baris
#              "[pagespeed-recheck] summary {...}" ketemu. Exit 0 PASS / 1 FAIL.
#              Jalankan tepat setelah cron Senin 09:07 WIB. Zero mutasi.
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
# Path yg di-inspect 'firstrun'. Override HANYA untuk test sandbox — default = path prod.
CHK_LOCK="${KT_PAGESPEED_FIRSTRUN_LOCK:-${LOCK}}"
CHK_LOG="${KT_PAGESPEED_FIRSTRUN_LOG:-${LOG}}"
FIRSTRUN_MAX_AGE="${KT_PAGESPEED_FIRSTRUN_MAX_AGE:-86400}"

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

cmd_firstrun() {
  # Read-only PASS/FAIL: bukti cron pagespeed baru benar-benar fire.
  # PASS = log ada & berisi + baris summary ketemu + lock umurnya < FIRSTRUN_MAX_AGE.
  log "firstrun (read-only): bukti cron pagespeed fire (lock=${CHK_LOCK}, log=${CHK_LOG}, max_age=${FIRSTRUN_MAX_AGE}s)"
  local out lock_age="" summary="" reasons=()
  out="$(sshq "now=\$(date +%s); lk=\$(stat -c %Y '${CHK_LOCK}' 2>/dev/null || echo 0); echo LOCK_EPOCH=\$lk; if [ \$lk -eq 0 ]; then echo LOCK=BELUM_ADA; else echo LOCK_AGE=\$((now - lk)); fi; if [ -s '${CHK_LOG}' ]; then echo LOG_OK; grep -oE '\[pagespeed-recheck\] summary \{[^}]*\}' '${CHK_LOG}' | tail -n 1; echo '--- tail ---'; tail -n 3 '${CHK_LOG}'; else echo LOG_KOSONG; fi" 2>&1)" || out=""
  echo "$out"
  if grep -q '^LOCK_AGE=' <<<"$out"; then
    lock_age="$(sed -n 's/^LOCK_AGE=//p' <<<"$out" | head -n 1)"
  fi
  summary="$(sed -n 's/^\[pagespeed-recheck\] summary //p' <<<"$out" | tail -n 1)"
  if ! grep -q '^LOG_OK$' <<<"$out"; then
    reasons+=("log kosong/absen: ${CHK_LOG}")
  fi
  if [[ -z "$summary" ]]; then
    reasons+=("baris '[pagespeed-recheck] summary {...}' absen di log")
  fi
  if [[ -z "$lock_age" ]]; then
    reasons+=("lock absen: ${CHK_LOCK} (cron belum pernah exec)")
  elif (( lock_age > FIRSTRUN_MAX_AGE )); then
    reasons+=("lock basi: age=${lock_age}s > max ${FIRSTRUN_MAX_AGE}s (bukan hasil fire terakhir)")
  fi
  if (( ${#reasons[@]} == 0 )); then
    log "FIRSTRUN PASS ✔ — lock age=${lock_age}s; summary: ${summary}"
    return 0
  fi
  log "FIRSTRUN FAIL ✘ — ${reasons[*]}"
  return 1
}

case "${1:-}" in
  status) cmd_status ;;
  fix)    cmd_fix ;;
  verify) cmd_verify ;;
  firstrun) cmd_firstrun ;;
  ""|-h|--help)
    grep '^#   ' "$0" | sed 's/^#   //'
    ;;
  *) die "perintah tidak dikenal: $1 (lihat: bash scripts/fix_pagespeed_crontab.sh)" ;;
esac
