# Production Launch Guide — Kantorteman

## Urutan Jalankan di Server

```bash
# 1. Tambah kolom baru ke database
python migrate.py

# 2. Seed semua data bisnis
python seed.py

# 3. Bersihkan data dev/test
python reset_data.py
```

Jalankan berurutan. Jangan skip step.

### Default Admin Login

```
Email: admin@kantorteman.com
Password: admin123
```

> ⚠️ Ganti password segera setelah login pertama via Pengaturan → Profil.

---

## Konfigurasi Post-Launch (via UI)

### Fonnte Quota
1. Buka **Pusat Biaya & Kuota → Fonnte WhatsApp**
2. Set **Monthly Quota** = jumlah pesan yang kamu top up per bulan
3. Set **Remaining Quota** = sisa pesan saat ini
4. Scheduler akan auto-reset `remaining_quota` ke `monthly_quota` setiap tanggal 1 jam 00:00

### API Keys
Pastikan sudah diisi di **Pengaturan → API** (isi sesuai provider yang dipilih, tidak harus semua):
- `FONNTE_TOKEN` — wajib untuk WhatsApp blast
- `GEMINI_API_KEY` — opsional, jika pakai Gemini sebagai AI provider
- `CLAUDE_API_KEY` — opsional, jika pakai Claude sebagai AI provider
- `OPENAI_API_KEY` — opsional, jika pakai OpenAI/compatible sebagai AI provider

> Pilih satu AI provider di Settings → AI Config. Hanya API key provider yang dipilih yang perlu diisi.

### Wallet Saldo Awal
1. Buka **Keuangan → Wallet**
2. Set saldo awal **Rekening Utama** sesuai saldo rekening saat ini
3. Set saldo awal **Dana Darurat** sesuai dana darurat saat ini

### Followup Otomatis
1. Buka **Pengaturan → Otomasi**
2. Toggle **Followup Enabled** = ON
3. Set **Followup Hour** = jam WIB (misal `9` untuk jam 09:00 WIB)

> Scheduler jalan tiap jam, hanya kirim followup pas `current_hour == followup_hour`. Tanpa flag ini, sequence followup tidak dieksekusi.

### AI Proxy (9router)
1. Pastikan 9router running di server (default port `20128`)
2. Buka **Pengaturan → AI Config**
3. Set **Proxy URL** ke endpoint 9router (contoh: `http://localhost:20128/v1` atau remote tunnel)
4. Pilih **Active Combo** (default `combo-kiro` = Claude Sonnet)
5. Cek health via tombol "Test Connection"

> Jika 9router down, semua fitur AI (chat, content gen, lead analysis) akan gagal. Verifikasi `GET /api/ai/health` return ok.

---

## Data yang Di-seed

| Data | Isi |
|---|---|
| Kategori | 5 kategori layanan |
| Produk | 18 paket (Starter/Pro/Expert) |
| Template WA | 13 template blast & follow up |
| Wallet | Rekening Utama, Dana Darurat |
| Klien | PT Mitra Lindung Sarana, PT Momen Harmoni Kreatif |
| Proyek | 6 proyek (3 MLS, 3 MHK) |
| Transaksi | 17 transaksi April–Mei 2026 |

---

## Data yang Dipertahankan Saat Reset

- `users` — akun admin
- `system_settings`, `provider_configs` — konfigurasi sistem
- `categories`, `products`, `dynamic_templates` — katalog layanan
- `wallets`, `transactions`, `subscriptions` — data keuangan
- `leads` dengan status `Closed/Client` — PT MLS & PT MHK
- `projects` terkait klien di atas

## Data yang Dihapus Saat Reset

- Semua leads hasil scraping
- Board, kolom, card, komentar, checklist
- Chat projects, conversations, messages, memories
- Content sessions, generations, schedules
- Documents, document folders
- Proposals, blast campaigns, ads campaigns
- Follow up sequences, reengagement alerts
- Client notes, credentials, documents
- Contacts, audit logs, message templates, service items
