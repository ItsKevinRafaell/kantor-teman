#!/usr/bin/env bash
# ============================================================================
# Test harness 0-SSH untuk deploy.sh.NEW (v2) — Kantorteman backend
#
# Menjalankan deploy.sh.NEW di sandbox PENUH:
#   - fake git / python3 / mysqldump / mysql (shim PATH, log semua panggilan)
#   - tanpa binary `python` di PATH  → simulasi jailshell prod (bug lama)
#   - health server HTTP lokal (200) / port tertutup (simulasi gagal)
#   - lock nyata /tmp/kt-deploy.lock (flock asli)
# Tidak ada SSH, tidak ada sentuhan prod, tidak butuh MySQL.
#
# Jalankan:  bash backend/scripts/test_deploy_sh_new.sh
# Output:    "TEST n: <nama> — PASS/FAIL" + ringkasan N/N. Exit 0 = semua pass.
# ============================================================================
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$REPO_ROOT/backend/deploy.sh.NEW"
DEFAULT_URL='mysql+pymysql://ktuser:p%40ss@127.0.0.1:3306/kt_test_db?charset=utf8mb4'

PASS=0; FAIL=0
SBX="" BIN="" GITLOG="" PY3LOG="" DUMPLOG="" MYSQLLOG=""
HEALTH_URL="" HPID=""
OUT=""; RC=0

report() { # $1=num $2=nama $3=ok(0 pass) $4=detail
  if [ "$3" = "0" ]; then
    PASS=$((PASS+1)); echo "TEST $1: $2 — PASS"
  else
    FAIL=$((FAIL+1))
    echo "TEST $1: $2 — FAIL: ${4:-}"
    echo "   [debug] rc=$RC out_tail=$(printf '%s' "$OUT" | tail -3 | tr '\n' '|')"
    echo "   [debug] lock=$(flock -n /tmp/kt-deploy.lock -c 'echo BEBAS' 2>/dev/null || echo DIP EGANG)"
  fi
}
file_has() { grep -qF -- "$2" "$1" 2>/dev/null; }
str_has()  { printf '%s' "$1" | grep -qF -- "$2"; }

cleanup_sbx() { [ -n "${SBX:-}" ] && [ -d "$SBX" ] && rm -rf "$SBX"; }
trap 'kill ${HPID:-0} 2>/dev/null; cleanup_sbx' EXIT

# ---------------------------------------------------------------------------
new_sbx() { # $1 = DATABASE_URL opsional; tanpa arg = MySQL default
  cleanup_sbx
  SBX="$(mktemp -d /tmp/kt-deploytest-XXXXXX)"
  BIN="$SBX/bin"
  mkdir -p "$BIN" "$SBX/tmp" "$SBX/backups"
  cp "$SRC" "$SBX/deploy.sh"
  GITLOG="$SBX/git.log"; PY3LOG="$SBX/py3.log"; DUMPLOG="$SBX/dump.log"; MYSQLLOG="$SBX/mysql.log"

  cat > "$BIN/git" <<'SH'
#!/bin/bash
echo "git $*" >> "${KT_GIT_LOG:-/dev/null}"
exit 0
SH
  cat > "$BIN/python3" <<'SH'
#!/bin/bash
echo "python3 $*" >> "${KT_PY3_LOG:-/dev/null}"
exit 0
SH
  cat > "$BIN/mysqldump" <<'SH'
#!/bin/bash
{ echo "mysqldump $*"; echo "MYSQL_PWD=${MYSQL_PWD-}"; } >> "${KT_DUMP_LOG:-/dev/null}"
case "${KT_DUMP_MODE:-ok}" in
  empty) exit 0 ;;
  fail)  echo "mysqldump: error" >&2; exit 1 ;;
  *)     head -c 4096 /dev/zero | tr '\0' 'D'; echo ;;
esac
SH
  cat > "$BIN/mysql" <<'SH'
