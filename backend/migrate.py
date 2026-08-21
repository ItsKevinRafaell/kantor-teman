"""
Migrasi: tambah kolom product_interest, batch_name, dan rating ke tabel leads.
Rebuild tabel proposals untuk multi-service. Tambah tabel service_items.
Jalankan sekali: python migrate.py
"""
import sqlite3, os
from urllib.parse import unquote
from dotenv import load_dotenv

_env_file = os.environ.get("ENV_FILE", ".env.production")
load_dotenv(_env_file)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=False)


def _resolve_sqlite_db_path(db_url: str) -> str:
    if db_url.startswith("sqlite:///"):
        raw_path = unquote(db_url.replace("sqlite:///", "", 1))
        if raw_path.startswith("/"):
            return raw_path
        return os.path.abspath(os.path.join(os.path.dirname(__file__), raw_path))
    return os.path.join(os.path.dirname(__file__), "leads.db")

# ---------------------------------------------------------------------------
# MySQL Migration (jalan dulu jika production MySQL)
# ---------------------------------------------------------------------------
_db_url = os.getenv("DATABASE_URL", "")
if "mysql" in _db_url:
    import pymysql
    from sqlalchemy.engine import make_url
    _p = make_url(_db_url)
    _mc = pymysql.connect(
        host=_p.host, port=_p.port or 3306,
        user=_p.username, password=_p.password,
        database=_p.database, charset="utf8mb4",
    )
    _cur = _mc.cursor()

    def _col_exists(table, col):
        _cur.execute(f"SHOW COLUMNS FROM `{table}` LIKE %s", (col,))
        return _cur.fetchone() is not None

    def _table_exists(table):
        _cur.execute("SHOW TABLES LIKE %s", (table,))
        return _cur.fetchone() is not None

    _migrations = [
        # brand kits — chosen default asset for PDF documents
        ("brand_kits", "default_document_asset_id", "ALTER TABLE brand_kits ADD COLUMN default_document_asset_id VARCHAR(36) NULL"),
        # leads
        ("leads", "is_archived", "ALTER TABLE leads ADD COLUMN is_archived TINYINT(1) NOT NULL DEFAULT 0"),
        ("leads", "deleted_at", "ALTER TABLE leads ADD COLUMN deleted_at VARCHAR(255) NULL"),
        ("leads", "lead_score", "ALTER TABLE leads ADD COLUMN lead_score INT NOT NULL DEFAULT 0"),
        ("leads", "website_url", "ALTER TABLE leads ADD COLUMN website_url VARCHAR(2000) NULL"),
        ("leads", "google_rating", "ALTER TABLE leads ADD COLUMN google_rating FLOAT NULL"),
        ("leads", "review_count", "ALTER TABLE leads ADD COLUMN review_count INT NULL"),
        ("leads", "latitude", "ALTER TABLE leads ADD COLUMN latitude FLOAT NULL"),
        ("leads", "longitude", "ALTER TABLE leads ADD COLUMN longitude FLOAT NULL"),
        ("leads", "instagram_url", "ALTER TABLE leads ADD COLUMN instagram_url VARCHAR(500) NULL"),
        ("leads", "facebook_url", "ALTER TABLE leads ADD COLUMN facebook_url VARCHAR(500) NULL"),
        ("leads", "tiktok_url", "ALTER TABLE leads ADD COLUMN tiktok_url VARCHAR(500) NULL"),
        ("leads", "sales_owner", "ALTER TABLE leads ADD COLUMN sales_owner VARCHAR(255) NULL"),
        ("leads", "next_action_at", "ALTER TABLE leads ADD COLUMN next_action_at VARCHAR(255) NULL"),
        ("leads", "loss_reason", "ALTER TABLE leads ADD COLUMN loss_reason VARCHAR(500) NULL"),
        ("leads", "do_not_contact", "ALTER TABLE leads ADD COLUMN do_not_contact TINYINT(1) NOT NULL DEFAULT 0"),
        ("leads", "score_adjustment", "ALTER TABLE leads ADD COLUMN score_adjustment INT NOT NULL DEFAULT 0"),
        ("leads", "score_adjustment_reason", "ALTER TABLE leads ADD COLUMN score_adjustment_reason VARCHAR(500) NULL"),
        ("leads", "score_updated_at", "ALTER TABLE leads ADD COLUMN score_updated_at VARCHAR(255) NULL"),
        # proposals/report tracking
        ("proposals", "report_open_count", "ALTER TABLE proposals ADD COLUMN report_open_count INT NOT NULL DEFAULT 0"),
        ("proposals", "last_report_viewed_at", "ALTER TABLE proposals ADD COLUMN last_report_viewed_at VARCHAR(255) NULL"),
        ("proposals", "max_report_duration_seconds", "ALTER TABLE proposals ADD COLUMN max_report_duration_seconds INT NOT NULL DEFAULT 0"),
        ("proposal_analytics", "visitor_hash", "ALTER TABLE proposal_analytics ADD COLUMN visitor_hash VARCHAR(64) NULL"),
        ("proposal_analytics", "source", "ALTER TABLE proposal_analytics ADD COLUMN source VARCHAR(50) NULL"),
        ("proposal_analytics", "metadata_json", "ALTER TABLE proposal_analytics ADD COLUMN metadata_json TEXT NULL"),
        # projects
        ("projects", "color", "ALTER TABLE projects ADD COLUMN color VARCHAR(20) NOT NULL DEFAULT 'gray'"),
        ("projects", "is_archived", "ALTER TABLE projects ADD COLUMN is_archived TINYINT(1) NOT NULL DEFAULT 0"),
        ("projects", "dp_percent", "ALTER TABLE projects ADD COLUMN dp_percent FLOAT NULL"),
        ("projects", "monthly_invoice_enabled", "ALTER TABLE projects ADD COLUMN monthly_invoice_enabled TINYINT(1) NOT NULL DEFAULT 0"),
        ("projects", "next_invoice_date", "ALTER TABLE projects ADD COLUMN next_invoice_date VARCHAR(255) NULL"),
        ("projects", "completed_at", "ALTER TABLE projects ADD COLUMN completed_at VARCHAR(255) NULL"),
        ("projects", "proposal_id", "ALTER TABLE projects ADD COLUMN proposal_id VARCHAR(36) NULL"),
        ("boards", "color", "ALTER TABLE boards ADD COLUMN color VARCHAR(20) NOT NULL DEFAULT 'gray'"),
        ("board_columns", "color", "ALTER TABLE board_columns ADD COLUMN color VARCHAR(20) NOT NULL DEFAULT 'gray'"),
        ("board_cards", "color", "ALTER TABLE board_cards ADD COLUMN color VARCHAR(20) NOT NULL DEFAULT 'gray'"),
        ("board_cards", "is_archived", "ALTER TABLE board_cards ADD COLUMN is_archived TINYINT(1) NOT NULL DEFAULT 0"),
        ("board_card_comments", "author", "ALTER TABLE board_card_comments ADD COLUMN author TEXT NOT NULL DEFAULT ''"),
        ("document_folders", "parent_id", "ALTER TABLE document_folders ADD COLUMN parent_id VARCHAR(36) NULL"),
        ("document_folders", "color", "ALTER TABLE document_folders ADD COLUMN color VARCHAR(20) NOT NULL DEFAULT '#6B7280'"),
        ("documents", "folder_id", "ALTER TABLE documents ADD COLUMN folder_id VARCHAR(36) NULL"),
        ("documents", "name", "ALTER TABLE documents ADD COLUMN name VARCHAR(255) NOT NULL DEFAULT ''"),
        ("documents", "type", "ALTER TABLE documents ADD COLUMN type VARCHAR(50) NOT NULL DEFAULT 'document'"),
        ("documents", "content", "ALTER TABLE documents ADD COLUMN content LONGTEXT NULL"),
        ("documents", "file_size", "ALTER TABLE documents ADD COLUMN file_size INT NULL"),
        ("documents", "title", "ALTER TABLE documents ADD COLUMN title VARCHAR(500) NOT NULL DEFAULT ''"),
        ("documents", "body", "ALTER TABLE documents ADD COLUMN body LONGTEXT NULL"),
        ("documents", "url", "ALTER TABLE documents ADD COLUMN url VARCHAR(2000) NULL"),
        ("documents", "tags", "ALTER TABLE documents ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'"),
        ("documents", "status", "ALTER TABLE documents ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'Draft'"),
        ("documents", "review_notes", "ALTER TABLE documents ADD COLUMN review_notes TEXT NULL"),
        ("documents", "approved_at", "ALTER TABLE documents ADD COLUMN approved_at VARCHAR(255) NULL"),
        ("documents", "rejected_at", "ALTER TABLE documents ADD COLUMN rejected_at VARCHAR(255) NULL"),
        ("documents", "sent_at", "ALTER TABLE documents ADD COLUMN sent_at VARCHAR(255) NULL"),
        ("documents", "signed_at", "ALTER TABLE documents ADD COLUMN signed_at VARCHAR(255) NULL"),
        ("documents", "archived_at", "ALTER TABLE documents ADD COLUMN archived_at VARCHAR(255) NULL"),
        ("documents", "source_type", "ALTER TABLE documents ADD COLUMN source_type VARCHAR(50) NULL"),
        ("documents", "source_id", "ALTER TABLE documents ADD COLUMN source_id VARCHAR(255) NULL"),
        ("documents", "updated_at", "ALTER TABLE documents ADD COLUMN updated_at VARCHAR(255) NULL"),
        ("documents", "lead_id", "ALTER TABLE documents ADD COLUMN lead_id INT NULL"),
        ("document_folders", "lead_id", "ALTER TABLE document_folders ADD COLUMN lead_id INT NULL"),
        ("provider_configs", "monthly_quota", "ALTER TABLE provider_configs ADD COLUMN monthly_quota FLOAT NOT NULL DEFAULT 0"),
        ("scrape_history", "batch_name", "ALTER TABLE scrape_history ADD COLUMN batch_name VARCHAR(255) NULL"),
        ("users", "role", "ALTER TABLE users ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'admin'"),
        ("users", "token_version", "ALTER TABLE users ADD COLUMN token_version INT NOT NULL DEFAULT 1"),
        ("ai_proxies", "feature", "ALTER TABLE ai_proxies ADD COLUMN feature VARCHAR(50) NULL"),
        ("contacts", "lead_id", "ALTER TABLE contacts ADD COLUMN lead_id INT NULL"),
        ("ai_proxies", "provider", "ALTER TABLE ai_proxies ADD COLUMN provider VARCHAR(50) NOT NULL DEFAULT '9router'"),
        ("brand_kits", "brand_name", "ALTER TABLE brand_kits ADD COLUMN brand_name VARCHAR(255) NOT NULL DEFAULT ''"),
        ("brand_kits", "tagline", "ALTER TABLE brand_kits ADD COLUMN tagline VARCHAR(255) NOT NULL DEFAULT ''"),
        ("brand_kits", "phone", "ALTER TABLE brand_kits ADD COLUMN phone VARCHAR(50) NOT NULL DEFAULT ''"),
        ("brand_kits", "email", "ALTER TABLE brand_kits ADD COLUMN email VARCHAR(255) NOT NULL DEFAULT ''"),
        ("brand_kits", "address", "ALTER TABLE brand_kits ADD COLUMN address TEXT NULL"),
        ("brand_kits", "logo", "ALTER TABLE brand_kits ADD COLUMN logo TEXT NULL"),
        ("generated_documents", "status", "ALTER TABLE generated_documents ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'Draft'"),
        ("generated_documents", "payment_status", "ALTER TABLE generated_documents ADD COLUMN payment_status VARCHAR(50) NULL"),
        ("generated_documents", "review_notes", "ALTER TABLE generated_documents ADD COLUMN review_notes TEXT NULL"),
        ("generated_documents", "approved_at", "ALTER TABLE generated_documents ADD COLUMN approved_at VARCHAR(255) NULL"),
        ("generated_documents", "rejected_at", "ALTER TABLE generated_documents ADD COLUMN rejected_at VARCHAR(255) NULL"),
        ("generated_documents", "sent_at", "ALTER TABLE generated_documents ADD COLUMN sent_at VARCHAR(255) NULL"),
        ("generated_documents", "signed_at", "ALTER TABLE generated_documents ADD COLUMN signed_at VARCHAR(255) NULL"),
        ("generated_documents", "archived_at", "ALTER TABLE generated_documents ADD COLUMN archived_at VARCHAR(255) NULL"),
        # report_snapshots — report-triggered invoice (plan report->invoice)
        ("report_snapshots", "finalized_at", "ALTER TABLE report_snapshots ADD COLUMN finalized_at VARCHAR(255) NULL"),
        ("report_snapshots", "finalized_by", "ALTER TABLE report_snapshots ADD COLUMN finalized_by VARCHAR(255) NULL"),
        ("report_snapshots", "generated_invoice_id", "ALTER TABLE report_snapshots ADD COLUMN generated_invoice_id VARCHAR(36) NULL"),
    ]

    # Backfill contacts.lead_id by phone match
    if _table_exists("contacts") and _col_exists("contacts", "lead_id"):
        _cur.execute("SELECT id, phone_number FROM contacts WHERE lead_id IS NULL")
        for (contact_id, phone) in _cur.fetchall():
            if not phone:
                continue
            # Normalize to 08xx
            digits = ''.join(c for c in phone if c.isdigit())
            if digits.startswith('62'):
                digits = '0' + digits[2:]
            _cur.execute("SELECT id FROM leads WHERE REPLACE(REPLACE(REPLACE(REPLACE(phone_number, ' ', ''), '-', ''), '+62', '0') = %s OR phone_number = %s", (digits, phone))
            lead_row = _cur.fetchone()
            if lead_row:
                _cur.execute("UPDATE contacts SET lead_id = %s WHERE id = %s", (lead_row[0], contact_id))
                print(f"  Linked contact {contact_id} -> lead {lead_row[0]}")
    print("= contacts.lead_id backfill done")

    # Backfill ai_proxies.provider = '9router' for old or empty values.
    if _table_exists("ai_proxies") and _col_exists("ai_proxies", "provider"):
        _cur.execute("UPDATE ai_proxies SET provider = '9router' WHERE provider IS NULL OR provider = '' OR provider != '9router'")
        affected = _cur.rowcount
        if affected > 0:
            print(f"  Set provider=9router for {affected} ai_proxies")
        print("= ai_proxies.provider backfill done")
    elif _table_exists("ai_proxies"):
        print("= ai_proxies.provider belum ada, skip backfill")

    # Create ai_models table if not exists
    if not _table_exists("ai_models"):
        _cur.execute("""
            CREATE TABLE ai_models (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                model_id VARCHAR(255) NOT NULL,
                description TEXT,
                capabilities TEXT NOT NULL DEFAULT '["chat"]',
                is_active TINYINT(1) DEFAULT 1,
                is_default_chat TINYINT(1) DEFAULT 0,
                is_default_image TINYINT(1) DEFAULT 0,
                is_default_article TINYINT(1) DEFAULT 0,
                is_default_analysis TINYINT(1) DEFAULT 0,
                created_at VARCHAR(255) NOT NULL
            )
        """)
        print("+ MySQL: tabel ai_models dibuat")
    else:
        print("= MySQL: ai_models sudah ada, skip")

    if not _table_exists("notifications"):
        _cur.execute("""
            CREATE TABLE notifications (
                id VARCHAR(36) PRIMARY KEY,
                user_id INT NULL,
                title VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                type VARCHAR(50) NOT NULL DEFAULT 'info',
                target_type VARCHAR(50) NULL,
                target_id VARCHAR(255) NULL,
                action_url VARCHAR(1000) NULL,
                is_read TINYINT(1) NOT NULL DEFAULT 0,
                created_at VARCHAR(255) NOT NULL,
                read_at VARCHAR(255) NULL
            )
        """)
        print("+ MySQL: tabel notifications dibuat")
    else:
        print("= MySQL: notifications sudah ada, skip")

    if not _table_exists("report_snapshots"):
        _cur.execute("""
            CREATE TABLE report_snapshots (
                id VARCHAR(36) PRIMARY KEY,
                report_type VARCHAR(50) NOT NULL DEFAULT 'monthly',
                target_type VARCHAR(50) NOT NULL DEFAULT 'project',
                target_id VARCHAR(255) NULL,
                project_id VARCHAR(36) NULL,
                lead_id INT NULL,
                service_type VARCHAR(50) NULL,
                title VARCHAR(500) NOT NULL,
                period_start VARCHAR(50) NULL,
                period_end VARCHAR(50) NULL,
                month_number INT NULL,
                metrics_json LONGTEXT NOT NULL,
                evidence_json LONGTEXT NOT NULL,
                narrative_json LONGTEXT NOT NULL,
                public_slug VARCHAR(255) NULL,
                public_enabled TINYINT(1) NOT NULL DEFAULT 1,
                open_count INT NOT NULL DEFAULT 0,
                first_viewed_at VARCHAR(255) NULL,
                last_viewed_at VARCHAR(255) NULL,
                max_duration_seconds INT NOT NULL DEFAULT 0,
                generated_document_id VARCHAR(36) NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'Draft',
                finalized_at VARCHAR(255) NULL,
                finalized_by VARCHAR(255) NULL,
                generated_invoice_id VARCHAR(36) NULL,
                generated_by VARCHAR(255) NULL,
                created_at VARCHAR(255) NOT NULL,
                updated_at VARCHAR(255) NULL,
                UNIQUE KEY uniq_report_public_slug (public_slug),
                INDEX idx_report_project_id (project_id),
                INDEX idx_report_lead_id (lead_id),
                INDEX idx_report_generated_document_id (generated_document_id)
            )
        """)
        print("+ MySQL: tabel report_snapshots dibuat")
    else:
        print("= MySQL: report_snapshots sudah ada, skip")

    if not _table_exists("board_card_attachments"):
        _cur.execute("""
            CREATE TABLE board_card_attachments (
                id VARCHAR(36) PRIMARY KEY,
                card_id VARCHAR(36) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                file_type VARCHAR(100) NULL,
                uploaded_by VARCHAR(255) NULL,
                uploaded_at VARCHAR(255) NOT NULL,
                INDEX idx_board_card_attachments_card_id (card_id)
            )
        """)
        print("+ MySQL: tabel board_card_attachments dibuat")
    else:
        print("= MySQL: board_card_attachments sudah ada, skip")

    if not _table_exists("password_reset_tokens"):
        _cur.execute("""
            CREATE TABLE password_reset_tokens (
                id VARCHAR(36) PRIMARY KEY,
                user_id INT NOT NULL,
                token_hash VARCHAR(64) NOT NULL,
                expires_at VARCHAR(255) NOT NULL,
                used_at VARCHAR(255) NULL,
                created_at VARCHAR(255) NOT NULL,
                UNIQUE KEY uniq_password_reset_token_hash (token_hash),
                INDEX idx_password_reset_user_id (user_id),
                INDEX idx_password_reset_expires_at (expires_at)
            )
        """)
        print("+ MySQL: tabel password_reset_tokens dibuat")
    else:
        print("= MySQL: password_reset_tokens sudah ada, skip")

    if not _table_exists("project_riwayat"):
        _cur.execute("""
            CREATE TABLE project_riwayat (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) NOT NULL,
                timestamp VARCHAR(255) NOT NULL,
                actor VARCHAR(255) NOT NULL,
                category VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                attachments TEXT NULL,
                INDEX idx_project_riwayat_project_id (project_id),
                INDEX idx_project_riwayat_timestamp (timestamp)
            )
        """)
        print("+ MySQL: tabel project_riwayat dibuat")
    else:
        print("= MySQL: project_riwayat sudah ada, skip")

    for table, col, sql in _migrations:
        if not _table_exists(table):
            print(f"= {table} belum ada, skip (akan dibuat SQLAlchemy)")
            continue
        if not _col_exists(table, col):
            _cur.execute(sql)
            print(f"+ MySQL: {table}.{col} ditambahkan")
        else:
            print(f"= MySQL: {table}.{col} sudah ada, skip")

    # generated_documents.display_filename
    if _table_exists("generated_documents") and not _col_exists("generated_documents", "display_filename"):
        _cur.execute("ALTER TABLE generated_documents ADD COLUMN display_filename VARCHAR(500) NULL")
        print("+ MySQL: generated_documents.display_filename ditambahkan")
    elif _table_exists("generated_documents"):
        print("= MySQL: generated_documents.display_filename sudah ada, skip")

    # document_sequences table
    if not _table_exists("document_sequences"):
        _cur.execute("""
            CREATE TABLE document_sequences (
                id INT PRIMARY KEY AUTO_INCREMENT,
                target_id VARCHAR(255) NOT NULL,
                template_type VARCHAR(50) NOT NULL,
                last_seq INT NOT NULL DEFAULT 0,
                UNIQUE KEY uniq_target_type (target_id, template_type)
            )
        """)
        print("+ MySQL: tabel document_sequences dibuat")
    else:
        print("= MySQL: tabel document_sequences sudah ada, skip")

    # Upgrade built-in client-facing templates once. Custom templates are untouched.
    if _table_exists("document_templates"):
        from document_template_library import DEFAULT_DOCUMENT_TEMPLATES
        import json as _json_templates
        import uuid as _uuid_templates
        _template_version = "client_ready_v5"
        _should_upgrade = True
        if _table_exists("system_settings"):
            _cur.execute("SELECT value FROM system_settings WHERE `key` = %s", ("document_templates_version",))
            _row = _cur.fetchone()
            _should_upgrade = not _row or _row[0] != _template_version
        if _should_upgrade:
            for _template in DEFAULT_DOCUMENT_TEMPLATES:
                _cur.execute("SELECT id FROM document_templates WHERE name = %s LIMIT 1", (_template["name"],))
                _existing = _cur.fetchone()
                _variables = _json_templates.dumps(_template["variables"])
                if _existing:
                    _cur.execute(
                        "UPDATE document_templates SET type = %s, html_template = %s, variables = %s, is_active = 1 WHERE id = %s",
                        (_template["type"], _template["html_template"], _variables, _existing[0]),
                    )
                else:
                    _cur.execute(
                        "INSERT INTO document_templates (id, name, type, html_template, variables, is_active, created_at) VALUES (%s,%s,%s,%s,%s,1,%s)",
                        (str(_uuid_templates.uuid4()), _template["name"], _template["type"], _template["html_template"], _variables, "2026-06-01T00:00:00+00:00"),
                    )
            if _table_exists("system_settings"):
                _cur.execute(
                    "INSERT INTO system_settings (`key`, value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value = VALUES(value)",
                    ("document_templates_version", _template_version),
                )
            print("+ MySQL: built-in document templates upgraded ke client_ready_v5")
        else:
            print("= MySQL: built-in document templates sudah client_ready_v5, skip")

    # Make projects.lead_id nullable (was NOT NULL, breaks create-project-without-lead)
    if _table_exists("projects") and _col_exists("projects", "lead_id"):
        _cur.execute("""
            SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects' AND COLUMN_NAME = 'lead_id'
        """)
        row = _cur.fetchone()
        if row and row[0] == "NO":
            # Drop FK constraint first (MySQL blocks MODIFY on FK columns)
            _cur.execute("""
                SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'projects'
                  AND COLUMN_NAME = 'lead_id' AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            fk_rows = _cur.fetchall()
            for (fk_name,) in fk_rows:
                _cur.execute(f"ALTER TABLE projects DROP FOREIGN KEY `{fk_name}`")
                print(f"- MySQL: dropped FK {fk_name}")
            _cur.execute("ALTER TABLE projects MODIFY COLUMN lead_id INT NULL")
            print("+ MySQL: projects.lead_id set to NULL")
            # Re-add FK (nullable FK still enforces referential integrity when not null)
            _cur.execute("""
                ALTER TABLE projects ADD CONSTRAINT projects_lead_fk
                FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE SET NULL
            """)
            print("+ MySQL: re-added FK projects.lead_id → leads.id ON DELETE SET NULL")
        else:
            print("= MySQL: projects.lead_id already nullable, skip")

    # Add FK constraint workspace_rows.board_card_id → board_cards.id ON DELETE SET NULL
    if _table_exists("workspace_rows") and _table_exists("board_cards"):
        _cur.execute("""
            SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'workspace_rows'
            AND COLUMN_NAME = 'board_card_id' AND REFERENCED_TABLE_NAME = 'board_cards'
        """)
        if not _cur.fetchone():
            try:
                _cur.execute("""
                    ALTER TABLE workspace_rows ADD CONSTRAINT fk_workspace_rows_board_card
                    FOREIGN KEY (board_card_id) REFERENCES board_cards(id) ON DELETE SET NULL
                """)
                print("+ MySQL: FK workspace_rows.board_card_id → board_cards.id ON DELETE SET NULL")
            except Exception as _e:
                print(f"= MySQL: FK workspace_rows.board_card_id skip ({_e})")
        else:
            print("= MySQL: FK workspace_rows.board_card_id sudah ada, skip")

    # -----------------------------------------------------------------------
    # Opsi B (product-driven) Tahap 1 — schema only.
    # 1) projects.product_id -> products.id (nullable, ON DELETE SET NULL)
    # 2) tabel baru project_addons (add-on line items per project)
    # Tidak menyentuh logika report/proposal/kontrak (tahap berikutnya).
    # -----------------------------------------------------------------------
    if _table_exists("projects") and not _col_exists("projects", "product_id"):
        _cur.execute("ALTER TABLE projects ADD COLUMN product_id VARCHAR(36) NULL")
        _cur.execute("CREATE INDEX idx_projects_product_id ON projects (product_id)")
        if _table_exists("products"):
            try:
                _cur.execute("""
                    ALTER TABLE projects ADD CONSTRAINT fk_projects_product
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
                """)
                print("+ MySQL: projects.product_id ditambahkan (+FK products ON DELETE SET NULL)")
            except Exception as _e:
                print(f"+ MySQL: projects.product_id ditambahkan (FK skip: {_e})")
        else:
            print("+ MySQL: projects.product_id ditambahkan (products belum ada, FK di-skip)")
    elif _table_exists("projects"):
        print("= MySQL: projects.product_id sudah ada, skip")

    if not _table_exists("project_addons"):
        _cur.execute("""
            CREATE TABLE project_addons (
                id VARCHAR(36) PRIMARY KEY,
                project_id VARCHAR(36) NOT NULL,
                product_id VARCHAR(36) NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT NULL,
                price FLOAT NOT NULL DEFAULT 0,
                quantity INT NOT NULL DEFAULT 1,
                is_recurring TINYINT(1) NOT NULL DEFAULT 0,
                created_at VARCHAR(255) NOT NULL,
                INDEX idx_project_addons_project_id (project_id),
                INDEX idx_project_addons_product_id (product_id),
                CONSTRAINT fk_project_addons_project
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                CONSTRAINT fk_project_addons_product
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
            )
        """)
        print("+ MySQL: tabel project_addons dibuat")
    else:
        print("= MySQL: tabel project_addons sudah ada, skip")

    _mc.commit()
    _mc.close()
    print("MySQL migration selesai.")
    exit(0)

# ---------------------------------------------------------------------------
# SQLite Migration (local dev)
# ---------------------------------------------------------------------------
DB_PATH = _resolve_sqlite_db_path(os.getenv("DATABASE_URL", ""))
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Cek apakah tabel leads ada
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='leads'")
leads_table_exists = cur.fetchone() is not None

if not leads_table_exists:
    print("= leads belum ada, akan dibuat oleh SQLAlchemy saat startup — skip semua ALTER leads")
    conn.close()
    print("Migrasi selesai (DB baru, semua tabel akan dibuat oleh SQLAlchemy).")
    exit(0)

# Cek kolom yang sudah ada di leads
cur.execute("PRAGMA table_info(leads)")
existing = {row[1] for row in cur.fetchall()}

if "product_interest" not in existing:
    cur.execute("ALTER TABLE leads ADD COLUMN product_interest TEXT")
    print("+ kolom product_interest ditambahkan")
else:
    print("= product_interest sudah ada, skip")

if "batch_name" not in existing:
    cur.execute("ALTER TABLE leads ADD COLUMN batch_name TEXT")
    print("+ kolom batch_name ditambahkan")
else:
    print("= batch_name sudah ada, skip")

if "rating" not in existing:
    cur.execute("ALTER TABLE leads ADD COLUMN rating INTEGER DEFAULT 0")
    print("+ kolom rating ditambahkan")
else:
    print("= rating sudah ada, skip")

for col, ddl in [
    ("sales_owner", "ALTER TABLE leads ADD COLUMN sales_owner VARCHAR(255)"),
    ("next_action_at", "ALTER TABLE leads ADD COLUMN next_action_at VARCHAR(255)"),
    ("loss_reason", "ALTER TABLE leads ADD COLUMN loss_reason VARCHAR(500)"),
    ("do_not_contact", "ALTER TABLE leads ADD COLUMN do_not_contact BOOLEAN NOT NULL DEFAULT 0"),
    ("score_adjustment", "ALTER TABLE leads ADD COLUMN score_adjustment INTEGER NOT NULL DEFAULT 0"),
    ("score_adjustment_reason", "ALTER TABLE leads ADD COLUMN score_adjustment_reason VARCHAR(500)"),
    ("score_updated_at", "ALTER TABLE leads ADD COLUMN score_updated_at VARCHAR(255)"),
]:
    if col not in existing:
        cur.execute(ddl)
        print(f"+ kolom {col} ditambahkan ke leads")
    else:
        print(f"= leads.{col} sudah ada, skip")

# Rebuild proposals table for multi-service structure
cur.execute("PRAGMA table_info(proposals)")
proposal_cols = {row[1] for row in cur.fetchall()}

if "services_detail" not in proposal_cols:
    # Need to rebuild - migrate old data
    import json
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proposals'")
    if cur.fetchone():
        # Backup old data
        cur.execute("SELECT id, lead_id, service_name, price, features, additional_options, status, created_at FROM proposals")
        old_rows = cur.fetchall()
        cur.execute("DROP TABLE proposals")
        print("- tabel proposals lama di-drop")
    else:
        old_rows = []

    cur.execute("""
    CREATE TABLE proposals (
        id TEXT PRIMARY KEY,
        lead_id INTEGER NOT NULL REFERENCES leads(id),
        services_detail TEXT NOT NULL,
        total_price REAL NOT NULL DEFAULT 0,
        additional_options TEXT,
        status TEXT NOT NULL DEFAULT 'Sent',
        created_at TEXT
    )
    """)
    print("+ tabel proposals baru dibuat (multi-service)")

    # Migrate old data
    for row in old_rows:
        old_id, lead_id, service_name, price, features, additional_options, status, created_at = row
        try:
            features_list = json.loads(features) if features else []
        except Exception:
            features_list = []
        services_detail = json.dumps([{"name": service_name or "", "price": price or 0, "features": features_list}])
        cur.execute(
            "INSERT INTO proposals (id, lead_id, services_detail, total_price, additional_options, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (old_id, lead_id, services_detail, price or 0, additional_options, status, created_at)
        )
    if old_rows:
        print(f"  migrated {len(old_rows)} existing proposals")
else:
    print("= proposals sudah multi-service, skip")

# Tabel service_items
cur.execute("""
CREATE TABLE IF NOT EXISTS service_items (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    default_price REAL NOT NULL,
    default_features TEXT NOT NULL
)
""")
print("+ tabel service_items ready")

# Tabel proposal_analytics
cur.execute("""
CREATE TABLE IF NOT EXISTS proposal_analytics (
    id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL REFERENCES proposals(id),
    opened_at TEXT NOT NULL,
    last_ping TEXT,
    total_time_seconds INTEGER DEFAULT 0,
    sections_viewed TEXT DEFAULT '[]',
    event VARCHAR(50),
    duration_seconds INTEGER,
    visitor_hash VARCHAR(64),
    source VARCHAR(50),
    metadata_json TEXT
)
""")
print("+ tabel proposal_analytics ready")

cur.execute("""
CREATE TABLE IF NOT EXISTS report_snapshots (
    id TEXT PRIMARY KEY,
    report_type TEXT NOT NULL DEFAULT 'monthly',
    target_type TEXT NOT NULL DEFAULT 'project',
    target_id TEXT,
    project_id TEXT,
    lead_id INTEGER,
    service_type TEXT,
    title TEXT NOT NULL,
    period_start TEXT,
    period_end TEXT,
    month_number INTEGER,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    evidence_json TEXT NOT NULL DEFAULT '{}',
    narrative_json TEXT NOT NULL DEFAULT '{}',
    public_slug TEXT UNIQUE,
    public_enabled BOOLEAN NOT NULL DEFAULT 1,
    open_count INTEGER NOT NULL DEFAULT 0,
    first_viewed_at TEXT,
    last_viewed_at TEXT,
    max_duration_seconds INTEGER NOT NULL DEFAULT 0,
    generated_document_id TEXT,
    status TEXT NOT NULL DEFAULT 'Draft',
    finalized_at TEXT,
    finalized_by TEXT,
    generated_invoice_id TEXT,
    generated_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_report_snapshots_project_id ON report_snapshots(project_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_report_snapshots_lead_id ON report_snapshots(lead_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_report_snapshots_slug ON report_snapshots(public_slug)")
# Idempotent ALTER untuk DB dev lama (CREATE TABLE IF NOT EXISTS di atas tak
# menambah kolom baru ke tabel yang sudah ada). Report-triggered invoice +
# fondasi status draft/final (FIX#4 status, plan report->invoice sisanya).
cur.execute("PRAGMA table_info(report_snapshots)")
_rs_cols = {row[1] for row in cur.fetchall()}
for _col, _ddl in [
    ("status", "ALTER TABLE report_snapshots ADD COLUMN status TEXT NOT NULL DEFAULT 'Draft'"),
    ("finalized_at", "ALTER TABLE report_snapshots ADD COLUMN finalized_at TEXT"),
    ("finalized_by", "ALTER TABLE report_snapshots ADD COLUMN finalized_by TEXT"),
    ("generated_invoice_id", "ALTER TABLE report_snapshots ADD COLUMN generated_invoice_id TEXT"),
]:
    if _rs_cols and _col not in _rs_cols:
        cur.execute(_ddl)
        print(f"+ report_snapshots.{_col} ditambahkan")
    elif _rs_cols:
        print(f"= report_snapshots.{_col} sudah ada, skip")
print("+ tabel report_snapshots ready")

cur.execute("""
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token_hash TEXT UNIQUE NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_user_id ON password_reset_tokens(user_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_expires_at ON password_reset_tokens(expires_at)")
print("+ tabel password_reset_tokens ready")

# project_riwayat: timeline per project
cur.execute("""
CREATE TABLE IF NOT EXISTS project_riwayat (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    actor TEXT NOT NULL,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    attachments TEXT
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_project_riwayat_project_id ON project_riwayat(project_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_project_riwayat_timestamp ON project_riwayat(timestamp)")
print("+ tabel project_riwayat ready")

# Opsi B (product-driven) Tahap 1 — schema only (dev SQLite).
# 1) projects.product_id (nullable). SQLite tak enforce FK by default; definisi
#    FK ada di model SQLAlchemy untuk DB fresh. ALTER hanya menambah kolom.
# 2) tabel baru project_addons.
cur.execute("PRAGMA table_info(projects)")
_proj_cols = {row[1] for row in cur.fetchall()}
if _proj_cols and "product_id" not in _proj_cols:
    cur.execute("ALTER TABLE projects ADD COLUMN product_id TEXT")
    print("+ projects.product_id ditambahkan")
elif _proj_cols:
    print("= projects.product_id sudah ada, skip")
cur.execute("CREATE INDEX IF NOT EXISTS idx_projects_product_id ON projects(product_id)")

# project_addons: add-on line items per project (Opsi B)
cur.execute("""
CREATE TABLE IF NOT EXISTS project_addons (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    product_id TEXT REFERENCES products(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL DEFAULT 0,
    quantity INTEGER NOT NULL DEFAULT 1,
    is_recurring INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
)
""")
cur.execute("CREATE INDEX IF NOT EXISTS idx_project_addons_project_id ON project_addons(project_id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_project_addons_product_id ON project_addons(product_id)")
print("+ tabel project_addons ready")

# Add event column if missing
cur.execute("PRAGMA table_info(proposal_analytics)")
pa_cols = {row[1] for row in cur.fetchall()}
if "event" not in pa_cols:
    cur.execute("ALTER TABLE proposal_analytics ADD COLUMN event VARCHAR(50)")
    print("+ kolom event ditambahkan ke proposal_analytics")
else:
    print("= proposal_analytics.event sudah ada, skip")

conn.commit()

# ---------------------------------------------------------------------------
# Migrasi client_credentials: kolom lama -> kolom fields (JSON key-value)
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(client_credentials)")
cred_cols = {row[1] for row in cur.fetchall()}

if "fields" not in cred_cols and "username" in cred_cols:
    import json as _json
    from cryptography.fernet import Fernet as _Fernet
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()
    _key = os.getenv("SECRET_ENCRYPTION_KEY", "")

    # Backup existing data
    cur.execute("SELECT id, lead_id, category, title, username, encrypted_password, login_url, created_at FROM client_credentials")
    old_creds = cur.fetchall()
    cur.execute("DROP TABLE client_credentials")
    print("- tabel client_credentials lama di-drop")

    cur.execute("""
    CREATE TABLE client_credentials (
        id TEXT PRIMARY KEY,
        lead_id INTEGER REFERENCES leads(id),
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        fields TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL
    )
    """)
    print("+ tabel client_credentials baru dibuat (key-value fields)")

    # Migrate old data
    for row in old_creds:
        old_id, lead_id, category, title, username, encrypted_password, login_url, created_at = row
        fields = []
        if username:
            fields.append({"key": "Username", "value": username, "is_secret": False})
        if encrypted_password:
            fields.append({"key": "Password", "value": encrypted_password, "is_secret": True})
        if login_url:
            fields.append({"key": "Login URL", "value": login_url, "is_secret": False})
        cur.execute(
            "INSERT INTO client_credentials (id, lead_id, category, title, fields, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (old_id, lead_id, category, title, _json.dumps(fields), created_at or "")
        )
    if old_creds:
        print(f"  migrated {len(old_creds)} existing credentials")

    conn.commit()
elif "fields" in cred_cols:
    print("= client_credentials sudah format key-value, skip")
else:
    print("= client_credentials belum ada, akan dibuat oleh SQLAlchemy")

# ---------------------------------------------------------------------------
# Migrasi blast_campaigns: tambah kolom baru
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(blast_campaigns)")
blast_cols = {row[1] for row in cur.fetchall()}

if blast_cols:
    if "total_operational_cost_idr" not in blast_cols:
        cur.execute("ALTER TABLE blast_campaigns ADD COLUMN total_operational_cost_idr REAL DEFAULT 0")
        print("+ kolom total_operational_cost_idr ditambahkan ke blast_campaigns")
    else:
        print("= total_operational_cost_idr sudah ada, skip")

    if "converted_clients_count" not in blast_cols:
        cur.execute("ALTER TABLE blast_campaigns ADD COLUMN converted_clients_count INTEGER DEFAULT 0")
        print("+ kolom converted_clients_count ditambahkan ke blast_campaigns")
    else:
        print("= converted_clients_count sudah ada, skip")

    conn.commit()
else:
    print("= blast_campaigns belum ada, akan dibuat oleh SQLAlchemy")

# ---------------------------------------------------------------------------
# Tabel provider_configs
# ---------------------------------------------------------------------------
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='provider_configs'")
if not cur.fetchone():
    cur.execute("""
    CREATE TABLE provider_configs (
        id TEXT PRIMARY KEY,
        provider_name TEXT NOT NULL,
        remaining_quota REAL DEFAULT 0,
        price_per_unit_idr REAL DEFAULT 0,
        price_input_token_usd REAL DEFAULT 0,
        price_output_token_usd REAL DEFAULT 0
    )
    """)
    cur.execute("INSERT INTO provider_configs VALUES ('FONNTE', 'Fonnte WhatsApp', 10000, 6.6, 0, 0)")
    cur.execute("INSERT INTO provider_configs VALUES ('9ROUTER', '9router AI', 0, 0, 0, 0)")
    conn.commit()
    print("+ tabel provider_configs dibuat dengan seed data")
else:
    print("= provider_configs sudah ada, skip")

# ---------------------------------------------------------------------------
# Migrasi proposals: tambah kolom slug
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(proposals)")
proposal_cols_2 = {row[1] for row in cur.fetchall()}

if "slug" not in proposal_cols_2:
    cur.execute("ALTER TABLE proposals ADD COLUMN slug TEXT")
    print("+ kolom slug ditambahkan ke proposals")
else:
    print("= slug sudah ada di proposals, skip")

if "base_price" not in proposal_cols_2:
    cur.execute("ALTER TABLE proposals ADD COLUMN base_price REAL")
    print("+ kolom base_price ditambahkan ke proposals")
else:
    print("= base_price sudah ada, skip")

if "discount_price" not in proposal_cols_2:
    cur.execute("ALTER TABLE proposals ADD COLUMN discount_price REAL")
    print("+ kolom discount_price ditambahkan ke proposals")
else:
    print("= discount_price sudah ada, skip")

if "discount_expires_at" not in proposal_cols_2:
    cur.execute("ALTER TABLE proposals ADD COLUMN discount_expires_at TEXT")
    print("+ kolom discount_expires_at ditambahkan ke proposals")
else:
    print("= discount_expires_at sudah ada, skip")

if "first_viewed_at" not in proposal_cols_2:
    cur.execute("ALTER TABLE proposals ADD COLUMN first_viewed_at TEXT")
    print("+ kolom first_viewed_at ditambahkan ke proposals")
else:
    print("= first_viewed_at sudah ada di proposals, skip")

if "faqs" not in proposal_cols_2:
    cur.execute("ALTER TABLE proposals ADD COLUMN faqs TEXT")
    print("+ kolom faqs ditambahkan ke proposals")
else:
    print("= faqs sudah ada di proposals, skip")

if "selected_addons" not in proposal_cols_2:
    cur.execute("ALTER TABLE proposals ADD COLUMN selected_addons TEXT DEFAULT '[]'")
    print("+ kolom selected_addons ditambahkan ke proposals")
else:
    print("= selected_addons sudah ada di proposals, skip")

if "timeline_data" not in proposal_cols_2:
    cur.execute("ALTER TABLE proposals ADD COLUMN timeline_data TEXT")
    print("+ kolom timeline_data ditambahkan ke proposals")
else:
    print("= timeline_data sudah ada di proposals, skip")

if "accepted_at" not in proposal_cols_2:
    cur.execute("ALTER TABLE proposals ADD COLUMN accepted_at VARCHAR(255)")
    print("+ kolom accepted_at ditambahkan ke proposals")
else:
    print("= accepted_at sudah ada di proposals, skip")

if "rejected_at" not in proposal_cols_2:
    cur.execute("ALTER TABLE proposals ADD COLUMN rejected_at VARCHAR(255)")
    print("+ kolom rejected_at ditambahkan ke proposals")
else:
    print("= rejected_at sudah ada di proposals, skip")

for col, ddl in [
    ("report_open_count", "ALTER TABLE proposals ADD COLUMN report_open_count INTEGER NOT NULL DEFAULT 0"),
    ("last_report_viewed_at", "ALTER TABLE proposals ADD COLUMN last_report_viewed_at VARCHAR(255)"),
    ("max_report_duration_seconds", "ALTER TABLE proposals ADD COLUMN max_report_duration_seconds INTEGER NOT NULL DEFAULT 0"),
]:
    if col not in proposal_cols_2:
        cur.execute(ddl)
        print(f"+ kolom {col} ditambahkan ke proposals")
    else:
        print(f"= proposals.{col} sudah ada, skip")

# ---------------------------------------------------------------------------
# Migrasi leads: tambah kolom lead_score
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(leads)")
lead_cols_2 = {row[1] for row in cur.fetchall()}

if "lead_score" not in lead_cols_2:
    cur.execute("ALTER TABLE leads ADD COLUMN lead_score INTEGER DEFAULT 0")
    print("+ kolom lead_score ditambahkan ke leads")
else:
    print("= lead_score sudah ada di leads, skip")

if "last_followup_at" not in lead_cols_2:
    cur.execute("ALTER TABLE leads ADD COLUMN last_followup_at VARCHAR(255)")
    print("+ kolom last_followup_at ditambahkan ke leads")
else:
    print("= leads.last_followup_at sudah ada, skip")

conn.commit()

# ---------------------------------------------------------------------------
# Migrasi proposal_analytics: duration_seconds
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(proposal_analytics)")
pa_cols2 = {row[1] for row in cur.fetchall()}
if "duration_seconds" not in pa_cols2:
    cur.execute("ALTER TABLE proposal_analytics ADD COLUMN duration_seconds INTEGER")
    print("+ kolom duration_seconds ditambahkan ke proposal_analytics")
else:
    print("= proposal_analytics.duration_seconds sudah ada, skip")

for col, ddl in [
    ("visitor_hash", "ALTER TABLE proposal_analytics ADD COLUMN visitor_hash VARCHAR(64)"),
    ("source", "ALTER TABLE proposal_analytics ADD COLUMN source VARCHAR(50)"),
    ("metadata_json", "ALTER TABLE proposal_analytics ADD COLUMN metadata_json TEXT"),
]:
    if col not in pa_cols2:
        cur.execute(ddl)
        print(f"+ kolom {col} ditambahkan ke proposal_analytics")
    else:
        print(f"= proposal_analytics.{col} sudah ada, skip")

conn.commit()

# ---------------------------------------------------------------------------
# Migrasi projects: lead_id nullable + tambah kolom color + is_archived
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(projects)")
proj_info = cur.fetchall()
proj_cols = {row[1]: row for row in proj_info}

need_rebuild = proj_cols.get("lead_id") and proj_cols["lead_id"][3] == 1  # notnull=1
has_proj_color = "color" in proj_cols

if need_rebuild or not has_proj_color:
    cur.execute("PRAGMA foreign_keys = OFF")
    cur.execute("ALTER TABLE projects RENAME TO projects_old")
    cur.execute("""
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            lead_id INTEGER REFERENCES leads(id),
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            nominal REAL NOT NULL DEFAULT 0,
            start_date TEXT,
            end_date TEXT,
            color TEXT DEFAULT 'gray',
            dp_percent REAL,
            monthly_invoice_enabled INTEGER NOT NULL DEFAULT 0,
            next_invoice_date TEXT,
            completed_at TEXT
        )
    """)
    cur.execute("""
        INSERT INTO projects (id, lead_id, name, type, status, nominal, start_date, end_date)
        SELECT id, lead_id, name, type, status, nominal, start_date, end_date
        FROM projects_old
    """)
    cur.execute("DROP TABLE projects_old")
    cur.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    print("+ projects direbuild: lead_id nullable, kolom color ditambahkan")
else:
    print("= projects lead_id dan color sudah up-to-date, skip")

# Tambah is_archived ke projects jika belum ada (terpisah dari rebuild)
cur.execute("PRAGMA table_info(projects)")
proj_cols_now = {row[1] for row in cur.fetchall()}
if proj_cols_now and "is_archived" not in proj_cols_now:
    cur.execute("ALTER TABLE projects ADD COLUMN is_archived INTEGER DEFAULT 0")
    conn.commit()
    print("+ kolom is_archived ditambahkan ke projects")
elif proj_cols_now:
    print("= projects.is_archived sudah ada, skip")

cur.execute("PRAGMA table_info(projects)")
proj_cols_billing = {row[1] for row in cur.fetchall()}
for col, ddl in [
    ("dp_percent", "ALTER TABLE projects ADD COLUMN dp_percent REAL"),
    ("monthly_invoice_enabled", "ALTER TABLE projects ADD COLUMN monthly_invoice_enabled INTEGER NOT NULL DEFAULT 0"),
    ("next_invoice_date", "ALTER TABLE projects ADD COLUMN next_invoice_date TEXT"),
    ("completed_at", "ALTER TABLE projects ADD COLUMN completed_at TEXT"),
    ("proposal_id", "ALTER TABLE projects ADD COLUMN proposal_id TEXT"),
]:
    if col not in proj_cols_billing:
        cur.execute(ddl)
        print(f"+ projects.{col} ditambahkan")
    else:
        print(f"= projects.{col} sudah ada, skip")
conn.commit()

# P0-1: UNIQUE index proposal_id -> satu proposal maksimal satu project.
# Partial index (WHERE proposal_id IS NOT NULL) supaya row lama (proposal_id NULL)
# tidak bentrok.
try:
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_projects_proposal_id "
        "ON projects(proposal_id) WHERE proposal_id IS NOT NULL"
    )
    conn.commit()
    print("+ unique index ux_projects_proposal_id dipastikan ada")
except Exception as _e:
    print(f"= skip unique index projects.proposal_id: {_e}")

# ---------------------------------------------------------------------------
# Migrasi board_columns: tambah kolom color
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(board_columns)")
bcol_cols = {row[1] for row in cur.fetchall()}

if bcol_cols:
    if "color" not in bcol_cols:
        cur.execute("ALTER TABLE board_columns ADD COLUMN color TEXT DEFAULT 'gray'")
        print("+ kolom color ditambahkan ke board_columns")
    else:
        print("= board_columns.color sudah ada, skip")
else:
    print("= board_columns belum ada, akan dibuat oleh SQLAlchemy")

# ---------------------------------------------------------------------------
# Migrasi board_cards: tambah lead_id dan color
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(board_cards)")
card_cols = {row[1] for row in cur.fetchall()}

if card_cols:
    if "lead_id" not in card_cols:
        cur.execute("ALTER TABLE board_cards ADD COLUMN lead_id INTEGER REFERENCES leads(id)")
        print("+ kolom lead_id ditambahkan ke board_cards")
    else:
        print("= board_cards.lead_id sudah ada, skip")

    if "color" not in card_cols:
        cur.execute("ALTER TABLE board_cards ADD COLUMN color TEXT DEFAULT 'gray'")
        print("+ kolom color ditambahkan ke board_cards")
    else:
        print("= board_cards.color sudah ada, skip")
else:
    print("= board_cards belum ada, akan dibuat oleh SQLAlchemy")

# ---------------------------------------------------------------------------
# Migrasi boards: tambah kolom color
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(boards)")
board_cols = {row[1] for row in cur.fetchall()}

if board_cols:
    if "color" not in board_cols:
        cur.execute("ALTER TABLE boards ADD COLUMN color TEXT DEFAULT 'gray'")
        print("+ kolom color ditambahkan ke boards")
    else:
        print("= boards.color sudah ada, skip")
else:
    print("= boards belum ada, akan dibuat oleh SQLAlchemy")

# ---------------------------------------------------------------------------
# Migrasi board_card_checklists: tambah is_done dan position
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(board_card_checklists)")
checklist_cols = {row[1] for row in cur.fetchall()}

if checklist_cols:
    if "is_done" not in checklist_cols:
        cur.execute("ALTER TABLE board_card_checklists ADD COLUMN is_done INTEGER DEFAULT 0")
        print("+ kolom is_done ditambahkan ke board_card_checklists")
    else:
        print("= board_card_checklists.is_done sudah ada, skip")

    if "position" not in checklist_cols:
        cur.execute("ALTER TABLE board_card_checklists ADD COLUMN position INTEGER DEFAULT 0")
        print("+ kolom position ditambahkan ke board_card_checklists")
    else:
        print("= board_card_checklists.position sudah ada, skip")
else:
    print("= board_card_checklists belum ada, akan dibuat oleh SQLAlchemy")

# ---------------------------------------------------------------------------
# Migrasi board_card_activities: pastikan semua kolom ada
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(board_card_activities)")
activity_cols = {row[1] for row in cur.fetchall()}

if activity_cols:
    if "action" not in activity_cols:
        cur.execute("ALTER TABLE board_card_activities ADD COLUMN action TEXT NOT NULL DEFAULT 'updated'")
        print("+ kolom action ditambahkan ke board_card_activities")
    if "description" not in activity_cols:
        cur.execute("ALTER TABLE board_card_activities ADD COLUMN description TEXT NOT NULL DEFAULT ''")
        print("+ kolom description ditambahkan ke board_card_activities")
    if "actor" not in activity_cols:
        cur.execute("ALTER TABLE board_card_activities ADD COLUMN actor TEXT NOT NULL DEFAULT ''")
        print("+ kolom actor ditambahkan ke board_card_activities")
    print("= board_card_activities kolom dicek")
else:
    print("= board_card_activities belum ada, akan dibuat oleh SQLAlchemy")

# ---------------------------------------------------------------------------
# Migrasi board_cards: pastikan assignee dan lead_id ada
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(board_cards)")
bcard_cols = {row[1] for row in cur.fetchall()}

if bcard_cols:
    if "assignee" not in bcard_cols:
        cur.execute("ALTER TABLE board_cards ADD COLUMN assignee TEXT")
        print("+ kolom assignee ditambahkan ke board_cards")
    if "due_date" not in bcard_cols:
        cur.execute("ALTER TABLE board_cards ADD COLUMN due_date TEXT")
        print("+ kolom due_date ditambahkan ke board_cards")
    if "labels" not in bcard_cols:
        cur.execute("ALTER TABLE board_cards ADD COLUMN labels TEXT")
        print("+ kolom labels ditambahkan ke board_cards")
    if "is_archived" not in bcard_cols:
        cur.execute("ALTER TABLE board_cards ADD COLUMN is_archived INTEGER DEFAULT 0")
        print("+ kolom is_archived ditambahkan ke board_cards")
    if "updated_at" not in bcard_cols:
        cur.execute("ALTER TABLE board_cards ADD COLUMN updated_at TEXT")
        print("+ kolom updated_at ditambahkan ke board_cards")
    print("= board_cards kolom dicek")
else:
    print("= board_cards belum ada, akan dibuat oleh SQLAlchemy")

# ---------------------------------------------------------------------------
# Migrasi board_card_comments: pastikan semua kolom ada
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(board_card_comments)")
comment_cols = {row[1] for row in cur.fetchall()}

if comment_cols:
    if "author" not in comment_cols:
        cur.execute("ALTER TABLE board_card_comments ADD COLUMN author TEXT NOT NULL DEFAULT ''")
        print("+ kolom author ditambahkan ke board_card_comments")
    print("= board_card_comments kolom dicek")
else:
    print("= board_card_comments belum ada, akan dibuat oleh SQLAlchemy")

cur.execute("""
CREATE TABLE IF NOT EXISTS board_card_attachments (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL REFERENCES board_cards(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT,
    uploaded_by TEXT,
    uploaded_at TEXT NOT NULL
)
""")
print("+ tabel board_card_attachments ready")

conn.commit()

# ---------------------------------------------------------------------------
# Content Generator Tables
# ---------------------------------------------------------------------------
cur.execute("""
CREATE TABLE IF NOT EXISTS content_providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tool_type TEXT NOT NULL DEFAULT 'image',
    base_url TEXT NOT NULL,
    api_key TEXT,
    model TEXT NOT NULL,
    extra_params TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
)
""")
print("+ tabel content_providers ready")

cur.execute("""
CREATE TABLE IF NOT EXISTS content_sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL
)
""")
print("+ tabel content_sessions ready")

cur.execute("""
CREATE TABLE IF NOT EXISTS content_generations (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    session_id TEXT REFERENCES content_sessions(id),
    tool_type TEXT NOT NULL,
    input_data TEXT NOT NULL,
    output_data TEXT,
    model_used TEXT,
    provider_name TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    error_msg TEXT,
    created_at TEXT NOT NULL
)
""")
print("+ tabel content_generations ready")

# Add missing columns to content_generations (safe re-run)
existing = {row[1] for row in cur.execute("PRAGMA table_info(content_generations)").fetchall()}
for col, defn in [
    ("session_id", "TEXT REFERENCES content_sessions(id)"),
    ("tool_type", "TEXT NOT NULL DEFAULT 'seo_article'"),
    ("input_data", "TEXT NOT NULL DEFAULT '{}'"),
    ("output_data", "TEXT"),
    ("model_used", "TEXT"),
    ("provider_name", "TEXT"),
    ("status", "TEXT NOT NULL DEFAULT 'done'"),
    ("error_msg", "TEXT"),
]:
    if col not in existing:
        cur.execute(f"ALTER TABLE content_generations ADD COLUMN {col} {defn}")
        print(f"+ content_generations.{col} ditambahkan")
existing = {row[1] for row in cur.execute("PRAGMA table_info(content_generations)").fetchall()}
if {"type", "tool_type"}.issubset(existing):
    cur.execute("UPDATE content_generations SET tool_type = COALESCE(NULLIF(tool_type, ''), type, 'seo_article')")
if {"prompt", "input_data"}.issubset(existing):
    cur.execute("UPDATE content_generations SET input_data = COALESCE(NULLIF(input_data, ''), json_object('prompt', prompt))")
if {"result", "output_data"}.issubset(existing):
    cur.execute("UPDATE content_generations SET output_data = COALESCE(NULLIF(output_data, ''), result)")

conn.commit()

# ---------------------------------------------------------------------------
# Document Folders & Documents Tables
# ---------------------------------------------------------------------------
cur.execute("""
CREATE TABLE IF NOT EXISTS document_folders (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    parent_id TEXT REFERENCES document_folders(id),
    color TEXT NOT NULL DEFAULT '#6B7280',
    created_at TEXT NOT NULL
)
""")
print("+ tabel document_folders ready")

cur.execute("""
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    folder_id TEXT REFERENCES document_folders(id),
    name TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT 'document',
    content TEXT,
    file_size INTEGER,
    title TEXT NOT NULL,
    body TEXT,
    url TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'Draft',
    review_notes TEXT,
    approved_at TEXT,
    rejected_at TEXT,
    sent_at TEXT,
    signed_at TEXT,
    archived_at TEXT,
    source_type TEXT,
    source_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
)
""")
print("+ tabel documents ready")

# Add missing columns to document_folders (safe re-run)
cur.execute("PRAGMA table_info(document_folders)")
df_cols = {row[1] for row in cur.fetchall()}
if df_cols:
    for col, defn in [
        ("parent_id", "TEXT REFERENCES document_folders(id)"),
        ("color", "TEXT NOT NULL DEFAULT '#6B7280'"),
        ("lead_id", "INTEGER REFERENCES leads(id)"),
    ]:
        if col not in df_cols:
            cur.execute(f"ALTER TABLE document_folders ADD COLUMN {col} {defn}")
            print(f"+ document_folders.{col} ditambahkan")

# Add missing columns to documents (safe re-run)

# document_folders.lead_id (client link)
cur.execute("PRAGMA table_info(document_folders)")
_df_cols = {row[1] for row in cur.fetchall()}
if _df_cols and "lead_id" not in _df_cols:
    cur.execute("ALTER TABLE document_folders ADD COLUMN lead_id INTEGER REFERENCES leads(id)")
    print("+ document_folders.lead_id ditambahkan")

cur.execute("PRAGMA table_info(documents)")
doc_cols = {row[1] for row in cur.fetchall()}
if doc_cols:
    for col, defn in [
        ("folder_id", "TEXT REFERENCES document_folders(id)"),
        ("name", "TEXT NOT NULL DEFAULT ''"),
        ("type", "TEXT NOT NULL DEFAULT 'document'"),
        ("content", "TEXT"),
        ("file_size", "INTEGER"),
        ("title", "TEXT NOT NULL DEFAULT ''"),
        ("body", "TEXT"),
        ("url", "TEXT"),
        ("tags", "TEXT NOT NULL DEFAULT '[]'"),
        ("status", "TEXT NOT NULL DEFAULT 'Draft'"),
        ("review_notes", "TEXT"),
        ("approved_at", "TEXT"),
        ("rejected_at", "TEXT"),
        ("sent_at", "TEXT"),
        ("signed_at", "TEXT"),
        ("archived_at", "TEXT"),
        ("source_type", "TEXT"),
        ("source_id", "TEXT"),
        ("updated_at", "TEXT"),
        ("lead_id", "INTEGER REFERENCES leads(id)"),
    ]:
        if col not in doc_cols:
            cur.execute(f"ALTER TABLE documents ADD COLUMN {col} {defn}")
            print(f"+ documents.{col} ditambahkan")
    cur.execute("UPDATE documents SET name = COALESCE(NULLIF(name, ''), title, '') WHERE name = '' OR name IS NULL")
    cur.execute("UPDATE documents SET type = COALESCE(NULLIF(type, ''), CASE WHEN url IS NOT NULL AND url != '' THEN 'link' ELSE 'document' END) WHERE type = '' OR type IS NULL")
    cur.execute("UPDATE documents SET content = COALESCE(content, body) WHERE content IS NULL AND body IS NOT NULL")

# ---------------------------------------------------------------------------
# Migrasi scrape_history: tambah batch_name
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(scrape_history)")
sh_cols = {row[1] for row in cur.fetchall()}
if sh_cols and "batch_name" not in sh_cols:
    cur.execute("ALTER TABLE scrape_history ADD COLUMN batch_name TEXT")
    print("+ kolom batch_name ditambahkan ke scrape_history")
elif sh_cols:
    print("= scrape_history.batch_name sudah ada, skip")

# ---------------------------------------------------------------------------
# Migrasi users: tambah role
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(users)")
users_cols = {row[1] for row in cur.fetchall()}
if users_cols and "role" not in users_cols:
    cur.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'admin'")
    print("+ kolom role ditambahkan ke users")
elif users_cols:
    print("= users.role sudah ada, skip")

# ---------------------------------------------------------------------------
# Migrasi users: tambah token_version
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(users)")
users_cols = {row[1] for row in cur.fetchall()}
if users_cols and "token_version" not in users_cols:
    cur.execute("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 1")
    print("+ kolom token_version ditambahkan ke users")
elif users_cols:
    print("= users.token_version sudah ada, skip")

conn.commit()

# ---------------------------------------------------------------------------
# Migrasi: brand_kits + brand_assets tables
# ---------------------------------------------------------------------------
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='brand_kits'")
if not cur.fetchone():
    cur.execute("""
        CREATE TABLE brand_kits (
            id VARCHAR(36) PRIMARY KEY,
            kit_name VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            created_at VARCHAR(255) NOT NULL,
            brand_name VARCHAR(255) NOT NULL DEFAULT '',
            tagline VARCHAR(255) NOT NULL DEFAULT '',
            phone VARCHAR(50) NOT NULL DEFAULT '',
            email VARCHAR(255) NOT NULL DEFAULT '',
            address TEXT,
            logo TEXT
        )
    """)
    print("+ tabel brand_kits dibuat")
else:
    print("= tabel brand_kits sudah ada, skip")

cur.execute("PRAGMA table_info(brand_kits)")
brand_kit_cols = {row[1] for row in cur.fetchall()}
brand_kit_migrations = [
    ("brand_name", "ALTER TABLE brand_kits ADD COLUMN brand_name VARCHAR(255) NOT NULL DEFAULT ''"),
    ("tagline", "ALTER TABLE brand_kits ADD COLUMN tagline VARCHAR(255) NOT NULL DEFAULT ''"),
    ("phone", "ALTER TABLE brand_kits ADD COLUMN phone VARCHAR(50) NOT NULL DEFAULT ''"),
    ("email", "ALTER TABLE brand_kits ADD COLUMN email VARCHAR(255) NOT NULL DEFAULT ''"),
    ("address", "ALTER TABLE brand_kits ADD COLUMN address TEXT"),
    ("logo", "ALTER TABLE brand_kits ADD COLUMN logo TEXT"),
]
for col_name, sql in brand_kit_migrations:
    if col_name not in brand_kit_cols:
        cur.execute(sql)
        print(f"+ kolom brand_kits.{col_name} ditambahkan")
    else:
        print(f"= brand_kits.{col_name} sudah ada, skip")
cur.execute("UPDATE brand_kits SET brand_name = kit_name WHERE (brand_name IS NULL OR brand_name = '') AND kit_name IS NOT NULL")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='brand_assets'")
if not cur.fetchone():
    cur.execute("""
        CREATE TABLE brand_assets (
            id VARCHAR(36) PRIMARY KEY,
            kit_id VARCHAR(36) NOT NULL REFERENCES brand_kits(id),
            asset_type VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            value TEXT,
            file_url VARCHAR(500),
            position INTEGER DEFAULT 0,
            asset_metadata TEXT
        )
    """)
    print("+ tabel brand_assets dibuat")
else:
    print("= tabel brand_assets sudah ada, skip")

conn.commit()

# Seed default brand kit
cur.execute("SELECT id FROM brand_kits LIMIT 1")
if not cur.fetchone():
    import uuid as _uuid
    kit_id = str(_uuid.uuid4())
    cur.execute(
        "INSERT INTO brand_kits (id, kit_name, is_active, created_at, brand_name, tagline, phone, email, address, logo) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)",
        (kit_id, "Kantor Teman", "2026-05-26T00:00:00+00:00", "Kantor Teman", "Partner digital bisnis Anda", "", "", "", ""),
    )
    default_assets = [
        (str(_uuid.uuid4()), kit_id, "color", "Optimism Yellow", "#f5a700", None, 0, None),
        (str(_uuid.uuid4()), kit_id, "color", "Dark Charcoal", "#242423", None, 1, None),
        (str(_uuid.uuid4()), kit_id, "color", "Pure Snow", "#fcfaf7", None, 2, None),
        (str(_uuid.uuid4()), kit_id, "font", "Heading Font", "Fredoka", None, 0, '{"weight":"700","fallback":"sans-serif"}'),
        (str(_uuid.uuid4()), kit_id, "font", "Body Font", "Poppins", None, 1, '{"weight":"400","fallback":"sans-serif"}'),
        (str(_uuid.uuid4()), kit_id, "tagline", "Tagline", "Sahabat Digital, UMKM Makin Maju.", None, 0, None),
    ]
    cur.executemany("INSERT INTO brand_assets (id, kit_id, asset_type, name, value, file_url, position, asset_metadata) VALUES (?,?,?,?,?,?,?,?)", default_assets)
    conn.commit()
    print(f"+ seed brand kit 'Teman UMKM Kita' + {len(default_assets)} assets")
else:
    print("= brand kit sudah ada, skip seed")

# ---------------------------------------------------------------------------
# Migrasi: document_templates + generated_documents tables
# ---------------------------------------------------------------------------
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_templates'")
if not cur.fetchone():
    cur.execute("""
        CREATE TABLE document_templates (
            id VARCHAR(36) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(50) NOT NULL,
            html_template TEXT NOT NULL,
            variables TEXT DEFAULT '[]',
            is_active BOOLEAN DEFAULT 1,
            created_at VARCHAR(255) NOT NULL
        )
    """)
    print("+ tabel document_templates dibuat")
else:
    print("= tabel document_templates sudah ada, skip")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='generated_documents'")
if not cur.fetchone():
    cur.execute("""
        CREATE TABLE generated_documents (
            id VARCHAR(36) PRIMARY KEY,
            template_id VARCHAR(36) REFERENCES document_templates(id),
            template_name VARCHAR(255),
            target_type VARCHAR(50),
            target_id VARCHAR(255),
            variables_used TEXT,
            file_url VARCHAR(500),
            display_filename VARCHAR(500),
            status VARCHAR(50) NOT NULL DEFAULT 'Draft',
            payment_status VARCHAR(50),
            review_notes TEXT,
            approved_at VARCHAR(255),
            rejected_at VARCHAR(255),
            sent_at VARCHAR(255),
            signed_at VARCHAR(255),
            archived_at VARCHAR(255),
            generated_at VARCHAR(255) NOT NULL,
            generated_by VARCHAR(255)
        )
    """)
    print("+ tabel generated_documents dibuat")
else:
    print("= tabel generated_documents sudah ada, skip")

# Add display_filename to generated_documents
cur.execute("PRAGMA table_info(generated_documents)")
gd_cols = {row[1] for row in cur.fetchall()}
if gd_cols and "display_filename" not in gd_cols:
    cur.execute("ALTER TABLE generated_documents ADD COLUMN display_filename VARCHAR(500)")
    print("+ generated_documents.display_filename ditambahkan")
elif gd_cols:
    print("= generated_documents.display_filename sudah ada, skip")

for col, ddl in [
    ("status", "ALTER TABLE generated_documents ADD COLUMN status VARCHAR(50) NOT NULL DEFAULT 'Draft'"),
    ("payment_status", "ALTER TABLE generated_documents ADD COLUMN payment_status VARCHAR(50)"),
    ("review_notes", "ALTER TABLE generated_documents ADD COLUMN review_notes TEXT"),
    ("approved_at", "ALTER TABLE generated_documents ADD COLUMN approved_at VARCHAR(255)"),
    ("rejected_at", "ALTER TABLE generated_documents ADD COLUMN rejected_at VARCHAR(255)"),
    ("sent_at", "ALTER TABLE generated_documents ADD COLUMN sent_at VARCHAR(255)"),
    ("signed_at", "ALTER TABLE generated_documents ADD COLUMN signed_at VARCHAR(255)"),
    ("archived_at", "ALTER TABLE generated_documents ADD COLUMN archived_at VARCHAR(255)"),
]:
    if gd_cols and col not in gd_cols:
        cur.execute(ddl)
        print(f"+ generated_documents.{col} ditambahkan")
    elif gd_cols:
        print(f"= generated_documents.{col} sudah ada, skip")

# document_sequences: per-target per-type counter for filename auto-naming
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_sequences'")
if not cur.fetchone():
    cur.execute("""
        CREATE TABLE document_sequences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id VARCHAR(255) NOT NULL,
            template_type VARCHAR(50) NOT NULL,
            last_seq INTEGER NOT NULL DEFAULT 0
        )
    """)
    cur.execute("CREATE UNIQUE INDEX idx_doc_seq_target_type ON document_sequences(target_id, template_type)")
    print("+ tabel document_sequences dibuat")
else:
    print("= tabel document_sequences sudah ada, skip")

conn.commit()

# Seed default document templates
cur.execute("SELECT COUNT(*) FROM document_templates")
if cur.fetchone()[0] == 0:
    import uuid as _uuid2
    _now = "2026-05-26T00:00:00+00:00"
    _templates = [
        (str(_uuid2.uuid4()), "Invoice", "invoice", """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{font-family:'Poppins',sans-serif;margin:0;padding:40px;color:#242423}
.header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:40px}
.logo{max-height:60px}
.title{font-size:28px;font-weight:700;color:#f5a700;margin:0}
.meta{font-size:12px;color:#666;margin-top:4px}
table{width:100%;border-collapse:collapse;margin:20px 0}
th{background:#f5a700;color:#fff;padding:10px 12px;text-align:left;font-size:12px}
td{padding:10px 12px;border-bottom:1px solid #eee;font-size:13px}
.total-row td{font-weight:700;border-top:2px solid #242423;font-size:15px}
.footer{margin-top:40px;padding-top:20px;border-top:1px solid #eee;font-size:11px;color:#999;text-align:center}
</style></head><body>
<div class="header"><div>{{logo}}<p class="title">INVOICE</p><p class="meta">{{nomor_invoice}}</p></div><div style="text-align:right"><p style="font-weight:600">{{klien}}</p><p class="meta">Tanggal: {{tanggal}}</p><p class="meta">Jatuh Tempo: {{due_date}}</p></div></div>
<table><thead><tr><th>Item</th><th>Qty</th><th>Harga</th><th>Subtotal</th></tr></thead><tbody>{{items_rows}}</tbody><tr class="total-row"><td colspan="3">TOTAL</td><td>{{total}}</td></tr></table>
<div class="footer">Teman UMKM Kita · temanumkmkita.com</div>
</body></html>""", '["nomor_invoice","tanggal","klien","items_rows","total","due_date"]', 1, _now),

        (str(_uuid2.uuid4()), "Proposal Penawaran PDF", "proposal_pdf", """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{font-family:'Poppins',sans-serif;margin:0;padding:40px;color:#242423}
.header{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:3px solid #f5a700;padding-bottom:16px;margin-bottom:30px}
.header-left{text-align:left}
.header-right{text-align:right}
.logo-img{max-height:50px;max-width:150px}
.title{font-size:24px;font-weight:700;color:#f5a700;margin:0}
.nomor{font-size:12px;color:#666;margin-top:4px}
.subtitle{font-size:14px;color:#666;margin-top:4px}
.section{margin:24px 0}
.section h2{font-size:14px;text-transform:uppercase;letter-spacing:1px;color:#f5a700;border-bottom:2px solid #f5a700;padding-bottom:4px}
.from-to{display:flex;gap:20px;margin:24px 0}
.from-box,.to-box{flex:1;background:#fcfaf7;border:1px solid #eee;border-radius:8px;padding:16px}
.box-title{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#f5a700;margin-bottom:8px;font-weight:700}
.box-name{font-weight:700;font-size:15px}
.box-detail{font-size:12px;color:#666;margin-top:4px}
.service{background:#fcfaf7;border:1px solid #eee;border-radius:8px;padding:16px;margin:12px 0}
.service-name{font-weight:700;font-size:15px}
.service-price{color:#f5a700;font-weight:700}
.total{font-size:22px;font-weight:700;color:#f5a700;text-align:right;margin-top:20px}
.validity{font-size:11px;color:#999;text-align:center;margin-top:30px}
.footer{margin-top:40px;text-align:center;font-size:11px;color:#999}
</style></head><body>
<div class="header">
  <div class="header-left">
    <div class="logo-img">{{logo}}</div>
    <p class="title">Proposal Penawaran</p>
    <p class="nomor">No. {{nomor}}</p>
  </div>
  <div class="header-right">
    <p class="subtitle">Tanggal: {{tanggal}}</p>
    <p class="subtitle">Berlaku hingga: {{valid_until}}</p>
  </div>
</div>
<div class="from-to">
  <div class="from-box">
    <div class="box-title">Penyedia Jasa</div>
    <div class="box-name">{{brand_name}}</div>
    <div class="box-detail">{{alamat_perusahaan}}</div>
    <div class="box-detail">{{phone_perusahaan}}</div>
    <div class="box-detail">{{email_perusahaan}}</div>
  </div>
  <div class="to-box">
    <div class="box-title">Disiapkan Untuk</div>
    <div class="box-name">{{klien}}</div>
    <div class="box-detail">{{alamat}}</div>
    <div class="box-detail">{{phone}}</div>
  </div>
</div>
<div class="section"><h2>Layanan</h2>{{services_html}}</div>
<p class="total">Total: {{total}}</p>
<div class="section"><h2>FAQ</h2>{{faqs_html}}</div>
<p class="validity">Berlaku hingga: {{validity}}</p>
<div class="footer">Teman UMKM Kita · temanumkmkita.com<br/>Dokumen ini dibuat secara digital.</div>
</body></html>""", '["nomor","tanggal","valid_until","validity","brand_name","alamat_perusahaan","phone_perusahaan","email_perusahaan","klien","alamat","phone","services_html","total","faqs_html"]', 1, _now),

        (str(_uuid2.uuid4()), "Surat Penawaran Formal", "surat_penawaran", """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{font-family:'Poppins',sans-serif;margin:0;padding:50px;color:#242423;font-size:13px;line-height:1.8}
.kop{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #f5a700;padding-bottom:16px;margin-bottom:30px}
.kop-logo{max-height:50px}
.kop-info{text-align:right;font-size:11px;color:#666}
.nomor{font-size:11px;color:#666;margin-bottom:20px}
.perihal{font-weight:700;margin:16px 0}
.ttd{margin-top:60px}
.ttd-line{border-top:1px solid #242423;width:200px;margin-top:60px;padding-top:4px}
</style></head><body>
<div class="kop"><div>{{logo}}</div><div class="kop-info">Teman UMKM Kita<br>temanumkmkita.com<br>+62 895-0192-5395</div></div>
<p class="nomor">No: {{nomor}}<br>Tanggal: {{tanggal}}</p>
<p>Kepada Yth,<br><strong>{{klien}}</strong></p>
<p class="perihal">Perihal: {{perihal}}</p>
<div>{{body}}</div>
<div class="ttd"><p>Hormat kami,</p><div class="ttd-line">{{ttd}}</div></div>
</body></html>""", '["nomor","tanggal","klien","perihal","body","ttd"]', 1, _now),

        (str(_uuid2.uuid4()), "Kontrak / MoU", "kontrak", """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{font-family:'Poppins',sans-serif;margin:0;padding:50px;color:#242423;font-size:13px;line-height:1.8}
.title{text-align:center;font-size:18px;font-weight:700;text-transform:uppercase;margin-bottom:30px;border-bottom:2px solid #f5a700;padding-bottom:10px}
.section{margin:20px 0}
.section h3{font-size:13px;font-weight:700;color:#f5a700;margin-bottom:8px}
.signatures{display:flex;justify-content:space-between;margin-top:80px}
.sig-box{text-align:center;width:45%}
.sig-line{border-top:1px solid #242423;margin-top:80px;padding-top:4px;font-size:12px}
</style></head><body>
<p class="title">Kontrak Kerja Sama</p>
<div class="section"><h3>Pihak-Pihak</h3>{{parties}}</div>
<div class="section"><h3>Lingkup Pekerjaan</h3>{{scope}}</div>
<div class="section"><h3>Timeline</h3>{{timeline}}</div>
<div class="section"><h3>Ketentuan Pembayaran</h3>{{payment_terms}}</div>
<div class="signatures"><div class="sig-box"><div class="sig-line">Pihak Pertama</div></div><div class="sig-box"><div class="sig-line">Pihak Kedua</div></div></div>
</body></html>""", '["parties","scope","timeline","payment_terms"]', 1, _now),

        (str(_uuid2.uuid4()), "Receipt / Bukti Pembayaran", "invoice", """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body{font-family:'Poppins',sans-serif;margin:0;padding:40px;color:#242423}
.header{text-align:center;margin-bottom:30px}
.title{font-size:22px;font-weight:700;color:#f5a700}
.receipt-box{border:2px solid #f5a700;border-radius:12px;padding:24px;max-width:400px;margin:0 auto}
.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eee;font-size:13px}
.row:last-child{border:none}
.row .label{color:#666}
.row .value{font-weight:600}
.amount{font-size:24px;font-weight:700;color:#f5a700;text-align:center;margin:20px 0}
.footer{text-align:center;margin-top:30px;font-size:11px;color:#999}
</style></head><body>
<div class="header">{{logo}}<p class="title">Bukti Pembayaran</p></div>
<div class="receipt-box">
<div class="row"><span class="label">No. Receipt</span><span class="value">{{nomor}}</span></div>
<div class="row"><span class="label">Klien</span><span class="value">{{klien}}</span></div>
<div class="row"><span class="label">Tanggal</span><span class="value">{{tanggal}}</span></div>
<div class="row"><span class="label">Metode</span><span class="value">{{payment_method}}</span></div>
<p class="amount">{{amount}}</p>
</div>
<div class="footer">Teman UMKM Kita · temanumkmkita.com</div>
</body></html>""", '["nomor","klien","amount","tanggal","payment_method"]', 1, _now),
    ]
    for t in _templates:
        cur.execute("INSERT INTO document_templates (id, name, type, html_template, variables, is_active, created_at) VALUES (?,?,?,?,?,?,?)", t)
    conn.commit()
    print(f"+ seed {len(_templates)} document templates")
else:
    print("= document templates sudah ada, skip seed")

# Upgrade built-in client-facing templates once. Custom templates are untouched.
from document_template_library import DEFAULT_DOCUMENT_TEMPLATES
import json as _json_templates
import uuid as _uuid_templates

_template_version = "client_ready_v5"
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_settings'")
_has_settings = cur.fetchone() is not None
_should_upgrade = True
if _has_settings:
    cur.execute("SELECT value FROM system_settings WHERE key = ?", ("document_templates_version",))
    _row = cur.fetchone()
    _should_upgrade = not _row or _row[0] != _template_version

if _should_upgrade:
    for _template in DEFAULT_DOCUMENT_TEMPLATES:
        cur.execute("SELECT id FROM document_templates WHERE name = ? LIMIT 1", (_template["name"],))
        _existing = cur.fetchone()
        _variables = _json_templates.dumps(_template["variables"])
        if _existing:
            cur.execute(
                "UPDATE document_templates SET type = ?, html_template = ?, variables = ?, is_active = 1 WHERE id = ?",
                (_template["type"], _template["html_template"], _variables, _existing[0]),
            )
        else:
            cur.execute(
                "INSERT INTO document_templates (id, name, type, html_template, variables, is_active, created_at) VALUES (?,?,?,?,?,1,?)",
                (str(_uuid_templates.uuid4()), _template["name"], _template["type"], _template["html_template"], _variables, "2026-06-01T00:00:00+00:00"),
            )
    if _has_settings:
        cur.execute(
            "INSERT INTO system_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("document_templates_version", _template_version),
        )
    conn.commit()
    print("+ built-in document templates upgraded ke client_ready_v5")
else:
    print("= built-in document templates sudah client_ready_v5, skip")

# ---------------------------------------------------------------------------
# Migrasi: blast_messages table
# ---------------------------------------------------------------------------
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='blast_messages'")
if not cur.fetchone():
    cur.execute("""
        CREATE TABLE blast_messages (
            id VARCHAR(36) PRIMARY KEY,
            campaign_id VARCHAR(36) REFERENCES blast_campaigns(id),
            lead_id INTEGER NOT NULL REFERENCES leads(id),
            template_id VARCHAR(36) REFERENCES dynamic_templates(id),
            phone_number VARCHAR(255) NOT NULL,
            sent_at VARCHAR(255) NOT NULL,
            delivered_at VARCHAR(255),
            read_at VARCHAR(255),
            replied_at VARCHAR(255),
            status VARCHAR(50) NOT NULL DEFAULT 'sent',
            error_message TEXT
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_blast_messages_lead_id ON blast_messages(lead_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_blast_messages_template_id ON blast_messages(template_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_blast_messages_phone ON blast_messages(phone_number)")
    print("+ tabel blast_messages dibuat")
else:
    print("= tabel blast_messages sudah ada, skip")

conn.commit()

# ---------------------------------------------------------------------------
# Migrasi: workspace tables
# ---------------------------------------------------------------------------
for tbl, ddl in [
    ("workspace_sheets", """
        CREATE TABLE workspace_sheets (
            id VARCHAR(36) PRIMARY KEY,
            project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            sheet_index INTEGER NOT NULL,
            sheet_label VARCHAR(100) NOT NULL,
            service_type VARCHAR(50),
            month_number INTEGER,
            created_at VARCHAR(255) NOT NULL,
            updated_at VARCHAR(255),
            UNIQUE(project_id, sheet_index)
        )"""),
    ("workspace_columns", """
        CREATE TABLE workspace_columns (
            id VARCHAR(36) PRIMARY KEY,
            sheet_id VARCHAR(36) NOT NULL REFERENCES workspace_sheets(id) ON DELETE CASCADE,
            column_key VARCHAR(100) NOT NULL,
            column_label VARCHAR(100) NOT NULL,
            column_type VARCHAR(30) NOT NULL DEFAULT 'text',
            column_options TEXT,
            column_order INTEGER NOT NULL DEFAULT 0,
            is_system BOOLEAN DEFAULT 0,
            created_at VARCHAR(255) NOT NULL
        )"""),
    ("workspace_rows", """
        CREATE TABLE workspace_rows (
            id VARCHAR(36) PRIMARY KEY,
            sheet_id VARCHAR(36) NOT NULL REFERENCES workspace_sheets(id) ON DELETE CASCADE,
            row_order INTEGER NOT NULL DEFAULT 0,
            board_card_id VARCHAR(36),
            is_template BOOLEAN DEFAULT 1,
            created_at VARCHAR(255) NOT NULL,
            updated_at VARCHAR(255)
        )"""),
    ("workspace_cells", """
        CREATE TABLE workspace_cells (
            id VARCHAR(36) PRIMARY KEY,
            row_id VARCHAR(36) NOT NULL REFERENCES workspace_rows(id) ON DELETE CASCADE,
            column_id VARCHAR(36) NOT NULL REFERENCES workspace_columns(id) ON DELETE CASCADE,
            value_text TEXT,
            value_bool BOOLEAN,
            value_number REAL,
            value_date VARCHAR(50),
            value_json TEXT,
            updated_at VARCHAR(255),
            UNIQUE(row_id, column_id)
        )"""),
    ("workspace_attachments", """
        CREATE TABLE workspace_attachments (
            id VARCHAR(36) PRIMARY KEY,
            row_id VARCHAR(36) NOT NULL REFERENCES workspace_rows(id) ON DELETE CASCADE,
            column_id VARCHAR(36) NOT NULL REFERENCES workspace_columns(id) ON DELETE CASCADE,
            file_path VARCHAR(500) NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_type VARCHAR(100),
            uploaded_at VARCHAR(255) NOT NULL
        )"""),
]:
    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
    if not cur.fetchone():
        cur.execute(ddl)
        print(f"+ tabel {tbl} dibuat")
    else:
        print(f"= tabel {tbl} sudah ada, skip")

conn.commit()

# Alter projects: service_type + contract_months
cur.execute("PRAGMA table_info(projects)")
proj_cols_ws = {row[1] for row in cur.fetchall()}
if "service_type" not in proj_cols_ws:
    cur.execute("ALTER TABLE projects ADD COLUMN service_type VARCHAR(50)")
    print("+ kolom service_type ditambahkan ke projects")
else:
    print("= projects.service_type sudah ada, skip")
if "contract_months" not in proj_cols_ws:
    cur.execute("ALTER TABLE projects ADD COLUMN contract_months INTEGER DEFAULT 1")
    print("+ kolom contract_months ditambahkan ke projects")
else:
    print("= projects.contract_months sudah ada, skip")

conn.commit()

# ---------------------------------------------------------------------------
# Migrasi: notifications table
# ---------------------------------------------------------------------------
cur.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'info',
    target_type VARCHAR(50),
    target_id VARCHAR(255),
    action_url VARCHAR(1000),
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at VARCHAR(255) NOT NULL,
    read_at VARCHAR(255)
)
""")
print("+ tabel notifications ready")

conn.commit()

# ---------------------------------------------------------------------------
# Migrasi ai_proxies: tambah kolom feature (per-feature routing)
# ---------------------------------------------------------------------------
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_proxies'")
if cur.fetchone():
    cur.execute("PRAGMA table_info(ai_proxies)")
    proxy_cols = {row[1] for row in cur.fetchall()}
    if "feature" not in proxy_cols:
        cur.execute("ALTER TABLE ai_proxies ADD COLUMN feature VARCHAR(50)")
        print("+ kolom feature ditambahkan ke ai_proxies")
    else:
        print("= ai_proxies.feature sudah ada, skip")
else:
    print("= ai_proxies belum ada, akan dibuat oleh SQLAlchemy")

conn.commit()

# ---------------------------------------------------------------------------
# Migrasi contacts: tambah kolom lead_id + backfill
# ---------------------------------------------------------------------------
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'")
if cur.fetchone():
    cur.execute("PRAGMA table_info(contacts)")
    contact_cols = {row[1] for row in cur.fetchall()}
    if "lead_id" not in contact_cols:
        cur.execute("ALTER TABLE contacts ADD COLUMN lead_id INTEGER REFERENCES leads(id)")
        print("+ kolom lead_id ditambahkan ke contacts")
    else:
        print("= contacts.lead_id sudah ada, skip")

    # Backfill contacts.lead_id by phone match (normalize to 08xx)
    cur.execute("SELECT id, phone_number FROM contacts WHERE lead_id IS NULL")
    for (contact_id, phone) in cur.fetchall():
        if not phone:
            continue
        digits = ''.join(c for c in phone if c.isdigit())
        if digits.startswith('62'):
            digits = '0' + digits[2:]
        cur.execute(
            "SELECT id FROM leads WHERE phone_number = ? OR REPLACE(REPLACE(REPLACE(phone_number, ' ', ''), '-', ''), '+62', '0') = ?",
            (digits, digits)
        )
        lead_row = cur.fetchone()
        if lead_row:
            cur.execute("UPDATE contacts SET lead_id = ? WHERE id = ?", (lead_row[0], contact_id))
            print(f"  Linked contact {contact_id} -> lead {lead_row[0]}")
    conn.commit()
    print("= contacts.lead_id backfill done")
else:
    print("= contacts belum ada, akan dibuat oleh SQLAlchemy")

# ---------------------------------------------------------------------------
# Migrasi ai_proxies: tambah kolom provider + backfill
# ---------------------------------------------------------------------------
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_proxies'")
if cur.fetchone():
    cur.execute("PRAGMA table_info(ai_proxies)")
    proxy_cols2 = {row[1] for row in cur.fetchall()}
    if "provider" not in proxy_cols2:
        cur.execute("ALTER TABLE ai_proxies ADD COLUMN provider VARCHAR(50) NOT NULL DEFAULT '9router'")
        print("+ kolom provider ditambahkan ke ai_proxies")
    else:
        print("= ai_proxies.provider sudah ada, skip")
    # Backfill NULL/empty/legacy provider
    cur.execute("UPDATE ai_proxies SET provider = '9router' WHERE provider IS NULL OR provider = '' OR provider != '9router'")
    if cur.rowcount > 0:
        print(f"  Set provider=9router untuk {cur.rowcount} rows")
    print("= ai_proxies.provider backfill done")
else:
    print("= ai_proxies belum ada, akan dibuat oleh SQLAlchemy")

# ---------------------------------------------------------------------------
# Migrasi: document drafts, versions, editable columns
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(generated_documents)")
gd_cols = {row[1] for row in cur.fetchall()}
if "edited_html" not in gd_cols:
    cur.execute("ALTER TABLE generated_documents ADD COLUMN edited_html TEXT")
    print("+ kolom edited_html ditambahkan ke generated_documents")
else:
    print("= generated_documents.edited_html sudah ada, skip")

if "is_edited" not in gd_cols:
    cur.execute("ALTER TABLE generated_documents ADD COLUMN is_edited BOOLEAN DEFAULT FALSE")
    print("+ kolom is_edited ditambahkan ke generated_documents")
else:
    print("= generated_documents.is_edited sudah ada, skip")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_drafts'")
if not cur.fetchone():
    cur.execute("""
        CREATE TABLE document_drafts (
            id VARCHAR(36) PRIMARY KEY,
            user_id INTEGER NOT NULL,
            template_id VARCHAR(36),
            template_name VARCHAR(255),
            target_type VARCHAR(50),
            target_id VARCHAR(255),
            variables_json TEXT NOT NULL,
            line_items_json TEXT,
            created_at VARCHAR(255) NOT NULL,
            updated_at VARCHAR(255)
        )
    """)
    print("+ tabel document_drafts dibuat")
else:
    print("= document_drafts sudah ada, skip")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_versions'")
if not cur.fetchone():
    cur.execute("""
        CREATE TABLE document_versions (
            id VARCHAR(36) PRIMARY KEY,
            document_id VARCHAR(36) NOT NULL,
            version_number INTEGER NOT NULL,
            variables_json TEXT,
            html_content TEXT,
            change_summary VARCHAR(500),
            created_at VARCHAR(255) NOT NULL,
            created_by VARCHAR(255)
        )
    """)
    print("+ tabel document_versions dibuat")
else:
    print("= document_versions sudah ada, skip")

conn.commit()

conn.close()
print("Migrasi selesai.")
