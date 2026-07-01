"""
Seeder: Membersihkan dan mengisi ulang tabel categories, products, dan templates.
Works with both SQLite (local) and PostgreSQL (production).

Jalankan: python seed.py
"""
import os
import uuid
import json
import sys

# ============================================================================
# DATA (importable by main.py endpoint)
# ============================================================================
categories = {
    "web_dev": {"name": "Web Development", "description": "Jasa pembuatan website profesional untuk bisnis Anda. Website yang cepat, responsif, dan dioptimalkan untuk mesin pencari — menjadi pusat kredibilitas digital yang bekerja 24/7 mendatangkan pelanggan."},
    "web_dev_bulanan": {"name": "Web Development Bulanan", "description": "Paket website berlangganan bulanan tanpa biaya besar di awal. Domain & hosting termasuk, bisa upgrade atau berhenti kapan saja."},
    "seo": {"name": "SEO & Google Maps", "description": "Optimasi SEO lokal dan Google Business Profile agar bisnis Anda tampil di halaman pertama Google. 46% pencarian di Google bersifat lokal — pastikan pelanggan menemukan Anda, bukan kompetitor."},
    "socmed": {"name": "Kelola Sosial Media", "description": "Kelola media sosial bisnis Anda secara profesional. Konten konsisten, desain branded, caption persuasif — bangun brand awareness dan engagement yang menghasilkan konversi."},
    "maintenance": {"name": "Maintenance Website", "description": "Layanan perawatan website rutin: backup, security scan, update, dan monitoring. Website yang tidak di-maintenance rentan terkena malware dan kehilangan kepercayaan pelanggan."},
    "logo": {"name": "Desain Logo & Identitas Visual", "description": "Desain logo profesional yang merepresentasikan nilai dan visi bisnis Anda. Bayar sekali, file menjadi milik Anda selamanya. Termasuk berbagai format untuk cetak maupun digital."},
}

