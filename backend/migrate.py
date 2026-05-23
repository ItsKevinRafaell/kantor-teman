"""
Migrasi: tambah kolom product_interest, batch_name, dan rating ke tabel leads.
Rebuild tabel proposals untuk multi-service. Tambah tabel service_items.
Jalankan sekali: python migrate.py
"""
import sqlite3, os

# ---------------------------------------------------------------------------
# MySQL Migration (jalan dulu jika production MySQL)
# ---------------------------------------------------------------------------
_db_url = os.getenv("DATABASE_URL", "")
if "mysql" in _db_url:
    import pymysql
    from urllib.parse import urlparse, unquote
    _p = urlparse(_db_url.replace("mysql+pymysql://", "mysql://"))
    _mc = pymysql.connect(
        host=_p.hostname, port=_p.port or 3306,
        user=unquote(_p.username), password=unquote(_p.password),
        database=_p.path.lstrip("/"), charset="utf8mb4",
    )
    _cur = _mc.cursor()

    def _col_exists(table, col):
        _cur.execute(f"SHOW COLUMNS FROM `{table}` LIKE %s", (col,))
        return _cur.fetchone() is not None

    def _table_exists(table):
        _cur.execute("SHOW TABLES LIKE %s", (table,))
        return _cur.fetchone() is not None

    _migrations = [
        # leads
        ("leads", "is_archived", "ALTER TABLE leads ADD COLUMN is_archived TINYINT(1) NOT NULL DEFAULT 0"),
        ("leads", "deleted_at", "ALTER TABLE leads ADD COLUMN deleted_at VARCHAR(255) NULL"),
        ("leads", "lead_score", "ALTER TABLE leads ADD COLUMN lead_score INT NOT NULL DEFAULT 0"),
        ("leads", "website_url", "ALTER TABLE leads ADD COLUMN website_url VARCHAR(2000) NULL"),
        ("leads", "google_rating", "ALTER TABLE leads ADD COLUMN google_rating FLOAT NULL"),
        ("leads", "review_count", "ALTER TABLE leads ADD COLUMN review_count INT NULL"),
        ("leads", "latitude", "ALTER TABLE leads ADD COLUMN latitude FLOAT NULL"),
        ("leads", "longitude", "ALTER TABLE leads ADD COLUMN longitude FLOAT NULL"),
        # projects
        ("projects", "color", "ALTER TABLE projects ADD COLUMN color VARCHAR(20) NOT NULL DEFAULT 'yellow'"),
        ("projects", "is_archived", "ALTER TABLE projects ADD COLUMN is_archived TINYINT(1) NOT NULL DEFAULT 0"),
        ("boards", "color", "ALTER TABLE boards ADD COLUMN color VARCHAR(20) NOT NULL DEFAULT 'yellow'"),
        ("board_columns", "color", "ALTER TABLE board_columns ADD COLUMN color VARCHAR(20) NOT NULL DEFAULT 'yellow'"),
        ("board_cards", "color", "ALTER TABLE board_cards ADD COLUMN color VARCHAR(20) NOT NULL DEFAULT 'yellow'"),
        ("board_cards", "is_archived", "ALTER TABLE board_cards ADD COLUMN is_archived TINYINT(1) NOT NULL DEFAULT 0"),
        ("board_card_comments", "author", "ALTER TABLE board_card_comments ADD COLUMN author TEXT NOT NULL DEFAULT ''"),
        ("document_folders", "parent_id", "ALTER TABLE document_folders ADD COLUMN parent_id VARCHAR(36) NULL"),
        ("document_folders", "color", "ALTER TABLE document_folders ADD COLUMN color VARCHAR(20) NOT NULL DEFAULT '#6B7280'"),
        ("documents", "folder_id", "ALTER TABLE documents ADD COLUMN folder_id VARCHAR(36) NULL"),
        ("documents", "title", "ALTER TABLE documents ADD COLUMN title VARCHAR(500) NOT NULL DEFAULT ''"),
        ("documents", "body", "ALTER TABLE documents ADD COLUMN body LONGTEXT NULL"),
        ("documents", "url", "ALTER TABLE documents ADD COLUMN url VARCHAR(2000) NULL"),
        ("documents", "tags", "ALTER TABLE documents ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'"),
        ("documents", "updated_at", "ALTER TABLE documents ADD COLUMN updated_at VARCHAR(255) NULL"),
    ]

    for table, col, sql in _migrations:
        if not _table_exists(table):
            print(f"= {table} belum ada, skip (akan dibuat SQLAlchemy)")
            continue
        if not _col_exists(table, col):
            _cur.execute(sql)
            print(f"+ MySQL: {table}.{col} ditambahkan")
        else:
            print(f"= MySQL: {table}.{col} sudah ada, skip")

    _mc.commit()
    _mc.close()
    print("MySQL migration selesai.")
    exit(0)

# ---------------------------------------------------------------------------
# SQLite Migration (local dev)
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "leads.db")
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
    sections_viewed TEXT DEFAULT '[]'
)
""")
print("+ tabel proposal_analytics ready")

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
    cur.execute("INSERT INTO provider_configs VALUES ('GEMINI', 'Gemini 2.5 Flash', 0, 0, 0.000075, 0.0003)")
    cur.execute("INSERT INTO provider_configs VALUES ('CLAUDE', 'Claude 4.5 Haiku', 0, 0, 0.00025, 0.0125)")
    cur.execute("INSERT INTO provider_configs VALUES ('OPENAI', 'GPT-5', 0, 0, 0.0025, 0.010)")
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
            color TEXT DEFAULT 'yellow'
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

# ---------------------------------------------------------------------------
# Migrasi board_columns: tambah kolom color
# ---------------------------------------------------------------------------
cur.execute("PRAGMA table_info(board_columns)")
bcol_cols = {row[1] for row in cur.fetchall()}

if bcol_cols:
    if "color" not in bcol_cols:
        cur.execute("ALTER TABLE board_columns ADD COLUMN color TEXT DEFAULT 'yellow'")
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
        cur.execute("ALTER TABLE board_cards ADD COLUMN color TEXT DEFAULT 'yellow'")
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
        cur.execute("ALTER TABLE boards ADD COLUMN color TEXT DEFAULT 'yellow'")
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
    ("model_used", "TEXT"),
    ("provider_name", "TEXT"),
    ("error_msg", "TEXT"),
]:
    if col not in existing:
        cur.execute(f"ALTER TABLE content_generations ADD COLUMN {col} {defn}")
        print(f"+ content_generations.{col} ditambahkan")

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
    title TEXT NOT NULL,
    body TEXT,
    url TEXT,
    tags TEXT NOT NULL DEFAULT '[]',
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
    ]:
        if col not in df_cols:
            cur.execute(f"ALTER TABLE document_folders ADD COLUMN {col} {defn}")
            print(f"+ document_folders.{col} ditambahkan")

# Add missing columns to documents (safe re-run)
cur.execute("PRAGMA table_info(documents)")
doc_cols = {row[1] for row in cur.fetchall()}
if doc_cols:
    for col, defn in [
        ("folder_id", "TEXT REFERENCES document_folders(id)"),
        ("title", "TEXT NOT NULL DEFAULT ''"),
        ("body", "TEXT"),
        ("url", "TEXT"),
        ("tags", "TEXT NOT NULL DEFAULT '[]'"),
        ("updated_at", "TEXT"),
    ]:
        if col not in doc_cols:
            cur.execute(f"ALTER TABLE documents ADD COLUMN {col} {defn}")
            print(f"+ documents.{col} ditambahkan")

conn.commit()
conn.close()
print("Migrasi selesai.")

