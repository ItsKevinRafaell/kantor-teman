# Opus Sprint — Hermes Mika/Nara Skills Audit (2026-07-23)

Time-box audit: anti-slop + calendar routing for profiles **mika** / **nara** on VPS `temanumkm-vps` (`sg.ireng.uk:20015`). Local machine has **no** `profiles/mika|nara` — live state is VPS-only under `/root/.hermes/`.

**No secrets in this doc.** Do not cat `google_service_account.json` / `.env` / tokens.

## What was found (live VPS)

### Paths
| Item | Path |
|------|------|
| Mika skills | `/root/.hermes/profiles/mika/skills/` |
| Nara skills | `/root/.hermes/profiles/nara/skills/` |
| Mika MEMORY | `/root/.hermes/profiles/mika/memories/MEMORY.md` |
| Nara MEMORY | `/root/.hermes/profiles/nara/memories/MEMORY.md` |
| Calendar client | `/root/.hermes/shared/scripts/calendar_client.py` |
| SA JSON (do not print) | `/root/.hermes/google_service_account.json` |
| Mika calendar skill | `/root/.hermes/profiles/mika/skills/calendar/SKILL.md` |
| Nara calendar skill | `/root/.hermes/profiles/nara/skills/calendar/SKILL.md` |
| Mika posting | `/root/.hermes/profiles/mika/skills/posting.md` (527 lines, rich anti-slop) |
| Nara posting | `/root/.hermes/profiles/nara/skills/posting.md` (202 lines, **missing** language hard-rules) |
| Mika humanizer | has §5 em-dash OVERRIDE |
| Nara humanizer | **missing** §5 OVERRIDE (still soft "berlebihan") |

### Calendar (OK path, one alias polish)
- `calendar_client.py` uses **service account** (not OAuth). Verified `list` → owner on:
  - `kevin.sabran@gmail.com` (Mika)
  - `temanumkm.kita@gmail.com` (Nara)
- Alias `pribadi` → `kevin.sabran@gmail.com` (correct; not `primary`).
- Alias `temanumkmkita` → `temanumkmkita@gmail.com` (works via Gmail dots-optional, but **list id** is `temanumkm.kita@gmail.com` → harden to exact).
- Mika/Nara `calendar/SKILL.md` already ban OAuth + require `event_id` verify. Patch copies strengthen JANGAN list + SA path.

### Anti-slop
| Check | Mika | Nara |
|-------|------|------|
| posting.md ATURAN KERAS (em-dash/buzzword/self-correct) | YES | **NO** |
| humanizer §5 hard ban em-dash on social | YES | **NO** |
| MEMORY anti-slop hard rules | YES (partial, mature) | **NO** language block |
| MEMORY calendar routing explicit no-OAuth | weak (mentions client only) | **NO** |
| self-correction via skill_manage | in posting | missing |

## Local patches (this repo)

```
/home/kevin/kantorteman/docs/hermes-skills-patches/
  mika/
    MEMORY-calendar-routing.append.md
    calendar.SKILL.md
  nara/
    posting-anti-slop.append.md
    humanizer-section5-override.patch.txt
    MEMORY-anti-slop-calendar.append.md
    calendar.SKILL.md
  shared/
    calendar_client.aliases.patch.py
```

## Deploy via SSH (apply on VPS)

Host alias: `temanumkm-vps` (see `~/.ssh/config`).

### 0) Backup
```bash
ssh temanumkm-vps 'TS=$(date +%Y%m%d_%H%M%S); \
  mkdir -p /root/.hermes/backups/skills-$TS; \
  cp -a /root/.hermes/profiles/mika/skills/posting.md \
        /root/.hermes/profiles/nara/skills/posting.md \
        /root/.hermes/profiles/mika/skills/humanizer-bahasa-indonesia.md \
        /root/.hermes/profiles/nara/skills/humanizer-bahasa-indonesia.md \
        /root/.hermes/profiles/mika/skills/calendar/SKILL.md \
        /root/.hermes/profiles/nara/skills/calendar/SKILL.md \
        /root/.hermes/profiles/mika/memories/MEMORY.md \
        /root/.hermes/profiles/nara/memories/MEMORY.md \
        /root/.hermes/shared/scripts/calendar_client.py \
        /root/.hermes/backups/skills-$TS/; \
  echo backup=/root/.hermes/backups/skills-$TS'
```

### 1) SCP patches
```bash
LOCAL=/home/kevin/kantorteman/docs/hermes-skills-patches
scp "$LOCAL/mika/calendar.SKILL.md" temanumkm-vps:/root/.hermes/profiles/mika/skills/calendar/SKILL.md
scp "$LOCAL/nara/calendar.SKILL.md" temanumkm-vps:/root/.hermes/profiles/nara/skills/calendar/SKILL.md
scp "$LOCAL/nara/posting-anti-slop.append.md" \
    "$LOCAL/nara/MEMORY-anti-slop-calendar.append.md" \
    "$LOCAL/mika/MEMORY-calendar-routing.append.md" \
    "$LOCAL/nara/humanizer-section5-override.patch.txt" \
    "$LOCAL/shared/calendar_client.aliases.patch.py" \
    temanumkm-vps:/tmp/hermes-skill-audit/
```

### 2) Append Nara posting anti-slop
```bash
ssh temanumkm-vps 'cat /tmp/hermes-skill-audit/posting-anti-slop.append.md \
  >> /root/.hermes/profiles/nara/skills/posting.md'
```