products_data = [
    # (name, description, price, features, category_key, is_retainer)
    # Web Development Tahunan
    ("Web Starter (Tahunan)", "Bayangkan pelanggan bisa cek bisnis Anda 24 jam, bahkan saat Anda tidur. Website 1 halaman ini bikin bisnis Anda terlihat serius dan dipercaya. Sudah termasuk domain dan hosting tahun pertama - tinggal pakai!", 1000000, ["Website 1 Halaman yang Fokus Menjual", "Domain & Hosting Gratis Tahun Pertama", "Tombol WhatsApp untuk Konversi Langsung", "Sertifikat SSL untuk Keamanan & Kepercayaan", "Tampilan Mobile yang Sempurna di Semua HP", "Siap Online dalam 5-7 Hari Kerja"], "web_dev", False),
    ("Web Pro (Tahunan)", "Bayangkan pelanggan gampang nemuin bisnis Anda di Google Maps dan langsung datang ke lokasi. Website 5 halaman lengkap dengan SEO dasar supaya muncul di pencarian Google, plus analytics untuk tracking pengunjung.", 2250000, ["5 Halaman Profesional yang Membangun Kredibilitas", "Domain & Hosting Gratis Tahun Pertama", "Google Maps Terintegrasi agar Mudah Ditemukan", "SEO Dasar agar Muncul di Halaman Pertama Google", "Google Analytics untuk Tracking Pengunjung", "Tombol WhatsApp untuk Konversi Langsung", "Sertifikat SSL untuk Keamanan", "Tampilan Mobile yang Sempurna", "Siap Online dalam 7-10 Hari Kerja"], "web_dev", False),
    ("Web Expert (Tahunan)", "Bayangkan bisnis Anda terlihat seperti perusahaan besar dengan website premium 10 halaman. Ada blog untuk konten marketing, email profesional, dan loading super cepat supaya pelanggan tidak kabur.", 3750000, ["10 Halaman Premium yang Menunjukkan Profesionalisme", "Domain & Hosting Gratis Tahun Pertama", "Blog/Artikel untuk Content Marketing", "Email Profesional (nama@bisnisanda.com)", "Loading Super Cepat agar Pelanggan Tidak Kabur", "Google Maps Terintegrasi", "SEO Lengkap + Analytics untuk Dominasi Pasar", "Tombol WhatsApp untuk Konversi", "Sertifikat SSL untuk Keamanan", "Tampilan Mobile yang Sempurna", "Siap Online dalam 10-14 Hari Kerja"], "web_dev", False),
    # Web Development Bulanan
    ("Web Starter (Bulanan)", "Bayangkan punya website profesional tanpa modal besar di awal. Bayar bulanan, sudah termasuk domain dan hosting. Cocok untuk yang baru mulai bisnis online dan mau test market dulu tanpa commitment besar.", 120000, ["Website 1 Halaman yang Fokus Menjual", "Domain & Hosting Gratis Tahun Pertama", "Tombol WhatsApp untuk Konversi Langsung", "Sertifikat SSL untuk Keamanan & Kepercayaan", "Tampilan Mobile yang Sempurna di Semua HP", "Bisa Berhenti Kapan Saja Tanpa Penalty", "Siap Online dalam 5-7 Hari Kerja"], "web_dev_bulanan", True),
    ("Web Pro (Bulanan)", "Bayangkan pelanggan gampang nemuin bisnis Anda di Google Maps. Website 5 halaman lengkap dengan pembayaran bulanan. Sudah termasuk Google Maps, SEO dasar, dan analytics. Solusi terbaik untuk yang mau tampil profesional di Google tanpa investasi besar di awal.", 250000, ["5 Halaman Profesional yang Membangun Kredibilitas", "Domain & Hosting Gratis Tahun Pertama", "Google Maps Terintegrasi agar Mudah Ditemukan", "SEO Dasar agar Muncul di Halaman Pertama Google", "Google Analytics untuk Tracking Pengunjung", "Tombol WhatsApp untuk Konversi Langsung", "Sertifikat SSL untuk Keamanan", "Tampilan Mobile yang Sempurna", "Bisa Berhenti Kapan Saja Tanpa Penalty", "Siap Online dalam 7-10 Hari Kerja"], "web_dev_bulanan", True),
    ("Web Expert (Bulanan)", "Bayangkan bisnis Anda terlihat seperti perusahaan besar dengan website premium, tapi bayar bulanan. Website 10 halaman dengan blog dan email profesional. Sudah termasuk loading cepat, SEO lengkap, dan analytics. Buat yang serius mau dominasi pasar digital tanpa memberatkan cashflow.", 375000, ["10 Halaman Premium yang Menunjukkan Profesionalisme", "Domain & Hosting Gratis Tahun Pertama", "Blog/Artikel untuk Content Marketing", "Email Profesional (nama@bisnisanda.com)", "Loading Super Cepat agar Pelanggan Tidak Kabur", "Google Maps Terintegrasi", "SEO Lengkap + Analytics untuk Dominasi Pasar", "Tombol WhatsApp untuk Konversi", "Sertifikat SSL untuk Keamanan", "Tampilan Mobile yang Sempurna", "Bisa Berhenti Kapan Saja Tanpa Penalty", "Siap Online dalam 10-14 Hari Kerja"], "web_dev_bulanan", True),
    # SEO & Google Maps
    ("SEO Starter", "Bayangkan bisnis Anda muncul di Google saat orang cari layanan di daerah Anda. Lebih banyak telepon masuk, lebih banyak pelanggan datang. Kami urus profil Google Business Profile Anda, bikin 2 artikel per bulan, dan kasih laporan performa bulanan.", 1000000, ["Setup & Optimasi Profil Google Business Profile", "2 Artikel SEO Lokal per Bulan agar Muncul di Google", "SEO On-Page untuk Ranking Lebih Baik", "Laporan Performa Bulanan yang Transparan", "Riset Keyword Lokal yang Tepat Target", "Tanpa Kontrak Jangka Panjang - Fleksibel"], "seo", True),
    ("SEO Pro", "Bayangkan bisnis Anda naik peringkat di Google dan kalahkan kompetitor lokal. Lebih banyak pengunjung website, lebih banyak pelanggan yang datang. Kami audit website Anda, riset keyword strategis, bikin 6-8 artikel per bulan, dan kasih laporan detail trafik & ranking.", 2500000, ["Full Management Google Business Profile", "6-8 Artikel Strategis per Bulan yang Mendominasi Google", "Audit Website Mendalam & Riset Keyword Kompetitor", "Laporan Detail Trafik & Ranking Bulanan", "SEO On-Page & Technical untuk Ranking Maksimal", "Monitoring Kompetitor agar Selalu di Depan", "Tanpa Kontrak Jangka Panjang - Fleksibel"], "seo", True),
    ("SEO Expert", "Bayangkan bisnis Anda selalu muncul pertama di Google saat orang cari layanan Anda. Lebih banyak telepon masuk, lebih banyak pelanggan datang, lebih banyak penjualan terjadi. Dengan 10-12 artikel berkualitas per bulan, profil Google yang selalu aktif, dan strategi yang terus dioptimasi, Anda akan meninggalkan kompetitor jauh di belakang. Ini investasi untuk dominasi pasar jangka panjang.", 4500000, ["Full Management Google Business Profile + Balas Ulasan", "10-12 Artikel Otoritas per Bulan yang Mendominasi Halaman Pertama", "Analisis Kompetitor & Optimasi Konversi untuk Penjualan Maksimal", "Full Monthly Strategy Insights & Konsultasi", "On-Page, Technical & Local SEO Lengkap", "Conversion Rate Optimization agar Pengunjung Jadi Pelanggan", "Priority Support untuk Kebutuhan Mendesak", "Tanpa Kontrak Jangka Panjang - Fleksibel"], "seo", True),
    # Social Media
    ("Sosmed Starter", "Bayangkan media sosial bisnis Anda aktif dan profesional. Followers bertambah, engagement naik, brand awareness meningkat. Kami bikin 9 konten feed per bulan dengan desain branded dan caption yang menarik.", 500000, ["9 Konten Feed per Bulan (3x Seminggu)", "Desain Branded yang Konsisten & Profesional", "Caption & Hashtag yang Dioptimasi untuk Engagement", "1 Platform (Instagram/Facebook) yang Tepat Target", "Penjadwalan Otomatis untuk Konsistensi", "Laporan Bulanan untuk Tracking Performa"], "socmed", True),
    ("Sosmed Pro", "Bayangkan followers Anda jadi pelanggan. Lebih banyak DM masuk, lebih banyak order, lebih banyak penjualan. Kami bikin 15 konten feed per bulan, 2 video reels, content plan strategis, dan copywriting persuasif.", 1200000, ["15 Konten Feed per Bulan (Hampir Setiap Hari)", "2 Video Reels Editing Sederhana untuk Engagement Lebih Tinggi", "Content Plan & Strategy Bulanan yang Terukur", "Caption Persuasif (Copywriting) yang Mengkonversi", "2 Platform (Instagram + Facebook) untuk Jangkauan Luas", "Hashtag Research & Scheduling Otomatis", "Laporan Performa Mingguan untuk Optimasi"], "socmed", True),
    ("Sosmed Expert", "Bayangkan Anda dominasi media sosial. Brand Anda jadi yang paling diingat, paling dicari, paling dipercaya. Kami bikin 24 konten feed per bulan, 4 video reels premium, branding guidelines lengkap, dan daily story.", 2000000, ["24 Konten Feed per Bulan (Setiap Hari) untuk Dominasi Feed", "4 Video Reels Premium Editing untuk Engagement Maksimal", "Full Branding Guidelines untuk Konsistensi Brand", "Daily Story Template & Design untuk Kehadiran Harian", "3 Platform (Instagram, Facebook, TikTok) untuk Jangkauan Maksimal", "Advanced Content Strategy untuk Pertumbuhan Eksponensial", "Competitor Analysis untuk Selalu di Depan", "Priority Support untuk Kebutuhan Mendesak"], "socmed", True),
    # Maintenance
    ("Maintenance Starter", "Bayangkan website Anda selalu aman dan jalan lancar. Tidak ada downtime, tidak ada malware, tidak ada masalah teknis. Anda fokus bisnis, kami yang urus teknis. Backup mingguan, scan malware bulanan, dan update otomatis.", 350000, ["Backup Mingguan untuk Keamanan Data", "Data Retention: 1 Bulan untuk Recovery", "WordPress Core & Plugin Updates Otomatis", "Malware Scan Bulanan untuk Keamanan", "Security Monitoring 24/7", "Laporan Bulanan untuk Transparansi"], "maintenance", True),
    ("Maintenance Pro", "Bayangkan website Anda selalu fresh, aman, dan optimal. Loading cepat, konten selalu update, email profesional aktif. Anda tidak perlu pusing urus teknis. Backup mingguan, scan malware, update konten bisnis, setup email profesional, dan manajemen Google Maps.", 750000, ["Backup Mingguan untuk Keamanan Data", "Data Retention: 1 Bulan untuk Recovery", "Setup & Troubleshoot Titan Mail untuk Email Profesional", "Update Konten Bisnis (Teks/Gambar) sesuai Kebutuhan", "Malware Scan + Removal untuk Keamanan Maksimal", "Google Maps Management untuk Visibilitas Lokal", "Performance Monitoring untuk Kecepatan Website", "Priority Email Support untuk Kebutuhan Mendesak", "Laporan Mingguan untuk Tracking Performa"], "maintenance", True),
    ("Maintenance Expert", "Bayangkan website Anda selalu optimal dengan dukungan prioritas dan keamanan maksimal. Tidak ada downtime, loading super cepat, keamanan terjamin. Anda fokus bisnis, kami yang urus semuanya. Backup harian, scan malware + recovery, optimasi performa, dan monitoring 24/7. Termasuk custom development sampai 5 jam/bulan.", 1500000, ["Backup Harian untuk Keamanan Data Maksimal", "Data Retention: 3 Bulan untuk Recovery Lengkap", "Full Priority Support (Response < 4 Jam) untuk Kebutuhan Mendesak", "Custom Development (5 Jam/Bulan) untuk Perubahan Besar", "Security Hardening & Monitoring untuk Keamanan Enterprise", "Malware Scan + Removal + Recovery untuk Proteksi Total", "Performance Optimization untuk Kecepatan Maksimal", "Uptime Monitoring 24/7 untuk Ketersediaan Website", "Laporan Mingguan Detail untuk Tracking Performa"], "maintenance", True),
    # Logo & Branding
    ("Logo Starter", "Bayangkan bisnis Anda punya logo profesional yang bikin pelanggan percaya. Logo yang siap dalam 24 jam dengan 2 opsi desain dan revisi minor sampai 2x. Cepat, profesional, dan ekonomis.", 250000, ["2 Opsi Desain Logo untuk Pilihan Terbaik", "Format File: JPEG & PNG (Transparent) untuk Fleksibilitas", "Pengerjaan Maks. 24 Jam untuk Kebutuhan Cepat", "2x Revisi Minor untuk Penyempurnaan", "File Siap Pakai untuk Semua Kebutuhan Digital"], "logo", False),
    ("Logo Pro", "Bayangkan bisnis Anda punya logo berkualitas tinggi yang bikin Anda terlihat profesional di semua media. Logo dengan file vektor master dan 3D mockup. 3 opsi desain dengan revisi sampai 3x.", 450000, ["3 Opsi Desain Logo untuk Pilihan Lebih Banyak", "Format File: Bitmap + Vector (Master File) untuk Kualitas Maksimal", "3D Mockup Presentation untuk Visualisasi Profesional", "Pengerjaan Maks. 24 Jam untuk Kebutuhan Cepat", "3x Revisi untuk Penyempurnaan Sempurna", "File Siap Pakai untuk Cetak & Digital"], "logo", False),
    ("Logo Expert", "Bayangkan bisnis Anda punya brand identity lengkap yang bikin Anda terlihat profesional dan konsisten di semua media. Logo dengan 4 opsi desain, unlimited revisi, plus kartu nama, kop surat, dan stempel. Investasi sekali untuk brand yang kuat.", 1500000, ["4 Opsi Desain Logo untuk Pilihan Komprehensif", "Full Vector & Identity Assets untuk Kualitas Premium", "Kartu Nama Design untuk Profesionalisme", "Kop Surat & Amplop Design untuk Konsistensi Brand", "Stempel Design untuk Legalitas", "Pengerjaan Maks. 3 Hari untuk Kebutuhan Cepat", "Unlimited Revisi untuk Kesempurnaan", "Brand Guidelines Document untuk Konsistensi", "File Siap Pakai untuk Semua Media"], "logo", False),
]

