"""Client-facing default templates for the document generator."""

# Pre-written scope templates for each service type
SCOPE_TEMPLATES = {
    "web_dev": {
        "name": "Pembuatan Website",
        "scope": "Pembuatan website profesional untuk bisnis Anda, meliputi:\n\n- Konsultasi dan riset kebutuhan bisnis\n- Desain tampilan yang menarik dan mudah digunakan\n- Integrasi WhatsApp untuk komunikasi langsung dengan pelanggan\n- Optimasi agar mudah ditemukan di Google\n- Website responsif untuk HP dan komputer\n- Domain dan hosting tahun pertama\n- Pelatihan cara update konten website",
    },
    "seo_gmaps": {
        "name": "SEO & Google Maps",
        "scope": "Optimasi agar bisnis Anda muncul di halaman pertama Google dan Google Maps, meliputi:\n\n- Riset kata kunci yang sering dicari pelanggan di daerah Anda\n- Optimasi profil Google Business Profile (foto, deskripsi, jam buka)\n- Pembuatan artikel/blog yang relevan dengan bisnis Anda\n- Optimasi teknis website agar cepat dan mudah dibaca Google\n- Monitoring peringkat dan laporan bulanan\n- Balasan ulasan pelanggan untuk membangun reputasi",
    },
    "sosmed": {
        "name": "Kelola Media Sosial",
        "scope": "Pengelolaan media sosial bisnis Anda agar aktif dan menarik pelanggan, meliputi:\n\n- Strategi konten bulanan sesuai target audiens\n- Desain konten visual yang konsisten dengan brand Anda\n- Penulisan caption yang menarik dan mendorong interaksi\n- Penjadwalan posting otomatis\n- Riset hashtag yang relevan\n- Laporan performa bulanan (jumlah like, komentar, followers baru)",
    },
    "maintenance": {
        "name": "Maintenance Website",
        "scope": "Perawatan rutin website Anda agar tetap aman dan berjalan lancar, meliputi:\n\n- Backup data mingguan (jaga-jaga kalau ada masalah)\n- Scan malware dan keamanan bulanan\n- Update sistem dan plugin otomatis\n- Monitoring performa website 24/7\n- Perbaikan bug atau error yang muncul\n- Laporan kondisi website bulanan",
    },
    "branding": {
        "name": "Desain Logo & Branding",
        "scope": "Pembuatan identitas visual bisnis Anda yang profesional dan konsisten, meliputi:\n\n- Konsultasi visi dan target audiens bisnis\n- Pembuatan beberapa opsi desain logo\n- Revisi hingga sesuai keinginan\n- File logo dalam berbagai format (untuk cetak dan digital)\n- Panduan penggunaan logo dan warna brand\n- Desain kartu nama dan kop surat (untuk paket lengkap)",
    },
    "retainer": {
        "name": "Paket Retainer Bulanan",
        "scope": "Layanan digital bulanan lengkap untuk bisnis Anda, meliputi kombinasi dari:\n\n- Pengembangan dan perawatan website\n- Optimasi SEO dan Google Maps\n- Pengelolaan media sosial\n- Konsultasi strategi digital\n- Laporan performa bulanan\n- Dukungan teknis prioritas",
    },
}

BASE_STYLE = """
@page{size:A4;margin:28pt 34pt}
body{font-family:Helvetica,Arial,sans-serif;color:#1f2937;font-size:10.5pt;line-height:1.45}
table{border-collapse:collapse}
.w100{width:100%}
.top{border-bottom:2pt solid #111827;margin-bottom:16pt;padding-bottom:12pt}
.logo img{max-height:48pt;max-width:150pt}
.eyebrow{font-size:8pt;font-weight:bold;color:#6b7280;text-transform:uppercase}
.title{font-size:22pt;font-weight:bold;color:#111827}
.accent{color:#b45309}
.right{text-align:right}
.muted{font-size:9pt;color:#6b7280}
.strong{font-weight:bold;color:#111827}
.box{border:1pt solid #d1d5db;padding:9pt;vertical-align:top}
.box-title{font-size:8pt;font-weight:bold;color:#6b7280;text-transform:uppercase;margin-bottom:4pt}
.section-title{font-size:8pt;font-weight:bold;color:#4b5563;text-transform:uppercase;border-bottom:1pt solid #d1d5db;padding-bottom:3pt;margin-top:14pt;margin-bottom:6pt}
.note{border:1pt solid #f59e0b;background-color:#fffbeb;color:#92400e;padding:8pt}
.soft{background-color:#f8fafc;padding:8pt}
.footer{border-top:1pt solid #d1d5db;margin-top:18pt;padding-top:8pt;font-size:8pt;color:#6b7280}
.sig-space{height:46pt}
.sig-line{border-top:1pt solid #111827;padding-top:5pt;text-align:center;font-weight:bold}
"""


INVOICE_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr>
  <td width="58%" valign="top"><div class="logo">{{logo}}</div><div class="eyebrow">{{brand_name}}</div><div class="title">INVOICE <span class="accent">{{nomor_invoice}}</span></div></td>
  <td width="42%" valign="top" class="right muted">Tanggal: <span class="strong">{{tanggal}}</span><br/>Jatuh tempo: <span class="strong">{{due_date}}</span></td>
</tr></table>
<table class="w100" cellspacing="0" cellpadding="0"><tr>
  <td width="49%" class="box"><div class="box-title">Dari</div><div class="strong">{{brand_name}}</div><div class="muted">{{alamat_perusahaan}}<br/>{{phone_perusahaan}}<br/>{{email_perusahaan}}</div></td>
  <td width="2%"></td>
  <td width="49%" class="box"><div class="box-title">Ditagihkan Kepada</div><div class="strong">{{klien}}</div><div class="muted">{{alamat}}<br/>{{phone}}</div></td>
</tr></table>
<div class="section-title">Rincian Tagihan</div>{{items_rows}}
<table class="w100" cellspacing="0" cellpadding="0"><tr>
  <td width="58%" valign="top"><div class="section-title">Pembayaran</div><div class="note">{{payment_info}}</div></td>
  <td width="2%"></td>
  <td width="40%" valign="top"><div class="section-title">Ketentuan</div><div class="soft">{{terms}}</div></td>
</tr></table>
<div class="section-title">Catatan</div><div class="muted">{{catatan}}</div>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>{{tagline}}<br/>Dokumen ini dibuat secara digital.</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE)


RECEIPT_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr><td><div class="logo">{{logo}}</div><div class="eyebrow">{{brand_name}}</div><div class="title">BUKTI PEMBAYARAN</div></td><td class="right muted">No. <span class="strong">{{nomor}}</span><br/>{{tanggal}}</td></tr></table>
<table class="w100 box">
  <tr><td class="muted">Diterima dari</td><td class="right strong">{{klien}}</td></tr>
  <tr><td class="muted">Untuk pembayaran</td><td class="right strong">{{layanan}}</td></tr>
  <tr><td class="muted">Metode pembayaran</td><td class="right strong">{{payment_method}}</td></tr>
  <tr><td colspan="2" class="muted">{{keterangan}}</td></tr>
</table>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>{{tagline}}<br/>Bukti pembayaran sah tanpa tanda tangan basah.</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE)


