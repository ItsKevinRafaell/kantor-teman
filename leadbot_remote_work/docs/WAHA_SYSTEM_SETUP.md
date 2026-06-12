# WAHA System Setup

Status saat ini:
- LeadBot sudah memakai `wahaService` untuk webhook inbound, auto-reply, dashboard reply, dan Telegram admin reply.
- Engine lama Fonnte/keyword/mode/answer-engine deterministic sudah dihapus dari source.
- Docker sudah disiapkan untuk menjalankan WAHA lokal di `127.0.0.1:3001`.
- Image WAHA belum dipull karena storage VPS kecil; jalankan pull setelah storage dinaikkan.

Konfigurasi runtime:
- Image default: `devlikeapro/waha:noweb`
- Container: `leadbot-waha`
- Port host: `127.0.0.1:3001 -> container 3000`
- Session folder: `/opt/leadbot/.waha/.sessions`
- Media folder: `/opt/leadbot/.waha/.media`
- Webhook WAHA ke LeadBot: `http://host.docker.internal:3000/api/webhook`
- Event webhook default: `message`

Perintah setelah storage VPS dinaikkan:

```bash
cd /opt/leadbot
scripts/waha-pull.sh
systemctl enable --now leadbot-waha.service
systemctl status leadbot-waha.service --no-pager
curl -sS http://127.0.0.1:3001/api/sessions
```

Dashboard LeadBot:
- Buka menu `WhatsApp`.
- Start session jika belum aktif.
- Ambil QR atau pairing code.
- Setelah status WAHA working, chat WhatsApp akan masuk ke `/api/webhook`.

Catatan storage:
- Jangan aktifkan full media auto-download sebelum backup Google Drive siap.
- Jaga minimal 5 GB free sebelum pull image WAHA.
- Jika perlu bersih-bersih Docker: `docker system prune -af --volumes`.
