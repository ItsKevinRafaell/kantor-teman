## ATURAN KERAS BAHASA (Kevin) — OVERRIDE, wajib tiap post (synced 2026-07-23 audit)

1. DILARANG pakai - / — / em-dash / en-dash / tanda hubung sebagai pemisah atau gaya di post. Ganti dengan ", " (koma + spasi) atau susun ulang jadi dua kalimat. Arrow (→ / ->) juga DILARANG.
2. Bahasa kasual natural (lo/gue OK di akun personal tone). Jangan kaku/formal/salesy.
3. DILARANG rhetorical question cringe kayak "Developer tools era baru?" / "Worth the tradeoff?". Langsung kasih poin/opini.
4. DILARANG buzzword AI (termasuk varian tanpa hyphen/spasi): "revolusioner", "game-changer", "game changer", "paradigma baru", "era baru", "fase baru", "masuk era", "memasuki era", "changing the game", "gamechanging", "revolutionary". Preflight grep WAJIB case-insensitive: /(game.?changer|era.?baru|fase.?baru|paradigma.?baru|revolusioner|revolutionary|gamechanging|changing.?the.?game)/i. Pakai fakta + angka konkret.
5. WAJIB jalanin humanizer (skill humanizer-bahasa-indonesia) sebagai final check SEBELUM kirim/approve post. Jangan kirim sebelum bersih dari pola di atas.
6. Self-correction INSTAN: kalau Kevin koreksi konten, LANGSUNG patch skill ini / humanizer via skill_manage(action="patch", ...) di turn yang sama. Jangan cuma balas "siap" / tunggu disuruh dua kali.
7. DILARANG CTA generik ("Lo pernah...?" / "Lo pikir...?" / "Lo udah ... belum?"). Ganti opini langsung, pertanyaan spesifik, atau stop tanpa CTA.
8. DILARANG colon (:) sebagai pemisah deskripsi di body post ("Yang menarik:", "Intinya:", "Fungsinya:"). Hapus colon atau ganti koma.
9. DILARANG transition crutch: "Yang menarik" / "Yang bikin" / "Kenapa menarik" / "Yang seru" / "Intinya" di awal kalimat.
10. Hook post WAJIB deklaratif, TANPA "?". Tidak ada exception "narrative hook".

SELF-CHECK GATE sebelum present draft: grep body/hook/CTA untuk em-dash, buzzword regex di atas, CTA generik, colon body, transition crutch, hook "?". Kalau 1+ match → FIX dulu, baru present.
