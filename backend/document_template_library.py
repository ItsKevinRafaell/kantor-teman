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


INVOICE_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr>
  <td width="58%" valign="top"><div class="logo">{{{{logo}}}}</div><div class="eyebrow">{{{{brand_name}}}}</div><div class="title">INVOICE <span class="accent">{{{{nomor_invoice}}}}</span></div></td>
  <td width="42%" valign="top" class="right muted">Tanggal: <span class="strong">{{{{tanggal}}}}</span><br/>Jatuh tempo: <span class="strong">{{{{due_date}}}}</span></td>
</tr></table>
<table class="w100" cellspacing="0" cellpadding="0"><tr>
  <td width="49%" class="box"><div class="box-title">Dari</div><div class="strong">{{{{brand_name}}}}</div><div class="muted">{{{{alamat_perusahaan}}}}<br/>{{{{phone_perusahaan}}}}<br/>{{{{email_perusahaan}}}}</div></td>
  <td width="2%"></td>
  <td width="49%" class="box"><div class="box-title">Ditagihkan Kepada</div><div class="strong">{{{{klien}}}}</div><div class="muted">{{{{alamat}}}}<br/>{{{{phone}}}}</div></td>
</tr></table>
<div class="section-title">Rincian Tagihan</div>{{{{items_rows}}}}
<table class="w100" cellspacing="0" cellpadding="0"><tr>
  <td width="58%" valign="top"><div class="section-title">Pembayaran</div><div class="note">{{{{payment_info}}}}</div></td>
  <td width="2%"></td>
  <td width="40%" valign="top"><div class="section-title">Ketentuan</div><div class="soft">{{{{terms}}}}</div></td>
</tr></table>
<div class="section-title">Catatan</div><div class="muted">{{{{catatan}}}}</div>
<div class="footer"><span class="strong">{{{{brand_name}}}}</span><br/>{{{{tagline}}}}<br/>Dokumen ini dibuat secara digital.</div>
</body></html>"""


RECEIPT_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}.amount{{font-size:24pt;font-weight:bold;color:#b45309;text-align:center;padding:18pt}}</style></head><body>
<table class="w100 top"><tr><td><div class="logo">{{{{logo}}}}</div><div class="eyebrow">{{{{brand_name}}}}</div><div class="title">BUKTI PEMBAYARAN</div></td><td class="right muted">No. <span class="strong">{{{{nomor}}}}</span><br/>{{{{tanggal}}}}</td></tr></table>
<table class="w100 box">
  <tr><td class="muted">Diterima dari</td><td class="right strong">{{{{klien}}}}</td></tr>
  <tr><td class="muted">Untuk pembayaran</td><td class="right strong">{{{{layanan}}}}</td></tr>
  <tr><td class="muted">Metode pembayaran</td><td class="right strong">{{{{payment_method}}}}</td></tr>
  <tr><td colspan="2" class="amount">{{{{amount}}}}</td></tr>
  <tr><td colspan="2" class="muted">{{{{keterangan}}}}</td></tr>
</table>
<div class="footer"><span class="strong">{{{{brand_name}}}}</span><br/>{{{{tagline}}}}<br/>Bukti pembayaran sah tanpa tanda tangan basah.</div>
</body></html>"""


