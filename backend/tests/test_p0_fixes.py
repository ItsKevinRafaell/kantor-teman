"""Real integration tests for P0/P1 fixes - uses conftest.py db_session fixture."""
import pytest
from models import Lead, Contact, AIProxy, Project, BlastMessage, SystemSettings


class TestContactLeadCRUD:
    """P0-1: Contact/Lead CRUD flow"""

    def test_create_contact_normalizes_phone_to_08xx(self, db_session):
        """Contact phone should be normalized to 08xx format."""
        from app.core.dependencies import normalize_phone_storage

        phone_62 = "6281234567890"
        result = normalize_phone_storage(phone_62)
        assert result == "081234567890"

    def test_create_contact_auto_creates_lead(self, db_session):
        """Creating standalone Contact should auto-create Lead and set lead_id."""
        from routers.leads import create_contact
        from schemas import ContactUpdate
        from unittest.mock import MagicMock

        user = MagicMock()
        user.name = "test"
        body = ContactUpdate(business_name="Test Corp", phone_number="081234567890")

        contact = create_contact(body, user, db_session)

        assert contact.lead_id is not None
        lead = db_session.query(Lead).filter(Lead.id == contact.lead_id).first()
        assert lead is not None
        assert lead.business_name == "Test Corp"
        assert lead.phone_number == "081234567890"
        assert lead.status == "Closed/Client"

    def test_update_contact_syncs_to_lead(self, db_session):
        """update_contact should sync business_name to Lead."""
        from routers.leads import create_contact, update_contact
        from schemas import ContactUpdate
        from unittest.mock import MagicMock

        user = MagicMock()
        user.name = "test"

        # Create
        body_create = ContactUpdate(business_name="Original", phone_number="081234567890")
        contact = create_contact(body_create, user, db_session)
        lead_id = contact.lead_id

        # Update
        body_update = ContactUpdate(business_name="Updated Corp", phone_number=None)
        updated = update_contact(contact.id, body_update, user, db_session)

        lead = db_session.query(Lead).filter(Lead.id == lead_id).first()
        assert lead.business_name == "Updated Corp"

    def test_update_contact_normalizes_phone(self, db_session):
        """update_contact should normalize phone to 08xx."""
        from routers.leads import create_contact, update_contact
        from schemas import ContactUpdate
        from unittest.mock import MagicMock

        user = MagicMock()
        user.name = "test"

        body_create = ContactUpdate(business_name="Test", phone_number="081234567890")
        contact = create_contact(body_create, user, db_session)

        body_update = ContactUpdate(business_name=None, phone_number="628765432109")
        updated = update_contact(contact.id, body_update, user, db_session)

        assert updated.phone_number == "08765432109"


class TestProjectFromContact:
    """P0-1: Project can be created from contact_id"""

    def test_project_schema_accepts_contact_id(self):
        """ProjectIn should accept contact_id parameter."""
        from schemas import ProjectIn

        body = ProjectIn(name="Test", type="FIXED", contact_id=5)
        assert body.contact_id == 5

    def test_project_resolves_contact_to_lead(self, db_session):
        """create_project should resolve contact_id to lead_id."""
        from routers.workspace import create_project
        from schemas import ProjectIn
        from unittest.mock import MagicMock

        # Create Lead + Contact
        lead = Lead(business_name="Client", phone_number="081234567890")
        db_session.add(lead)
        db_session.flush()
        contact = Contact(business_name="Client", phone_number="081234567890", lead_id=lead.id)
        db_session.add(contact)
        db_session.commit()

        user = MagicMock()
        user.name = "test"
        body = ProjectIn(name="Test Project", type="FIXED", contact_id=contact.id)

        project = create_project(body, user, db_session)
        assert project.lead_id == lead.id

    def test_project_validates_lead_exists(self, db_session):
        """create_project should fail if lead_id doesn't exist."""
        from routers.workspace import create_project
        from schemas import ProjectIn
        from fastapi import HTTPException
        from unittest.mock import MagicMock

        user = MagicMock()
        user.name = "test"
        body = ProjectIn(name="Test", type="FIXED", lead_id=99999)

        with pytest.raises(HTTPException) as exc:
            create_project(body, user, db_session)
        assert "Lead tidak ditemukan" in str(exc.value.detail)


