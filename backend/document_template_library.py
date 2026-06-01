"""Client-facing default templates for the document generator."""

BASE_STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700&display=swap');
@page{size:A4;margin:0}
*{font-family:'Noto Sans',Arial,sans-serif;box-sizing:border-box}
body{margin:0;color:#1e293b;font-size:11px;line-height:1.65;background:#fff}
.page{padding:42px 48px;min-height:297mm}
.top{display:flex;justify-content:space-between;gap:24px;padding-bottom:20px;border-bottom:2px solid #1e293b;margin-bottom:24px}
.logo img{max-height:54px;max-width:180px}
.eyebrow{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#94a3b8}
.title{margin:4px 0 0;font-size:25px;line-height:1.1;color:#0f172a}
.accent{color:#d97706}
.meta{text-align:right;color:#64748b;font-size:10px;line-height:1.8}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:18px 0}
.card{border:1px solid #e2e8f0;border-radius:8px;padding:13px 15px}
.card-title{margin-bottom:6px;font-size:9px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#94a3b8}
.strong{font-weight:700;color:#0f172a}
.muted{font-size:10px;color:#64748b}
.section{margin-top:20px}
.section-title{padding-bottom:5px;border-bottom:1px solid #e2e8f0;margin-bottom:9px;font-size:9px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#64748b}
.text-box{padding:12px 14px;border-radius:7px;background:#f8fafc;color:#475569;white-space:pre-line}
.notice{padding:11px 13px;border:1px solid #fde68a;border-radius:7px;background:#fffbeb;color:#92400e;white-space:pre-line}
.footer{display:flex;justify-content:space-between;gap:16px;margin-top:26px;padding-top:12px;border-top:1px solid #e2e8f0;font-size:9px;color:#94a3b8}
.signatures{display:grid;grid-template-columns:1fr 1fr;gap:42px;margin-top:54px}
.sig{text-align:center}
.sig-space{height:54px}
.sig-line{padding-top:6px;border-top:1px solid #334155;font-weight:700;color:#0f172a}
.sig-role{font-size:9px;color:#94a3b8}
"""


INVOICE_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}
.payment{{display:grid;grid-template-columns:1.2fr .8fr;gap:16px;margin-top:20px}}
</style></head><body><div class="page">
<div class="top">
  <div><div class="logo">{{{{logo}}}}</div><div class="eyebrow">{{{{nama_perusahaan}}}}</div><h1 class="title">INVOICE <span class="accent">{{{{nomor_invoice}}}}</span></h1></div>
  <div class="meta">Tanggal: <strong>{{{{tanggal}}}}</strong><br>Jatuh tempo: <strong>{{{{due_date}}}}</strong></div>
</div>
<div class="grid-2">
  <div class="card"><div class="card-title">Dari</div><div class="strong">{{{{nama_perusahaan}}}}</div><div class="muted">{{{{alamat_perusahaan}}}}<br>{{{{phone_perusahaan}}}}<br>{{{{email_perusahaan}}}}</div></div>
  <div class="card"><div class="card-title">Ditagihkan Kepada</div><div class="strong">{{{{klien}}}}</div><div class="muted">{{{{alamat}}}}<br>{{{{phone}}}}</div></div>
</div>
<div class="section"><div class="section-title">Rincian Tagihan</div>{{{{items_rows}}}}</div>
<div class="payment">
  <div><div class="section-title">Pembayaran</div><div class="notice">{{{{payment_info}}}}</div></div>
  <div><div class="section-title">Ketentuan</div><div class="text-box">{{{{terms}}}}</div></div>
</div>
<div class="section"><div class="section-title">Catatan</div><div class="muted">{{{{catatan}}}}</div></div>
<div class="footer"><div><strong>{{{{nama_perusahaan}}}}</strong><br>{{{{tagline}}}}</div><div>Dokumen ini dibuat secara digital.</div></div>
</div></body></html>"""


RECEIPT_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}
.receipt{{max-width:500px;margin:28px auto;padding:24px;border:1px solid #e2e8f0;border-top:4px solid #d97706;border-radius:10px}}
.receipt-row{{display:flex;justify-content:space-between;gap:16px;padding:9px 0;border-bottom:1px solid #f1f5f9}}
.amount{{margin:20px 0;text-align:center;font-size:26px;font-weight:700;color:#d97706}}
</style></head><body><div class="page">
<div class="top"><div><div class="logo">{{{{logo}}}}</div><div class="eyebrow">{{{{nama_perusahaan}}}}</div><h1 class="title">BUKTI PEMBAYARAN</h1></div><div class="meta">No. <strong>{{{{nomor}}}}</strong><br>{{{{tanggal}}}}</div></div>
<div class="receipt">
  <div class="receipt-row"><span class="muted">Diterima dari</span><strong>{{{{klien}}}}</strong></div>
  <div class="receipt-row"><span class="muted">Untuk pembayaran</span><strong>{{{{layanan}}}}</strong></div>
  <div class="receipt-row"><span class="muted">Metode pembayaran</span><strong>{{{{payment_method}}}}</strong></div>
  <div class="amount">{{{{amount}}}}</div>
  <div class="muted">{{{{keterangan}}}}</div>
</div>
<div class="footer"><div><strong>{{{{nama_perusahaan}}}}</strong><br>{{{{tagline}}}}</div><div>Bukti pembayaran sah tanpa tanda tangan basah.</div></div>
</div></body></html>"""


PROPOSAL_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body><div class="page">
<div class="top"><div><div class="logo">{{{{logo}}}}</div><div class="eyebrow">{{{{nama_perusahaan}}}}</div><h1 class="title">PROPOSAL PENAWARAN</h1></div><div class="meta">Tanggal: <strong>{{{{tanggal}}}}</strong><br>Berlaku hingga: <strong>{{{{valid_until}}}}</strong></div></div>
<div class="grid-2">
  <div class="card"><div class="card-title">Penyedia Jasa</div><div class="strong">{{{{nama_perusahaan}}}}</div><div class="muted">{{{{phone_perusahaan}}}}<br>{{{{email_perusahaan}}}}</div></div>
  <div class="card"><div class="card-title">Disiapkan Untuk</div><div class="strong">{{{{klien}}}}</div><div class="muted">{{{{alamat}}}}<br>{{{{phone}}}}</div></div>
</div>
<div class="section"><div class="section-title">Layanan Utama</div><div class="text-box"><strong>{{{{layanan}}}}</strong></div></div>
<div class="section"><div class="section-title">Lingkup Pekerjaan</div><div class="text-box">{{{{scope}}}}</div></div>
<div class="section"><div class="section-title">Rincian Investasi</div>{{{{items_rows}}}}</div>
<div class="section"><div class="notice">Penawaran ini berlaku hingga <strong>{{{{valid_until}}}}</strong>. Harga dan jadwal pengerjaan dapat berubah setelah tanggal tersebut.</div></div>
<div class="footer"><div><strong>{{{{nama_perusahaan}}}}</strong><br>{{{{tagline}}}}</div><div>Proposal penawaran layanan.</div></div>
</div></body></html>"""


QUOTATION_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body><div class="page">
<div class="top"><div><div class="logo">{{{{logo}}}}</div><div class="eyebrow">{{{{nama_perusahaan}}}}</div><h1 class="title">SURAT PENAWARAN</h1></div><div class="meta">No. <strong>{{{{nomor}}}}</strong><br>{{{{tanggal}}}}</div></div>
<div class="card"><div class="card-title">Kepada Yth.</div><div class="strong">{{{{klien}}}}</div><div class="muted">{{{{alamat}}}}<br>{{{{phone}}}}</div></div>
<div class="section"><div class="section-title">Perihal</div><div class="strong">{{{{perihal}}}}</div></div>
<p>Dengan hormat, bersama surat ini kami mengajukan penawaran layanan sebagai berikut:</p>
<div class="section">{{{{items_rows}}}}</div>
<div class="section"><div class="section-title">Syarat dan Ketentuan</div><div class="text-box">{{{{terms}}}}</div></div>
<p>Demikian penawaran ini kami sampaikan. Atas perhatian dan kepercayaan Anda, kami ucapkan terima kasih.</p>
<div class="signatures"><div></div><div class="sig"><div>Hormat kami,</div><div class="sig-space"></div><div class="sig-line">{{{{nama_perusahaan}}}}</div><div class="sig-role">Penyedia Jasa</div></div></div>
</div></body></html>"""


AGREEMENT_HTML = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{BASE_STYLE}</style></head><body><div class="page">
<div class="top"><div><div class="logo">{{{{logo}}}}</div><div class="eyebrow">{{{{nama_perusahaan}}}}</div><h1 class="title">PERJANJIAN KERJA SAMA</h1></div><div class="meta">Mulai: <strong>{{{{tanggal_mulai}}}}</strong><br>Selesai: <strong>{{{{tanggal_akhir}}}}</strong></div></div>
<p>Perjanjian kerja sama ini dibuat dan disepakati oleh pihak-pihak berikut:</p>
<div class="grid-2">
  <div class="card"><div class="card-title">Pihak Pertama - Penyedia Jasa</div><div class="strong">{{{{nama_perusahaan}}}}</div><div class="muted">{{{{alamat_perusahaan}}}}<br>{{{{phone_perusahaan}}}}<br>{{{{email_perusahaan}}}}</div></div>
  <div class="card"><div class="card-title">Pihak Kedua - Klien</div><div class="strong">{{{{klien}}}}</div><div class="muted">{{{{alamat}}}}<br>{{{{phone}}}}</div></div>
</div>
<div class="grid-2">
  <div class="card"><div class="card-title">Layanan</div><div class="strong">{{{{layanan}}}}</div></div>
  <div class="card"><div class="card-title">Nilai dan Durasi</div><div class="strong">{{{{nilai_kontrak}}}}</div><div class="muted">{{{{durasi}}}}</div></div>
</div>
<div class="section"><div class="section-title">Lingkup Pekerjaan</div><div class="text-box">{{{{scope}}}}</div></div>
<div class="section"><div class="section-title">Syarat dan Ketentuan</div><div class="text-box">{{{{terms}}}}</div></div>
<div class="signatures">
  <div class="sig"><div>Pihak Pertama,</div><div class="sig-space"></div><div class="sig-line">{{{{nama_perusahaan}}}}</div><div class="sig-role">Penyedia Jasa</div></div>
  <div class="sig"><div>Pihak Kedua,</div><div class="sig-space"></div><div class="sig-line">{{{{klien}}}}</div><div class="sig-role">Klien</div></div>
</div>
<div class="footer"><div><strong>{{{{nama_perusahaan}}}}</strong><br>{{{{tagline}}}}</div><div>Perjanjian kerja sama layanan.</div></div>
</div></body></html>"""


DEFAULT_DOCUMENT_TEMPLATES = [
    {
        "name": "Invoice",
        "type": "invoice",
        "html_template": INVOICE_HTML,
        "variables": [
            "logo", "nomor_invoice", "tanggal", "due_date", "klien", "alamat", "phone",
            "items_rows", "payment_info", "terms", "catatan", "nama_perusahaan",
            "alamat_perusahaan", "phone_perusahaan", "email_perusahaan", "tagline",
        ],
    },
    {
        "name": "Receipt / Bukti Pembayaran",
        "type": "receipt",
        "html_template": RECEIPT_HTML,
        "variables": ["logo", "nomor", "tanggal", "klien", "layanan", "payment_method", "amount", "keterangan", "nama_perusahaan", "tagline"],
    },
    {
        "name": "Proposal Penawaran PDF",
        "type": "proposal_pdf",
        "html_template": PROPOSAL_HTML,
        "variables": [
            "logo", "tanggal", "valid_until", "klien", "alamat", "phone", "layanan",
            "scope", "items_rows", "nama_perusahaan", "alamat_perusahaan",
            "phone_perusahaan", "email_perusahaan", "tagline",
        ],
    },
    {
        "name": "Surat Penawaran Formal",
        "type": "surat_penawaran",
        "html_template": QUOTATION_HTML,
        "variables": [
            "logo", "nomor", "tanggal", "klien", "alamat", "phone", "perihal",
            "items_rows", "terms", "nama_perusahaan", "alamat_perusahaan",
            "phone_perusahaan", "email_perusahaan",
        ],
    },
    {
        "name": "Kontrak / MoU",
        "type": "kontrak",
        "html_template": AGREEMENT_HTML,
        "variables": [
            "logo", "tanggal_mulai", "tanggal_akhir", "klien", "alamat", "phone",
            "layanan", "durasi", "nilai_kontrak", "scope", "terms", "nama_perusahaan",
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
