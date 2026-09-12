#!/usr/bin/env bash
# test_fix_pagespeed_crontab_sh.sh — test lokal fix_pagespeed_crontab.sh via fake ssh shim.
# ZERO koneksi prod: PAGESPEED_FIX_SSH_CMD → fake_ssh.sh + sandbox $FAKE_HOME.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/fix_pagespeed_crontab.sh"
TMP="$(mktemp -d)"
FAKE="$TMP/home"
mkdir -p "$FAKE"
export FAKE_HOME="$FAKE"

cat > "$TMP/fake_ssh.sh" <<'SHIM'
#!/usr/bin/env bash
# Fake ssh: strip opsi ssh (-o X), skip host, eval command string di sandbox.
export HOME="${FAKE_HOME:?}"
args=()
prev_opt=0
for a in "$@"; do
  if [[ $prev_opt -eq 1 ]]; then prev_opt=0; continue; fi
  case "$a" in
    -o) prev_opt=1 ;;
    -*) ;;
    *) args+=("$a") ;;
  esac
done
cmd="${args[-1]:-}"
crontab() {
  local f="$HOME/crontab.txt"
  if [[ "${1:-}" == "-l" ]]; then
    cat "$f" 2>/dev/null; return 0
  elif [[ "${1:-}" == "-" ]]; then
    cat > "$f"; return 0
  fi
  echo "fake crontab: arg tak dikenal: $*" >&2; return 1
}
eval "$cmd"
SHIM
chmod +x "$TMP/fake_ssh.sh"

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "PASS: $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL: $1"; }

set_crontab() { printf '%s\n' "$1" > "$FAKE/crontab.txt"; }
run() { PAGESPEED_FIX_SSH_CMD="$TMP/fake_ssh.sh" bash "$SCRIPT" "$@" 2>&1; }
rc()  { PAGESPEED_FIX_SSH_CMD="$TMP/fake_ssh.sh" bash "$SCRIPT" "$@" >/dev/null 2>&1; echo $?; }

CANON="7 9 * * 1 flock -n /tmp/kt-pagespeed.lock /home/qqwtlphb/virtualenv/backend/3.13/bin/python /home/qqwtlphb/backend/scripts/run_pagespeed_recheck.py >> /home/qqwtlphb/backend/logs/pagespeed_recheck.log 2>&1"
BUGGY="7 9 * * 1 flock -n /tmp/kt-pagespeed.lock cd /home/qqwtlphb/backend && /home/qqwtlphb/virtualenv/backend/3.13/bin/python scripts/run_pagespeed_recheck.py >> /home/qqwtlphb/backend/logs/pagespeed_recheck.log 2>&1"
WARMUP="*/2 * * * * /home/qqwtlphb/scripts/warmup.sh >> /home/qqwtlphb/backend/warmup.log 2>&1"

# T1 status buggy → BUGGY, exit 0
set_crontab "$WARMUP
$BUGGY"
out="$(run status)"
[[ "$out" == *"BUGGY"* ]] && ok "T1 status deteksi BUGGY" || bad "T1 status: $out"
[[ "$(rc status)" == "0" ]] && ok "T1 status exit 0" || bad "T1 status exit bukan 0"

# T2 fix TANPA ACK → exit 3, crontab tak berubah
set_crontab "$WARMUP
$BUGGY"
[[ "$(rc fix)" == "3" ]] && ok "T2 fix tanpa ACK exit 3" || bad "T2 exit bukan 3: $(rc fix)"
grep -q "lock cd " "$FAKE/crontab.txt" && ok "T2 crontab tak tersentuh tanpa ACK" || bad "T2 crontab berubah!"

# T3 fix DENGAN ACK → 1 kanonis, 0 buggy, backup ada
out="$(KT_PAGESPEED_FIX_ACK=deploy run fix)"
n_canon="$(grep -Fc "$CANON" "$FAKE/crontab.txt")"; n_buggy="$(grep -c "lock cd " "$FAKE/crontab.txt" || true)"
[[ "$n_canon" == "1" && "$n_buggy" == "0" ]] && ok "T3 fix → 1 kanonis 0 buggy" || bad "T3: canon=$n_canon buggy=$n_buggy"
ls "$FAKE"/crontab-backup-pagespeed-*.txt >/dev/null 2>&1 && ok "T3 backup dibuat" || bad "T3 backup absen"
grep -q "fix OK" <<< "$out" && ok "T3 verifikasi pasca-fix lulus" || bad "T3 output: $out"
grep -Fq "$WARMUP" "$FAKE/crontab.txt" && ok "T3 baris non-pagespeed utuh (warmup)" || bad "T3 warmup hilang!"