#!/bin/bash
echo "mysql $* MYSQL_PWD=${MYSQL_PWD-}" >> "${KT_MYSQL_LOG:-/dev/null}"
exit 0
SH
  chmod +x "$BIN/"*

  printf 'DATABASE_URL=%s\n' "${1:-$DEFAULT_URL}" > "$SBX/.env.production"
}

run_deploy() { # $1 = timeout detik
  OUT="$(cd "$SBX" && PATH="$BIN:/usr/bin:/bin" timeout "${1:-60}" env \
    HEALTH_URL="$HEALTH_URL" \
    KT_GIT_LOG="$GITLOG" KT_PY3_LOG="$PY3LOG" \
    KT_DUMP_LOG="$DUMPLOG" KT_MYSQL_LOG="$MYSQLLOG" \
    KT_DUMP_MODE="${DUMP_MODE:-ok}" \
    bash deploy.sh 2>&1)"
  RC=$?
}

start_health() {
  for p in $(seq 18471 18485); do
    /usr/bin/python3 -m http.server "$p" --bind 127.0.0.1 >/dev/null 2>&1 &
    HPID=$!
    sleep 0.4
    if kill -0 "$HPID" 2>/dev/null; then
      HEALTH_URL="http://127.0.0.1:$p/"   # http.server: / = 200 (directory listing)
      return 0
    fi
    kill "$HPID" 2>/dev/null; wait "$HPID" 2>/dev/null
  done
  echo "FATAL: tidak ada port bebas untuk health server" >&2
  exit 2
}

# ---------------------------------------------------------------------------
echo "=== test_deploy_sh_new.sh — sandbox 0-SSH, SRC=$SRC ==="
bash -n "$SRC" >/dev/null 2>&1; report 1 "syntax bash -n" "$?" "bash -n gagal"

start_health

# --- T2..T7: happy path jailshell (tanpa `python`) + MySQL + health OK -------
new_sbx
run_deploy 60
if [ "$RC" = "0" ]; then report 2 "jailshell: tanpa python, deploy sukses (exit 0)" 0
else report 2 "jailshell: tanpa python, deploy sukses (exit 0)" 1 "RC=$RC out=$(printf '%s' "$OUT" | tail -2 | tr '\n' ' ')"; fi

if file_has "$PY3LOG" "migrate.py"; then report 3 "migrate jalan via python3 (bukan python)" 0
else report 3 "migrate jalan via python3 (bukan python)" 1 "py3.log: $(head -1 "$PY3LOG" 2>/dev/null)"; fi

if file_has "$GITLOG" "pull origin main"; then report 4 "git pull origin main terpanggil" 0
else report 4 "git pull origin main terpanggil" 1 "git.log: $(head -2 "$GITLOG" 2>/dev/null | tr '\n' ' ')"; fi

ls "$SBX"/backups/db-*.sql.gz >/dev/null 2>&1; report 5 "dump MySQL kebuat" "$?"

if file_has "$DUMPLOG" "mysqldump --host=127.0.0.1 --port=3306 --user=ktuser" \
   && file_has "$DUMPLOG" " kt_test_db"; then
  report 6 "parse DATABASE_URL: host/port/user/db" 0
else
  report 6 "parse DATABASE_URL: host/port/user/db" 1 "$(head -1 "$DUMPLOG" 2>/dev/null)"
fi

if file_has "$DUMPLOG" "MYSQL_PWD=p@ss"; then report 7 "password url-decoded (p%40ss -> p@ss), tak lewat argv" 0
else report 7 "password url-decoded (p%40ss -> p@ss), tak lewat argv" 1 "MYSQL_PWD tidak ter-decode"; fi

# --- T8: mysqldump exit 0 tapi output kosong (gzip header saja) ---------------
new_sbx
DUMP_MODE=empty run_deploy 60
if [ "$RC" != "0" ] && str_has "$OUT" "Dump kosong"; then report 8 "dump kosong ditolak (bukan cuma cek -s)" 0
else report 8 "dump kosong ditolak (bukan cuma cek -s)" 1 "RC=$RC"; fi

