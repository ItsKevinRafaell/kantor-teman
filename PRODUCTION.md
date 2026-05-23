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

---

## Konfigurasi Post-Launch (via UI)

### Fonnte Quota
1. Buka **Pusat Biaya & Kuota → Fonnte WhatsApp**
2. Set **Monthly Quota** = jumlah pesan yang kamu top up per bulan
3. Set **Remaining Quota** = sisa pesan saat ini
4. Scheduler akan auto-reset `remaining_quota` ke `monthly_quota` setiap tanggal 1 jam 00:00

### API Keys
Pastikan sudah diisi di **Pengaturan → API**:
- `FONNTE_TOKEN`
- `GEMINI_API_KEY` (atau Claude / OpenAI sesuai kebutuhan)

### Wallet Saldo Awal
1. Buka **Keuangan → Wallet**
2. Set saldo awal **Rekening Utama** sesuai saldo rekening saat ini
3. Set saldo awal **Dana Darurat** sesuai dana darurat saat ini

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
