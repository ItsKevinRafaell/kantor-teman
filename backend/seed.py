"""
Seeder: Membersihkan dan mengisi ulang tabel categories, products, dan templates.
Works with both SQLite (local) and PostgreSQL (production).

Jalankan: python seed.py
"""
import os
import uuid
import json
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from main import (
    engine, SessionLocal, Base,
    Category, Product, DynamicTemplate,
)

Base.metadata.create_all(engine)
db = SessionLocal()

# ============================================================================
# CLEAN existing data
# ============================================================================
db.query(Product).delete()
db.query(Category).delete()
db.query(DynamicTemplate).filter(DynamicTemplate.type.in_(["WA_BLAST", "FOLLOW_UP"])).delete()
db.commit()
print("Cleaned: products, categories, templates")

# ============================================================================
# CATEGORIES
# ============================================================================
categories = {
    "web_dev": Category(id=str(uuid.uuid4()), name="Web Development", description="Jasa pembuatan website responsif, cepat, dan dioptimalkan untuk meningkatkan konversi penjualan.", is_active=True),
    "seo": Category(id=str(uuid.uuid4()), name="SEO & Google Maps", description="Optimasi keberadaan bisnis online agar mudah ditemukan calon pelanggan melalui Google dan Google Maps.", is_active=True),
    "socmed": Category(id=str(uuid.uuid4()), name="Kelola Sosial Media", description="Tingkatkan engagement audiens dan bangun brand awareness yang konsisten di berbagai platform media sosial.", is_active=True),
    "maintenance": Category(id=str(uuid.uuid4()), name="Maintenance Website", description="Jaga website tetap aman, selalu di-backup, dan berkinerja optimal.", is_active=True),
    "logo": Category(id=str(uuid.uuid4()), name="Desain Logo & Identitas Visual", description="Desain logo profesional yang merepresentasikan nilai dan visi bisnis, siap untuk cetak maupun digital.", is_active=True),
}

for cat in categories.values():
    db.add(cat)
db.commit()
print(f"Seeded: {len(categories)} categories")