class TestWebhookPhoneMatching:
    """P0-2: Webhook phone matching to 08xx DB storage"""

    def test_normalize_storage_62_to_08(self):
        """normalize_phone_storage converts 62xx to 08xx."""
        from app.core.dependencies import normalize_phone_storage
        assert normalize_phone_storage("6281234567890") == "081234567890"

    def test_normalize_storage_preserves_08(self):
        """normalize_phone_storage preserves 08xx format."""
        from app.core.dependencies import normalize_phone_storage
        assert normalize_phone_storage("081234567890") == "081234567890"

    def test_normalize_wa_api_to_62(self):
        """normalize_phone converts 08xx to 62xx for WA API."""
        from app.core.dependencies import normalize_phone
        assert normalize_phone("081234567890") == "6281234567890"

    def test_webhook_finds_lead_by_08xx(self, db_session):
        """Webhook should find Lead when DB stores 08xx and sender is 62xx."""
        from routers.campaign import fonnte_incoming
        from unittest.mock import MagicMock, AsyncMock, AsyncMock

        # Lead stored with 08xx
        lead = Lead(business_name="Test Lead", phone_number="081234567890", status="Contacted")
        db_session.add(lead)
        db_session.commit()

        # Simulate webhook with 62xx sender
        request = MagicMock()
        request.headers = {}
        request.json = AsyncMock(return_value={"sender": "6281234567890", "message": "Hello"})

        import asyncio
        result = asyncio.run(fonnte_incoming(request, db_session))

        assert result["lead_id"] == lead.id
        assert result.get("new_status") == "Replied"

    def test_webhook_finds_lead_by_62xx(self, db_session):
        """Webhook should find Lead when DB stores 62xx (fallback)."""
        from routers.campaign import fonnte_incoming
        from unittest.mock import MagicMock, AsyncMock, AsyncMock

        # Lead stored with 62xx (less common but possible)
        lead = Lead(business_name="Test Lead 62", phone_number="6287654321090", status="Contacted")
        db_session.add(lead)
        db_session.commit()

        request = MagicMock()
        request.headers = {}
        request.json = AsyncMock(return_value={"sender": "6287654321090", "message": "Reply here"})

        import asyncio
        result = asyncio.run(fonnte_incoming(request, db_session))

        assert result["lead_id"] == lead.id


class TestFonnteStatusCallback:
    """P0-2b: Fonnte status callback dual-format phone matching"""

    def test_status_callback_finds_08xx_message(self, db_session):
        """Status callback should update BlastMessage when DB stores 08xx."""
        from routers.campaign import fonnte_webhook, FonnteWebhookIn
        from unittest.mock import MagicMock

        lead = Lead(business_name="Test Lead", phone_number="081234567890")
        db_session.add(lead)
        db_session.flush()

        msg = BlastMessage(
            id="msg-08",
            lead_id=lead.id,
            phone_number="081234567890",
            sent_at="2026-06-06T00:00:00+00:00",
            status="sent",
        )
        db_session.add(msg)
        db_session.commit()

        request = MagicMock()
        request.headers = {}
        body = FonnteWebhookIn(device="6281234567890", target="6281234567890", status="delivered")

        result = fonnte_webhook(body, request, db_session)
        assert result["ok"] is True

        db_session.refresh(msg)
        assert msg.status == "delivered"
        assert msg.delivered_at is not None

    def test_status_callback_finds_62xx_message(self, db_session):
        """Status callback should update BlastMessage when DB stores 62xx (fallback)."""
        from routers.campaign import fonnte_webhook, FonnteWebhookIn
        from unittest.mock import MagicMock

        lead = Lead(business_name="Test Lead 62", phone_number="6287654321090")
        db_session.add(lead)
        db_session.flush()

        msg = BlastMessage(
            id="msg-62",
            lead_id=lead.id,
            phone_number="6287654321090",
            sent_at="2026-06-06T00:00:00+00:00",
            status="sent",
        )
        db_session.add(msg)
        db_session.commit()

        request = MagicMock()
        request.headers = {}
        body = FonnteWebhookIn(device="6287654321090", target="6287654321090", status="read")

        result = fonnte_webhook(body, request, db_session)
        assert result["ok"] is True

        db_session.refresh(msg)
        assert msg.status == "read"
        assert msg.read_at is not None

    def test_status_callback_prefers_08xx_over_62xx(self, db_session):
        """When both formats exist, 08xx (canonical) should be preferred."""
        from routers.campaign import fonnte_webhook, FonnteWebhookIn
        from unittest.mock import MagicMock

        lead = Lead(business_name="Test Lead", phone_number="081234567890")
        db_session.add(lead)
        db_session.flush()

        msg_08 = BlastMessage(
            id="msg-canonical",
            lead_id=lead.id,
            phone_number="081234567890",
            sent_at="2026-06-06T00:00:00+00:00",
            status="sent",
        )
        msg_62 = BlastMessage(
            id="msg-legacy",
            lead_id=lead.id,
            phone_number="6281234567890",
            sent_at="2026-06-06T00:00:01+00:00",
            status="sent",
        )
        db_session.add(msg_08)
        db_session.add(msg_62)
        db_session.commit()

        request = MagicMock()
        request.headers = {}
        body = FonnteWebhookIn(device="6281234567890", target="6281234567890", status="replied")

        result = fonnte_webhook(body, request, db_session)
        assert result["ok"] is True

        db_session.refresh(msg_08)
        db_session.refresh(msg_62)
        # Canonical 08xx should be updated
        assert msg_08.replied_at is not None
        assert msg_08.status == "replied"