### 3) Nara humanizer §5 override (insert after heading if missing)
```bash
ssh temanumkm-vps 'python3 - <<'\''PY'\''
from pathlib import Path
p = Path("/root/.hermes/profiles/nara/skills/humanizer-bahasa-indonesia.md")
text = p.read_text()
needle = "### 5. Penggunaan Tanda Hubung Berlebihan\n"
override = (
    needle
    + "> ATURAN KERAS KEVIN (override untuk media sosial): Di post/media sosial, "
    + "em-dash (—), en-dash (–), dan tanda hubung sebagai pemisah DILARANG SAMA SEKALI. "
    + "Ganti dengan \", \" atau pisah jadi dua kalimat. Contoh skill yang pakai em-dash "
    + "hanya berlaku untuk artikel formal, BUKAN caption/post Kevin.\n\n"
)
if "ATURAN KERAS KEVIN (override untuk media sosial)" in text:
    print("nara humanizer already patched")
elif needle not in text:
    raise SystemExit("heading not found")
else:
    p.write_text(text.replace(needle, override, 1))
    print("nara humanizer patched")
PY'
```

### 4) MEMORY appends
```bash
ssh temanumkm-vps '
  cat /tmp/hermes-skill-audit/MEMORY-anti-slop-calendar.append.md \
    >> /root/.hermes/profiles/nara/memories/MEMORY.md
  cat /tmp/hermes-skill-audit/MEMORY-calendar-routing.append.md \
    >> /root/.hermes/profiles/mika/memories/MEMORY.md
'
```

### 5) Fix calendar aliases (exact ids)
```bash
ssh temanumkm-vps 'python3 - <<'\''PY'\''
from pathlib import Path
p = Path("/root/.hermes/shared/scripts/calendar_client.py")
text = p.read_text()
old = '''CALENDAR_ALIASES = {
    "pribadi": "kevin.sabran@gmail.com",  # Kevin.s personal calendar (Mika)
    "temanumkmkita": "temanumkmkita@gmail.com",  # update if different
}'''
new = '''CALENDAR_ALIASES = {
    "pribadi": "kevin.sabran@gmail.com",  # Mika
    "temanumkmkita": "temanumkm.kita@gmail.com",  # Nara exact list id
    "teman": "temanumkm.kita@gmail.com",
}'''
if "temanumkm.kita@gmail.com" in text and '"teman"' in text:
    print("aliases already exact")
elif old not in text:
    # fallback: replace only the wrong value
    t2 = text.replace('"temanumkmkita": "temanumkmkita@gmail.com"',
                      '"temanumkmkita": "temanumkm.kita@gmail.com"')
    if t2 == text:
        raise SystemExit("alias block not matched; edit manually")
    if '"teman"' not in t2:
        t2 = t2.replace(
            '"temanumkmkita": "temanumkm.kita@gmail.com"',
            '"temanumkmkita": "temanumkm.kita@gmail.com",\n    "teman": "temanumkm.kita@gmail.com"',
        )
    p.write_text(t2)
    print("aliases patched via value replace")
else:
    p.write_text(text.replace(old, new))
    print("aliases patched full block")
PY'
```

### 6) Smoke calendar (no secrets)
```bash
ssh temanumkm-vps '
  PY=/usr/local/lib/hermes-agent/venv/bin/python
  CAL=/root/.hermes/shared/scripts/calendar_client.py
  $PY $CAL list
  $PY $CAL events pribadi 2
  $PY $CAL events temanumkmkita 2
'
# Expect calendar ids: kevin.sabran@gmail.com + temanumkm.kita@gmail.com
```

### 7) Restart gateways (PPID=1, no systemd — manual)
```bash
ssh temanumkm-vps '
  # find current pids
  pgrep -af "hermes_cli.main --profile mika" || true
  pgrep -af "hermes_cli.main --profile nara" || true

  # kill + replace (adjust if your start command differs)
  pkill -f "hermes_cli.main --profile mika" || true
  pkill -f "hermes_cli.main --profile nara" || true
  sleep 2
  setsid /usr/local/lib/hermes-agent/venv/bin/python -m hermes_cli.main \
    --profile mika gateway run --replace \
    >/root/.hermes/profiles/mika/gateway.out 2>&1 & disown
  setsid /usr/local/lib/hermes-agent/venv/bin/python -m hermes_cli.main \
    --profile nara gateway run --replace \
    >/root/.hermes/profiles/nara/gateway.out 2>&1 & disown
  sleep 3
  pgrep -af "hermes_cli.main --profile" || true
  tail -n 5 /root/.hermes/profiles/mika/gateway.out
  tail -n 5 /root/.hermes/profiles/nara/gateway.out
'
```

### 8) E2E checks (Telegram)
1. **Mika anti-slop:** minta draft Threads → body must have no `—`, no "era baru" / "game changer", no hook `?`.
2. **Mika calendar:** "jadwalin smoke test 10 menit dari sekarang 15 menit" → must return `event_id` + `html_link`, then `events pribadi` shows it. Delete via UI after.
3. **Nara calendar:** same against `temanumkmkita` / bisnis calendar.
4. **Nara anti-slop:** minta caption singkat → same bans as Mika.

If agent claims calendar done without `event_id` → still OAuth-halu path; check `agent.log` / tool_executor for `google-workspace` / `setup.py`.

## Rollback
```bash
ssh temanumkm-vps 'ls -1dt /root/.hermes/backups/skills-* | head -1'
# then cp -a files back from that dir, restart gateways
```

## Out of scope / deferred
- systemd unit per profile (still manual kill+setsid after reboot)
- full Mika→Nara posting.md sync (Nara gets hard-rule block only; not full 527-line Mika maturity log)
- OAuth token install (intentionally avoided; SA is the supported path)