# ============================================================================
# PRODUCTS
# ============================================================================
products_data = [
    ("Landing Page (Tahunan)", "1 Halaman (Sales Focus). Domain & Hosting termasuk tahun ke-1.", 1000000, ["1 Halaman (Sales Focus)", "Domain & Hosting Termasuk (Tahun ke-1)", "WhatsApp Chat", "SSL", "Mobile Friendly"], "web_dev", False),
    ("Standard Biz (Tahunan)", "Max. 5 Halaman. Domain & Hosting termasuk tahun ke-1.", 2250000, ["Max. 5 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Maps Embed", "SEO Dasar", "Google Analytics"], "web_dev", False),
    ("Premium Biz (Tahunan)", "Max. 10 Halaman. Domain & Hosting termasuk tahun ke-1.", 3750000, ["Max. 10 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Setup Mail", "Blog System", "Speed Optimization"], "web_dev", False),
    ("Landing Page (Bulanan)", "1 Halaman (Sales Focus). Pembayaran bulanan.", 120000, ["1 Halaman (Sales Focus)", "Domain & Hosting Termasuk (Tahun ke-1)", "WhatsApp Chat", "SSL", "Mobile Friendly"], "web_dev", True),
    ("Standard Biz (Bulanan)", "Max. 5 Halaman. Pembayaran bulanan.", 250000, ["Max. 5 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Maps Embed", "SEO Dasar", "Google Analytics"], "web_dev", True),
    ("Premium Biz (Bulanan)", "Max. 10 Halaman. Pembayaran bulanan.", 375000, ["Max. 10 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Setup Titan Mail", "Blog System", "Speed Optimization"], "web_dev", True),
    ("SEO Starter", "Paket SEO dasar untuk bisnis lokal yang baru mulai optimasi online.", 1000000, ["Setup & Update Foto GBP", "2 Artikel Lokal / Bulan", "On-Page Dasar", "Laporan Performa Ringkas"], "seo", True),
    ("SEO Growth", "Paket SEO menengah dengan audit mendalam dan strategi keyword.", 2500000, ["Full Management GBP (Google Business Profile)", "6-8 Artikel Strategis / Bulan", "Audit Semrush & Keyword Gap", "Laporan Detail Trafik & Ranking"], "seo", True),
    ("SEO Dominator", "Paket SEO premium untuk mendominasi pencarian lokal dan nasional.", 4500000, ["Full Management GBP + Review Reply", "10-12 Artikel Otoritas / Bulan", "Competitor Gap & CRO (Conversion Rate Optimization)", "Full Insight & Strategi"], "seo", True),
    ("Active Basic", "Paket sosial media dasar dengan 9 konten per bulan.", 500000, ["9 Konten (3x Seminggu)", "Branded Template", "Caption & Hashtag Dasar"], "socmed", True),
    ("Active Grow", "Paket sosial media menengah dengan konten harian dan video reels.", 1200000, ["15 Konten (Hampir Setiap Hari)", "2 Video Reels Sederhana", "Content Plan & Strategy", "Caption Persuasif (Copywriting)"], "socmed", True),
    ("Active Leader", "Paket sosial media premium dengan konten setiap hari dan video reels berkelas.", 2000000, ["24 Konten (Setiap Hari)", "4 Video Reels Berkelas", "Full Branding Guidelines", "Daily Story Template"], "socmed", True),
    ("Basic Guard", "Maintenance dasar: backup mingguan dan keamanan website.", 350000, ["Backup Mingguan (Weekly)", "Retensi Data: Hapus otomatis > 1 bulan", "Update WordPress & Malware Scan"], "maintenance", True),
    ("Business Partner", "Maintenance menengah dengan dukungan email dan update konten.", 750000, ["Backup Mingguan (Weekly)", "Retensi Data: Hapus otomatis > 1 bulan", "Setup & Troubleshoot Titan Mail", "Update Informasi Bisnis Dasar", "Malware Scan + Manajemen Google Maps"], "maintenance", True),
    ("Priority Ops", "Maintenance premium dengan priority response dan security hardening.", 1500000, ["Backup Mingguan (Weekly)", "Retensi Data: Hapus otomatis > 1 bulan", "Full Support & Priority Response", "Ganti Teks/Gambar (Maks. 3x)", "Malware Scan + Security Hardening"], "maintenance", True),
    ("Logo Starter", "Desain logo cepat dengan 2 opsi konsep, selesai maks. 24 jam.", 250000, ["2 Opsi Desain", "Format: JPEG & PNG (Transparan)", "Pengerjaan Maks. 24 Jam"], "logo", False),
    ("Logo Business", "Desain logo profesional dengan file vektor dan 3D mockup.", 450000, ["3 Opsi Desain", "Format: Bitmap + File Vektor (Master File)", "3D Mockup Presentation", "Pengerjaan Maks. 24 Jam"], "logo", False),
    ("Logo Corporate", "Paket identitas visual lengkap: logo, kartu nama, kop surat, stempel.", 1500000, ["4 Opsi Desain", "Format: Full Vector & Identity Assets", "Kartu Nama, Kop Surat, Stempel", "Pengerjaan Maks. 3 Hari"], "logo", False),
]

for name, desc, price, features, cat_key, is_retainer in products_data:
    db.add(Product(
        id=str(uuid.uuid4()),
        name=name,
        description=desc,
        base_price=price,
        features=json.dumps(features),
        category_id=categories[cat_key].id,
        is_active=True,
        is_retainer=is_retainer,
    ))
db.commit()
print(f"Seeded: {len(products_data)} products")

