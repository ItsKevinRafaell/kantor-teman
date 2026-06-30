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
    ("Web Starter (Tahunan)", "Bayangkan pelanggan bisa cek bisnis Anda 24 jam, bahkan saat Anda tidur. Website 1 halaman ini bikin bisnis Anda terlihat profesional dan mudah dihubungi. Sudah termasuk domain dan hosting tahun pertama - tinggal pakai!", 1000000, ["1 Halaman (Sales Focus)", "Domain & Hosting Termasuk (Tahun ke-1)", "WhatsApp Chat Button", "SSL Certificate (HTTPS)", "Mobile Responsive Design", "Pengerjaan 5-7 Hari Kerja"], "web_dev", False),
    ("Web Pro (Tahunan)", "Bikin pelanggan gampang nemuin bisnis Anda di Google! Website 5 halaman dengan Google Maps, SEO dasar, dan analytics. Bayangkan berapa banyak pelanggan baru yang bisa datang cuma karena mereka bisa find Anda di Google.", 2250000, ["Hingga 5 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Google Maps Embed", "SEO Dasar (Meta Tags, Heading, Sitemap)", "Google Analytics Setup", "WhatsApp Chat Button", "SSL Certificate (HTTPS)", "Mobile Responsive Design", "Pengerjaan 7-10 Hari Kerja"], "web_dev", False),
    ("Web Expert (Tahunan)", "Website lengkap yang bikin bisnis Anda terlihat seperti perusahaan besar! 10 halaman dengan blog untuk konten marketing, email profesional, dan loading super cepat. Ini investasi yang bakal bikin pelanggan percaya dan pilih Anda dibanding kompetitor.", 3750000, ["Hingga 10 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Blog/Article System", "Professional Email (Titan Mail)", "Speed Optimization", "Google Maps Embed", "SEO Lengkap + Analytics", "WhatsApp Chat Button", "SSL Certificate (HTTPS)", "Mobile Responsive Design", "Pengerjaan 10-14 Hari Kerja"], "web_dev", False),
    # Web Development Bulanan
    ("Web Starter (Bulanan)", "Mau punya website tapi belum punya budget besar? Mulai dari Rp 120rb/bulan aja! Sudah termasuk domain dan hosting. Cocok buat yang baru mulai bisnis online dan mau test market dulu.", 120000, ["1 Halaman (Sales Focus)", "Domain & Hosting Termasuk (Tahun ke-1)", "WhatsApp Chat Button", "SSL Certificate (HTTPS)", "Mobile Responsive Design", "Bisa Berhenti Kapan Saja", "Pengerjaan 5-7 Hari Kerja"], "web_dev_bulanan", True),
    ("Web Pro (Bulanan)", "Website profesional dengan pembayaran bulanan yang ramah di kantong. Sudah termasuk Google Maps biar pelanggan gampang nemuin lokasi Anda, SEO dasar biar muncul di Google, dan analytics buat tracking pengunjung.", 250000, ["Hingga 5 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Google Maps Embed", "SEO Dasar (Meta Tags, Heading, Sitemap)", "Google Analytics Setup", "WhatsApp Chat Button", "SSL Certificate (HTTPS)", "Mobile Responsive Design", "Bisa Berhenti Kapan Saja", "Pengerjaan 7-10 Hari Kerja"], "web_dev_bulanan", True),
    ("Web Expert (Bulanan)", "Website premium dengan semua fitur canggih, bayar bulanan tanpa memberatkan cashflow. Ada blog system buat konten marketing, email profesional buat komunikasi bisnis, dan loading super cepat biar pelanggan gak kabur.", 375000, ["Hingga 10 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Blog/Article System", "Professional Email (Titan Mail)", "Speed Optimization", "Google Maps Embed", "SEO Lengkap + Analytics", "WhatsApp Chat Button", "SSL Certificate (HTTPS)", "Mobile Responsive Design", "Bisa Berhenti Kapan Saja", "Pengerjaan 10-14 Hari Kerja"], "web_dev_bulanan", True),
    # SEO & Google Maps
    ("SEO Starter", "Mau bisnis Anda muncul di Google saat orang cari layanan di daerah Anda? Paket ini fokus bikin Google Business Profile Anda optimal dan bikin konten lokal. Dengan 2 artikel per bulan, bisnis Anda mulai terlihat di pencarian Google. Investasi kecil buat pertumbuhan besar!", 1000000, ["Setup & Update Foto Google Business Profile", "2 Artikel Lokal SEO / Bulan", "On-Page SEO Dasar", "Laporan Performa Bulanan", "Riset Keyword Lokal", "Tanpa Kontrak Jangka Panjang"], "seo", True),
    ("SEO Pro", "Bikin bisnis Anda naik peringkat di Google dan kalahkan kompetitor lokal! Paket ini termasuk audit mendalam pakai Semrush, strategi keyword yang terukur, dan 6-8 artikel strategis per bulan. Ada laporan detail trafik & ranking biar Anda bisa lihat ROI jelas.", 2500000, ["Full Management Google Business Profile", "6-8 Artikel Strategis / Bulan", "Audit Semrush & Keyword Gap Analysis", "Laporan Detail Trafik & Ranking", "On-Page & Technical SEO", "Competitor Monitoring", "Tanpa Kontrak Jangka Panjang"], "seo", True),
    ("SEO Expert", "Jadilah nomor 1 di Google untuk industri Anda! Paket premium ini bikin Anda dominasi pencarian lokal dan nasional dengan 10-12 artikel otoritas per bulan, analisis kompetitor, optimasi konversi, dan strategi bulanan lengkap. Bahkan ada review reply buat bangun reputasi bisnis. Ini buat yang serius mau jadi market leader!", 4500000, ["Full Management Google Business Profile + Review Reply", "10-12 Artikel Otoritas / Bulan", "Competitor Gap Analysis & CRO Optimization", "Full Monthly Strategy Insights", "On-Page, Technical & Local SEO", "Conversion Rate Optimization", "Priority Support", "Tanpa Kontrak Jangka Panjang"], "seo", True),
    # Social Media
    ("Sosmed Starter", "Bikin media sosial bisnis Anda aktif dan profesional! 9 konten branded per bulan dengan caption dan hashtag yang dioptimasi buat engagement. Cocok buat yang baru mulai bangun presence digital tanpa repot. Investasi kecil buat brand awareness yang besar.", 500000, ["9 Konten Feed (3x Seminggu)", "Branded Template Design", "Caption & Hashtag Optimized", "1 Platform (Instagram/Facebook)", "Content Scheduling", "Laporan Bulanan"], "socmed", True),
    ("Sosmed Pro", "Sosmed aktif setiap hari dengan konten yang bikin followers jadi pelanggan! 15 konten feed per bulan, 2 video reels, content plan strategis, dan copywriting persuasif. Ada laporan performa mingguan biar Anda bisa lihat pertumbuhan jelas.", 1200000, ["15 Konten Feed (Hampir Setiap Hari)", "2 Video Reels Editing Sederhana", "Content Plan & Strategy Bulanan", "Caption Persuasif (Copywriting)", "2 Platform (Instagram + Facebook)", "Hashtag Research & Scheduling", "Laporan Performa Mingguan"], "socmed", True),
    ("Sosmed Expert", "Dominasi media sosial dengan konten harian berkualitas tinggi! 24 konten feed per bulan, 4 video reels premium, full branding guidelines, dan daily story template. Hadir di 3 platform (Instagram, Facebook, TikTok) dengan strategi konten advanced dan analisis kompetitor. Paket lengkap buat yang mau jadi brand terdepan di media sosial.", 2000000, ["24 Konten Feed (Setiap Hari)", "4 Video Reels Premium Editing", "Full Branding Guidelines", "Daily Story Template & Design", "3 Platform (Instagram, Facebook, TikTok)", "Advanced Content Strategy", "Competitor Analysis", "Priority Support"], "socmed", True),
    # Maintenance
    ("Maintenance Starter", "Bikin website Anda tetap aman dan jalan lancar! Backup mingguan, malware scan bulanan, dan update WordPress otomatis. Cocok buat website statis yang butuh perawatan minimal tanpa ribet. Investasi kecil buat keamanan besar.", 350000, ["Backup Mingguan (Weekly)", "Data Retention: 1 Bulan", "WordPress Core & Plugin Updates", "Malware Scan Bulanan", "Security Monitoring", "Laporan Bulanan"], "maintenance", True),
    ("Maintenance Pro", "Website selalu fresh, aman, dan optimal! Backup mingguan, malware scan, update konten bisnis, setup email profesional, dan manajemen Google Maps. Ada priority email support dan laporan mingguan detail. Buat yang butuh website selalu tampil prima tanpa repot urus teknis.", 750000, ["Backup Mingguan (Weekly)", "Data Retention: 1 Bulan", "Setup & Troubleshoot Titan Mail", "Update Konten Bisnis (Teks/Gambar)", "Malware Scan + Removal", "Google Maps Management", "Performance Monitoring", "Priority Email Support", "Laporan Mingguan"], "maintenance", True),
    ("Maintenance Expert", "Website selalu optimal dengan priority response dan security hardening! Backup harian, malware scan + removal + recovery, performance optimization, dan uptime monitoring 24/7. Termasuk custom development sampai 5 jam/bulan buat perubahan besar. Response time < 4 jam buat masalah kritis. Buat yang gak bisa afford website down dan butuh performa maksimal.", 1500000, ["Backup Harian (Daily)", "Data Retention: 3 Bulan", "Full Priority Support (Response < 4 Jam)", "Custom Development (5 Jam/Bulan)", "Security Hardening & Monitoring", "Malware Scan + Removal + Recovery", "Performance Optimization", "Uptime Monitoring 24/7", "Laporan Mingguan Detail"], "maintenance", True),
    # Logo & Branding
    ("Logo Starter", "Logo profesional siap dalam 24 jam! 2 opsi desain dengan format JPEG & PNG transparan. Cepat, profesional, dan ekonomis - cocok buat yang butuh logo berkualitas tanpa nunggu lama. File siap pakai buat semua kebutuhan digital Anda.", 250000, ["2 Opsi Desain Logo", "Format File: JPEG & PNG (Transparent)", "Pengerjaan Maks. 24 Jam", "2x Revisi Minor", "File Siap Pakai untuk Digital"], "logo", False),
    ("Logo Pro", "Logo berkualitas tinggi dengan file vektor master dan 3D mockup presentation! 3 opsi desain dengan revisi sampai 3x. File siap pakai buat cetak & digital dengan fleksibilitas penggunaan di semua media. Buat yang butuh logo premium dengan kualitas profesional.", 450000, ["3 Opsi Desain Logo", "Format File: Bitmap + Vector (Master File)", "3D Mockup Presentation", "Pengerjaan Maks. 24 Jam", "3x Revisi", "File Siap Pakai untuk Cetak & Digital"], "logo", False),
    ("Logo Expert", "Bangun brand identity yang konsisten dan profesional! Paket lengkap: logo profesional plus kartu nama, kop surat, amplop, dan stempel. 4 opsi desain dengan unlimited revisi, brand guidelines document, dan file vector lengkap. Investasi sekali buat brand yang kuat dan kredibel di mata pelanggan.", 1500000, ["4 Opsi Desain Logo", "Full Vector & Identity Assets", "Kartu Nama Design", "Kop Surat & Amplop Design", "Stempel Design", "Pengerjaan Maks. 3 Hari", "Unlimited Revisi", "Brand Guidelines Document", "File Siap Pakai untuk Semua Media"], "logo", False),
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
