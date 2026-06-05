// Starter templates for document generation
// These are data constants, not React components

export const STARTER_VARIABLES: Record<string, string> = {
  invoice: "logo, nomor_invoice, tanggal, due_date, klien, alamat, phone, items_rows, payment_info, terms, catatan, nama_perusahaan, alamat_perusahaan, phone_perusahaan, email_perusahaan, tagline",
  receipt: "logo, nomor, tanggal, klien, layanan, payment_method, amount, keterangan, nama_perusahaan, tagline",
  proposal_pdf: "logo, tanggal, valid_until, klien, alamat, phone, layanan, items_rows, scope, nama_perusahaan, alamat_perusahaan, phone_perusahaan, email_perusahaan, tagline",
  surat_penawaran: "logo, nomor, tanggal, klien, alamat, phone, pertaining, items_rows, terms, nama_perusahaan, alamat_perusahaan, phone_perusahaan, email_perusahaan",
  kontrak: "logo, tanggal_mulai, tanggal_akhir, klien, alamat, phone, layanan, durasi, nilai_kontrak, scope, terms, nama_perusahaan, alamat_perusahaan, phone_perusahaan, email_perusahaan, tagline",
  custom: "",
};

export const STARTER_TEMPLATES: Record<string, string> = {
  invoice: `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,600;0,700;1,400&display=swap');
@page{size:A4;margin:0}
*{font-family:'Noto Sans',Arial,sans-serif;box-sizing:border-box;margin:0;padding:0}
body{color:#1e293b;font-size:11px;line-height:1.6;background:#fff}
.page{padding:40px 48px;min-height:297mm}
.top-bar{background:#1e293b;color:#fff;padding:28px 48px 24px;margin:-40px -48px 32px}
.top-bar .brand{font-size:10px;letter-spacing:2px;text-transform:uppercase;opacity:.6;margin-bottom:4px}
.top-bar .doc-title{font-size:28px;font-weight:700;letter-spacing:-0.5px}
.top-bar .doc-meta{font-size:10px;opacity:.7;margin-top:6px}
.accent{color:#f59e0b}
.parties{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:28px}
.party-box{padding:16px;border:1px solid #e2e8f0;border-radius:8px}
.party-box .party-label{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#94a3b8;margin-bottom:8px}
.party-box .party-name{font-size:13px;font-weight:700;color:#0f172a;margin-bottom:4px}
.party-box .party-detail{font-size:10px;color:#64748b;line-height:1.7}
.section-label{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#94a3b8;margin-bottom:10px}
.items-wrap{margin-bottom:24px}
table{width:100%;border-collapse:collapse;font-size:10.5px}
thead tr{background:#f8fafc;border-bottom:2px solid #e2e8f0}
thead th{padding:10px 12px;text-align:left;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#64748b}
thead th:last-child,thead th:nth-last-child(2),thead th:nth-last-child(3){text-align:right}
tbody tr{border-bottom:1px solid #f1f5f9}
tbody tr:last-child{border-bottom:none}
tbody td{padding:10px 12px;color:#334155}
tbody td:last-child,tbody td:nth-last-child(2),tbody td:nth-last-child(3){text-align:right}
tfoot tr{background:#fef9ee;border-top:2px solid #f59e0b}
tfoot td{padding:12px;font-weight:700;color:#92400e}
tfoot td:last-child{text-align:right;font-size:14px}
.terms-box{background:#f8fafc;border-left:3px solid #f59e0b;padding:12px 16px;border-radius:0 6px 6px 0;font-size:10px;color:#475569;line-height:1.7;margin-bottom:24px}
.footer{border-top:1px solid #e2e8f0;padding-top:16px;display:flex;justify-content:space-between;align-items:center}
.footer .brand-name{font-size:11px;font-weight:700;color:#1e293b}
.footer .tagline{font-size:9px;color:#94a3b8}
</style></head><body><div class="page">
<div class="top-bar">
  <div class="brand">{{nama_perusahaan}}</div>
  <div class="doc-title">INVOICE <span class="accent">{{nomor_invoice}}</span></div>
  <div class="doc-meta">Tanggal: {{tanggal}} &nbsp;·&nbsp; Jatuh Tempo: {{due_date}}</div>
</div>
<div class="parties">
  <div class="party-box">
    <div class="party-label">Dari</div>
    <div class="party-name">{{nama_perusahaan}}</div>
    <div class="party-detail">{{alamat_perusahaan}}<br/>{{phone_perusahaan}}<br/>{{email_perusahaan}}</div>
  </div>
  <div class="party-box">
    <div class="party-label">Kepada</div>
    <div class="party-name">{{klien}}</div>
    <div class="party-detail">{{alamat}}<br/>{{phone}}</div>
  </div>
</div>
<div class="items-wrap">
  <div class="section-label">Rincian Layanan</div>
  {{items_rows}}
</div>
<div class="terms-box"><strong>Syarat &amp; Ketentuan:</strong><br/>{{terms}}</div>
<div class="footer">
  <div><div class="brand-name">{{nama_perusahaan}}</div><div class="tagline">{{tagline}}</div></div>
  <div style="text-align:right;font-size:10px;color:#94a3b8">Dokumen ini dibuat secara digital</div>
</div>
</div></body></html>`,

  proposal_pdf: `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,600;0,700;1,400&display=swap');
@page{size:A4;margin:0}
*{font-family:'Noto Sans',Arial,sans-serif;box-sizing:border-box;margin:0;padding:0}
body{color:#1e293b;font-size:11px;line-height:1.6;background:#fff}
.page{padding:40px 48px;min-height:297mm}
.header{margin-bottom:32px;padding-bottom:24px;border-bottom:1px solid #e2e8f0}
.header-top{display:flex;justify-content:space-between;align-items:flex-start}
.doc-title{font-size:26px;font-weight:700;color:#0f172a;letter-spacing:-0.5px;margin-top:8px}
.doc-subtitle{font-size:10px;color:#64748b;margin-top:4px}
.validity-badge{background:#fef3c7;border:1px solid #fcd34d;border-radius:20px;padding:6px 14px;font-size:10px;font-weight:600;color:#92400e;white-space:nowrap}
.parties{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:28px}
.party-box{padding:16px;border:1px solid #e2e8f0;border-radius:8px}
.party-box .party-label{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#94a3b8;margin-bottom:8px}
.party-box .party-name{font-size:13px;font-weight:700;color:#0f172a;margin-bottom:4px}
.party-box .party-detail{font-size:10px;color:#64748b;line-height:1.7}
.section{margin-bottom:24px}
.section-title{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#94a3b8;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid #f1f5f9}
table{width:100%;border-collapse:collapse;font-size:10.5px}
thead tr{background:#f8fafc;border-bottom:2px solid #e2e8f0}
thead th{padding:10px 12px;text-align:left;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#64748b}
thead th:last-child,thead th:nth-last-child(2),thead th:nth-last-child(3){text-align:right}
tbody tr{border-bottom:1px solid #f1f5f9}
tbody td{padding:10px 12px;color:#334155}
tbody td:last-child,tbody td:nth-last-child(2),tbody td:nth-last-child(3){text-align:right}
tfoot tr{background:#fef9ee;border-top:2px solid #f59e0b}
tfoot td{padding:12px;font-weight:700;color:#92400e}
tfoot td:last-child{text-align:right;font-size:14px}
.scope-box{background:#f8fafc;padding:14px 16px;border-radius:8px;font-size:11px;color:#475569;white-space:pre-line;line-height:1.8}
.validity-note{background:#fef9ee;border:1px solid #fcd34d;border-radius:8px;padding:12px 16px;font-size:10px;color:#92400e;margin-top:20px}
.footer{border-top:1px solid #e2e8f0;padding-top:16px;margin-top:24px;display:flex;justify-content:space-between;align-items:center}
.footer .brand-name{font-size:11px;font-weight:700;color:#1e293b}
.footer .tagline{font-size:9px;color:#94a3b8}
</style></head><body><div class="page">
<div class="header">
  <div class="header-top">
    <div>{{logo}}<div class="doc-title">PROPOSAL PENAWARAN</div><div class="doc-subtitle">{{tanggal}} &nbsp;·&nbsp; Layanan: {{layanan}}</div></div>
    <div class="validity-badge">Berlaku s/d {{valid_until}}</div>
  </div>
</div>
<div class="parties">
  <div class="party-box">
    <div class="party-label">Dari</div>
    <div class="party-name">{{nama_perusahaan}}</div>
    <div class="party-detail">{{alamat_perusahaan}}<br/>{{phone_perusahaan}}<br/>{{email_perusahaan}}</div>
  </div>
  <div class="party-box">
    <div class="party-label">Kepada</div>
    <div class="party-name">{{klien}}</div>
    <div class="party-detail">{{alamat}}<br/>{{phone}}</div>
  </div>
</div>
<div class="section">
  <div class="section-title">Layanan yang Ditawarkan</div>
  {{items_rows}}
</div>
<div class="section">
  <div class="section-title">Lingkup Pekerjaan</div>
  <div class="scope-box">{{scope}}</div>
</div>
<div class="validity-note">Proposal ini berlaku hingga <strong>{{valid_until}}</strong>. Setelah tanggal tersebut, harga dan ketersediaan dapat berubah tanpa pemberitahuan.</div>
<div class="footer">
  <div><div class="brand-name">{{nama_perusahaan}}</div><div class="tagline">{{tagline}}</div></div>
  <div style="text-align:right;font-size:10px;color:#94a3b8">Dokumen ini dibuat secara digital</div>
</div>
</div></body></html>`,

  receipt: `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page{size:A4;margin:0}*{font-family:'Noto Sans',Arial,sans-serif;box-sizing:border-box}
body{margin:0;color:#1e293b;font-size:11px}.page{padding:48px}.title{font-size:24px;font-weight:700}
.receipt{margin:30px auto;max-width:500px;border:1px solid #e2e8f0;border-top:4px solid #d97706;border-radius:10px;padding:24px}
.row{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid #f1f5f9}.amount{text-align:center;font-size:26px;font-weight:700;color:#d97706;margin:20px}
</style></head><body><div class="page"><div>{{logo}}</div><h1 class="title">BUKTI PEMBAYARAN</h1>
<div class="receipt"><div class="row"><span>No.</span><strong>{{nomor}}</strong></div><div class="row"><span>Klien</span><strong>{{klien}}</strong></div><div class="row"><span>Layanan</span><strong>{{layanan}}</strong></div><div class="row"><span>Metode</span><strong>{{payment_method}}</strong></div><div class="amount">{{amount}}</div><p>{{keterangan}}</p></div>
</div></body></html>`,

  surat_penawaran: `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,600;0,700;1,400&display=swap');
@page{size:A4;margin:0}
*{font-family:'Noto Sans',Arial,sans-serif;box-sizing:border-box;margin:0;padding:0}
body{color:#1e293b;font-size:11px;line-height:1.6;background:#fff}
.page{padding:48px}
.kop{display:flex;justify-content:space-between;align-items:flex-start;padding-bottom:20px;border-bottom:2px solid #1e293b;margin-bottom:24px}
.kop-left .company-name{font-size:16px;font-weight:700;color:#0f172a}
.kop-left .company-detail{font-size:9.5px;color:#64748b;margin-top:4px;line-height:1.7}
.kop-right{text-align:right;font-size:9.5px;color:#64748b;line-height:1.7}
.nomor-box{background:#f8fafc;border-radius:6px;padding:10px 14px;font-size:10px;color:#475569;margin-bottom:20px;display:inline-block}
.nomor-box strong{color:#0f172a}
.recipient{margin:20px 0;padding:14px 16px;border:1px solid #e2e8f0;border-radius:8px;font-size:11px}
.recipient .to-label{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#94a3b8;margin-bottom:8px}
.recipient .to-name{font-weight:700;font-size:13px;color:#0f172a;margin-bottom:4px}
.recipient .to-detail{color:#64748b;font-size:10px;line-height:1.7}
.perihal{font-size:12px;font-weight:700;color:#0f172a;margin:20px 0 8px}
.body-text{font-size:11px;color:#475569;margin-bottom:20px}
.section-label{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#94a3b8;margin-bottom:10px}
table{width:100%;border-collapse:collapse;font-size:10.5px}
thead tr{background:#f8fafc;border-bottom:2px solid #e2e8f0}
thead th{padding:10px 12px;text-align:left;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#64748b}
thead th:last-child,thead th:nth-last-child(2),thead th:nth-last-child(3){text-align:right}
tbody tr{border-bottom:1px solid #f1f5f9}
tbody td{padding:10px 12px;color:#334155}
tbody td:last-child,tbody td:nth-last-child(2),tbody td:nth-last-child(3){text-align:right}
tfoot tr{background:#fef9ee;border-top:2px solid #f59e0b}
tfoot td{padding:12px;font-weight:700;color:#92400e}
tfoot td:last-child{text-align:right;font-size:14px}
.terms-box{background:#f8fafc;border-left:3px solid #cbd5e1;padding:12px 16px;border-radius:0 6px 6px 0;font-size:10px;color:#475569;line-height:1.7;margin:20px 0}
.signature-area{margin-top:48px;display:flex;justify-content:flex-end}
.sig-block{text-align:center;min-width:180px}
.sig-block .sig-label{font-size:10px;color:#64748b;margin-bottom:60px}
.sig-block .sig-line{border-top:1px solid #1e293b;padding-top:6px;font-size:11px;font-weight:700;color:#0f172a}
.sig-block .sig-role{font-size:9px;color:#94a3b8;margin-top:2px}
</style></head><body><div class="page">
<div class="kop">
  <div class="kop-left">{{logo}}<div class="company-name">{{nama_perusahaan}}</div>
    <div class="company-detail">{{alamat_perusahaan}}<br/>{{phone_perusahaan}} &nbsp;·&nbsp; {{email_perusahaan}}</div>
  </div>
  <div class="kop-right"><div class="nomor-box">No: <strong>{{nomor}}</strong><br/>Tanggal: {{tanggal}}</div></div>
</div>
<div class="recipient"><div class="to-label">Kepada Yth.</div><div class="to-name">{{klien}}</div><div class="to-detail">{{alamat}}<br/>{{phone}}</div></div>
<div class="perihal">Perihal: {{perihal}}</div>
<div class="body-text">Dengan hormat, bersama surat ini kami mengajukan penawaran jasa kepada Bapak/Ibu sebagai berikut:</div>
<div class="section-label">Rincian Penawaran</div>
{{items_rows}}
<div class="terms-box"><strong>Syarat &amp; Ketentuan:</strong><br/>{{terms}}</div>
<div class="body-text">Demikian surat penawaran ini kami sampaikan. Atas perhatian dan kepercayaan Bapak/Ibu, kami ucapkan terima kasih.</div>
<div class="signature-area"><div class="sig-block"><div class="sig-label">Hormat kami,</div><div class="sig-line">{{nama_perusahaan}}</div><div class="sig-role">Pihak Penyedia Jasa</div></div></div>
</div></body></html>`,

  kontrak: `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,400;0,600;0,700;1,400&display=swap');
@page{size:A4;margin:0}
*{font-family:'Noto Sans',Arial,sans-serif;box-sizing:border-box;margin:0;padding:0}
body{color:#1e293b;font-size:11px;line-height:1.6;background:#fff}
.page{padding:48px}
.header{text-align:center;padding-bottom:24px;border-bottom:2px solid #1e293b;margin-bottom:28px}
.header .logo-wrap{margin-bottom:12px}
.header h1{font-size:18px;font-weight:700;letter-spacing:3px;color:#0f172a;margin-bottom:4px}
.header .subtitle{font-size:10px;color:#64748b;letter-spacing:1px}
.intro{font-size:11px;color:#475569;margin-bottom:20px;line-height:1.8}
.parties{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}
.party-box{padding:14px 16px;border:1px solid #e2e8f0;border-radius:8px}
.party-box .party-label{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#94a3b8;margin-bottom:8px}
.party-box .party-name{font-size:13px;font-weight:700;color:#0f172a;margin-bottom:4px}
.party-box .party-detail{font-size:10px;color:#64748b;line-height:1.7}
.summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:24px}
.summary-item{background:#f8fafc;border-radius:8px;padding:12px 14px;border:1px solid #e2e8f0}
.summary-item .s-label{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#94a3b8;margin-bottom:4px}
.summary-item .s-value{font-size:12px;font-weight:700;color:#0f172a}
.date-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:24px}
.date-item{background:#fef9ee;border-radius:8px;padding:12px 14px;border:1px solid #fcd34d}
.date-item .d-label{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#92400e;margin-bottom:4px}
.date-item .d-value{font-size:12px;font-weight:700;color:#78350f}
.section{margin-bottom:20px}
.section-title{font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#94a3b8;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid #f1f5f9}
.scope-box{background:#f8fafc;padding:14px 16px;border-radius:8px;font-size:11px;color:#475569;white-space:pre-line;line-height:1.8}
.terms-box{font-size:10.5px;color:#475569;white-space:pre-line;line-height:1.9;padding:14px 16px;background:#f8fafc;border-radius:8px}
.signatures{display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:56px}
.sig-block{text-align:center}
.sig-block .sig-label{font-size:10px;color:#64748b;margin-bottom:56px}
.sig-block .sig-line{border-top:1px solid #1e293b;padding-top:6px;font-size:11px;font-weight:700;color:#0f172a}
.sig-block .sig-role{font-size:9px;color:#94a3b8;margin-top:2px}
.footer{border-top:1px solid #e2e8f0;padding-top:14px;margin-top:28px;text-align:center;font-size:9px;color:#94a3b8}
</style></head><body><div class="page">
<div class="header"><div class="logo-wrap">{{logo}}</div><h1>PERJANJIAN KERJA SAMA</h1><div class="subtitle">Dibuat pada {{tanggal_mulai}}</div></div>
<div class="intro">Pada hari ini, <strong>{{tanggal_mulai}}</strong>, telah disepakati perjanjian kerja sama antara pihak-pihak berikut:</div>
<div class="parties">
  <div class="party-box"><div class="party-label">Pihak Pertama — Penyedia Jasa</div><div class="party-name">{{nama_perusahaan}}</div><div class="party-detail">{{alamat_perusahaan}}<br/>{{phone_perusahaan}}<br/>{{email_perusahaan}}</div></div>
  <div class="party-box"><div class="party-label">Pihak Kedua — Klien</div><div class="party-name">{{klien}}</div><div class="party-detail">{{alamat}}<br/>{{phone}}</div></div>
</div>
<div class="summary-grid">
  <div class="summary-item"><div class="s-label">Layanan</div><div class="s-value">{{layanan}}</div></div>
  <div class="summary-item"><div class="s-label">Durasi</div><div class="s-value">{{durasi}}</div></div>
  <div class="summary-item"><div class="s-label">Nilai Kontrak</div><div class="s-value">{{nilai_kontrak}}</div></div>
</div>
<div class="date-grid">
  <div class="date-item"><div class="d-label">Tanggal Mulai</div><div class="d-value">{{tanggal_mulai}}</div></div>
  <div class="date-item"><div class="d-label">Tanggal Selesai</div><div class="d-value">{{tanggal_akhir}}</div></div>
</div>
<div class="section"><div class="section-title">Lingkup Pekerjaan</div><div class="scope-box">{{scope}}</div></div>
<div class="section"><div class="section-title">Syarat &amp; Ketentuan</div><div class="terms-box">{{terms}}</div></div>
<div class="signatures">
  <div class="sig-block"><div class="sig-label">Pihak Pertama,</div><div class="sig-line">{{nama_perusahaan}}</div><div class="sig-role">Penyedia Jasa</div></div>
  <div class="sig-block"><div class="sig-label">Pihak Kedua,</div><div class="sig-line">{{klien}}</div><div class="sig-role">Klien</div></div>
</div>
<div class="footer">{{nama_perusahaan}} &nbsp;·&nbsp; {{tagline}}</div>
</div></body></html>`,

  custom: `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;600;700&display=swap');
@page{size:A4;margin:2cm}
*{font-family:'Noto Sans',Arial,sans-serif;box-sizing:border-box}
body{color:#1e293b;font-size:12px;line-height:1.6}
</style></head><body>
<p>Tulis konten dokumen di sini...</p>
</body></html>`,
};