# ============================================================================
# DYNAMIC TEMPLATES (WA_BLAST & FOLLOW_UP per category)
# ============================================================================
templates_data = [
    ("WA Blast - Web Development (Audit)", "WA_BLAST", "web_dev", "Halo {{business_name}}, saya baru saja cek website bisnis Anda dan menemukan beberapa hal yang bisa diperbaiki agar lebih banyak pelanggan datang dari Google.\n\nSaya sudah buatkan laporan gratisnya di sini:\n{{proposal_link}}\n\nLaporan ini hanya berlaku 24 jam. Boleh saya jelaskan lebih detail?"),
    ("WA Blast - Web Development (No Website)", "WA_BLAST", "web_dev", "Halo {{business_name}}, saya perhatikan bisnis Anda belum punya website. Di era digital ini, 80% calon pelanggan mencari bisnis lewat Google sebelum membeli.\n\nKami punya solusi website profesional mulai dari Rp 120rb/bulan:\n{{proposal_link}}\n\nMau saya jelaskan lebih lanjut?"),
    ("Follow Up - Web Development", "FOLLOW_UP", "web_dev", "Halo {{business_name}}, ini follow up dari penawaran website kemarin. Apakah sudah sempat lihat proposalnya?\n\nKalau ada pertanyaan soal fitur atau harga, saya siap bantu jelaskan. Slot bulan ini tinggal beberapa lagi."),
    ("WA Blast - SEO (Audit)", "WA_BLAST", "seo", "Halo {{business_name}}, saya baru cek posisi bisnis Anda di Google Maps dan hasilnya cukup mengkhawatirkan — kompetitor Anda sudah lebih dulu tampil di halaman pertama.\n\nSaya buatkan laporan lengkapnya di sini:\n{{proposal_link}}\n\n⚠️ Laporan berlaku 24 jam. Mau saya jelaskan strateginya?"),
    ("WA Blast - SEO (Visibility)", "WA_BLAST", "seo", "Halo {{business_name}}, tahukah Anda bahwa 46% pencarian di Google bersifat lokal? Artinya calon pelanggan di sekitar Anda sedang mencari layanan seperti yang Anda tawarkan.\n\nSaya sudah analisa peluangnya:\n{{proposal_link}}\n\nBoleh saya jelaskan bagaimana bisnis Anda bisa tampil di posisi teratas?"),
    ("Follow Up - SEO", "FOLLOW_UP", "seo", "Halo {{business_name}}, ini follow up terkait optimasi Google Maps dan SEO yang saya tawarkan kemarin.\n\nSudah sempat cek laporannya? Kompetitor di area Anda terus bertambah, jadi semakin cepat dioptimasi semakin baik hasilnya."),
    ("WA Blast - Sosmed (Engagement)", "WA_BLAST", "socmed", "Halo {{business_name}}, saya lihat akun media sosial bisnis Anda punya potensi besar tapi belum dikelola secara konsisten.\n\nKami bisa bantu kelola konten profesional mulai 9 post/bulan:\n{{proposal_link}}\n\nMau saya jelaskan paketnya?"),
    ("WA Blast - Sosmed (Brand)", "WA_BLAST", "socmed", "Halo {{business_name}}, di era sekarang, bisnis yang aktif di sosial media mendapat 3x lebih banyak kepercayaan dari calon pelanggan.\n\nKami punya paket kelola sosmed lengkap dengan desain & strategi konten:\n{{proposal_link}}\n\nBoleh saya jelaskan lebih detail?"),
    ("Follow Up - Sosial Media", "FOLLOW_UP", "socmed", "Halo {{business_name}}, follow up dari penawaran kelola sosial media kemarin. Sudah sempat lihat contoh konten dan paketnya?\n\nKalau mau lihat portofolio hasil kerja kami, saya bisa kirimkan. Tinggal kabari saja ya."),
    ("WA Blast - Maintenance (Security)", "WA_BLAST", "maintenance", "Halo {{business_name}}, website yang tidak di-maintenance rutin rentan terkena malware dan bisa membuat pelanggan kehilangan kepercayaan.\n\nKami punya layanan maintenance mulai Rp 350rb/bulan:\n{{proposal_link}}\n\nMau saya jelaskan apa saja yang termasuk?"),
    ("Follow Up - Maintenance", "FOLLOW_UP", "maintenance", "Halo {{business_name}}, follow up soal layanan maintenance website. Apakah saat ini website Anda sudah rutin di-backup dan di-scan malware?\n\nKalau belum, ini bisa jadi risiko besar. Saya bisa bantu jelaskan solusinya."),
    ("WA Blast - Logo (Branding)", "WA_BLAST", "logo", "Halo {{business_name}}, logo adalah kesan pertama bisnis Anda di mata pelanggan. Logo yang profesional bisa meningkatkan kepercayaan hingga 75%.\n\nKami bisa buatkan logo berkualitas mulai Rp 250rb, selesai dalam 24 jam:\n{{proposal_link}}\n\nMau lihat contoh desainnya?"),
    ("Follow Up - Logo", "FOLLOW_UP", "logo", "Halo {{business_name}}, follow up dari penawaran desain logo kemarin. Apakah sudah ada gambaran konsep yang diinginkan?\n\nKalau mau diskusi soal warna, style, atau referensi, saya siap bantu kapan saja."),
]

for name, ttype, cat_key, content in templates_data:
    db.add(DynamicTemplate(
        id=str(uuid.uuid4()),
        name=name,
        type=ttype,
        content=content,
        is_active=True,
        category_id=categories[cat_key].id,
    ))
db.commit()
print(f"Seeded: {len(templates_data)} dynamic templates")

db.close()
print("\nSeeder selesai!")