# T4 idempotent: fix lagi → tetap 1 kanonis
KT_PAGESPEED_FIX_ACK=deploy run fix >/dev/null 2>&1
n_canon="$(grep -Fc "$CANON" "$FAKE/crontab.txt")"
[[ "$n_canon" == "1" ]] && ok "T4 idempotent (tetap 1 kanonis)" || bad "T4 duplikat: $n_canon"

# T5 status canonical → CANONICAL
out="$(run status)"
[[ "$out" == *"CANONICAL"* ]] && ok "T5 status deteksi CANONICAL" || bad "T5: $out"

# T6 tanpa entri pagespeed sama sekali → fix memasang kanonis
set_crontab "$WARMUP"
KT_PAGESPEED_FIX_ACK=deploy run fix >/dev/null 2>&1
grep -Fq "$CANON" "$FAKE/crontab.txt" && ok "T6 ABSENT → kanonis dipasang" || bad "T6 gagal pasang"

# T7 buggy + kanonis campur → fix merapikan jadi 1 kanonis
set_crontab "$WARMUP
$BUGGY
$CANON"
KT_PAGESPEED_FIX_ACK=deploy run fix >/dev/null 2>&1
n_canon="$(grep -Fc "$CANON" "$FAKE/crontab.txt")"; n_buggy="$(grep -c "lock cd " "$FAKE/crontab.txt" || true)"
[[ "$n_canon" == "1" && "$n_buggy" == "0" ]] && ok "T7 campuran → 1 kanonis bersih" || bad "T7: canon=$n_canon buggy=$n_buggy"

# T8 perintah tak dikenal → exit 1
[[ "$(rc ngerjain-prod)" == "1" ]] && ok "T8 perintah asing exit 1" || bad "T8 exit salah"

# firstrun: override path inspect ke sandbox (default = path prod, tak tersentuh)
fr_env() { KT_PAGESPEED_FIRSTRUN_LOCK="$FAKE/lock" KT_PAGESPEED_FIRSTRUN_LOG="$FAKE/ps.log" PAGESPEED_FIX_SSH_CMD="$TMP/fake_ssh.sh" bash "$SCRIPT" "${@:-firstrun}"; }
fr_rc()  { KT_PAGESPEED_FIRSTRUN_LOCK="$FAKE/lock" KT_PAGESPEED_FIRSTRUN_LOG="$FAKE/ps.log" PAGESPEED_FIX_SSH_CMD="$TMP/fake_ssh.sh" bash "$SCRIPT" "${@:-firstrun}" >/dev/null 2>&1; echo $?; }
SUMLINE='[pagespeed-recheck] summary {"checked": 3, "failed": 1, "skipped": 0, "recorded_dead": 1}'

# T9 firstrun: lock & log absen → FAIL exit 1
rm -f "$FAKE/lock" "$FAKE/ps.log"
out="$(fr_env)"
[[ "$(fr_rc)" == "1" && "$out" == *"FIRSTRUN FAIL"* ]] && ok "T9 firstrun kosong → FAIL exit 1" || bad "T9: rc=$(fr_rc) out=$out"

# T10 firstrun: lock segar + log dgn summary → PASS exit 0
printf '%s\n[pagespeed-recheck] lead=1 skor=88\n%s\n' "start" "$SUMLINE" > "$FAKE/ps.log"
touch -d '10 minutes ago' "$FAKE/lock"
out="$(fr_env)"
[[ "$(fr_rc)" == "0" && "$out" == *"FIRSTRUN PASS"* && "$out" == *'"checked": 3'* ]] && ok "T10 firstrun segar+summary → PASS" || bad "T10: rc=$(fr_rc) out=$out"

# T11 firstrun: lock basi (3 hari) → FAIL walau log oke
touch -d '3 days ago' "$FAKE/lock"
[[ "$(fr_rc)" == "1" ]] && ok "T11 lock basi → FAIL" || bad "T11 rc=$(fr_rc)"

# T12 firstrun: lock segar tapi log TANPA summary → FAIL
touch -d '10 minutes ago' "$FAKE/lock"
printf 'hanya noise tanpa summary\n' > "$FAKE/ps.log"
out="$(fr_env)"
[[ "$(fr_rc)" == "1" && "$out" == *"summary"*"absen"* ]] && ok "T12 log tanpa summary → FAIL" || bad "T12: rc=$(fr_rc) out=$out"

# T13 firstrun default tanpa override = path prod asli, lock /tmp lokal VPS dev — read-only aman
out="$(PAGESPEED_FIX_SSH_CMD="$TMP/fake_ssh.sh" bash "$SCRIPT" firstrun 2>&1 || true)"
[[ "$out" == *"FIRSTRUN"* ]] && ok "T13 firstrun default jalan (read-only)" || bad "T13: $out"

echo "=== RESULT: PASS=$PASS FAIL=$FAIL ==="
rm -rf "$TMP"
[[ $FAIL -eq 0 ]]