PROPOSAL_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr><td><div class="logo">{{{{logo}}}}</div><div class="eyebrow">{{{{brand_name}}}}</div><div class="title">PROPOSAL PENAWARAN</div></td><td class="right muted">Tanggal: <span class="strong">{{{{tanggal}}}}</span><br/>Berlaku hingga: <span class="strong">{{{{valid_until}}}}</span></td></tr></table>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Penyedia Jasa</div><div class="strong">{{{{brand_name}}}}</div><div class="muted">{{{{phone_perusahaan}}}}<br/>{{{{email_perusahaan}}}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Disiapkan Untuk</div><div class="strong">{{{{klien}}}}</div><div class="muted">{{{{alamat}}}}<br/>{{{{phone}}}}</div></td></tr></table>
<div class="section-title">Layanan Utama</div><div class="soft"><span class="strong">{{{{layanan}}}}</span></div>
<div class="section-title">Lingkup Pekerjaan</div><div class="soft">{{{{scope}}}}</div>
<div class="section-title">Rincian Investasi</div>{{{{items_rows}}}}
<div class="note">Penawaran ini berlaku hingga <span class="strong">{{{{valid_until}}}}</span>. Harga dan jadwal pengerjaan dapat berubah setelah tanggal tersebut.</div>
<div class="footer"><span class="strong">{{{{brand_name}}}}</span><br/>{{{{tagline}}}}<br/>Proposal penawaran layanan.</div>
</body></html>"""


QUOTATION_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr><td><div class="logo">{{{{logo}}}}</div><div class="eyebrow">{{{{brand_name}}}}</div><div class="title">SURAT PENAWARAN</div></td><td class="right muted">No. <span class="strong">{{{{nomor}}}}</span><br/>{{{{tanggal}}}}</td></tr></table>
<div class="box"><div class="box-title">Kepada Yth.</div><div class="strong">{{{{klien}}}}</div><div class="muted">{{{{alamat}}}}<br/>{{{{phone}}}}</div></div>
<div class="section-title">Perihal</div><div class="strong">{{{{perihal}}}}</div>
<p>Dengan hormat, bersama surat ini kami mengajukan penawaran layanan sebagai berikut:</p>
{{{{items_rows}}}}
<div class="section-title">Syarat dan Ketentuan</div><div class="soft">{{{{terms}}}}</div>
<p>Demikian penawaran ini kami sampaikan. Atas perhatian dan kepercayaan Anda, kami ucapkan terima kasih.</p>
<table class="w100"><tr><td width="55%"></td><td width="45%" class="right">Hormat kami,<div class="sig-space"></div><div class="sig-line">{{{{brand_name}}}}</div><div class="muted">Penyedia Jasa</div></td></tr></table>
</body></html>"""


AGREEMENT_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body>
<table class="w100 top"><tr><td><div class="logo">{{{{logo}}}}</div><div class="eyebrow">{{{{brand_name}}}}</div><div class="title">PERJANJIAN KERJA SAMA</div></td><td class="right muted">Mulai: <span class="strong">{{{{tanggal_mulai}}}}</span><br/>Selesai: <span class="strong">{{{{tanggal_akhir}}}}</span></td></tr></table>
<p>Perjanjian kerja sama ini dibuat dan disepakati oleh pihak-pihak berikut:</p>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Pihak Pertama - Penyedia Jasa</div><div class="strong">{{{{brand_name}}}}</div><div class="muted">{{{{alamat_perusahaan}}}}<br/>{{{{phone_perusahaan}}}}<br/>{{{{email_perusahaan}}}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Pihak Kedua - Klien</div><div class="strong">{{{{klien}}}}</div><div class="muted">{{{{alamat}}}}<br/>{{{{phone}}}}</div></td></tr></table>
<table class="w100"><tr><td width="49%" class="box"><div class="box-title">Layanan</div><div class="strong">{{{{layanan}}}}</div></td><td width="2%"></td><td width="49%" class="box"><div class="box-title">Nilai dan Durasi</div><div class="strong">{{{{nilai_kontrak}}}}</div><div class="muted">{{{{durasi}}}}</div></td></tr></table>
<div class="section-title">Lingkup Pekerjaan</div><div class="soft">{{{{scope}}}}</div>
<div class="section-title">Syarat dan Ketentuan</div><div class="soft">{{{{terms}}}}</div>
<table class="w100"><tr><td width="45%" class="right">Pihak Pertama,<div class="sig-space"></div><div class="sig-line">{{{{brand_name}}}}</div><div class="muted">Penyedia Jasa</div></td><td width="10%"></td><td width="45%" class="right">Pihak Kedua,<div class="sig-space"></div><div class="sig-line">{{{{klien}}}}</div><div class="muted">Klien</div></td></tr></table>
<div class="footer"><span class="strong">{{{{brand_name}}}}</span><br/>{{{{tagline}}}}<br/>Perjanjian kerja sama layanan.</div>
</body></html>"""


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
        "name": "Kontrak / MoU",
        "type": "kontrak",
        "html_template": AGREEMENT_HTML,
        "variables": [
            "logo", "tanggal_mulai", "tanggal_akhir", "klien", "alamat", "phone",
            "layanan", "durasi", "nilai_kontrak", "scope", "terms", "brand_name",
            "alamat_perusahaan", "phone_perusahaan", "email_perusahaan", "tagline",
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