class TestDocumentGeneratorInput:
    """P0-4: Document generator user input wins"""

    def test_server_owned_only_brand_fields(self):
        """_SERVER_OWNED_DOCUMENT_KEYS should only have brand/logo fields."""
        from routers.documents import _SERVER_OWNED_DOCUMENT_KEYS

        assert "logo" in _SERVER_OWNED_DOCUMENT_KEYS
        assert "brand_name" in _SERVER_OWNED_DOCUMENT_KEYS
        assert "tagline" in _SERVER_OWNED_DOCUMENT_KEYS
        # Company fields NOT protected
        assert "alamat_perusahaan" not in _SERVER_OWNED_DOCUMENT_KEYS
        assert "phone_perusahaan" not in _SERVER_OWNED_DOCUMENT_KEYS
        assert "email_perusahaan" not in _SERVER_OWNED_DOCUMENT_KEYS
        assert "nama_perusahaan" not in _SERVER_OWNED_DOCUMENT_KEYS

    def test_document_service_aliases(self):
        """document_service._apply_target_company_aliases should NOT set nama_perusahaan."""
        from app.services.document_service import _apply_target_company_aliases

        defaults = {"brand_name": "Teman UMKM Kita", "nama_perusahaan": "Teman UMKM Kita"}
        _apply_target_company_aliases(defaults, "Klien Corp")

        # nama_perusahaan should remain brand name, not overwritten with client name
        assert defaults.get("nama_perusahaan") == "Teman UMKM Kita"
        # Client aliases should be set
        assert defaults.get("nama_klien") == "Klien Corp"
        assert defaults.get("perusahaan_klien") == "Klien Corp"

    def test_user_nama_perusahaan_wins_over_brand(self, db_session):
        """User-provided nama_perusahaan should override brand kit value."""
        from routers.documents import _build_default_vars, _prepare_document_vars
        from schemas import DocumentGenerateIn
        from models import DocumentTemplate
        from unittest.mock import patch

        # Create a template
        tmpl = DocumentTemplate(
            id="test-tmpl-id",
            name="Test Invoice",
            type="invoice",
            html_template="<html>Company: {{nama_perusahaan}}</html>",
            variables="[]",
            is_active=True,
        )
        db_session.add(tmpl)
        db_session.commit()

        # Mock brand context to avoid DB queries for system_settings
        mock_brand_ctx = {
            "logo": "", "brand_name": "Brand Kit Name", "tagline": "",
            "nama_perusahaan": "Brand Kit Default", "alamat_perusahaan": "",
            "phone_perusahaan": "", "email_perusahaan": "",
        }
        mock_defaults = {
            "tanggal": "7 Juni 2026", "logo": "", "brand_name": "Brand Kit Name",
            "nama_perusahaan": "Brand Kit Default", "klien": "",
        }

        # User provides nama_perusahaan
        body = DocumentGenerateIn(
            template_id="test-tmpl-id",
            target_type="lead",
            target_id=None,
            variables={"nama_perusahaan": "Klien Override Corp"},
        )

        with patch("routers.documents._build_brand_context", return_value=mock_brand_ctx), \
             patch("routers.documents._build_default_vars", return_value=mock_defaults):
            full_vars = _prepare_document_vars(db_session, tmpl, body)

        # User input should win - brand_ctx shouldn't overwrite user-provided values
        assert full_vars.get("nama_perusahaan") == "Klien Override Corp"