wallets_data = [
    {"name": "Rekening Utama", "balance": 0, "icon": "bank", "color": "#3B82F6"},
    {"name": "Dana Darurat", "balance": 0, "icon": "shield", "color": "#10B981"},
]

# (business_name, phone_number, owner_name, product_interest)
clients_data = [
    (
        "PT Mitra Lindung Sarana",
        "+62 812-5529-025",
        "Pak Agung",
        "SEO & Google Maps",
    ),
    (
        "PT Momen Harmoni Kreatif",
        "+62 811-559-025",
        "Bu Ayuana",
        "Maintenance Website",
    ),
]

# (client_phone, name, type, status, nominal, start_date, end_date, color)
projects_data = [
    ("+62 812-5529-025", "Pembuatan Website MLS", "FIXED", "COMPLETED", 2500000, "2025-01-01", "2025-12-31", "blue"),
    ("+62 812-5529-025", "Kontrak SEO MLS (6 Bulan)", "RETAINER", "COMPLETED", 2500000, "2025-02-01", "2025-07-31", "green"),
    ("+62 812-5529-025", "Kontrak SEO MLS (1 Tahun)", "RETAINER", "ACTIVE", 2500000, "2026-02-01", "2027-01-01", "yellow"),
    ("+62 811-559-025", "Logo & Company Profile MHK", "FIXED", "COMPLETED", 1000000, "2025-01-01", "2025-12-31", "purple"),
    ("+62 811-559-025", "Pembuatan Website MHK", "FIXED", "COMPLETED", 2500000, "2025-01-01", "2025-12-31", "blue"),
    ("+62 811-559-025", "Maintenance Website MHK", "RETAINER", "ACTIVE", 500000, "2025-08-01", "2026-08-01", "yellow"),
]

