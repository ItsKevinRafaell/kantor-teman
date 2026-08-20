# FIX A3 — Investigasi: `competitor_count` & `monthly_search_volume` = 0 (Section FOMO mati)

Status: **INVESTIGASI SAJA — tidak ada kode diedit / deploy.**
Prinsip: ANTI-HALU. Tidak mengarang angka.

---

## TL;DR

Section FOMO ada di **outreach/audit report publik** (bukan client monthly report).
Kedua field DIISI di `backend/routers/proposals.py`, **semua dari data internal ERP** — tidak
ada API eksternal (DataForSEO/Google Ads) yang terpasang. Keduanya 0 bukan karena bug integrasi,
tapi karena **data sumber di ERP tidak cocok / kosong**:

- `competitor_count = 0` → query menghitung lead lain dengan `product_interest` + kota sama.
  Gagal karena **`product_interest` menyimpan JASA AGENSI (web_development, seo_google_maps, ...),
  BUKAN kategori bisnis klien** (kontraktor, cafe, salon). Jadi "bisnis sejenis" tidak pernah
  ketemu secara bermakna, dan/atau `address`/`product_interest` lead-nya kosong.
- `monthly_search_volume = 0` → `get_monthly_search_volume(category, city)` mencari `category` di
  tabel heuristik `SEARCH_VOLUME_DATA` yang keys-nya kategori bisnis (`KONTRAKTOR`, `CAFE`, ...).
  Dipanggil dengan `lead.product_interest` (= jasa agensi) → **tidak pernah match** → return 0.

**Rekomendasi jujur:** Ini bisa diperbaiki dari data yang SUDAH ADA di ERP *jika* ERP mulai
menyimpan **kategori bisnis klien** per-lead (saat ini tidak ada field-nya). Tanpa itu, angka
akurat butuh sumber eksternal. Detail di bawah.

---

## 1. Di mana field DIISI (file + baris)

### `backend/routers/proposals.py`

Ada **dua endpoint** yang mengisi field ini (dua path report/proposal publik):

**A. `GET /api/proposals/public/by-slug/{slug}`** (baris 204–266)
- `competitor_count` dihitung di **baris 223–233**:
  ```py
  competitor_count = 0
  city = ""
  if lead and lead.address:
      city = lead.address.split(",")[-1].strip() if "," in (lead.address or "") else lead.address
  if lead and lead.product_interest and city:
      competitor_count = db.query(Lead).filter(
          Lead.product_interest == lead.product_interest,   # <-- MASALAH
          Lead.address.contains(city),
          Lead.id != lead.id,
          Lead.is_archived == False,
      ).count()
  ```
- di-return baris **264**. (Endpoint ini TIDAK mengisi `monthly_search_volume`.)

**B. `GET /api/proposals/public/report/{slug}` (report page outreach — yang dipakai section FOMO)**
(baris ~388–480)
- `competitor_count` dihitung di **baris 410–420** (identik dengan blok A).
- di-return baris **457**.
- `monthly_search_volume` di-return baris **460–463**:
  ```py
  "monthly_search_volume": get_monthly_search_volume(
      lead.product_interest or "",   # <-- MASALAH: ini jasa agensi, bukan kategori bisnis
      city if lead and lead.address else ""
  ) if lead else 0,
  ```

### `backend/search_volume_data.py` (fungsi `get_monthly_search_volume`, baris 127–168)
- Import: `proposals.py:31` → `from search_volume_data import get_monthly_search_volume`.
- **Bukan** API eksternal. Ini **tabel heuristik hardcoded** (estimasi internal) 17 kategori ×
  15 kota. Keys kategori: `KONTRAKTOR, EPOXY, WATERPROOFING, CAFE, RESTO, SALON, CATERING, AQIQAH,
  KLINIK_KECANTIKAN, LAUNDRY, WEDDING_ORGANIZER, TOKO_BANGUNAN, INTERIOR, PERCETAKAN, BENGKEL,
  FOTOGRAFI, FABRIKASI, KONSTRUKSI`.