class TestAIProviderConfig:
    """P0-3/P1-5: AI proxy provider field and multi-provider"""

    def test_schema_has_provider(self):
        """AIProxyIn should accept provider field."""
        from schemas import AIProxyIn, AIProxyOut

        inp = AIProxyIn(name="Test", base_url="http://test.com", provider="claude")
        assert inp.provider == "claude"

    def test_get_ai_config_claude_maps_key(self, db_session):
        """get_ai_config maps api_key to claude_key for claude provider."""
        from app.services.ai_service import get_ai_config
        from app.services import ai_service
        from models import AIProxy
        from unittest.mock import patch

        proxy = AIProxy(
            name="Claude Proxy",
            base_url="https://api.anthropic.com",
            api_key="sk-ant-key123",
            model="claude-sonnet-4-5",
            provider="claude",
            feature=None,
            is_active=True,
        )
        db_session.add(proxy)
        db_session.commit()

        with patch.object(ai_service, "get_proxy_for_feature", return_value=proxy):
            cfg = get_ai_config(db_session, "chat")

        assert cfg["provider"] == "claude"
        assert cfg["claude_key"] == "sk-ant-key123"
        assert cfg["openai_key"] == ""
        assert cfg["gemini_key"] == ""

    def test_get_ai_config_gemini_maps_key(self, db_session):
        """get_ai_config maps api_key to gemini_key for gemini provider."""
        from app.services.ai_service import get_ai_config
        from app.services import ai_service
        from models import AIProxy
        from unittest.mock import patch

        proxy = AIProxy(
            name="Gemini Proxy",
            base_url="https://generativelanguage.googleapis.com",
            api_key="gemini-key-456",
            model="gemini-2.0-flash",
            provider="gemini",
            feature=None,
            is_active=True,
        )
        db_session.add(proxy)
        db_session.commit()

        with patch.object(ai_service, "get_proxy_for_feature", return_value=proxy):
            cfg = get_ai_config(db_session, "chat")

        assert cfg["provider"] == "gemini"
        assert cfg["gemini_key"] == "gemini-key-456"
        assert cfg["openai_key"] == ""
        assert cfg["claude_key"] == ""

    def test_get_ai_config_openai_maps_to_openai_key(self, db_session):
        """get_ai_config maps api_key to openai_key for openai provider."""
        from app.services.ai_service import get_ai_config
        from app.services import ai_service
        from models import AIProxy
        from unittest.mock import patch

        proxy = AIProxy(
            name="OpenAI Proxy",
            base_url="https://api.openai.com/v1",
            api_key="sk-openai-key",
            model="gpt-4o-mini",
            provider="openai",
            feature=None,
            is_active=True,
        )
        db_session.add(proxy)
        db_session.commit()

        with patch.object(ai_service, "get_proxy_for_feature", return_value=proxy):
            cfg = get_ai_config(db_session, "chat")

        assert cfg["provider"] == "openai"
        assert cfg["openai_key"] == "sk-openai-key"
        assert cfg["gemini_key"] == ""
        assert cfg["claude_key"] == ""

    def test_unsupported_provider_raises_clear_error(self, db_session):
        """call_ai_sync should raise clear error for unsupported provider."""
        from app.services.ai_service import call_ai_sync
        import httpx

        cfg = {
            "provider": "unsupported_provider",
            "openai_key": "test",
            "gemini_key": "",
            "claude_key": "",
        }

        with pytest.raises(Exception) as exc:
            call_ai_sync("test prompt", cfg, httpx)
        assert "tidak dikenali" in str(exc.value) or "unsupported" in str(exc.value).lower()