PROPOSAL_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page{size:A4;margin:28pt 34pt}
body{font-family:Helvetica,Arial,sans-serif;color:#1f2937;font-size:10.5pt;line-height:1.45}
table{border-collapse:collapse}
.w100{width:100%}
.top{border-bottom:2pt solid #111827;margin-bottom:16pt;padding-bottom:12pt}
.logo img{max-height:48pt;max-width:150pt}
.eyebrow{font-size:8pt;font-weight:bold;color:#6b7280;text-transform:uppercase}
.title{font-size:22pt;font-weight:bold;color:#111827}
.accent{color:#b45309}
.right{text-align:right}
.muted{font-size:9pt;color:#6b7280}
.strong{font-weight:bold;color:#111827}
.box{border:1pt solid #d1d5db;padding:9pt;vertical-align:top}
.box-title{font-size:8pt;font-weight:bold;color:#6b7280;text-transform:uppercase;margin-bottom:4pt}
.section-title{font-size:8pt;font-weight:bold;color:#4b5563;text-transform:uppercase;border-bottom:1pt solid #d1d5db;padding-bottom:3pt;margin-top:14pt;margin-bottom:6pt}
.note{border:1pt solid #f59e0b;background-color:#fffbeb;color:#92400e;padding:8pt}
.soft{background-color:#f8fafc;padding:8pt}
.footer{border-top:1pt solid #d1d5db;margin-top:18pt;padding-top:8pt;font-size:8pt;color:#6b7280}
</style>
</head>
<body>
<table class="w100 top">
<tr>
<td width="58%" valign="top"><div class="logo">{{logo}}</div><div class="eyebrow">{{brand_name}}</div><div class="title">PROPOSAL PENAWARAN</div><div class="muted">No. <span class="strong">{{nomor}}</span></div></td>
<td width="42%" valign="top" class="right muted">Tanggal: <span class="strong">{{tanggal}}</span><br/>Berlaku hingga: <span class="strong">{{valid_until}}</span></td>
</tr>
</table>
<table class="w100">
<tr>
<td width="49%" class="box">
<div class="box-title">Penyedia Jasa</div>
<div class="strong">{{brand_name}}</div>
<div class="muted">{{alamat_perusahaan}}<br/>{{phone_perusahaan}}<br/>{{email_perusahaan}}</div>
</td>
<td width="2%"></td>
<td width="49%" class="box">
<div class="box-title">Disiapkan Untuk</div>
<div class="strong">{{klien}}</div>
<div class="muted">{{alamat}}<br/>{{phone}}</div>
</td>
</tr>
</table>
<div class="section-title">Layanan Utama</div>
<div class="soft"><span class="strong">{{layanan}}</span></div>
<div class="section-title">Lingkup Pekerjaan</div>
<div class="soft">{{scope}}</div>
<div class="section-title">Rincian Investasi</div>
{{items_rows}}
<div class="note">Penawaran ini berlaku hingga <span class="strong">{{valid_until}}</span>. Harga dan jadwal pengerjaan dapat berubah setelah tanggal tersebut.</div>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>{{tagline}}<br/>Proposal penawaran layanan.</div>
</body>
</html>"""


QUOTATION_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr><td><div class="logo">{{logo}}</div><div class="eyebrow">{{brand_name}}</div><div class="title">SURAT PENAWARAN</div></td><td class="right muted">No. <span class="strong">{{nomor}}</span><br/>{{tanggal}}</td></tr></table>
<div class="box"><div class="box-title">Kepada Yth.</div><div class="strong">{{klien}}</div><div class="muted">{{alamat}}<br/>{{phone}}</div></div>
<div class="section-title">Perihal</div><div class="strong">{{perihal}}</div>
<p>Dengan hormat, bersama surat ini kami mengajukan penawaran layanan sebagai berikut:</p>
{{items_rows}}
<div class="section-title">Syarat dan Ketentuan</div><div class="soft">{{terms}}</div>
<p>Demikian penawaran ini kami sampaikan. Atas perhatian dan kepercayaan Anda, kami ucapkan terima kasih.</p>
<table class="w100"><tr><td width="55%"></td><td width="45%" class="right">Hormat kami,<div class="sig-space"></div><div class="sig-line">{{brand_name}}</div><div class="muted">Penyedia Jasa</div></td></tr></table>
</body></html>""".format(BASE_STYLE=BASE_STYLE)


AGREEMENT_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr><td><div class="logo">{{logo}}</div><div class="eyebrow">{{brand_name}}</div><div class="title">PERJANJIAN KERJA SAMA</div></td><td class="right muted">Mulai: <span class="strong">{{tanggal_mulai}}</span><br/>Selesai: <span class="strong">{{tanggal_akhir}}</span></td></tr></table>
<p>Perjanjian kerja sama ini dibuat dan disepakati oleh pihak-pihak berikut:</p>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Pihak Pertama - Penyedia Jasa</div><div class="strong">{{brand_name}}</div><div class="muted">{{alamat_perusahaan}}<br/>{{phone_perusahaan}}<br/>{{email_perusahaan}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Pihak Kedua - Klien</div><div class="strong">{{klien}}</div><div class="muted">{{alamat}}<br/>{{phone}}</div></td></tr></table>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Layanan</div><div class="strong">{{layanan}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Nilai dan Durasi</div><div class="strong">{{nilai_kontrak}}</div><div class="muted">{{durasi}}</div></td></tr></table>
<div class="section-title">Lingkup Pekerjaan</div><div class="soft">{{scope}}</div>
<div class="section-title">Syarat dan Ketentuan</div><div class="soft">{{terms}}</div>
<table class="w100"><tr><td width="45%" class="right">Pihak Pertama,<div class="sig-space"></div><div class="sig-line">{{brand_name}}</div><div class="muted">Penyedia Jasa</div></td><td width="10%"></td><td width="45%" class="right">Pihak Kedua,<div class="sig-space"></div><div class="sig-line">{{klien}}</div><div class="muted">Klien</div></td></tr></table>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>{{tagline}}<br/>Perjanjian kerja sama layanan.</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE)


MOU_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr><td><div class="logo">{{logo}}</div><div class="eyebrow">{{brand_name}}</div><div class="title">MEMORANDUM OF UNDERSTANDING</div></td><td class="right muted">No. <span class="strong">{{nomor}}</span><br/>Tanggal: <span class="strong">{{tanggal}}</span></td></tr></table>
<p>Nota kesepahaman ini dibuat sebagai dasar kerja sama awal antara pihak-pihak berikut:</p>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Pihak Pertama - Penyedia Jasa</div><div class="strong">{{brand_name}}</div><div class="muted">{{alamat_perusahaan}}<br/>{{phone_perusahaan}}<br/>{{email_perusahaan}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Pihak Kedua - Klien</div><div class="strong">{{klien}}</div><div class="muted">{{alamat}}<br/>{{phone}}</div></td></tr></table>
<div class="section-title">Tujuan Kerja Sama</div><div class="soft">{{tujuan}}</div>
<div class="section-title">Ruang Lingkup</div><div class="soft">{{scope}}</div>
<div class="section-title">Tanggung Jawab Pihak Pertama</div><div class="soft">{{tanggung_jawab_seller}}</div>
<div class="section-title">Tanggung Jawab Pihak Kedua</div><div class="soft">{{tanggung_jawab_buyer}}</div>
<div class="section-title">Jangka Waktu dan Tindak Lanjut</div><div class="soft">{{durasi}}<br/>{{terms}}</div>
<p>Nota kesepahaman ini bukan invoice atau bukti pembayaran. Detail komersial final dapat dituangkan dalam kontrak kerja sama atau surat pesanan terpisah.</p>
<table class="w100"><tr><td width="45%" class="right">Pihak Pertama,<div class="sig-space"></div><div class="sig-line">{{brand_name}}</div><div class="muted">Penyedia Jasa</div></td><td width="10%"></td><td width="45%" class="right">Pihak Kedua,<div class="sig-space"></div><div class="sig-line">{{klien}}</div><div class="muted">Klien</div></td></tr></table>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>{{tagline}}<br/>Nota kesepahaman kerja sama.</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE)


# ─── Service-Specific Contract Addendum Templates ─────────────────────────────────


WEB_DEV_ADDENDUM_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr>
  <td><div class="logo">{{logo}}</div><div class="eyebrow">{brand_name}</div><div class="title">LAMPIRAN KONTRAK</div><div class="accent">Website Development</div></td>
  <td class="right muted">Mulai: <span class="strong">{{tanggal_mulai}}</span><br/>Selesai: <span class="strong">{{tanggal_akhir}}</span></td>
</tr></table>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Pihak Pertama</div><div class="strong">{{brand_name}}</div><div class="muted">{{alamat_perusahaan}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Pihak Kedua</div><div class="strong">{{klien}}</div><div class="muted">{{alamat}}</div></td></tr></table>
<div class="section-title">1. Spesifikasi Teknis</div><div class="soft">{{tech_spec}}</div>
<div class="section-title">2. Lingkup Deliverables</div><div class="soft">{{deliverables}}</div>
<div class="section-title">3. Batas Revisi</div><div class="soft">{{revision_limit}}</div>
<div class="section-title">4. Jadwal Pembayaran</div><div class="soft">{{payment_schedule}}</div>
<div class="section-title">5. Milestone &amp; Serah Terima</div><div class="soft">{{milestones}}</div>
<div class="section-title">6. Kepemilikan Domain &amp; Hosting</div><div class="soft">{{domain_hosting}}</div>
<div class="section-title">7. Garansi Bug Fixing</div><div class="soft">{{bug_warranty}}</div>
<div class="section-title">8. Hak atas Kekayaan Intelektual</div><div class="soft">{{ip_rights}}</div>
<div class="section-title">9. Di Luar Lingkup</div><div class="soft">{{out_of_scope}}</div>
<table class="w100"><tr><td width="45%" class="right">Pihak Pertama,<div class="sig-space"></div><div class="sig-line">{{brand_name}}</div><div class="muted">Penyedia Jasa</div></td><td width="10%"></td><td width="45%" class="right">Pihak Kedua,<div class="sig-space"></div><div class="sig-line">{{klien}}</div><div class="muted">Klien</div></td></tr></table>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>Lampiran Kontrak &mdash; Website Development</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE, brand_name="{{brand_name}}")


SEO_ADDENDUM_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr>
  <td><div class="logo">{{logo}}</div><div class="eyebrow">{brand_name}</div><div class="title">LAMPIRAN KONTRAK</div><div class="accent">SEO &amp; Google Business Profile</div></td>
  <td class="right muted">Mulai: <span class="strong">{{tanggal_mulai}}</span><br/>Selesai: <span class="strong">{{tanggal_akhir}}</span></td>
</tr></table>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Pihak Pertama</div><div class="strong">{{brand_name}}</div><div class="muted">{{alamat_perusahaan}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Pihak Kedua</div><div class="strong">{{klien}}</div><div class="muted">{{alamat}}</div></td></tr></table>
<div class="section-title">1. Keyword Target</div><div class="soft">{{target_keywords}}</div>
<div class="section-title">2. Metrik Keberhasilan</div><div class="soft">{{success_metrics}}</div>
<div class="section-title">3. Batasan Ekspektasi</div><div class="soft">{{disclaimer}}</div>
<div class="section-title">4. Deliverables per Bulan</div><div class="soft">{{deliverables}}</div>
<div class="section-title">5. Laporan &amp; Reporting</div><div class="soft">{{reporting}}</div>
<div class="section-title">6. Jadwal Pembayaran</div><div class="soft">{{payment_schedule}}</div>
<div class="section-title">7. Perubahan Keyword atau Arah</div><div class="soft">{{scope_change}}</div>
<div class="section-title">8. Di Luar Lingkup</div><div class="soft">{{out_of_scope}}</div>
<table class="w100"><tr><td width="45%" class="right">Pihak Pertama,<div class="sig-space"></div><div class="sig-line">{{brand_name}}</div><div class="muted">Penyedia Jasa</div></td><td width="10%"></td><td width="45%" class="right">Pihak Kedua,<div class="sig-space"></div><div class="sig-line">{{klien}}</div><div class="muted">Klien</div></td></tr></table>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>Lampiran Kontrak &mdash; SEO &amp; Google Business Profile</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE, brand_name="{{brand_name}}")


SOSMED_ADDENDUM_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr>
  <td><div class="logo">{{logo}}</div><div class="eyebrow">{brand_name}</div><div class="title">LAMPIRAN KONTRAK</div><div class="accent">Social Media Management</div></td>
  <td class="right muted">Mulai: <span class="strong">{{tanggal_mulai}}</span><br/>Selesai: <span class="strong">{{tanggal_akhir}}</span></td>
</tr></table>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Pihak Pertama</div><div class="strong">{{brand_name}}</div><div class="muted">{{alamat_perusahaan}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Pihak Kedua</div><div class="strong">{{klien}}</div><div class="muted">{{alamat}}</div></td></tr></table>
<div class="section-title">1. Platform</div><div class="soft">{{platforms}}</div>
<div class="section-title">2. Deliverables per Bulan</div><div class="soft">{{deliverables}}</div>
<div class="section-title">3. Batas Revisi per Konten</div><div class="soft">{{revision_limit}}</div>
<div class="section-title">4. Proses Approval Konten</div><div class="soft">{{approval_flow}}</div>
<div class="section-title">5. Hak Kepemilikan Konten</div><div class="soft">{{content_ownership}}</div>
<div class="section-title">6. Jadwal Pembayaran</div><div class="soft">{{payment_schedule}}</div>
<div class="section-title">7. Kepatuhan Aturan Platform</div><div class="soft">{{platform_rules}}</div>
<div class="section-title">8. Escalation &amp; Urgent Content</div><div class="soft">{{escalation}}</div>
<div class="section-title">9. Di Luar Lingkup</div><div class="soft">{{out_of_scope}}</div>
<table class="w100"><tr><td width="45%" class="right">Pihak Pertama,<div class="sig-space"></div><div class="sig-line">{{brand_name}}</div><div class="muted">Penyedia Jasa</div></td><td width="10%"></td><td width="45%" class="right">Pihak Kedua,<div class="sig-space"></div><div class="sig-line">{{klien}}</div><div class="muted">Klien</div></td></tr></table>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>Lampiran Kontrak &mdash; Social Media Management</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE, brand_name="{{brand_name}}")


MAINTENANCE_ADDENDUM_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr>
  <td><div class="logo">{{logo}}</div><div class="eyebrow">{brand_name}</div><div class="title">LAMPIRAN KONTRAK</div><div class="accent">Maintenance &amp; Support</div></td>
  <td class="right muted">Mulai: <span class="strong">{{tanggal_mulai}}</span><br/>Selesai: <span class="strong">{{tanggal_akhir}}</span></td>
</tr></table>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Pihak Pertama</div><div class="strong">{{brand_name}}</div><div class="muted">{{alamat_perusahaan}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Pihak Kedua</div><div class="strong">{{klien}}</div><div class="muted">{{alamat}}</div></td></tr></table>
<div class="section-title">1. Cakupan Layanan</div><div class="soft">{{scope_included}}</div>
<div class="section-title">2. SLA Response Time</div><div class="soft">{{sla_metrics}}</div>
<div class="section-title">3. Jam Coverage</div><div class="soft">{{coverage_hours}}</div>
<div class="section-title">4. Jadwal Pembayaran</div><div class="soft">{{payment_schedule}}</div>
<div class="section-title">5. Laporan Bulanan</div><div class="soft">{{reporting}}</div>
<div class="section-title">6. Di Luar Cakupan</div><div class="soft">{{out_of_scope}}</div>
<div class="section-title">7. Escalation Darurat</div><div class="soft">{{emergency_escalation}}</div>
<div class="section-title">8. Penyelesaian Ticket</div><div class="soft">{{ticket_resolution}}</div>
<table class="w100"><tr><td width="45%" class="right">Pihak Pertama,<div class="sig-space"></div><div class="sig-line">{{brand_name}}</div><div class="muted">Penyedia Jasa</div></td><td width="10%"></td><td width="45%" class="right">Pihak Kedua,<div class="sig-space"></div><div class="sig-line">{{klien}}</div><div class="muted">Klien</div></td></tr></table>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>Lampiran Kontrak &mdash; Maintenance &amp; Support</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE, brand_name="{{brand_name}}")


BRANDING_ADDENDUM_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr>
  <td><div class="logo">{{logo}}</div><div class="eyebrow">{brand_name}</div><div class="title">LAMPIRAN KONTRAK</div><div class="accent">Branding &amp; Visual Identity</div></td>
  <td class="right muted">Mulai: <span class="strong">{{tanggal_mulai}}</span><br/>Selesai: <span class="strong">{{tanggal_akhir}}</span></td>
</tr></table>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Pihak Pertama</div><div class="strong">{{brand_name}}</div><div class="muted">{{alamat_perusahaan}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Pihak Kedua</div><div class="strong">{{klien}}</div><div class="muted">{{alamat}}</div></td></tr></table>
<div class="section-title">1. Deliverables</div><div class="soft">{{deliverables}}</div>
<div class="section-title">2. Jumlah Konsep Awal</div><div class="soft">{{concept_count}}</div>
<div class="section-title">3. Batas Revisi</div><div class="soft">{{revision_limit}}</div>
<div class="section-title">4. Moodboard &amp; Brief Approval</div><div class="soft">{{moodboard_approval}}</div>
<div class="section-title">5. Standar Warna &amp; Tipografi</div><div class="soft">{{color_standards}}</div>
<div class="section-title">6. Format File &amp; Hak Penggunaan</div><div class="soft">{{file_usage_rights}}</div>
<div class="section-title">7. Jadwal Pembayaran</div><div class="soft">{{payment_schedule}}</div>
<div class="section-title">8. Di Luar Lingkup</div><div class="soft">{{out_of_scope}}</div>
<table class="w100"><tr><td width="45%" class="right">Pihak Pertama,<div class="sig-space"></div><div class="sig-line">{{brand_name}}</div><div class="muted">Penyedia Jasa</div></td><td width="10%"></td><td width="45%" class="right">Pihak Kedua,<div class="sig-space"></div><div class="sig-line">{{klien}}</div><div class="muted">Klien</div></td></tr></table>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>Lampiran Kontrak &mdash; Branding &amp; Visual Identity</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE, brand_name="{{brand_name}}")


RETAINER_ADDENDUM_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr>
  <td><div class="logo">{{logo}}</div><div class="eyebrow">{brand_name}</div><div class="title">LAMPIRAN KONTRAK</div><div class="accent">Paket Retainer Bulanan</div></td>
  <td class="right muted">Mulai: <span class="strong">{{tanggal_mulai}}</span><br/>Selesai: <span class="strong">{{tanggal_akhir}}</span></td>
</tr></table>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Pihak Pertama</div><div class="strong">{{brand_name}}</div><div class="muted">{{alamat_perusahaan}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Pihak Kedua</div><div class="strong">{{klien}}</div><div class="muted">{{alamat}}</div></td></tr></table>
<div class="section-title">1. Cakupan per Bulan</div><div class="soft">{{scope_monthly}}</div>
<div class="section-title">2. Penggunaan Jam/Slot Bulanan</div><div class="soft">{{hour_allocation}}</div>
<div class="section-title">3. Billing Cycle &amp; Pembayaran</div><div class="soft">{{payment_schedule}}</div>
<div class="section-title">4. Rate Add-on</div><div class="soft">{{addon_rate}}</div>
<div class="section-title">5. Perubahan atau Penambahan Cakupan</div><div class="soft">{{scope_change}}</div>
<div class="section-title">6. Proses Permintaan Layanan (Change Request)</div><div class="soft">{{change_request_process}}</div>
<div class="section-title">7. Pemberitahuan Penghentian</div><div class="soft">{{termination_notice}}</div>
<div class="section-title">8. Laporan Progres</div><div class="soft">{{reporting}}</div>
<table class="w100"><tr><td width="45%" class="right">Pihak Pertama,<div class="sig-space"></div><div class="sig-line">{{brand_name}}</div><div class="muted">Penyedia Jasa</div></td><td width="10%"></td><td width="45%" class="right">Pihak Kedua,<div class="sig-space"></div><div class="sig-line">{{klien}}</div><div class="muted">Klien</div></td></tr></table>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>Lampiran Kontrak &mdash; Paket Retainer Bulanan</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE, brand_name="{{brand_name}}")


DEFAULT_DOCUMENT_TEMPLATES = [
    {
        "name": "Invoice",
        "type": "invoice",
        "html_template": INVOICE_HTML,
        "variables": [
            "logo", "nomor_invoice", "tanggal", "due_date", "klien", "alamat", "phone",
            "items_rows", "payment_info", "terms", "catatan", "brand_name",
            "alamat_perusahaan", "phone_perusahaan", "email_perusahaan", "tagline",
        ],
    },
    {
        "name": "Receipt / Bukti Pembayaran",
        "type": "receipt",
        "html_template": RECEIPT_HTML,
        "variables": ["logo", "nomor", "tanggal", "klien", "layanan", "payment_method", "amount", "keterangan", "brand_name", "tagline"],
    },
    {
        "name": "Proposal Penawaran PDF",
        "type": "proposal_pdf",
        "html_template": PROPOSAL_HTML,
        "variables": [
            "logo", "tanggal", "valid_until", "klien", "alamat", "phone", "layanan",
            "scope", "items_rows", "brand_name", "alamat_perusahaan",
            "phone_perusahaan", "email_perusahaan", "tagline",
        ],
    },
    {
        "name": "Surat Penawaran Formal",
        "type": "surat_penawaran",
        "html_template": QUOTATION_HTML,
        "variables": [
            "logo", "nomor", "tanggal", "klien", "alamat", "phone", "perihal",
            "items_rows", "terms", "brand_name", "alamat_perusahaan",
            "phone_perusahaan", "email_perusahaan",
        ],
    },
    {
        "name": "Kontrak Kerja Sama",
        "type": "kontrak",
        "html_template": AGREEMENT_HTML,
        "variables": [
            "logo", "tanggal_mulai", "tanggal_akhir", "klien", "alamat", "phone",
            "layanan", "durasi", "nilai_kontrak", "scope", "terms", "brand_name",
            "alamat_perusahaan", "phone_perusahaan", "email_perusahaan", "tagline",
        ],
    },
    {
        "name": "MOU Kerja Sama",
        "type": "mou",
        "html_template": MOU_HTML,
        "variables": [
            "logo", "nomor", "tanggal", "klien", "alamat", "phone", "tujuan",
            "scope", "tanggung_jawab_seller", "tanggung_jawab_buyer", "durasi",
            "terms", "brand_name", "alamat_perusahaan", "phone_perusahaan",
            "email_perusahaan", "tagline",
        ],
    },
    # ─── Service-Specific Contract Addendum Templates ──────────────────────────
    {
        "name": "Kontrak — Website Development",
        "type": "kontrak_web_dev",
        "html_template": WEB_DEV_ADDENDUM_HTML,
        "variables": [
            "logo", "brand_name", "alamat_perusahaan", "phone_perusahaan", "email_perusahaan",
            "klien", "alamat", "phone", "tagline",
            "tanggal_mulai", "tanggal_akhir",
            "tech_spec", "deliverables", "revision_limit", "payment_schedule",
            "milestones", "domain_hosting", "bug_warranty", "ip_rights", "out_of_scope",
        ],
    },
    {
        "name": "Kontrak — SEO & Google Business",
        "type": "kontrak_seo",
        "html_template": SEO_ADDENDUM_HTML,
        "variables": [
            "logo", "brand_name", "alamat_perusahaan", "phone_perusahaan", "email_perusahaan",
            "klien", "alamat", "phone", "tagline",
            "tanggal_mulai", "tanggal_akhir",
            "target_keywords", "success_metrics", "disclaimer", "deliverables",
            "reporting", "payment_schedule", "scope_change", "out_of_scope",
        ],
    },
    {
        "name": "Kontrak — Social Media Management",
        "type": "kontrak_sosmed",
        "html_template": SOSMED_ADDENDUM_HTML,
        "variables": [
            "logo", "brand_name", "alamat_perusahaan", "phone_perusahaan", "email_perusahaan",
            "klien", "alamat", "phone", "tagline",
            "tanggal_mulai", "tanggal_akhir",
            "platforms", "deliverables", "revision_limit", "approval_flow",
            "content_ownership", "payment_schedule", "platform_rules", "escalation", "out_of_scope",
        ],
    },
    {
        "name": "Kontrak — Maintenance & Support",
        "type": "kontrak_maintenance",
        "html_template": MAINTENANCE_ADDENDUM_HTML,
        "variables": [
            "logo", "brand_name", "alamat_perusahaan", "phone_perusahaan", "email_perusahaan",
            "klien", "alamat", "phone", "tagline",
            "tanggal_mulai", "tanggal_akhir",
            "scope_included", "sla_metrics", "coverage_hours", "payment_schedule",
            "reporting", "out_of_scope", "emergency_escalation", "ticket_resolution",
        ],
    },
    {
        "name": "Kontrak — Branding & Visual Identity",
        "type": "kontrak_branding",
        "html_template": BRANDING_ADDENDUM_HTML,
        "variables": [
            "logo", "brand_name", "alamat_perusahaan", "phone_perusahaan", "email_perusahaan",
            "klien", "alamat", "phone", "tagline",
            "tanggal_mulai", "tanggal_akhir",
            "deliverables", "concept_count", "revision_limit", "moodboard_approval",
            "color_standards", "file_usage_rights", "payment_schedule", "out_of_scope",
        ],
    },
    {
        "name": "Kontrak — Paket Retainer Bulanan",
        "type": "kontrak_retainer",
        "html_template": RETAINER_ADDENDUM_HTML,
        "variables": [
            "logo", "brand_name", "alamat_perusahaan", "phone_perusahaan", "email_perusahaan",
            "klien", "alamat", "phone", "tagline",
            "tanggal_mulai", "tanggal_akhir",
            "scope_monthly", "hour_allocation", "payment_schedule", "addon_rate",
            "scope_change", "change_request_process", "termination_notice", "reporting",
        ],
    },
]


def get_document_template_starters() -> dict:
    return {
        item["type"]: {
            "name": item["name"],
            "html_template": item["html_template"],
            "variables": item["variables"],
        }
        for item in DEFAULT_DOCUMENT_TEMPLATES
    }


# ─── Professional Service Descriptions ────────────────────────────────────────────────────
# Wording yang profesional, menjanjikan, dan realistis (tidak over-promise).
# Digunakan di surat penawaran, kontrak, proposal PDF, dan MOU.

SERVICE_DESCRIPTIONS: dict[str, dict[str, str]] = {

    # ─── Website Development ──────────────────────────────────────────────────
    "web_dev": {
        "layanan": "Pengembangan Website Profesional — Dominasi Digital Presence Bisnis Anda",
        "scope": (
            "Di era digital ini, website bukan lagi pilihan — ini adalah KEHARUSAN. 80% calon pelanggan\n"
            "meriset bisnis Anda di Google SEBELUM memutuskan untuk membeli. Tanpa website profesional,\n"
            "Anda kehilangan pelanggan ke kompetitor yang sudah online.\n\n"
            "Penyedia Jasa akan membangun website yang Bekerja 24/7 untuk bisnis Anda:\n"
            "  1. Discovery & Wireframe — kami pahami kebutuhan bisnis Anda secara mendalam.\n"
            "  2. Desain UI Premium — visual yang konsisten dengan brand dan menarik pelanggan.\n"
            "  3. Development — implementasi dengan standar aksesibilitas dan SEO dasar.\n"
            "  4. Testing & QA — uji menyeluruh di berbagai browser dan perangkat.\n"
            "  5. Deployment — peluncuran ke hosting yang telah disepakati."
        ),
        "deliverables": (
            "- Website responsif yang bekerja 24/7 untuk bisnis Anda\n"
            "- Domain & hosting tahun pertama GRATIS (hemat hingga Rp 500.000)\n"
            "- Dokumentasi teknis lengkap + panduan CMS\n"
            "- File sumber desain (jika disepakati saat kick-off)\n"
            "- Pelatihan singkat pengelolaan konten (jika CMS terpasang)\n"
            "- Garansi bug fixing 30 hari setelah serah terima"
        ),
        "terms": (
            "1. Pembayaran sesuai termin yang disepakati. DP 50% untuk memulai proyek.\n"
            "2. Revisi desain dan konten 2 (dua) kali GRATIS. Revisi tambahan dikenakan biaya.\n"
            "3. Konten (teks, foto, video) disediakan oleh klien. Kami bisa bantu copywriting dengan biaya terpisah.\n"
            "4. Website diserahkan dalam kondisi siap pakai dan optimal.\n"
            "5. GARANSI bug fixing 30 hari setelah serah terima final."
        ),
        "out_of_scope": (
            "Pengembangan fitur baru di luar cakupan awal, penulisan konten (copywriting),\n"
            "fotografi profesional, dan hosting management memerlukan addendum terpisah.\n"
            "Maintenance dan dukungan teknis pasca-launch tersedia dalam paket bulanan terpisah."
        ),
        "revision_limit": "2 (dua) kali revisi GRATIS. Revisi tambahan dikenakan biaya per sesi sesuai kesepakatan.",
        "bug_warranty": "GARANSI bug fixing 30 hari setelah serah terima final. Issue di luar bug (fitur baru, redesign) memerlukan addendum.",
        "ip_rights": "Hak atas kode dan aset desain website menjadi milik klien SETELAH pelunasan pembayaran. Penyedia Jasa berhak menampilkan website sebagai portofolio.",
        "domain_hosting": "Domain dan hosting tahun pertama GRATIS atas nama klien. Konfigurasi teknis ditangani oleh Penyedia Jasa. Setelah tahun pertama, perpanjangan domain & hosting menjadi tanggung jawab klien.",
        "milestones": (
            "1. Discovery & Wireframe → approval klien (3-5 hari kerja)\n"
            "2. Desain UI → approval klien (5-7 hari kerja)\n"
            "3. Development → demo internal (7-10 hari kerja)\n"
            "4. Testing & Revisi → UAT klien (3-5 hari kerja)\n"
            "5. Serah terima final → pelunasan"
        ),
    },

    # ─── Website Development Bulanan ──────────────────────────────────────────
    "web_dev_bulanan": {
        "layanan": "Website Bulanan — Profesional Tanpa Modal Besar",
        "scope": (
            "Bayangkan punya website profesional tanpa harus keluar modal jutaan di awal.\n"
            "Dengan paket bulanan, Anda bisa langsung online dan fokus kembangkan bisnis,\n"
            "sementara kami yang urus teknisnya.\n\n"
            "Layanan berkelanjutan yang membuat website Anda SELALU OPTIMAL:\n"
            "  1. Pemeliharaan teknis — update platform, plugin, dan optimasi performa.\n"
            "  2. Pengembangan fitur — penambahan halaman atau fungsionalitas sesuai prioritas.\n"
            "  3. Monitoring & report — laporan performa, uptime, dan penggunaan bulanan."
        ),
        "deliverables": (
            "- Website selalu ter-update dan aman dari vulnerability\n"
            "- Pengembangan fitur baru sesuai prioritas bisnis Anda\n"
            "- Laporan bulanan: performa, update yang dilakukan, dan rekomendasi\n"
            "- Dukungan teknis via WhatsApp/email selama jam kerja\n"
            "- Fleksibilitas: upgrade atau stop kapan saja tanpa penalti"
        ),
        "terms": (
            "1. Pembayaran bulanan di muka, sebelum tanggal 10 setiap bulannya.\n"
            "2. Prioritas pekerjaan ditentukan bersama di awal setiap bulan.\n"
            "3. Jam pengembangan yang tidak terpakai tidak dapat di-akumulasi ke bulan berikutnya.\n"
            "4. Layanan di luar jam kerja hanya untuk kondisi darurat (website down, error kritis).\n"
            "5. Stop layanan kapan saja dengan pemberitahuan 30 hari."
        ),
        "out_of_scope": (
            "Redesign total, pembuatan landing page baru untuk campaign iklan,\n"
            "penulisan konten (copywriting), dan fotografi memerlukan addendum terpisah.\n"
            "Biaya addendum akan dikonfirmasi sebelum pengerjaan."
        ),
        "revision_limit": "Revisi pada setiap deliverable sebanyak 2 (dua) kali dalam bulan berjalan.",
        "scope_monthly": "Jam pengembangan teknis, maintenance rutin, monitoring performa, dan dukungan komunikasi.",
        "hour_allocation": "Slot/jam pengembangan yang tidak terpakai dalam bulan berjalan tidak dapat di-akumulasi atau diuangkan.",
        "addon_rate": "Layanan di luar paket akan dikenakan biaya tambahan yang dikonfirmasi dan disepakati sebelum pengerjaan.",
        "change_request_process": "Permintaan perubahan dikirim via WhatsApp atau email. Akan di-acknowledge dalam 1x24 jam kerja.",
        "termination_notice": "Penghentian layanan harus disampaikan secara tertulis minimal 30 hari kalender sebelum akhir bulan berjalan.",
    },

    # ─── SEO & Google Business Profile ────────────────────────────────────────
    "seo_gmaps": {
        "layanan": "SEO & Google Maps — Jangan Biarkan Kompetitor Mendominasi Google Lebih Lama",
        "scope": (
            "46% pencarian di Google bersifat LOKAL. Artinya, pelanggan di sekitar Anda sedang\n"
            "mencari bisnis seperti Anda SEKARANG JUGA. Pertanyaannya: apakah mereka menemukan\n"
            "Anda, atau kompetitor Anda?\n\n"
            "Kami akan memastikan bisnis Anda TAMPIL di halaman pertama Google:\n"
            "  1. Audit mendalam — analisis kondisi website dan Google Business Profile (GBP).\n"
            "  2. Riset keyword strategis — identifikasi kata kunci yang menghasilkan KONVERSI.\n"
            "  3. On-page optimization — optimasi meta tag, heading, konten, dan kecepatan.\n"
            "  4. Off-page optimization — backlink berkualitas dan lokal citation.\n"
            "  5. GBP optimization — profil, posting rutin, dan review management.\n"
            "  6. Reporting transparan — laporan ranking, traffic, dan ROI setiap bulan."
        ),
        "deliverables": (
            "- Laporan audit digital awal (nilai Rp 500.000 — GRATIS untuk klien SEO)\n"
            "- Riset keyword strategis dengan volume pencarian dan tingkat kompetisi\n"
            "- Optimasi on-page menyeluruh (meta tag, heading, internal linking)\n"
            "- Posting Google Business Profile 4-12x per bulan (sesuai paket)\n"
            "- Laporan bulanan detail: ranking, traffic organik, dan rekomendasi strategis"
        ),
        "terms": (
            "1. Pembayaran bulanan di muka. Tanpa kontrak jangka panjang — berhenti kapan saja.\n"
            "2. Hasil SEO bersifat gradual. Peningkatan signifikan biasanya terlihat dalam 3-6 bulan.\n"
            "3. Perubahan keyword atau arah optimasi memerlukan addendum tertulis.\n"
            "4. Klien menyediakan akses ke website, Google Analytics, dan Google Search Console."
        ),
        "out_of_scope": (
            "Google Ads management (kami bisa bantu dengan biaya terpisah), penulisan konten blog\n"
            "(kecuali sudah termasuk dalam paket), desain grafis, dan pengembangan website.\n"
            "Biaya iklan Google Ads dibayar langsung oleh klien."
        ),
        "disclaimer": (
            "Hasil SEO bergantung pada algoritma Google, tingkat kompetisi, dan faktor eksternal.\n"
            "Kami TIDAK menjamin ranking #1 atau posisi spesifik. Namun, kami berkomitmen pada\n"
            "proses optimasi terbaik dengan strategi yang terbukti efektif. Peningkatan visibilitas\n"
            "biasanya terlihat dalam 3-6 bulan pertama."
        ),
        "target_keywords": "Daftar keyword akan disesuaikan berdasarkan riset awal dan disepakati bersama saat kick-off. Fokus pada keyword yang menghasilkan konversi, bukan hanya traffic.",
        "success_metrics": (
            "Metrik keberhasilan: perubahan ranking keyword target, peningkatan traffic organik,\n"
            "dan impresi Google Business Profile. Data dimonitor via Google Search Console dan Analytics.\n"
            "Target realistis: peningkatan 50-200% traffic organik dalam 6 bulan."
        ),
        "scope_change": "Perubahan keyword target atau arah optimasi memerlukan addendum tertulis dan penyesuaian biaya.",
    },

    # ─── Social Media Management ──────────────────────────────────────────────
    "sosmed": {
        "layanan": "Kelola Sosial Media — Bangun Brand yang Dicintai Pelanggan",
        "scope": (
            "Media sosial bukan lagi sekadar tempat posting — ini adalah CHANNEL PENJUALAN\n"
            "yang bisa menghasilkan revenue langsung. Bisnis yang aktif di sosmed mendapat\n"
            "3x lebih banyak kepercayaan dari calon pelanggan.\n\n"
            "Kami akan mengelola sosmed Anda secara PROFESIONAL:\n"
            "  1. Content planning — content calendar strategis berdasarkan target audiens.\n"
            "  2. Content creation — desain visual branded, copywriting persuasif, scheduling.\n"
            "  3. Posting & monitoring — publikasi konsisten sesuai jadwal optimal.\n"
            "  4. Analytics & optimization — laporan performa dan rekomendasi bulanan."
        ),
        "deliverables": (
            "- Content calendar bulanan (disetujui H-3 sebelum minggu berjalan)\n"
            "- 9-24 konten feed per bulan (sesuai paket) dengan desain branded premium\n"
            "- Copywriting/caption persuasif yang menghasilkan engagement dan konversi\n"
            "- Video reels editing (untuk paket Pro & Expert)\n"
            "- Laporan bulanan detail: reach, engagement, follower growth, dan ROI"
        ),
        "terms": (
            "1. Pembayaran bulanan di muka. Tanpa kontrak jangka panjang.\n"
            "2. Content calendar dikirim H-3 sebelum minggu berjalan.\n"
            "3. Klien wajib memberikan approval maksimal H-1.\n"
            "4. Konten yang tidak di-approve akan di-skip dari jadwal posting.\n"
            "5. Revisi konten 1x per konten sebelum scheduling (GRATIS)."
        ),
        "out_of_scope": (
            "Pembelian iklan (ad spend), pengelolaan DM/chat (community management),\n"
            "fotografi/videografi on-site, dan influencer collaboration memerlukan layanan terpisah.\n"
            "Klien bertanggung jawab atas kepatuhan terhadap kebijakan platform media sosial."
        ),
        "platform_rules": (
            "Penyedia Jasa tidak bertanggung jawab atas penangguhan atau pembatasan akun\n"
            "akibat pelanggaran kebijakan platform oleh klien atau pihak ketiga.\n"
            "Klien wajib memastikan konten yang disediakan tidak melanggar hak cipta atau regulasi."
        ),
        "escalation": (
            "Untuk konten urgent (campaign, promo, announcement), klien harus menginformasikan\n"
            "minimal 4 jam sebelum waktu posting yang diinginkan. Di luar jam kerja (18.00-09.00)\n"
            "dan weekend, layanan hanya untuk kondisi darurat yang telah disepakati."
        ),
        "approval_flow": (
            "Content calendar dikirim H-3 sebelum minggu berjalan. Klien wajib memberikan approval\n"
            "maksimal H-1. Konten yang tidak di-approve akan di-skip. Revisi 1x per konten sebelum scheduling."
        ),
        "content_ownership": (
            "SEMUA konten (desain, caption, video) menjadi milik klien SETELAH pembayaran lunas.\n"
            "Penyedia Jasa berhak menggunakan konten sebagai portofolio dengan izin klien."
        ),
        "revision_limit": "1 (satu) kali revisi GRATIS per konten sebelum scheduling. Revisi tambahan: Rp 50.000/sesi.",
    },

    # ─── Maintenance & Support ────────────────────────────────────────────────
    "maintenance": {
        "layanan": "Maintenance Website — Jangan Biarkan Website Anda Menjadi Beban Operasional",
        "scope": (
            "Website yang tidak di-maintenance adalah BOM WAKTU. Plugin usang, keamanan bolong,\n"
            "backup tidak teratur — semua ini bisa membuat website Anda DOWN dan kehilangan\n"
            "pelanggan dalam sekejap.\n\n"
            "Kami menjaga website Anda tetap AMAN, CEPAT, dan TERKINI:\n"
            "  1. Update rutin — plugin, theme, dan core platform selalu ter-update.\n"
            "  2. Backup berkala — backup mingguan/harian dengan retensi 30-90 hari.\n"
            "  3. Security monitoring — scanning malware dan vulnerability 24/7.\n"
            "  4. Bug fixing — perbaikan error dalam cakupan yang disepakati.\n"
            "  5. Performance optimization — website tetap cepat dan responsif.\n"
            "  6. Monthly report — laporan kondisi website dan aktivitas maintenance."
        ),
        "deliverables": (
            "- Update plugin, theme, dan core platform (mencegah vulnerability)\n"
            "- Backup rutin (mingguan/harian) dengan retensi 30-90 hari\n"
            "- Monitoring keamanan 24/7 dan scanning malware\n"
            "- Perbaikan bug dan error (dalam cakupan)\n"
            "- Performance optimization (kecepatan website)\n"
            "- Laporan bulanan detail: kondisi website, update, dan rekomendasi"
        ),
        "terms": (
            "1. Pembayaran bulanan di muka. Tanpa kontrak jangka panjang.\n"
            "2. Response time sesuai SLA yang disepakati (critical: 4 jam).\n"
            "3. Issue dianggap resolved ketika klien memberikan sign-off.\n"
            "4. Jika tidak ada respon dalam 5 hari kerja setelah penyelesaian, ticket akan di-closed."
        ),
        "out_of_scope": (
            "Pengembangan fitur baru, redesign halaman, penulisan konten,\n"
            "optimasi SEO, dan pengelolaan media sosial memerlukan addendum terpisah.\n"
            "Biaya addendum akan dikonfirmasi sebelum pengerjaan."
        ),
        "sla_metrics": (
            "Critical (website down/error fatal): Response dalam 4 jam kerja\n"
            "Normal (fungsi terganggu): Response dalam 1x24 jam kerja\n"
            "Low (kosmetik/minor): Response dalam 3x24 jam kerja"
        ),
        "coverage_hours": "Senin - Jumat, 09.00 - 18.00 WIB. Emergency di luar jam kerja hanya untuk kondisi kritis (website down total).",
        "emergency_escalation": "Kontak WhatsApp/SMS ke nomor yang dicantumkan saat kick-off. Emergency di luar jam kerja hanya untuk kondisi kritis yang mempengaruhi operasional bisnis.",
        "ticket_resolution": "Issue dianggap resolved saat klien memberikan sign-off. Jika tidak ada respon dalam 5 hari kerja, ticket akan di-closed.",
    },

    # ─── Branding & Visual Identity ───────────────────────────────────────────
    "branding": {
        "layanan": "Desain Logo & Identitas Visual — Bangun Brand yang Tak Terlupakan",
        "scope": (
            "Logo bukan sekadar gambar — ini adalah WAJAH brand Anda yang akan diingat pelanggan\n"
            "sepanjang waktu. Logo yang profesional meningkatkan kepercayaan hingga 80% dan\n"
            "membuat bisnis Anda terlihat SERIUS dan KREDIBEL di mata pelanggan.\n\n"
            "Kami akan menciptakan identitas visual yang MENCERMINKAN nilai bisnis Anda:\n"
            "  1. Discovery & Brief — kami pahami visi, misi, dan target audiens Anda.\n"
            "  2. Moodboard & Konsep — 3 arah konsep visual yang berbeda untuk Anda pilih.\n"
            "  3. Development — pengembangan 1 arah konsep yang dipilih hingga sempurna.\n"
            "  4. Brand Guide — pedoman lengkap penggunaan elemen visual brand Anda.\n"
            "  5. File Delivery — semua file dalam format profesional siap pakai."
        ),
        "deliverables": (
            "- 3 arah konsep awal (moodboard + visual direction) — Anda pilih yang terbaik\n"
            "- Logo final dalam SEMUA format: AI, PNG, SVG, EPS (siap cetak & digital)\n"
            "- Brand guide lengkap: warna, tipografi, penggunaan logo\n"
            "- Palet warna profesional (Pantone, CMYK, HEX, RGB)\n"
            "- Tipografi utama dan sekunder yang konsisten\n"
            "- File master vector (bisa diedit kapan saja tanpa kehilangan kualitas)"
        ),
        "terms": (
            "1. DP 50% saat kick-off, pelunasan saat serah terima final.\n"
            "2. 3 arah konsep awal. Klien memilih 1 arah untuk dikembangkan.\n"
            "3. Revisi sebanyak 3 (tiga) kali GRATIS per konsep.\n"
            "4. Revisi di luar batas dikenakan biaya tambahan.\n"
            "5. File final diserahkan setelah pelunasan — SEMUA hak milik Anda."
        ),
        "out_of_scope": (
            "Pengembangan website, pengelolaan media sosial, strategi pemasaran,\n"
            "dan material cetak tambahan (kartu nama, brosur, dll) memerlukan\n"
            "layanan terpisah. Biaya akan dikonfirmasi sebelum pengerjaan."
        ),
        "concept_count": "3 (tiga) arah konsep awal. Klien memilih 1 (satu) arah untuk dikembangkan lebih lanjut.",
        "revision_limit": "3 (tiga) kali revisi GRATIS per konsep. Revisi di luar batas dikenakan biaya tambahan per sesi.",
        "moodboard_approval": (
            "Moodboard dan brief visual harus di-approve oleh klien sebelum desain dimulai.\n"
            "Klien dianggap menyetujui brief apabila tidak memberikan koreksi dalam 3 hari kerja."
        ),
        "color_standards": "Standar warna disediakan dalam format Pantone, CMYK, HEX, dan RGB sesuai kebutuhan cetak dan digital.",
        "file_usage_rights": (
            "File final diserahkan setelah pelunasan. Hak penggunaan komersial milik klien.\n"
            "Penyedia Jasa berhak menampilkan karya sebagai portofolio, kecuali ada kesepakatan tertulis lain."
        ),
    },

    # ─── Retainer / Paket Bulanan Multi-Layanan ───────────────────────────────
    "retainer": {
        "layanan": "Paket Retainer Bulanan — Solusi Digital All-in-One untuk Bisnis Anda",
        "scope": (
            "Bayangkan memiliki TIM DIGITAL LENGKAP yang bekerja untuk bisnis Anda setiap bulan,\n"
            "tanpa perlu rekrut karyawan atau investasi besar. Dengan paket retainer, Anda mendapat\n"
            "akses ke berbagai layanan digital profesional dengan SATU KONTAK dan SATU HARGA BULANAN.\n\n"
            "Layanan terpadu yang mencakup SEMUA kebutuhan digital bisnis Anda:\n"
            "  1. Pengembangan & maintenance website — website selalu optimal dan aman\n"
            "  2. Optimasi SEO & Google Business Profile — tampil di halaman pertama Google\n"
            "  3. Pengelolaan konten media sosial — brand aktif dan engagement tinggi\n"
            "  4. Dukungan teknis dan konsultasi digital strategy — kami siap bantu kapan saja"
        ),
        "deliverables": (
            "- Semua deliverables sesuai layanan yang termasuk dalam paket Anda\n"
            "- Laporan bulanan komprehensif: progres, metrik, ROI, dan rekomendasi strategis\n"
            "- Dukungan komunikasi via WhatsApp/email selama jam kerja (response cepat)\n"
            "- Konsultasi digital strategy tanpa batas — kami bantu Anda tumbuh\n"
            "- Fleksibilitas: upgrade atau downgrade paket sesuai kebutuhan bisnis"
        ),
        "terms": (
            "1. Pembayaran bulanan di muka, sebelum tanggal 10 setiap bulannya.\n"
            "2. Prioritas layanan ditentukan bersama di awal setiap bulan — Anda yang kontrol.\n"
            "3. Slot/jam yang tidak terpakai tidak dapat di-akumulasi ke bulan berikutnya.\n"
            "4. Layanan di luar paket memerlukan addendum tertulis.\n"
            "5. Stop layanan kapan saja dengan pemberitahuan 30 hari — tanpa penalti."
        ),
        "out_of_scope": (
            "Layanan yang tidak termasuk dalam paket bulanan memerlukan addendum terpisah.\n"
            "Biaya add-on akan dikonfirmasi dan disepakati sebelum pengerjaan.\n"
            "Contoh: Google Ads management, fotografi/videografi, influencer collaboration."
        ),
        "scope_monthly": "Layanan sesuai paket yang disepakati: pengembangan website, SEO, sosial media, dan dukungan teknis.",
        "hour_allocation": "Slot/jam pengembangan dan layanan yang tidak terpakai dalam bulan berjalan tidak dapat di-akumulasi atau diuangkan.",
        "addon_rate": "Layanan di luar paket akan dikenakan biaya tambahan yang dikonfirmasi dan disepakati sebelum pengerjaan.",
        "change_request_process": "Permintaan layanan dikirim via WhatsApp atau email. Akan di-acknowledge dalam 1x24 jam kerja.",
        "termination_notice": "Penghentian layanan harus disampaikan secara tertulis minimal 30 hari kalender sebelum akhir bulan berjalan.",
    },
}


def get_service_description(service_type: str) -> dict[str, str]:
    """Get professional description for a service type. Returns defaults if not found."""
    return SERVICE_DESCRIPTIONS.get(service_type, {})


def get_all_service_descriptions() -> dict[str, dict[str, str]]:
    """Get all service descriptions."""
    return dict(SERVICE_DESCRIPTIONS)