- Kalau kategori tidak match → **return 0** (by design; docstring: "no random invent — unmatched
  category/city returns 0 (FE hides)"). Jadi 0 = "jujur, tidak tahu", bukan bug.

### Frontend (konsumen field)
- `frontend/src/components/report/ReportFOMOCloser.tsx:32` → `{report.competitor_count > 0 && (...)}`
  → **kalau 0, blok "Database lead mencatat N bisnis sejenis" disembunyikan** (itu sebabnya "FOMO mati").
- `frontend/src/components/report/ReportHero.tsx`, `ReportPainBox.tsx`, `AuditScore.tsx` mengonsumsi
  `search_volume`/`competitor` juga (di-hide saat 0).

---

## 2. Kenapa 0 di semua report (david, mls, lrt)

### `monthly_search_volume` — PENYEBAB PASTI (mismatch semantik)
Fungsi mencocokkan `category` ke tabel kategori BISNIS (`KONTRAKTOR`, `CAFE`, ...), tapi dipanggil
dengan `lead.product_interest`. Berdasarkan `routers/leads.py:48-54`, nilai valid `product_interest`
adalah **jasa yang dijual agensi**:
```
web_development, seo_google_maps, kelola_sosial_media, maintenance_website, desain_logo
```
Tidak satu pun cocok dengan keys `SEARCH_VOLUME_DATA` → fuzzy match juga gagal → **selalu 0**.
Ini deterministik: berlaku untuk SEMUA lead selama ERP mengisi `product_interest` dengan jasa agensi.

### `competitor_count` — PENYEBAB (kombinasi)
Query "hitung lead lain dengan product_interest + kota sama". Jadi 0 kalau salah satu:
1. `lead.address` kosong/tanpa kota → `city` kosong → blok tidak jalan.
2. `lead.product_interest` kosong → blok tidak jalan.
3. Tidak ada lead LAIN di DB dengan `product_interest` sama **dan** `address` mengandung kota sama
   (sangat mungkin untuk klien yang di-input manual satu-satu, bukan hasil scraping batch).

Karena `product_interest` = jenis JASA (bukan kategori bisnis), kalaupun tidak 0, angkanya
misleading: itu menghitung "berapa lead lain yang juga tertarik jasa X di kota Y", **bukan**
"berapa kompetitor bisnis klien". Frontend sudah jujur soal ini:
`ReportFOMOCloser.tsx:36` → "(bukan hitungan live Google Maps)".

> Catatan bukti live: DB produksi (MySQL, shared hosting) TIDAK ada di workspace ini
> (`config.py:49` default `sqlite:///./leads.db`, tapi file itu tidak ada di repo). Jadi saya
> **tidak bisa** query langsung nilai `product_interest`/`address` untuk david/mls/lrt. Kesimpulan
> di atas berbasis logika kode + skema, bukan inspeksi baris DB mereka. Yang PASTI: dengan skema
> `product_interest` saat ini, `monthly_search_volume` mustahil non-zero.

---

## 3. (a) Bisa dari data yang UDAH ADA di ERP? / (b) Butuh eksternal?

### `monthly_search_volume`
- **(a) Sebagian bisa, TAPI butuh field baru.** Tabel heuristik `SEARCH_VOLUME_DATA` sudah ada dan
  siap pakai. Yang hilang: ERP **tidak menyimpan kategori bisnis klien** per-lead (model `Lead`
  tidak punya field industri/kategori — lihat `models/lead.py:8-38`). Yang mendekati:
  - `ScrapeHistory.category` (`models/lead.py:71`) = keyword scraping (mis. "kontraktor"), tapi
    **tidak ter-link ke lead individual** — hanya via `batch_name`.
  - `lead.batch_name` kadang memuat keyword scraping → bisa jadi sumber heuristik kategori, tapi
    tidak terstruktur/tidak dijamin.
  - `LeadAnalysis` (AI scraper, dipakai di `proposals.py:425`) punya `suggested_product` — itu jasa,
    bukan kategori bisnis.
  - **Jujur:** tanpa field kategori bisnis yang bersih, mengganti argumen fungsi ke `product_interest`
    yang lain tidak menyelesaikan apa-apa. Perlu: (i) tambah field `business_category` di Lead +
    isi saat scraping/input, ATAU (ii) derive kategori dari `batch_name`/`ScrapeHistory` (kotor,
    perlu mapping). Angka yang keluar tetap **estimasi internal heuristik**, bukan data live.
- **(b) Untuk angka AKURAT/live:** butuh integrasi eksternal — Google Ads Keyword Planner API atau
  DataForSEO. **Belum ada sama sekali** di repo (tidak ada key/klien/env untuk itu; satu-satunya
  "sumber" adalah tabel hardcoded).

### `competitor_count`
- **(a) Bisa dari data ERP** — query sudah jalan; masalahnya semantik + kelengkapan data:
  - Kalau tujuannya "jumlah lead sekategori sejalur" → cukup pastikan `address` & `product_interest`
    terisi. Tapi ini **bukan kompetitor klien**, dan frontend sudah menandai demikian. Nilai bisa 0
    wajar untuk klien yang bukan bagian dari batch scraping besar.
  - Kalau tujuannya "jumlah kompetitor BISNIS klien di kota" → butuh field kategori bisnis (sama
    seperti di atas) supaya query menghitung bisnis sejenis, bukan "lead yang mau jasa sama".
- **(b) Untuk "hitungan live kompetitor Google Maps"** (yang paling meyakinkan untuk FOMO): butuh
  Google Places/Maps API call by kategori+lokasi. `lead.original_url` (link GMaps) tersimpan, tapi
  **tidak ada** kode yang memanggil Places API untuk menghitung kompetitor. Belum terintegrasi.

---

## 4. Rekomendasi jujur (ringkas, tanpa ngarang)

1. **`monthly_search_volume`:** Root cause = argumen salah + tidak ada field kategori bisnis.
   - Quick-win TIDAK mengubah angka jadi benar hanya dengan ganti argumen — **wajib** ada sumber
     kategori bisnis klien dulu. Opsi:
     - **Minimal jujur (rekomendasi utama):** biarkan 0 → FE sudah sembunyikan → tidak ada klaim
       palsu. (Sesuai prinsip Kevin ANTI-HALU.)
     - **Kalau mau hidup pakai data internal:** tambah field `Lead.business_category` + isi saat
       scraping (kategori keyword sudah diketahui di `ScrapeHistory.category`), lalu panggil
       `get_monthly_search_volume(lead.business_category, city)`. Label WAJIB "estimasi internal",
       bukan "Google Keyword Planner".
     - **Kalau mau angka live/kredibel:** integrasi DataForSEO / Google Ads Keyword Planner
       (butuh akun + API key + biaya). Belum ada di repo.
2. **`competitor_count`:** Jelaskan/tetapkan maksudnya dulu.
   - Kalau tetap "lead sekategori di DB": pastikan `address` (dengan kota) & `product_interest`
     terisi; angka 0 itu valid/jujur kalau memang tidak ada pembanding. FE label sudah benar.
   - Kalau mau "kompetitor bisnis klien": butuh field kategori bisnis (internal) atau Places API (live).
3. **JANGAN** isi angka default/ngarang untuk menghidupkan FOMO. 0 = jujur; itu perilaku desain
   yang sudah benar (`search_volume_data.py` docstring & FE hide-on-zero).

---

## Lampiran — daftar file/baris kunci
- `backend/routers/proposals.py:31` — import `get_monthly_search_volume`
- `backend/routers/proposals.py:223-233, 264` — `competitor_count` (endpoint by-slug)
- `backend/routers/proposals.py:410-420, 457` — `competitor_count` (endpoint report)
- `backend/routers/proposals.py:460-463` — `monthly_search_volume` (endpoint report)
- `backend/search_volume_data.py:7-116` — tabel heuristik `SEARCH_VOLUME_DATA` (17 kategori × 15 kota)
- `backend/search_volume_data.py:127-168` — `get_monthly_search_volume()` (return 0 kalau no match)
- `backend/routers/leads.py:48-54` — `PRODUCT_INTEREST_LABELS` (bukti product_interest = jasa agensi)
- `backend/models/lead.py:8-38` — model `Lead` (TIDAK ada field kategori bisnis)
- `backend/models/lead.py:68-76` — `ScrapeHistory.category` (kategori scraping, tak ter-link per-lead)
- `frontend/src/components/report/ReportFOMOCloser.tsx:32-38` — hide FOMO block saat `competitor_count == 0`