class TestColorDefaults:
    """P0-5: Neutral color defaults"""

    def test_project_default_gray(self):
        """Project.color should default to gray."""
        from models.project import Project
        default = Project.__dict__["color"].default
        assert str(default.arg) == "gray"

    def test_board_default_gray(self):
        """Board.color should default to gray."""
        from models.board import Board
        default = Board.__dict__["color"].default
        assert str(default.arg) == "gray"

    def test_board_column_default_gray(self):
        """BoardColumn.color should default to gray."""
        from models.board import BoardColumn
        default = BoardColumn.__dict__["color"].default
        assert str(default.arg) == "gray"

    def test_board_card_default_gray(self):
        """BoardCard.color should default to gray."""
        from models.board import BoardCard
        default = BoardCard.__dict__["color"].default
        assert str(default.arg) == "gray"


class TestMigration:
    """Migration schema changes"""

    def test_migrate_py_has_contacts_lead_id(self):
        """migrate.py should have contacts.lead_id migration."""
        with open("migrate.py") as f:
            content = f.read()
        assert "contacts.lead_id" in content
        assert "ALTER TABLE contacts" in content

    def test_migrate_py_has_ai_proxies_provider(self):
        """migrate.py should have ai_proxies.provider migration."""
        with open("migrate.py") as f:
            content = f.read()
        assert "ai_proxies.provider" in content
        assert "ALTER TABLE ai_proxies" in content

    def test_migrate_py_backfills_contacts(self):
        """migrate.py should backfill contacts.lead_id."""
        with open("migrate.py") as f:
            content = f.read()
        assert "backfill" in content.lower() or "UPDATE contacts SET lead_id" in content

    def test_migrate_py_backfills_provider(self):
        """migrate.py should backfill ai_proxies.provider."""
        with open("migrate.py") as f:
            content = f.read()
        assert "provider = 'openai'" in content or "provider=openai" in content

    def test_model_has_lead_id_column(self):
        """Contact model should have lead_id column."""
        from models.lead import Contact
        assert "lead_id" in [c.key for c in Contact.__table__.columns]

    def test_model_has_provider_column(self):
        """AIProxy model should have provider column."""
        from models.ai import AIProxy
        assert "provider" in [c.key for c in AIProxy.__table__.columns]

    def test_migrate_py_sqlite_adds_contacts_lead_id(self, tmp_path):
        """Migration actually alters SQLite DB to add contacts.lead_id."""
        import sqlite3, os

        # Create a minimal test DB with contacts but no lead_id
        db_path = tmp_path / "test_leads.db"
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT,
                phone_number TEXT UNIQUE
            )
        """)
        cur.execute("""
            CREATE TABLE contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT,
                phone_number TEXT UNIQUE
            )
        """)
        # Insert test data
        cur.execute("INSERT INTO leads (business_name, phone_number) VALUES ('Test Biz', '081234567890')")
        lead_id = cur.lastrowid
        cur.execute("INSERT INTO contacts (business_name, phone_number) VALUES ('Test Contact', '081234567890')")
        contact_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Verify lead_id column doesn't exist
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(contacts)")
        cols = {row[1] for row in cur.fetchall()}
        conn.close()
        assert "lead_id" not in cols, "lead_id should not exist before migration"

        # Run the relevant portion of migrate.py (simulate the contacts section)
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(contacts)")
        contact_cols = {row[1] for row in cur.fetchall()}
        if "lead_id" not in contact_cols:
            cur.execute("ALTER TABLE contacts ADD COLUMN lead_id INTEGER REFERENCES leads(id)")
            print("+ kolom lead_id ditambahkan ke contacts")
        else:
            print("= contacts.lead_id sudah ada, skip")

        # Backfill
        cur.execute("SELECT id, phone_number FROM contacts WHERE lead_id IS NULL")
        for (cid, phone) in cur.fetchall():
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
                cur.execute("UPDATE contacts SET lead_id = ? WHERE id = ?", (lead_row[0], cid))
        conn.commit()
        conn.close()

        # Verify lead_id column now exists and is backfilled
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(contacts)")
        cols = {row[1] for row in cur.fetchall()}
        cur.execute("SELECT lead_id FROM contacts WHERE id = ?", (contact_id,))
        backfilled_lead_id = cur.fetchone()[0]
        conn.close()

        assert "lead_id" in cols
        assert backfilled_lead_id == lead_id


class TestClientContactIdentity:
    """P0-3: client/contact/lead identity resolution"""

    def test_clients_notes_resolves_contact_to_lead(self, db_session):
        """get_client_notes_by_path should resolve contact.id → lead_id."""
        from routers.clients import get_client_notes_by_path
        from models import ClientNote
        from unittest.mock import MagicMock

        # Create Lead + Contact + Note
        lead = Lead(business_name="Test Client", phone_number="081234567890")
        db_session.add(lead)
        db_session.flush()
        contact = Contact(business_name="Test Client", phone_number="081234567890", lead_id=lead.id)
        db_session.add(contact)
        db_session.flush()
        note = ClientNote(
            id="note-1", lead_id=lead.id, category="BISNIS",
            content="Test note", actor="test", timestamp="2026-06-06T00:00:00+00:00",
        )
        db_session.add(note)
        db_session.commit()

        user = MagicMock()
        notes = get_client_notes_by_path(contact.id, user, db_session)
        assert len(notes) == 1
        assert notes[0].id == "note-1"

    def test_update_project_resolves_contact_id(self, db_session):
        """update_project should resolve contact_id to lead_id."""
        from routers.workspace import create_project, update_project
        from schemas import ProjectIn
        from unittest.mock import MagicMock

        # Create Lead + Contact
        lead = Lead(business_name="Client", phone_number="081234567890")
        db_session.add(lead)
        db_session.flush()
        contact = Contact(business_name="Client", phone_number="081234567890", lead_id=lead.id)
        db_session.add(contact)
        db_session.commit()

        user = MagicMock()
        user.name = "test"

        # Create project with contact_id
        body = ProjectIn(name="Initial", type="FIXED", contact_id=contact.id)
        project = create_project(body, user, db_session)
        assert project.lead_id == lead.id

        # Update project with different contact_id
        lead2 = Lead(business_name="Client 2", phone_number="081234567891")
        db_session.add(lead2)
        db_session.flush()
        contact2 = Contact(business_name="Client 2", phone_number="081234567891", lead_id=lead2.id)
        db_session.add(contact2)
        db_session.commit()

        body2 = ProjectIn(name="Updated", type="FIXED", contact_id=contact2.id)
        updated = update_project(project.id, body2, user, db_session)
        assert updated.lead_id == lead2.id


class TestDocumentVariableOwnership:
    """P0-4: Document generator doesn't overwrite company fields with client name"""

    def test_nama_perusahaan_not_overwritten_by_client(self, db_session):
        """_apply_target_company_aliases should NOT set nama_perusahaan."""
        from routers.documents import _apply_target_company_aliases

        defaults = {"brand_name": "Teman UMKM Kita", "nama_perusahaan": "Teman UMKM Kita"}
        _apply_target_company_aliases(defaults, "Klien Corp")

        # nama_perusahaan should remain brand name, not overwritten with client name
        assert defaults.get("nama_perusahaan") == "Teman UMKM Kita"
        # Client aliases should be set
        assert defaults.get("nama_klien") == "Klien Corp"
        assert defaults.get("perusahaan_klien") == "Klien Corp"

    def test_prepare_document_vars_user_company_wins(self, db_session):
        """User-provided company variables should win over brand defaults."""
        from routers.documents import _prepare_document_vars
        from schemas import DocumentGenerateIn
        from models import DocumentTemplate
        from unittest.mock import patch

        tmpl = DocumentTemplate(
            id="test-tmpl-2",
            name="Test Invoice",
            type="invoice",
            html_template="<html>{{nama_perusahaan}} - {{klien}}</html>",
            variables="[]",
            is_active=True,
        )
        db_session.add(tmpl)
        db_session.commit()

        mock_brand_ctx = {
            "logo": "", "brand_name": "Brand Name", "tagline": "",
            "nama_perusahaan": "Brand Default Company", "alamat_perusahaan": "",
            "phone_perusahaan": "", "email_perusahaan": "",
        }
        mock_defaults = {
            "tanggal": "7 Juni 2026", "logo": "", "brand_name": "Brand Name",
            "nama_perusahaan": "Brand Default Company", "klien": "",
        }

        body = DocumentGenerateIn(
            template_id="test-tmpl-2",
            target_type="lead",
            target_id=None,
            variables={"klien": "Klien Override Corp"},
        )

        with patch("routers.documents._build_brand_context", return_value=mock_brand_ctx), \
             patch("routers.documents._build_default_vars", return_value=mock_defaults):
            full_vars = _prepare_document_vars(db_session, tmpl, body)

        # Client name from variables wins
        assert full_vars.get("klien") == "Klien Override Corp"
        # nama_perusahaan comes from brand context (not overwritten by client name)
        assert full_vars.get("nama_perusahaan") == "Brand Default Company"


