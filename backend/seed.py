"""
Seeder: Membersihkan dan mengisi ulang tabel categories & products
berdasarkan katalog layanan terbaru.

Jalankan: python seed.py
"""
import sqlite3
import os
import uuid
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "leads.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ============================================================================
# CLEAN existing data
# ============================================================================
cur.execute("DELETE FROM products")
cur.execute("DELETE FROM categories")
print("Cleaned: products & categories tables")

# ============================================================================
# CATEGORIES
# ============================================================================
categories = {
    "web_dev": {
        "id": str(uuid.uuid4()),
        "name": "Web Development",
        "description": "Jasa pembuatan website responsif, cepat, dan dioptimalkan untuk meningkatkan konversi penjualan.",
    },
    "seo": {
        "id": str(uuid.uuid4()),
        "name": "SEO & Google Maps",
        "description": "Optimasi keberadaan bisnis online agar mudah ditemukan calon pelanggan melalui Google dan Google Maps.",
    },
    "socmed": {
        "id": str(uuid.uuid4()),
        "name": "Kelola Sosial Media",
        "description": "Tingkatkan engagement audiens dan bangun brand awareness yang konsisten di berbagai platform media sosial.",
    },
    "maintenance": {
        "id": str(uuid.uuid4()),
        "name": "Maintenance Website",
        "description": "Jaga website tetap aman, selalu di-backup, dan berkinerja optimal.",
    },
    "logo": {
        "id": str(uuid.uuid4()),
        "name": "Desain Logo & Identitas Visual",
        "description": "Desain logo profesional yang merepresentasikan nilai dan visi bisnis, siap untuk cetak maupun digital.",
    },
}

for key, cat in categories.items():
    cur.execute(
        "INSERT INTO categories (id, name, description, is_active) VALUES (?, ?, ?, 1)",
        (cat["id"], cat["name"], cat["description"]),
    )
print(f"Seeded: {len(categories)} categories")