# (date, type, amount, category, notes)
transactions_data = [
    ("2026-04-05", "expense", 101499,  "Tools & Langganan",    "Groupy"),
    ("2026-04-05", "income",  500000,  "Setoran Modal",         ""),
    ("2026-04-08", "expense", 299000,  "Tools & Langganan",    "RatuAI"),
    ("2026-04-08", "expense", 285000,  "Operasional",           ""),
    ("2026-04-08", "income",  2000000, "Setoran Modal",         ""),
    ("2026-04-25", "expense", 168206,  "Tools & Langganan",    "Add: 3 Mail Titan Pro"),
    ("2026-05-04", "income",  699998,  "Pembayaran Maintenance","Momenara payment maintenance + 3 mail titan"),
    ("2026-05-05", "expense", 106382,  "Infrastruktur",         "Stand laptop Coobowe8"),
    ("2026-05-06", "income",  2500000, "Retainer SEO",          ""),
    ("2026-05-08", "expense", 272100,  "Infrastruktur",         "Keyboard Robot KL150"),
    ("2026-05-17", "expense", 20450,   "Operasional",           ""),
    ("2026-05-20", "expense", 200000,  "Hosting & Domain",      "DEVELOPER HOSTING ANYMHOST - 1 TAHUN"),
    ("2026-05-20", "expense", 60000,   "Tools & Langganan",    "API 9router"),
    ("2026-05-20", "expense", 75000,   "Tools & Langganan",    "1 Bulan API Key SEMUTSSH"),
    ("2026-05-23", "expense", 20000,   "Tools & Langganan",    "API 9router"),
    ("2026-05-23", "expense", 60000,   "Hosting & Domain",      "upgrade hosting teman umkm kita ke paket hosting newbie"),
    ("2026-05-23", "expense", 21000,   "Tools & Langganan",    "Telegram"),
]