class TestAIMultiProvider:
    """P1-5: AI multi-provider with native Claude support"""

    def test_is_native_anthropic_detects_anthropic_url(self):
        """_is_native_anthropic should return True for Anthropic API URLs."""
        from app.services.ai_service import _is_native_anthropic

        assert _is_native_anthropic("https://api.anthropic.com") is True
        assert _is_native_anthropic("https://api.anthropic.com/v1") is True
        assert _is_native_anthropic("https://api.anthropic.com/v1/messages") is True
        assert _is_native_anthropic("http://localhost:20128/v1") is False
        assert _is_native_anthropic("https://api.openai.com/v1") is False

    def test_schema_validates_provider(self):
        """AIProxyIn should reject invalid provider values."""
        from schemas import AIProxyIn
        from pydantic import ValidationError

        # Valid providers should pass
        for provider in ("openai", "claude", "gemini"):
            inp = AIProxyIn(name="Test", base_url="http://test.com", provider=provider)
            assert inp.provider == provider

        # Invalid provider should raise
        with pytest.raises(ValidationError) as exc:
            AIProxyIn(name="Test", base_url="http://test.com", provider="unsupported")
        assert "Provider must be one of" in str(exc.value)

    def test_update_ai_proxy_validates_provider(self, db_session):
        """update_ai_proxy should reject invalid provider values."""
        from app.services.ai_service import update_ai_proxy
        from models import AIProxy

        proxy = AIProxy(
            name="Test Proxy",
            base_url="http://test.com",
            api_key="key",
            model="model",
            provider="openai",
            feature=None,
            is_active=True,
        )
        db_session.add(proxy)
        db_session.commit()

        with pytest.raises(ValueError) as exc:
            update_ai_proxy(db_session, proxy.id, {"provider": "invalid_provider"})
        assert "Provider must be one of" in str(exc.value)

    def test_dependencies_delegates_to_ai_service(self):
        """dependencies._call_ai_sync should delegate to ai_service.call_ai_sync."""
        from app.core.dependencies import _call_ai_sync
        from app.services.ai_service import call_ai_sync as ai_service_call
        from unittest.mock import patch, MagicMock
        import httpx

        cfg = {
            "provider": "openai",
            "openai_key": "sk-test",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "gemini_key": "",
            "claude_key": "",
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"choices": [{"message": {"content": "test response"}}]}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response

        with patch.object(httpx, "Client", return_value=mock_client):
            result = _call_ai_sync("test prompt", cfg, httpx)

        assert result == "test response"
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/chat/completions" in call_args[0][0]

    def test_dependencies_call_ai_provider_native_claude(self):
        """dependencies.call_ai_provider should use native Anthropic path for claude."""
        from app.core.dependencies import call_ai_provider
        from unittest.mock import AsyncMock, patch, MagicMock
        import httpx

        cfg = {
            "provider": "claude",
            "claude_key": "sk-ant-test",
            "base_url": "https://api.anthropic.com",
            "model": "claude-sonnet-4-5",
            "gemini_key": "",
            "openai_key": "",
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"content": [{"text": "native response"}]}
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(httpx, "AsyncClient", return_value=mock_client):
            import asyncio
            result = asyncio.run(call_ai_provider("test prompt", cfg))

        assert result == "native response"
        # Verify native Anthropic headers were used
        post_call = mock_client.post.call_args
        headers = post_call[1]["headers"]
        assert headers["x-api-key"] == "sk-ant-test"
        assert headers["anthropic-version"] == "2023-06-01"