# ============================================================================
# PRODUCTS
# ============================================================================
products = [
    # --- Web Development - Skema Tahunan ---
    {
        "name": "Landing Page (Tahunan)",
        "description": "1 Halaman (Sales Focus). Domain & Hosting termasuk tahun ke-1.",
        "base_price": 1000000,
        "features": json.dumps([
            "1 Halaman (Sales Focus)",
            "Domain & Hosting Termasuk (Tahun ke-1)",
            "WhatsApp Chat",
            "SSL",
            "Mobile Friendly",
        ]),
        "category_id": categories["web_dev"]["id"],
        "is_retainer": False,
    },
    {
        "name": "Standard Biz (Tahunan)",
        "description": "Max. 5 Halaman. Domain & Hosting termasuk tahun ke-1.",
        "base_price": 2250000,
        "features": json.dumps([
            "Max. 5 Halaman",
            "Domain & Hosting Termasuk (Tahun ke-1)",
            "Maps Embed",
            "SEO Dasar",
            "Google Analytics",
        ]),
        "category_id": categories["web_dev"]["id"],
        "is_retainer": False,
    },
    {
        "name": "Premium Biz (Tahunan)",
        "description": "Max. 10 Halaman. Domain & Hosting termasuk tahun ke-1.",
        "base_price": 3750000,
        "features": json.dumps([
            "Max. 10 Halaman",
            "Domain & Hosting Termasuk (Tahun ke-1)",
            "Setup Mail",
            "Blog System",
            "Speed Optimization",
        ]),
        "category_id": categories["web_dev"]["id"],
        "is_retainer": False,
    },
    # --- Web Development - Skema Bulanan ---
    {
        "name": "Landing Page (Bulanan)",
        "description": "1 Halaman (Sales Focus). Pembayaran bulanan.",
        "base_price": 120000,
        "features": json.dumps([
            "1 Halaman (Sales Focus)",
            "Domain & Hosting Termasuk (Tahun ke-1)",
            "WhatsApp Chat",
            "SSL",
            "Mobile Friendly",
        ]),
        "category_id": categories["web_dev"]["id"],
        "is_retainer": True,
    },
    {
        "name": "Standard Biz (Bulanan)",
        "description": "Max. 5 Halaman. Pembayaran bulanan.",
        "base_price": 250000,
        "features": json.dumps([
            "Max. 5 Halaman",
            "Domain & Hosting Termasuk (Tahun ke-1)",
            "Maps Embed",
            "SEO Dasar",
            "Google Analytics",
        ]),
        "category_id": categories["web_dev"]["id"],
        "is_retainer": True,
    },
    {
        "name": "Premium Biz (Bulanan)",
        "description": "Max. 10 Halaman. Pembayaran bulanan.",
        "base_price": 375000,
        "features": json.dumps([
            "Max. 10 Halaman",
            "Domain & Hosting Termasuk (Tahun ke-1)",
            "Setup Titan Mail",
            "Blog System",
            "Speed Optimization",
        ]),
        "category_id": categories["web_dev"]["id"],
        "is_retainer": True,
    },
    # --- SEO & Google Maps ---
    {
        "name": "SEO Starter",
        "description": "Paket SEO dasar untuk bisnis lokal yang baru mulai optimasi online.",
        "base_price": 1000000,
        "features": json.dumps([
            "Setup & Update Foto GBP",
            "2 Artikel Lokal / Bulan",
            "On-Page Dasar",
            "Laporan Performa Ringkas",
        ]),
        "category_id": categories["seo"]["id"],
        "is_retainer": True,
    },
    {
        "name": "SEO Growth",
        "description": "Paket SEO menengah dengan audit mendalam dan strategi keyword.",
        "base_price": 2500000,
        "features": json.dumps([
            "Full Management GBP (Google Business Profile)",
            "6-8 Artikel Strategis / Bulan",
            "Audit Semrush & Keyword Gap",
            "Laporan Detail Trafik & Ranking",
        ]),
        "category_id": categories["seo"]["id"],
        "is_retainer": True,
    },
    {
        "name": "SEO Dominator",
        "description": "Paket SEO premium untuk mendominasi pencarian lokal dan nasional.",
        "base_price": 4500000,
        "features": json.dumps([
            "Full Management GBP + Review Reply",
            "10-12 Artikel Otoritas / Bulan",
            "Competitor Gap & CRO (Conversion Rate Optimization)",
            "Full Insight & Strategi",
        ]),
        "category_id": categories["seo"]["id"],
        "is_retainer": True,
    },
    # --- Kelola Sosial Media ---
    {
        "name": "Active Basic",
        "description": "Paket sosial media dasar dengan 9 konten per bulan.",
        "base_price": 500000,
        "features": json.dumps([
            "9 Konten (3x Seminggu)",
            "Branded Template",
            "Caption & Hashtag Dasar",
        ]),
        "category_id": categories["socmed"]["id"],
        "is_retainer": True,
    },
    {
        "name": "Active Grow",
        "description": "Paket sosial media menengah dengan konten harian dan video reels.",
        "base_price": 1200000,
        "features": json.dumps([
            "15 Konten (Hampir Setiap Hari)",
            "2 Video Reels Sederhana",
            "Content Plan & Strategy",
            "Caption Persuasif (Copywriting)",
        ]),
        "category_id": categories["socmed"]["id"],
        "is_retainer": True,
    },
    {
        "name": "Active Leader",
        "description": "Paket sosial media premium dengan konten setiap hari dan video reels berkelas.",
        "base_price": 2000000,
        "features": json.dumps([
            "24 Konten (Setiap Hari)",
            "4 Video Reels Berkelas",
            "Full Branding Guidelines",
            "Daily Story Template",
        ]),
        "category_id": categories["socmed"]["id"],
        "is_retainer": True,
    },
    # --- Maintenance Website ---
    {
        "name": "Basic Guard",
        "description": "Maintenance dasar: backup mingguan dan keamanan website.",
        "base_price": 350000,
        "features": json.dumps([
            "Backup Mingguan (Weekly)",
            "Retensi Data: Hapus otomatis > 1 bulan",
            "Update WordPress & Malware Scan",
        ]),
        "category_id": categories["maintenance"]["id"],
        "is_retainer": True,
    },
    {
        "name": "Business Partner",
        "description": "Maintenance menengah dengan dukungan email dan update konten.",
        "base_price": 750000,
        "features": json.dumps([
            "Backup Mingguan (Weekly)",
            "Retensi Data: Hapus otomatis > 1 bulan",
            "Setup & Troubleshoot Titan Mail",
            "Update Informasi Bisnis Dasar",
            "Malware Scan + Manajemen Google Maps",
        ]),
        "category_id": categories["maintenance"]["id"],
        "is_retainer": True,
    },
    {
        "name": "Priority Ops",
        "description": "Maintenance premium dengan priority response dan security hardening.",
        "base_price": 1500000,
        "features": json.dumps([
            "Backup Mingguan (Weekly)",
            "Retensi Data: Hapus otomatis > 1 bulan",
            "Full Support & Priority Response",
            "Ganti Teks/Gambar (Maks. 3x)",
            "Malware Scan + Security Hardening",
        ]),
        "category_id": categories["maintenance"]["id"],
        "is_retainer": True,
    },
    # --- Desain Logo & Identitas Visual ---
    {
        "name": "Logo Starter",
        "description": "Desain logo cepat dengan 2 opsi konsep, selesai maks. 24 jam.",
        "base_price": 250000,
        "features": json.dumps([
            "2 Opsi Desain",
            "Format: JPEG & PNG (Transparan)",
            "Pengerjaan Maks. 24 Jam",
        ]),
        "category_id": categories["logo"]["id"],
        "is_retainer": False,
    },
    {
        "name": "Logo Business",
        "description": "Desain logo profesional dengan file vektor dan 3D mockup.",
        "base_price": 450000,
        "features": json.dumps([
            "3 Opsi Desain",
            "Format: Bitmap + File Vektor (Master File)",
            "3D Mockup Presentation",
            "Pengerjaan Maks. 24 Jam",
        ]),
        "category_id": categories["logo"]["id"],
        "is_retainer": False,
    },
    {
        "name": "Logo Corporate",
        "description": "Paket identitas visual lengkap: logo, kartu nama, kop surat, stempel.",
        "base_price": 1500000,
        "features": json.dumps([
            "4 Opsi Desain",
            "Format: Full Vector & Identity Assets",
            "Kartu Nama, Kop Surat, Stempel",
            "Pengerjaan Maks. 3 Hari",
        ]),
        "category_id": categories["logo"]["id"],
        "is_retainer": False,
    },
]