# --- T9: mysqldump exit 1 -> pipefail batal sebelum git pull -------------------
new_sbx
DUMP_MODE=fail run_deploy 60
if [ "$RC" != "0" ] && ! file_has "$GITLOG" "pull origin main"; then
  report 9 "mysqldump gagal -> deploy batal (pipefail), sebelum git" 0
else
  report 9 "mysqldump gagal -> deploy batal (pipefail), sebelum git" 1 "RC=$RC"
fi

# --- T10: rotate backup simpan 7 terakhir -------------------------------------
new_sbx
for i in $(seq 1 9); do
  f="$SBX/backups/db-2026-08-$((10+i))-0000.sql.gz"
  head -c 512 /dev/zero | tr '\0' 'O' > "$f"
  touch -d "2026-08-$((10+i)) 09:00" "$f"
done
run_deploy 60
n=$(ls -1 "$SBX"/backups/db-*.sql.gz 2>/dev/null | wc -l)
if [ "$RC" = "0" ] && [ "$n" = "7" ]; then report 10 "rotate: 9 lama + 1 baru -> 7 tersisa" 0
else report 10 "rotate: 9 lama + 1 baru -> 7 tersisa" 1 "n=$n RC=$RC"; fi

# --- T11: lock — deploy paralel ditolak ---------------------------------------
new_sbx
exec 9>/tmp/kt-deploy.lock
flock -n 9 || echo "[warn-harness] gagal pegang lock utk test"
run_deploy 30          # deploy.sh harus menolak: test shell memegang lock
flock -u 9; exec 9>&-  # release eksplisit — tanpa proses background/orphan
if [ "$RC" != "0" ] && str_has "$OUT" "[LOCK]"; then report 11 "lock: run kedua ditolak saat deploy lain jalan" 0
else report 11 "lock: run kedua ditolak saat deploy lain jalan" 1 "RC=$RC"; fi

# --- T12: DATABASE_URL non-MySQL -> skip backup, tetap deploy ------------------
new_sbx "sqlite:////tmp/kt-test.db"
run_deploy 60
if [ "$RC" = "0" ] && str_has "$OUT" "bukan MySQL"; then report 12 "non-MySQL: skip mysqldump, deploy tetap sukses" 0
else report 12 "non-MySQL: skip mysqldump, deploy tetap sukses" 1 "RC=$RC"; fi

# --- T13: ENV_FILE hilang -> exit 1 --------------------------------------------
new_sbx
rm -f "$SBX/.env.production"
run_deploy 30
if [ "$RC" != "0" ] && str_has "$OUT" "tidak ditemukan"; then report 13 "env hilang -> exit 1 dgn pesan jelas" 0
else report 13 "env hilang -> exit 1 dgn pesan jelas" 1 "RC=$RC"; fi

# --- T14: health gagal -> auto-rollback (reset + restore dump + re-verify) -----
new_sbx
SAVED_URL="$HEALTH_URL"
HEALTH_URL="http://127.0.0.1:18479/health"   # port pasti tutup -> health gagal
run_deploy 150
HEALTH_URL="$SAVED_URL"
if [ "$RC" != "0" ] && file_has "$GITLOG" "reset --hard" && file_has "$MYSQLLOG" "kt_test_db" \
   && str_has "$OUT" "DB restore OK" && str_has "$OUT" "BUTUH INTERVENSI MANUAL"; then
  report 14 "rollback: reset git + restore dump + intervensi manual + exit 1" 0
else
  report 14 "rollback: reset git + restore dump + intervensi manual + exit 1" 1 "RC=$RC rollback_lines=$(printf '%s' "$OUT" | grep -c ROLLBACK)"
fi

# ---------------------------------------------------------------------------
echo "=== ringkasan: $PASS PASS, $FAIL FAIL dari $((PASS+FAIL)) ==="
[ "$FAIL" = "0" ]
