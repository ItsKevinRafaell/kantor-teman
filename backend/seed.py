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
    "web_dev": {"name": "Web Development", "description": "Jasa pembuatan website responsif, cepat, dan dioptimalkan untuk meningkatkan konversi penjualan."},
    "seo": {"name": "SEO & Google Maps", "description": "Optimasi keberadaan bisnis online agar mudah ditemukan calon pelanggan melalui Google dan Google Maps."},
    "socmed": {"name": "Kelola Sosial Media", "description": "Tingkatkan engagement audiens dan bangun brand awareness yang konsisten di berbagai platform media sosial."},
    "maintenance": {"name": "Maintenance Website", "description": "Jaga website tetap aman, selalu di-backup, dan berkinerja optimal."},
    "logo": {"name": "Desain Logo & Identitas Visual", "description": "Desain logo profesional yang merepresentasikan nilai dan visi bisnis, siap untuk cetak maupun digital."},
}

products_data = [
    # (name, description, price, features, category_key, is_retainer)
    ("Web Starter (Tahunan)", "1 Halaman (Sales Focus). Domain & Hosting termasuk tahun ke-1.", 1000000, ["1 Halaman (Sales Focus)", "Domain & Hosting Termasuk (Tahun ke-1)", "WhatsApp Chat", "SSL", "Mobile Friendly"], "web_dev", False),
    ("Web Pro (Tahunan)", "Max. 5 Halaman. Domain & Hosting termasuk tahun ke-1.", 2250000, ["Max. 5 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Maps Embed", "SEO Dasar", "Google Analytics"], "web_dev", False),
    ("Web Expert (Tahunan)", "Max. 10 Halaman. Domain & Hosting termasuk tahun ke-1.", 3750000, ["Max. 10 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Setup Mail", "Blog System", "Speed Optimization"], "web_dev", False),
    ("Web Starter (Bulanan)", "1 Halaman (Sales Focus). Pembayaran bulanan.", 120000, ["1 Halaman (Sales Focus)", "Domain & Hosting Termasuk (Tahun ke-1)", "WhatsApp Chat", "SSL", "Mobile Friendly"], "web_dev", True),
    ("Web Pro (Bulanan)", "Max. 5 Halaman. Pembayaran bulanan.", 250000, ["Max. 5 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Maps Embed", "SEO Dasar", "Google Analytics"], "web_dev", True),
    ("Web Expert (Bulanan)", "Max. 10 Halaman. Pembayaran bulanan.", 375000, ["Max. 10 Halaman", "Domain & Hosting Termasuk (Tahun ke-1)", "Setup Titan Mail", "Blog System", "Speed Optimization"], "web_dev", True),
    ("SEO Starter", "Paket SEO dasar untuk bisnis lokal yang baru mulai optimasi online.", 1000000, ["Setup & Update Foto GBP", "2 Artikel Lokal / Bulan", "On-Page Dasar", "Laporan Performa Ringkas"], "seo", True),
    ("SEO Pro", "Paket SEO menengah dengan audit mendalam dan strategi keyword.", 2500000, ["Full Management GBP (Google Business Profile)", "6-8 Artikel Strategis / Bulan", "Audit Semrush & Keyword Gap", "Laporan Detail Trafik & Ranking"], "seo", True),
    ("SEO Expert", "Paket SEO premium untuk mendominasi pencarian lokal dan nasional.", 4500000, ["Full Management GBP + Review Reply", "10-12 Artikel Otoritas / Bulan", "Competitor Gap & CRO (Conversion Rate Optimization)", "Full Insight & Strategi"], "seo", True),
    ("Sosmed Starter", "Paket sosial media dasar dengan 9 konten per bulan.", 500000, ["9 Konten (3x Seminggu)", "Branded Template", "Caption & Hashtag Dasar"], "socmed", True),
    ("Sosmed Pro", "Paket sosial media menengah dengan konten harian dan video reels.", 1200000, ["15 Konten (Hampir Setiap Hari)", "2 Video Reels Sederhana", "Content Plan & Strategy", "Caption Persuasif (Copywriting)"], "socmed", True),
    ("Sosmed Expert", "Paket sosial media premium dengan konten setiap hari dan video reels berkelas.", 2000000, ["24 Konten (Setiap Hari)", "4 Video Reels Berkelas", "Full Branding Guidelines", "Daily Story Template"], "socmed", True),
    ("Maintenance Starter", "Maintenance dasar: backup mingguan dan keamanan website.", 350000, ["Backup Mingguan (Weekly)", "Retensi Data: Hapus otomatis > 1 bulan", "Update WordPress & Malware Scan"], "maintenance", True),
    ("Maintenance Pro", "Maintenance menengah dengan dukungan email dan update konten.", 750000, ["Backup Mingguan (Weekly)", "Retensi Data: Hapus otomatis > 1 bulan", "Setup & Troubleshoot Titan Mail", "Update Informasi Bisnis Dasar", "Malware Scan + Manajemen Google Maps"], "maintenance", True),
    ("Maintenance Expert", "Maintenance premium dengan priority response dan security hardening.", 1500000, ["Backup Mingguan (Weekly)", "Retensi Data: Hapus otomatis > 1 bulan", "Full Support & Priority Response", "Ganti Teks/Gambar (Maks. 3x)", "Malware Scan + Security Hardening"], "maintenance", True),
    ("Logo Starter", "Desain logo cepat dengan 2 opsi konsep, selesai maks. 24 jam.", 250000, ["2 Opsi Desain", "Format: JPEG & PNG (Transparan)", "Pengerjaan Maks. 24 Jam"], "logo", False),
    ("Logo Pro", "Desain logo profesional dengan file vektor dan 3D mockup.", 450000, ["3 Opsi Desain", "Format: Bitmap + File Vektor (Master File)", "3D Mockup Presentation", "Pengerjaan Maks. 24 Jam"], "logo", False),
    ("Logo Expert", "Paket identitas visual lengkap: logo, kartu nama, kop surat, stempel.", 1500000, ["4 Opsi Desain", "Format: Full Vector & Identity Assets", "Kartu Nama, Kop Surat, Stempel", "Pengerjaan Maks. 3 Hari"], "logo", False),
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