for p in products:
    cur.execute(
        """INSERT INTO products (id, name, description, base_price, features, category_id, is_active, is_retainer, category, monthly_ads_cost, roi_months, roi_multiplier, comparison_points)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, NULL, 0, 0, 0, NULL)""",
        (
            str(uuid.uuid4()),
            p["name"],
            p["description"],
            p["base_price"],
            p["features"],
            p["category_id"],
            p.get("is_retainer", False),
        ),
    )

print(f"Seeded: {len(products)} products")

conn.commit()

# ============================================================================
# DYNAMIC TEMPLATES (WA_BLAST & FOLLOW_UP per category)
# ============================================================================
cur.execute("DELETE FROM dynamic_templates")

templates = [
    # --- Web Development ---
    {
        "name": "WA Blast - Web Development (Audit)",
        "type": "WA_BLAST",
        "category_id": categories["web_dev"]["id"],
        "content": "Halo {{business_name}}, saya baru saja cek website bisnis Anda dan menemukan beberapa hal yang bisa diperbaiki agar lebih banyak pelanggan datang dari Google.\n\nSaya sudah buatkan laporan gratisnya di sini:\n{{proposal_link}}\n\nLaporan ini hanya berlaku 24 jam. Boleh saya jelaskan lebih detail?",
    },
    {
        "name": "WA Blast - Web Development (No Website)",
        "type": "WA_BLAST",
        "category_id": categories["web_dev"]["id"],
        "content": "Halo {{business_name}}, saya perhatikan bisnis Anda belum punya website. Di era digital ini, 80% calon pelanggan mencari bisnis lewat Google sebelum membeli.\n\nKami punya solusi website profesional mulai dari Rp 120rb/bulan:\n{{proposal_link}}\n\nMau saya jelaskan lebih lanjut?",
    },
    {
        "name": "Follow Up - Web Development",
        "type": "FOLLOW_UP",
        "category_id": categories["web_dev"]["id"],
        "content": "Halo {{business_name}}, ini follow up dari penawaran website kemarin. Apakah sudah sempat lihat proposalnya?\n\nKalau ada pertanyaan soal fitur atau harga, saya siap bantu jelaskan. Slot bulan ini tinggal beberapa lagi.",
    },
    # --- SEO & Google Maps ---
    {
        "name": "WA Blast - SEO (Audit)",
        "type": "WA_BLAST",
        "category_id": categories["seo"]["id"],
        "content": "Halo {{business_name}}, saya baru cek posisi bisnis Anda di Google Maps dan hasilnya cukup mengkhawatirkan — kompetitor Anda sudah lebih dulu tampil di halaman pertama.\n\nSaya buatkan laporan lengkapnya di sini:\n{{proposal_link}}\n\n⚠️ Laporan berlaku 24 jam. Mau saya jelaskan strateginya?",
    },
    {
        "name": "WA Blast - SEO (Visibility)",
        "type": "WA_BLAST",
        "category_id": categories["seo"]["id"],
        "content": "Halo {{business_name}}, tahukah Anda bahwa 46% pencarian di Google bersifat lokal? Artinya calon pelanggan di sekitar Anda sedang mencari layanan seperti yang Anda tawarkan.\n\nSaya sudah analisa peluangnya:\n{{proposal_link}}\n\nBoleh saya jelaskan bagaimana bisnis Anda bisa tampil di posisi teratas?",
    },
    {
        "name": "Follow Up - SEO",
        "type": "FOLLOW_UP",
        "category_id": categories["seo"]["id"],
        "content": "Halo {{business_name}}, ini follow up terkait optimasi Google Maps dan SEO yang saya tawarkan kemarin.\n\nSudah sempat cek laporannya? Kompetitor di area Anda terus bertambah, jadi semakin cepat dioptimasi semakin baik hasilnya.",
    },
    # --- Kelola Sosial Media ---
    {
        "name": "WA Blast - Sosmed (Engagement)",
        "type": "WA_BLAST",
        "category_id": categories["socmed"]["id"],
        "content": "Halo {{business_name}}, saya lihat akun media sosial bisnis Anda punya potensi besar tapi belum dikelola secara konsisten.\n\nKami bisa bantu kelola konten profesional mulai 9 post/bulan:\n{{proposal_link}}\n\nMau saya jelaskan paketnya?",
    },
    {
        "name": "WA Blast - Sosmed (Brand)",
        "type": "WA_BLAST",
        "category_id": categories["socmed"]["id"],
        "content": "Halo {{business_name}}, di era sekarang, bisnis yang aktif di sosial media mendapat 3x lebih banyak kepercayaan dari calon pelanggan.\n\nKami punya paket kelola sosmed lengkap dengan desain & strategi konten:\n{{proposal_link}}\n\nBoleh saya jelaskan lebih detail?",
    },
    {
        "name": "Follow Up - Sosial Media",
        "type": "FOLLOW_UP",
        "category_id": categories["socmed"]["id"],
        "content": "Halo {{business_name}}, follow up dari penawaran kelola sosial media kemarin. Sudah sempat lihat contoh konten dan paketnya?\n\nKalau mau lihat portofolio hasil kerja kami, saya bisa kirimkan. Tinggal kabari saja ya.",
    },
    # --- Maintenance Website ---
    {
        "name": "WA Blast - Maintenance (Security)",
        "type": "WA_BLAST",
        "category_id": categories["maintenance"]["id"],
        "content": "Halo {{business_name}}, website yang tidak di-maintenance rutin rentan terkena malware dan bisa membuat pelanggan kehilangan kepercayaan.\n\nKami punya layanan maintenance mulai Rp 350rb/bulan:\n{{proposal_link}}\n\nMau saya jelaskan apa saja yang termasuk?",
    },
    {
        "name": "Follow Up - Maintenance",
        "type": "FOLLOW_UP",
        "category_id": categories["maintenance"]["id"],
        "content": "Halo {{business_name}}, follow up soal layanan maintenance website. Apakah saat ini website Anda sudah rutin di-backup dan di-scan malware?\n\nKalau belum, ini bisa jadi risiko besar. Saya bisa bantu jelaskan solusinya.",
    },
    # --- Desain Logo ---
    {
        "name": "WA Blast - Logo (Branding)",
        "type": "WA_BLAST",
        "category_id": categories["logo"]["id"],
        "content": "Halo {{business_name}}, logo adalah kesan pertama bisnis Anda di mata pelanggan. Logo yang profesional bisa meningkatkan kepercayaan hingga 75%.\n\nKami bisa buatkan logo berkualitas mulai Rp 250rb, selesai dalam 24 jam:\n{{proposal_link}}\n\nMau lihat contoh desainnya?",
    },
    {
        "name": "Follow Up - Logo",
        "type": "FOLLOW_UP",
        "category_id": categories["logo"]["id"],
        "content": "Halo {{business_name}}, follow up dari penawaran desain logo kemarin. Apakah sudah ada gambaran konsep yang diinginkan?\n\nKalau mau diskusi soal warna, style, atau referensi, saya siap bantu kapan saja.",
    },
]

for t in templates:
    cur.execute(
        "INSERT INTO dynamic_templates (id, name, type, content, is_active, category_id) VALUES (?, ?, ?, ?, 1, ?)",
        (str(uuid.uuid4()), t["name"], t["type"], t["content"], t["category_id"]),
    )

print(f"Seeded: {len(templates)} dynamic templates")

conn.commit()
conn.close()
print("\nSeeder selesai!")
