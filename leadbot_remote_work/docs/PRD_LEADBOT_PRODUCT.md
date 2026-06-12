# PRD LeadBot - WhatsApp Reply Conversion System

## Ringkasan
LeadBot adalah command center untuk menangani reply setelah WhatsApp blast. Fokus produk bukan blast, tapi konversi reply: klasifikasi intent, auto-reply, fallback AI/rule, human takeover, lead scoring, dan report campaign.

## Positioning
LeadBot = sistem auto-closing reply WhatsApp untuk bisnis Indonesia.

Bukan:
- WA blast tool generik
- chatbot keyword sederhana
- dashboard chat biasa

Ya:
- inbox operasional pasca campaign
- AI + rule fallback engine
- lead triage untuk sales/admin
- report conversion dari blast ke qualified lead

## Target User
- Agency lead generation
- UMKM yang rutin blast promo
- Sales/admin CS yang handle banyak nomor masuk
- Internal KantorTeman multi-client operation

## Masalah Utama
1. Reply WA blast masuk acak dan cepat tenggelam.
2. Admin lambat balas lead panas.
3. Auto-reply keyword terlalu kaku.
4. AI kadang gagal/lambat, perlu fallback aman.
5. Handoff manusia tidak jelas.
6. Tidak ada report campaign ke lead/conversion.

## Tujuan MVP
1. Pesan WA masuk muncul realtime di dashboard.
2. Sistem membalas otomatis jika aman.
3. Jika AI gagal, rule fallback tetap coba jalan.
4. Jika rule gagal, AI fallback tetap coba jalan.
5. Jika dua-duanya gagal, masuk antrean manusia.
6. Dashboard Bahasa Indonesia, sidebar, inbox nyaman.
7. Dashboard/API admin terlindungi auth.

## Workflow MVP
1. Customer reply WhatsApp.
2. Fonnte forward ke `/api/webhook`.
3. Sistem simpan conversation + inbound message.
4. Engine pilih route berdasarkan mode:
   - `ai_first`: AI -> keyword -> human.
   - `logic_ai`: keyword -> AI -> human.
5. Jika auto-reply berhasil, outbound tersimpan dan dikirim via Fonnte.
6. Jika gagal/berisiko, escalation persisted di DB.
7. Dashboard update via SSE realtime.
8. Admin bisa balas manual, generate saran AI, eskalasi, atau close.

## Fitur MVP Selesai
- Basic auth dashboard/admin API.
- SSE realtime endpoint.
- Sidebar UI Bahasa Indonesia.
- Inbox percakapan + chat detail.
- Mode AI dulu / Rule dulu.
- Test AI endpoint.
- Keyword CRUD.
- Escalation queue persisted di DB.
- Telegram admin guard.
- AI Vexo param fix (`key` + `text`).
- DB migration minimal.

## Fitur P1
1. Campaign-aware inbox.
   - simpan `campaign_id`, `campaign_name`, `segment`, `blast_copy`.
   - tampilkan asal reply di conversation.
2. Lead scoring.
   - hot: order, harga, booking, demo, butuh cepat.
   - warm: info, tanya produk, katalog.
   - risk: stop, komplain, salah sasaran.
3. Quick replies.
   - harga, katalog, follow-up, minta alamat, closing.
4. AI knowledge per campaign.
   - produk, harga, promo, FAQ, objection handling.
5. Agent assignment.
   - status: baru, bot replied, butuh manusia, follow-up, closing, selesai.
6. Report conversion.
   - reply rate, qualified rate, response time, AI resolved rate, handoff rate.

## Fitur P2
1. Multi-client workspace.
2. Multi-number routing.
3. Official WhatsApp Cloud API/BSP path.
4. Template/opt-in/unsubscribe handling.
5. Weekly PDF/WhatsApp report.
6. SLA timer + team performance.
7. CRM pipeline integration.

## Metrik Produk
- Reply rate per campaign.
- First response time.
- Auto-resolved rate.
- AI failure rate.
- Human takeover rate.
- Escalation backlog.
- Qualified lead rate.
- Campaign to lead conversion.
- Unsubscribe/stop rate.

## Non-Goal MVP
- Blast sender baru.
- Full CRM pipeline.
- Multi-tenant billing.
- Official WhatsApp BSP migration.

## Risiko
- Vexo bisa timeout/intermiten; fallback wajib aktif.
- Fonnte unofficial; perlu opsi official API untuk naik kelas.
- Dashboard auth basic cukup untuk MVP, belum production enterprise.
- Webhook secret belum wajib kalau Fonnte belum dikonfigurasi mengirim secret.

## Definition of Done MVP
Admin buka dashboard, kirim pesan WhatsApp, pesan muncul realtime, sistem membalas otomatis jika AI/rule berhasil, gagal masuk eskalasi, admin bisa balas manual dari web, dan semua status dasar tampil jelas.
