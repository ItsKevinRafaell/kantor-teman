"""
Seed initial data on first run.
ADMIN_INITIAL_PASSWORD env var is REQUIRED — no hardcoded default.
"""
import os
import json
from sqlalchemy.orm import Session

from app.core.security import hash_password
from models import (
    User, SystemSettings, ProviderConfig,
    DynamicTemplate,
)


def seed_data(db: Session):
    admin_password = os.getenv("ADMIN_INITIAL_PASSWORD")
    if not admin_password:
        raise RuntimeError(
            "ADMIN_INITIAL_PASSWORD env var is required. "
            "Set it before running migrations/seed."
        )

    if not db.query(User).first():
        db.add(User(name="Admin", email="admin@temanumkmkita.com", hashed_password=hash_password(admin_password)))
        db.commit()
    if not db.query(SystemSettings).filter_by(key="fonnte_token").first():
        db.add(SystemSettings(key="fonnte_token", value=os.getenv("FONNTE_TOKEN", "")))
        db.commit()
    default_settings = {
        "whatsapp_provider": "fonnte",
        "whatsapp_blast_delay_seconds": os.getenv("WHATSAPP_BLAST_DELAY_SECONDS", "5"),
    }
    for key, value in default_settings.items():
        if not db.query(SystemSettings).filter_by(key=key).first():
            db.add(SystemSettings(key=key, value=value))
    db.commit()
    if not db.query(ProviderConfig).first():
        providers = [
            ProviderConfig(id="FONNTE", provider_name="Fonnte WhatsApp", remaining_quota=10000, price_per_unit_idr=6.6, price_input_token_usd=0, price_output_token_usd=0),
            ProviderConfig(id="9ROUTER", provider_name="9router AI", remaining_quota=0, price_per_unit_idr=0, price_input_token_usd=0, price_output_token_usd=0),
        ]
        db.add_all(providers)
        db.commit()
    if not db.query(DynamicTemplate).filter_by(type="TIMELINE_TEMPLATE").first():
        timeline_templates = [
            DynamicTemplate(id="timeline-seo-lokal", name="Timeline SEO Lokal", type="TIMELINE_TEMPLATE",
                content=json.dumps([
                    {"sequence": 1, "title": "Audit & Riset Kata Kunci", "description": "Analisis kompetitor, riset kata kunci lokal bervolume tinggi, dan audit teknis website existing."},
                    {"sequence": 2, "title": "Optimasi On-Page & Teknis", "description": "Perbaikan struktur website, meta tags, schema markup, dan kecepatan loading halaman."},
                    {"sequence": 3, "title": "Setup Google Business Profile", "description": "Optimasi profil Google Maps, kategori bisnis, foto, dan informasi NAP (Name, Address, Phone)."},
                    {"sequence": 4, "title": "Content & Link Building Lokal", "description": "Pembuatan konten lokal berkualitas dan backlink dari direktori bisnis terpercaya di wilayah target."},
                    {"sequence": 5, "title": "Monitoring & Reporting", "description": "Tracking peringkat, analisis trafik organik, dan laporan performa bulanan dengan rekomendasi lanjutan."},
                ]), is_active=True, category_id=None),
            DynamicTemplate(id="timeline-web-dev", name="Timeline Web Development", type="TIMELINE_TEMPLATE",
                content=json.dumps([
                    {"sequence": 1, "title": "Discovery & Wireframe", "description": "Diskusi kebutuhan bisnis, pembuatan sitemap, wireframe UI/UX, dan approval desain awal."},
                    {"sequence": 2, "title": "Desain Visual & Prototype", "description": "Pembuatan desain high-fidelity, pemilihan color scheme, typography, dan interactive prototype."},
                    {"sequence": 3, "title": "Development Frontend & Backend", "description": "Coding halaman responsif, integrasi CMS/database, dan pengembangan fitur custom sesuai kebutuhan."},
                    {"sequence": 4, "title": "Testing & Quality Assurance", "description": "Pengujian fungsional, responsivitas, kecepatan, keamanan, dan kompatibilitas lintas browser/device."},
                    {"sequence": 5, "title": "Launch & Deployment", "description": "Migrasi ke server produksi, setup domain & SSL, konfigurasi SEO dasar, dan go-live monitoring."},
                    {"sequence": 6, "title": "Maintenance & Support", "description": "Dukungan teknis pasca-launch, backup rutin, update keamanan, dan minor revision selama 30 hari."},
                ]), is_active=True, category_id=None),
        ]
        db.add_all(timeline_templates)
        db.commit()