templates_data = [
    ("WA Blast - Web Development (Audit)", "WA_BLAST", "web_dev", "Halo {{business_name}}, saya baru saja cek website bisnis Anda dan menemukan beberapa hal yang bisa diperbaiki agar lebih banyak pelanggan datang dari Google.\n\nSaya sudah buatkan laporan gratisnya di sini:\n{{proposal_link}}\n\nLaporan ini hanya berlaku 24 jam. Boleh saya jelaskan lebih detail?"),
    ("WA Blast - Web Development (No Website)", "WA_BLAST", "web_dev", "Halo {{business_name}}, saya perhatikan bisnis Anda belum punya website. Di era digital ini, 80% calon pelanggan mencari bisnis lewat Google sebelum membeli.\n\nKami punya solusi website profesional mulai dari Rp 120rb/bulan:\n{{proposal_link}}\n\nMau saya jelaskan lebih lanjut?"),
    ("Follow Up - Web Development", "FOLLOW_UP", "web_dev", "Halo {{business_name}}, ini follow up dari penawaran website kemarin. Apakah sudah sempat lihat proposalnya?\n\nKalau ada pertanyaan soal fitur atau harga, saya siap bantu jelaskan. Slot bulan ini tinggal beberapa lagi."),
    ("WA Blast - SEO (Audit)", "WA_BLAST", "seo", "Halo {{business_name}}, saya baru cek posisi bisnis Anda di Google Maps dan hasilnya cukup mengkhawatirkan — kompetitor Anda sudah lebih dulu tampil di halaman pertama.\n\nSaya buatkan laporan lengkapnya di sini:\n{{proposal_link}}\n\nLaporan berlaku 24 jam. Mau saya jelaskan strateginya?"),
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

# ============================================================================
# MAIN EXECUTION (only when run directly)
# ============================================================================
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))
    from dotenv import load_dotenv
    load_dotenv()

    from main import (
        engine, SessionLocal, Base,
        Category, Product, DynamicTemplate, Wallet, Lead, Project, Transaction,
        DocumentTemplate, BrandKit,
    )

    Base.metadata.create_all(engine)
    db = SessionLocal()

    # Delete in FK order: child tables first
    db.query(DynamicTemplate).filter(DynamicTemplate.type.in_(["WA_BLAST", "FOLLOW_UP"])).delete(synchronize_session=False)
    db.query(Product).delete(synchronize_session=False)
    db.query(Category).delete(synchronize_session=False)
    db.commit()
    print("Cleaned: templates, products, categories")

    cat_objects = {}
    for key, cat in categories.items():
        c = Category(id=str(uuid.uuid4()), name=cat["name"], description=cat["description"], is_active=True)
        db.add(c)
        cat_objects[key] = c
    db.commit()
    print(f"Seeded: {len(categories)} categories")

    for name, desc, price, features, cat_key, is_retainer in products_data:
        db.add(Product(
            id=str(uuid.uuid4()), name=name, description=desc, base_price=price,
            features=json.dumps(features), category_id=cat_objects[cat_key].id,
            is_active=True, is_retainer=is_retainer,
        ))
    db.commit()
    print(f"Seeded: {len(products_data)} products")

    for name, ttype, cat_key, content in templates_data:
        db.add(DynamicTemplate(
            id=str(uuid.uuid4()), name=name, type=ttype, content=content,
            is_active=True, category_id=cat_objects[cat_key].id,
        ))
    db.commit()
    print(f"Seeded: {len(templates_data)} dynamic templates")

    existing_wallet_names = {w.name for w in db.query(Wallet).all()}
    wallets_added = 0
    for w in wallets_data:
        if w["name"] not in existing_wallet_names:
            db.add(Wallet(name=w["name"], balance=w["balance"], icon=w.get("icon"), color=w.get("color")))
            wallets_added += 1
    db.commit()
    print(f"Seeded: {wallets_added} wallets (skipped {len(wallets_data) - wallets_added} existing)")

    existing_phones = {l.phone_number for l in db.query(Lead).all()}
    client_map = {}
    clients_added = 0
    for business_name, phone, owner_name, product_interest in clients_data:
        if phone not in existing_phones:
            lead = Lead(
                business_name=business_name,
                phone_number=phone,
                status="Closed/Client",
                product_interest=product_interest,
                batch_name=f"PIC: {owner_name}",
            )
            db.add(lead)
            db.flush()
            client_map[phone] = lead.id
            clients_added += 1
        else:
            existing = db.query(Lead).filter(Lead.phone_number == phone).first()
            client_map[phone] = existing.id
    db.commit()
    print(f"Seeded: {clients_added} clients (skipped {len(clients_data) - clients_added} existing)")

    existing_projects = {(p.lead_id, p.name) for p in db.query(Project).all()}
    projects_added = 0
    for phone, name, ptype, status, nominal, start_date, end_date, color in projects_data:
        lead_id = client_map.get(phone)
        if lead_id and (lead_id, name) not in existing_projects:
            db.add(Project(
                id=str(uuid.uuid4()),
                lead_id=lead_id,
                name=name,
                type=ptype,
                status=status,
                nominal=nominal,
                start_date=start_date,
                end_date=end_date,
                color=color,
            ))
            projects_added += 1
    db.commit()
    print(f"Seeded: {projects_added} projects (skipped {len(projects_data) - projects_added} existing)")

    rekening = db.query(Wallet).filter(Wallet.name == "Rekening Utama").first()
    if rekening:
        existing_tx = {(t.date, t.amount, t.notes) for t in db.query(Transaction).filter(Transaction.wallet_id == rekening.id).all()}
        tx_added = 0
        for date, ttype, amount, category, notes in transactions_data:
            if (date, float(amount), notes) not in existing_tx:
                db.add(Transaction(
                    wallet_id=rekening.id,
                    type=ttype,
                    amount=float(amount),
                    category=category,
                    date=date,
                    notes=notes or None,
                ))
                tx_added += 1
        db.commit()
        print(f"Seeded: {tx_added} transactions (skipped {len(transactions_data) - tx_added} existing)")
    else:
        print("WARNING: Wallet 'Rekening Utama' not found, skipping transactions")

    # Seed DocumentTemplates from document_template_library
    from document_template_library import get_document_template_starters
    starters = get_document_template_starters()
    for doc_type, data in starters.items():
        existing = db.query(DocumentTemplate).filter(DocumentTemplate.type == doc_type).first()
        if existing:
            # Update with full template
            existing.name = data["name"]
            existing.html_template = data["html_template"]
            existing.variables = json.dumps(data["variables"])
        else:
            db.add(DocumentTemplate(
                id=str(uuid.uuid4()),
                name=data["name"],
                type=doc_type,
                html_template=data["html_template"],
                variables=json.dumps(data["variables"]),
                is_active=True,
            ))
    db.commit()
    print(f"Seeded/Updated: {len(starters)} document templates")

    # Seed default BrandKit if not exists
    existing_kits = db.query(BrandKit).filter(BrandKit.is_active == True).count()
    if existing_kits == 0:
        db.add(BrandKit(
            id=str(uuid.uuid4()),
            kit_name="Kantor Teman",
            brand_name="Kantor Teman",
            tagline="Partner Digital Bisnis Anda",
            phone="",
            email="",
            address="",
            logo="",
            is_active=True,
        ))
        db.commit()
        print("Seeded: 1 BrandKit")
    else:
        print(f"Skipped: BrandKit already exists ({existing_kits})")

    db.close()
    print("\nSeeder selesai!")
