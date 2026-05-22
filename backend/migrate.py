"""
Migrasi: tambah kolom product_interest, batch_name, dan rating ke tabel leads.
Rebuild tabel proposals untuk multi-service. Tambah tabel service_items.
Jalankan sekali: python migrate.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "leads.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

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
# Migrasi projects: lead_id nullable + tambah kolom color
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
    print("= projects sudah up-to-date, skip")

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
conn.close()
print("Migrasi selesai.")
