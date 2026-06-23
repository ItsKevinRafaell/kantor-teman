"""Client-facing default templates for the document generator."""

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


RECEIPT_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}.amount{{font-size:24pt;font-weight:bold;color:#b45309;text-align:center;padding:18pt}}</style></head><body>
<table class="w100 top"><tr><td><div class="logo">{{logo}}</div><div class="eyebrow">{{brand_name}}</div><div class="title">BUKTI PEMBAYARAN</div></td><td class="right muted">No. <span class="strong">{{nomor}}</span><br/>{{tanggal}}</td></tr></table>
<table class="w100 box">
  <tr><td class="muted">Diterima dari</td><td class="right strong">{{klien}}</td></tr>
  <tr><td class="muted">Untuk pembayaran</td><td class="right strong">{{layanan}}</td></tr>
  <tr><td class="muted">Metode pembayaran</td><td class="right strong">{{payment_method}}</td></tr>
  <tr><td colspan="2" class="amount">{{amount}}</td></tr>
  <tr><td colspan="2" class="muted">{{keterangan}}</td></tr>
</table>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>{{tagline}}<br/>Bukti pembayaran sah tanpa tanda tangan basah.</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE)


PROPOSAL_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr><td><div class="logo">{{logo}}</div><div class="eyebrow">{{brand_name}}</div><div class="title">PROPOSAL PENAWARAN</div></td><td class="right muted">Tanggal: <span class="strong">{{tanggal}}</span><br/>Berlaku hingga: <span class="strong">{{valid_until}}</span></td></tr></table>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Penyedia Jasa</div><div class="strong">{{brand_name}}</div><div class="muted">{{phone_perusahaan}}<br/>{{email_perusahaan}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Disiapkan Untuk</div><div class="strong">{{klien}}</div><div class="muted">{{alamat}}<br/>{{phone}}</div></td></tr></table>
<div class="section-title">Layanan Utama</div><div class="soft"><span class="strong">{{layanan}}</span></div>
<div class="section-title">Lingkup Pekerjaan</div><div class="soft">{{scope}}</div>
<div class="section-title">Rincian Investasi</div>{{items_rows}}
<div class="note">Penawaran ini berlaku hingga <span class="strong">{{valid_until}}</span>. Harga dan jadwal pengerjaan dapat berubah setelah tanggal tersebut.</div>
<div class="footer"><span class="strong">{{brand_name}}</span><br/>{{tagline}}<br/>Proposal penawaran layanan.</div>
</body></html>""".format(BASE_STYLE=BASE_STYLE)


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
