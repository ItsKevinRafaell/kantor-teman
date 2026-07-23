# Calendar Skill (Mika → kevin.sabran@gmail.com)

## PENTING — Jangan pakai skill "google-workspace" (OAuth)
Skill `productivity/google-workspace` butuh OAuth token (`google_token.json`)
yang TIDAK ada di server ini → akan gagal / halu. SELALU pakai script service
account di bawah. Ini sudah terhubung sebagai OWNER ke kalender Kevin.

JANGAN:
- jalankan google-workspace/scripts/setup.py
- cari / buat google_token.json
- pakai gws CLI (tidak terinstall)
- bilang "udah di-set" tanpa event_id

## Backend (sudah jadi, jangan di-setup ulang)
Script: `/root/.hermes/shared/scripts/calendar_client.py`
Service account JSON: `/root/.hermes/google_service_account.json` (JANGAN print isinya)
Jalankan dengan venv Hermes (wajib):
```
PY=/usr/local/lib/hermes-agent/venv/bin/python
CAL=/root/.hermes/shared/scripts/calendar_client.py
```

## Kalender Mika
- `pribadi`  → kevin.sabran@gmail.com   (alias, JANGAN pakai "primary")
- bisa juga pakai id explicit: kevin.sabran@gmail.com

## Perintah (copy-paste ke terminal tool)
```
# Lihat kalender yang bisa diakses
$PY $CAL list

# Lihat event akan datang (N event)
$PY $CAL events pribadi 10
$PY $CAL events kevin.sabran@gmail.com 10

# Event hari ini
$PY $CAL today pribadi

# BUAT event (wajib quote, format 2026-07-11T10:00 = Asia/Jakarta)
$PY $CAL create pribadi "Judul Rapat" "2026-07-11T10:00" "2026-07-11T11:00" "Lokasi opsional" "Deskripsi opsional"
```

## ATURAN WAJIB (biar ga halu)
1. Setelah `create`, output PASTI balikin `"success": true` + `"event_id"` + `"html_link"`.
   - JIKA tidak ada event_id → BELUM BERHASIL, jangan bilang "udah di-set".
2. SELALU verifikasi: jalankan `$PY $CAL events pribadi 5` dan pastikan event baru
   muncul sebelum bilang ke user "done / udah di-jadwalkan".
3. Jangan claim sukses kalau terminal tool balikin error / timeout / No such file.
4. Waktu tanpa timezone dianggap Asia/Jakarta (WIB). Konfirmasi kalau user pakai
   zona lain.
5. Jangan pakai `calendar delete` (belum didukung) — hapus lewat Google Calendar UI
   atau bilang user.
6. Kalau tool gagal → laporkan error apa adanya. JANGAN improvise OAuth.

## Contoh alur aman
User: "jadwalin rapat besok 10-11"
→ `$PY $CAL create pribadi "Rapat" "2026-07-11T10:00" "2026-07-11T11:00"`
→ cek output ada event_id
→ `$PY $CAL events pribadi 3` → pastikan muncul
→ baru balas: "Done, ini link-nya: <html_link>"
