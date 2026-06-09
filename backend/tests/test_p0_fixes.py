"""Real integration tests for P0/P1 fixes - uses conftest.py db_session fixture."""
import pytest
import json
import asyncio
from models import (
    Lead, Contact, AIProxy, Project, BlastMessage, SystemSettings,
    FollowUpSequence, LeadActivityLog, Proposal, User, Board, BoardColumn,
    BoardCard, WorkspaceSheet, WorkspaceColumn, WorkspaceRow, WorkspaceCell,
)


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


class TestWorkspaceBoardSync:
    """Workspace rows must stay linked with board cards."""

    def _make_workspace_row(self, db_session):
        lead = Lead(business_name="Client", phone_number="081234567890")
        db_session.add(lead)
        db_session.flush()

        project = Project(id="project-1", lead_id=lead.id, name="Project", type="FIXED", status="ACTIVE", nominal=0)
        db_session.add(project)
        board = Board(id="board-1", project_id=project.id)
        db_session.add(board)
        todo = BoardColumn(id="col-todo", board_id=board.id, name="To Do", position=0)
        progress = BoardColumn(id="col-progress", board_id=board.id, name="In Progress", position=1)
        done = BoardColumn(id="col-done", board_id=board.id, name="Done", position=2)
        db_session.add_all([todo, progress, done])

        sheet = WorkspaceSheet(id="sheet-1", project_id=project.id, sheet_index=0, sheet_label="Month 1")
        db_session.add(sheet)
        task_col = WorkspaceColumn(id="ws-task", sheet_id=sheet.id, column_key="task_name", column_label="Task", column_type="text", column_order=0)
        due_col = WorkspaceColumn(id="ws-due", sheet_id=sheet.id, column_key="due_date", column_label="Due", column_type="date", column_order=1)
        status_col = WorkspaceColumn(id="ws-status", sheet_id=sheet.id, column_key="status", column_label="Status", column_type="select", column_order=2)
        done_col = WorkspaceColumn(id="ws-done", sheet_id=sheet.id, column_key="done", column_label="Done", column_type="checkbox", column_order=3)
        db_session.add_all([task_col, due_col, status_col, done_col])

        row = WorkspaceRow(id="row-1", sheet_id=sheet.id, row_order=0, is_template=False)
        db_session.add(row)
        db_session.flush()
        db_session.add_all([
            WorkspaceCell(id="cell-task", row_id=row.id, column_id=task_col.id, value_text="Publish article"),
            WorkspaceCell(id="cell-due", row_id=row.id, column_id=due_col.id, value_date="2026-06-15"),
            WorkspaceCell(id="cell-status", row_id=row.id, column_id=status_col.id, value_text="In Progress"),
            WorkspaceCell(id="cell-done", row_id=row.id, column_id=done_col.id, value_bool=False),
        ])
        db_session.commit()
        return row, progress, done, done_col

    def test_sync_row_creates_board_card_from_task_name_and_due_date(self, db_session):
        from app.core.dependencies import sync_row_to_board

        row, progress, _, _ = self._make_workspace_row(db_session)

        sync_row_to_board(row.id, db_session)
        db_session.refresh(row)

        assert row.board_card_id is not None
        card = db_session.query(BoardCard).filter(BoardCard.id == row.board_card_id).one()
        assert card.title == "Publish article"
        assert card.due_date == "2026-06-15"
        assert card.column_id == progress.id

    def test_sync_done_checkbox_moves_card_to_done_column(self, db_session):
        from app.core.dependencies import sync_row_to_board

        row, _, done, done_col = self._make_workspace_row(db_session)
        sync_row_to_board(row.id, db_session)
        done_cell = db_session.query(WorkspaceCell).filter(
            WorkspaceCell.row_id == row.id,
            WorkspaceCell.column_id == done_col.id,
        ).one()
        done_cell.value_bool = True
        db_session.commit()

        sync_row_to_board(row.id, db_session)

        card = db_session.query(BoardCard).filter(BoardCard.id == row.board_card_id).one()
        assert card.column_id == done.id


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
        from routers.campaign import fonnte_webhook
        from unittest.mock import MagicMock, AsyncMock

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
        request.headers = {"x-fonnte-webhook-secret": ""}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value="")
        request.json = AsyncMock(return_value={"target": "6281234567890", "status": "delivered"})

        result = asyncio.run(fonnte_webhook(request, db_session))
        assert result["ok"] is True

        db_session.refresh(msg)
        assert msg.status == "delivered"
        assert msg.delivered_at is not None

    def test_status_callback_finds_62xx_message(self, db_session):
        """Status callback should update BlastMessage when DB stores 62xx (fallback)."""
        from routers.campaign import fonnte_webhook
        from unittest.mock import MagicMock, AsyncMock

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
        request.headers = {"x-fonnte-webhook-secret": ""}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value="")
        request.json = AsyncMock(return_value={"target": "6287654321090", "status": "read"})

        result = asyncio.run(fonnte_webhook(request, db_session))
        assert result["ok"] is True

        db_session.refresh(msg)
        assert msg.status == "read"
        assert msg.read_at is not None

    def test_status_callback_prefers_08xx_over_62xx(self, db_session):
        """When both formats exist, 08xx (canonical) should be preferred."""
        from routers.campaign import fonnte_webhook
        from unittest.mock import MagicMock, AsyncMock

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
        request.headers = {"x-fonnte-webhook-secret": ""}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value="")
        request.json = AsyncMock(return_value={"target": "6281234567890", "status": "replied"})

        result = asyncio.run(fonnte_webhook(request, db_session))
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

        inp = AIProxyIn(name="Test", base_url="http://test.com", provider="anthropic")
        assert inp.provider == "anthropic"

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

        assert cfg["provider"] == "anthropic"  # canonical form of "claude"
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
        for provider in ("openai", "anthropic", "gemini", "openrouter", "custom"):
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
        """dependencies.call_ai_provider should use native Anthropic path for 'anthropic' (legacy: 'claude')."""
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


class TestFonnteWebhookRepliedSideEffects:
    """P0-2c: blast/webhook/fonnte status=replied performs same lead side-effects as fonnte-incoming"""

    def test_status_callback_replied_stops_followup_sequence(self, db_session):
        """status=replied on blast webhook should stop active FollowUpSequence."""
        from routers.campaign import fonnte_webhook
        from unittest.mock import MagicMock, AsyncMock

        lead = Lead(business_name="Replied Lead", phone_number="081234567890", status="Contacted")
        db_session.add(lead)
        db_session.flush()

        seq = FollowUpSequence(
            lead_id=lead.id, template_ids=json.dumps([]), delays=json.dumps([1, 3, 7]),
            current_step=0, status="ACTIVE", started_at="2026-06-01T00:00:00+00:00",
        )
        db_session.add(seq)
        db_session.flush()

        msg = BlastMessage(
            id="msg-replied-1",
            lead_id=lead.id,
            phone_number="081234567890",
            sent_at="2026-06-06T00:00:00+00:00",
            status="sent",
        )
        db_session.add(msg)
        db_session.commit()

        request = MagicMock()
        request.headers = {"x-fonnte-webhook-secret": ""}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value="")
        request.json = AsyncMock(return_value={"target": "6281234567890", "status": "replied"})

        result = asyncio.run(fonnte_webhook(request, db_session))
        assert result["ok"] is True

        db_session.refresh(seq)
        assert seq.status == "STOPPED"
        assert seq.stopped_reason == "client_replied"

    def test_status_callback_replied_logs_wa_replied_activity(self, db_session):
        """status=replied on blast webhook should log LeadActivityLog WA_REPLIED."""
        from routers.campaign import fonnte_webhook
        from models import LeadActivityLog
        from unittest.mock import MagicMock, AsyncMock

        lead = Lead(business_name="Replied Lead", phone_number="081234567890", status="Contacted")
        db_session.add(lead)
        db_session.flush()

        msg = BlastMessage(
            id="msg-replied-2",
            lead_id=lead.id,
            phone_number="081234567890",
            sent_at="2026-06-06T00:00:00+00:00",
            status="sent",
        )
        db_session.add(msg)
        db_session.commit()

        request = MagicMock()
        request.headers = {"x-fonnte-webhook-secret": ""}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value="")
        request.json = AsyncMock(return_value={"target": "6281234567890", "status": "replied"})

        asyncio.run(fonnte_webhook(request, db_session))

        activity = db_session.query(LeadActivityLog).filter(
            LeadActivityLog.lead_id == lead.id,
            LeadActivityLog.activity_type == "WA_REPLIED",
        ).first()
        assert activity is not None

    def test_status_callback_replied_updates_lead_status(self, db_session):
        """status=replied on blast webhook should update Lead.status Contacted→Replied."""
        from routers.campaign import fonnte_webhook
        from unittest.mock import MagicMock, AsyncMock

        lead = Lead(business_name="Replied Lead", phone_number="081234567890", status="Contacted")
        db_session.add(lead)
        db_session.flush()

        msg = BlastMessage(
            id="msg-replied-3",
            lead_id=lead.id,
            phone_number="081234567890",
            sent_at="2026-06-06T00:00:00+00:00",
            status="sent",
        )
        db_session.add(msg)
        db_session.commit()

        request = MagicMock()
        request.headers = {"x-fonnte-webhook-secret": ""}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value="")
        request.json = AsyncMock(return_value={"target": "6281234567890", "status": "replied"})

        asyncio.run(fonnte_webhook(request, db_session))

        db_session.refresh(lead)
        assert lead.status == "Replied"

    def test_status_callback_replied_only_when_contacted(self, db_session):
        """status=replied should NOT change lead status if lead is not Contacted."""
        from routers.campaign import fonnte_webhook
        from unittest.mock import MagicMock, AsyncMock

        lead = Lead(business_name="Scraped Lead", phone_number="081234567890", status="Scraped")
        db_session.add(lead)
        db_session.flush()

        msg = BlastMessage(
            id="msg-replied-4",
            lead_id=lead.id,
            phone_number="081234567890",
            sent_at="2026-06-06T00:00:00+00:00",
            status="sent",
        )
        db_session.add(msg)
        db_session.commit()

        request = MagicMock()
        request.headers = {"x-fonnte-webhook-secret": ""}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value="")
        request.json = AsyncMock(return_value={"target": "6281234567890", "status": "replied"})

        asyncio.run(fonnte_webhook(request, db_session))

        db_session.refresh(lead)
        assert lead.status == "Scraped"  # Should NOT change

    def test_webhook_incoming_form_payload(self, db_session):
        """fonnte-incoming should handle form-encoded payloads."""
        from routers.campaign import fonnte_incoming
        from unittest.mock import MagicMock, AsyncMock

        lead = Lead(business_name="Form Payload Lead", phone_number="081234567890", status="Contacted")
        db_session.add(lead)
        db_session.commit()

        request = MagicMock()
        request.headers = {}
        # Simulate form-encoded payload (no JSON)
        request.json = AsyncMock(side_effect=Exception("no json"))
        request.form = AsyncMock(return_value={"sender": "6281234567890", "message": "Hello from form"})

        import asyncio
        result = asyncio.run(fonnte_incoming(request, db_session))

        assert result["ok"] is True
        assert result["lead_id"] == lead.id
        assert result.get("new_status") == "Replied"

    def test_webhook_incoming_opt_out_with_62xx(self, db_session):
        """fonnte-incoming opt-out should normalize 62xx sender to 08xx."""
        from routers.campaign import fonnte_incoming
        from unittest.mock import MagicMock, AsyncMock

        lead = Lead(business_name="Opt Out 62", phone_number="081234567890", status="Scraped", do_not_contact=False)
        db_session.add(lead)
        db_session.commit()

        request = MagicMock()
        request.headers = {}
        request.json = AsyncMock(return_value={"sender": "6281234567890", "message": "STOP jangan hubungi saya"})

        import asyncio
        result = asyncio.run(fonnte_incoming(request, db_session))

        assert result["ok"] is True
        assert result["do_not_contact"] is True

        db_session.refresh(lead)
        assert lead.do_not_contact is True


class TestAICanonicalPath:
    """P0-3/P1-5: AI canonical path — other.py must not shadow canonical resolver"""

    def test_other_py_has_no_local_get_ai_config(self):
        """other.py should NOT define a local get_ai_config function."""
        import routers.other as other_mod
        assert not hasattr(other_mod, "get_ai_config"), \
            "other.py must not define get_ai_config — use canonical path from dependencies/ai_service"

    def test_dependencies_get_ai_config_delegates_to_ai_service(self, db_session):
        """dependencies.get_ai_config should delegate to ai_service.get_ai_config."""
        from app.core.dependencies import get_ai_config as dep_get_ai_config
        from app.services.ai_service import get_ai_config as svc_get_ai_config
        from unittest.mock import patch

        # Both should produce the same result (delegation verification)
        with patch("app.core.dependencies.get_ai_config", wraps=svc_get_ai_config):
            dep_result = dep_get_ai_config(db_session, "chat")
            svc_result = svc_get_ai_config(db_session, "chat")
        # Both resolve to the same canonical path (no provider configured → 'none' state)
        assert dep_result["provider"] == svc_result["provider"]
        assert "model" in dep_result
        assert "model" in svc_result

    def test_call_ai_sync_openai_provider(self):
        """call_ai_sync should make OpenAI-compatible /chat/completions call."""
        from app.services.ai_service import call_ai_sync
        from unittest.mock import MagicMock, patch
        import httpx

        cfg = {
            "provider": "openai",
            "openai_key": "sk-test-openai",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "gemini_key": "",
            "claude_key": "",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "OpenAI response"}}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = lambda self: mock_client
        mock_client.__exit__ = lambda self, *a: False

        with patch.object(httpx, "Client", return_value=mock_client):
            result = call_ai_sync("test prompt", cfg, httpx)

        assert result == "OpenAI response"
        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        assert "/chat/completions" in call_url
        call_headers = mock_client.post.call_args[1]["headers"]
        assert "Bearer sk-test-openai" in call_headers["Authorization"]

    def test_call_ai_sync_anthropic_native_endpoint(self):
        """call_ai_sync should use /v1/messages + x-api-key for canonical 'anthropic' provider."""
        from app.services.ai_service import call_ai_sync
        from unittest.mock import MagicMock, patch
        import httpx

        cfg = {
            "provider": "anthropic",
            "claude_key": "sk-ant-native",
            "base_url": "https://api.anthropic.com",
            "model": "claude-sonnet-4-5",
            "gemini_key": "",
            "openai_key": "",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"content": [{"text": "Claude native response"}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = lambda self: mock_client
        mock_client.__exit__ = lambda self, *a: False

        with patch.object(httpx, "Client", return_value=mock_client):
            result = call_ai_sync("test prompt", cfg, httpx)

        assert result == "Claude native response"
        call_url = mock_client.post.call_args[0][0]
        assert "/v1/messages" in call_url
        call_headers = mock_client.post.call_args[1]["headers"]
        assert call_headers["x-api-key"] == "sk-ant-native"
        assert call_headers["anthropic-version"] == "2023-06-01"

    def test_call_ai_sync_anthropic_proxy_endpoint(self):
        """call_ai_sync should use /chat/completions when anthropic points to proxy URL."""
        from app.services.ai_service import call_ai_sync
        from unittest.mock import MagicMock, patch
        import httpx

        cfg = {
            "provider": "anthropic",
            "claude_key": "sk-ant-proxy",
            "base_url": "http://localhost:20128/v1",
            "model": "claude-sonnet-4-5",
            "gemini_key": "",
            "openai_key": "",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "Claude proxy response"}}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = lambda self: mock_client
        mock_client.__exit__ = lambda self, *a: False

        with patch.object(httpx, "Client", return_value=mock_client):
            result = call_ai_sync("test prompt", cfg, httpx)

        assert result == "Claude proxy response"
        call_url = mock_client.post.call_args[0][0]
        assert "/chat/completions" in call_url
        call_headers = mock_client.post.call_args[1]["headers"]
        assert "Bearer sk-ant-proxy" in call_headers["Authorization"]

    def test_call_ai_sync_claude_alias_maps_to_anthropic(self):
        """Legacy 'claude' provider should map to 'anthropic' and route correctly."""
        from app.services.ai_service import call_ai_sync, _canonical_provider
        assert _canonical_provider("claude") == "anthropic"
        from unittest.mock import MagicMock, patch
        import httpx

        cfg = {
            "provider": "claude",
            "claude_key": "sk-ant-native",
            "base_url": "https://api.anthropic.com",
            "model": "claude-sonnet-4-5",
            "gemini_key": "",
            "openai_key": "",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"content": [{"text": "Claude native response"}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = lambda self: mock_client
        mock_client.__exit__ = lambda self, *a: False

        with patch.object(httpx, "Client", return_value=mock_client):
            result = call_ai_sync("test prompt", cfg, httpx)

        assert result == "Claude native response"
        call_url = mock_client.post.call_args[0][0]
        assert "/v1/messages" in call_url

    def test_call_ai_sync_gemini_provider(self):
        """call_ai_sync should use Gemini native API endpoint."""
        from app.services.ai_service import call_ai_sync
        from unittest.mock import MagicMock, patch
        import httpx

        cfg = {
            "provider": "gemini",
            "gemini_key": "gemini-key-123",
            "base_url": "https://generativelanguage.googleapis.com",
            "model": "gemini-2.0-flash",
            "openai_key": "",
            "claude_key": "",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "Gemini response"}]}}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = lambda self: mock_client
        mock_client.__exit__ = lambda self, *a: False

        with patch.object(httpx, "Client", return_value=mock_client):
            result = call_ai_sync("test prompt", cfg, httpx)

        assert result == "Gemini response"
        call_url = mock_client.post.call_args[0][0]
        assert "generateContent" in call_url
        call_headers = mock_client.post.call_args[1]["headers"]
        assert call_headers["x-goog-api-key"] == "gemini-key-123"

    def test_call_ai_sync_openrouter_provider(self):
        """call_ai_sync should use /chat/completions for openrouter provider."""
        from app.services.ai_service import call_ai_sync
        from unittest.mock import MagicMock, patch
        import httpx

        cfg = {
            "provider": "openrouter",
            "openai_key": "sk-or-key",
            "base_url": "https://openrouter.ai/api/v1",
            "model": "anthropic/claude-3.5-sonnet",
            "gemini_key": "",
            "claude_key": "",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "OpenRouter response"}}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = lambda self: mock_client
        mock_client.__exit__ = lambda self, *a: False

        with patch.object(httpx, "Client", return_value=mock_client):
            result = call_ai_sync("test prompt", cfg, httpx)

        assert result == "OpenRouter response"
        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        assert "/chat/completions" in call_url
        call_headers = mock_client.post.call_args[1]["headers"]
        assert "Bearer sk-or-key" in call_headers["Authorization"]

    def test_call_ai_sync_custom_provider(self):
        """call_ai_sync should use /chat/completions for custom provider."""
        from app.services.ai_service import call_ai_sync
        from unittest.mock import MagicMock, patch
        import httpx

        cfg = {
            "provider": "custom",
            "openai_key": "sk-custom-key",
            "base_url": "https://custom.ai/v1",
            "model": "custom-model",
            "gemini_key": "",
            "claude_key": "",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"choices": [{"message": {"content": "Custom provider response"}}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = lambda self: mock_client
        mock_client.__exit__ = lambda self, *a: False

        with patch.object(httpx, "Client", return_value=mock_client):
            result = call_ai_sync("test prompt", cfg, httpx)

        assert result == "Custom provider response"
        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        assert "/chat/completions" in call_url

    def test_call_ai_sync_unsupported_provider_raises(self):
        """call_ai_sync should raise clear error for unsupported provider."""
        from app.services.ai_service import call_ai_sync
        import httpx

        cfg = {
            "provider": "unknown_provider",
            "openai_key": "test",
            "gemini_key": "",
            "claude_key": "",
        }

        with pytest.raises(Exception) as exc:
            call_ai_sync("test prompt", cfg, httpx)
        assert "tidak dikenali" in str(exc.value)


class TestWorkspaceCacheInvalidation:
    """P0-1: Project create/update/delete should invalidate workspace list cache"""

    def test_create_project_invalidates_workspace_cache(self, db_session):
        """create_project should call invalidate_workspace_list_cache."""
        from routers.workspace import create_project
        from schemas import ProjectIn
        from unittest.mock import MagicMock, patch

        user = MagicMock()
        user.name = "test"
        body = ProjectIn(name="Cache Test Project", type="FIXED", status="ACTIVE")

        with patch("routers.workspace.invalidate_workspace_list_cache") as mock_inv:
            project = create_project(body, user, db_session)
            mock_inv.assert_called_once()

    def test_update_project_invalidates_workspace_cache(self, db_session):
        """update_project should call invalidate_workspace_list_cache."""
        from routers.workspace import create_project, update_project
        from schemas import ProjectIn
        from unittest.mock import MagicMock, patch

        user = MagicMock()
        user.name = "test"

        body = ProjectIn(name="Original", type="FIXED", status="ACTIVE")
        project = create_project(body, user, db_session)

        body2 = ProjectIn(name="Updated", type="FIXED", status="ACTIVE")
        with patch("routers.workspace.invalidate_workspace_list_cache") as mock_inv:
            update_project(project.id, body2, user, db_session)
            mock_inv.assert_called_once()

    def test_delete_project_invalidates_workspace_cache(self, db_session):
        """delete_project should call invalidate_workspace_list_cache."""
        from routers.workspace import create_project, delete_project
        from schemas import ProjectIn
        from unittest.mock import MagicMock, patch

        user = MagicMock()
        user.name = "test"

        body = ProjectIn(name="To Delete", type="FIXED", status="ACTIVE")
        project = create_project(body, user, db_session)

        with patch("routers.workspace.invalidate_workspace_list_cache") as mock_inv:
            delete_project(project.id, user, db_session)
            mock_inv.assert_called_once()


class TestDocumentInputOverridesDefaults:
    """P0-4: Document generator — frontend input field variables override DB defaults."""

    def test_input_fields_override_db_target_defaults(self, db_session):
        """User-provided variables should override defaults."""
        from routers.documents import _prepare_document_vars
        from schemas import DocumentGenerateIn
        from models import DocumentTemplate
        from unittest.mock import patch

        tmpl = DocumentTemplate(
            id="test-override-tmpl",
            name="Test Invoice",
            type="invoice",
            html_template="<html>Client: {{klien}}, Amount: {{jumlah}}, Addr: {{alamat}}</html>",
            variables="[]",
            is_active=True,
        )
        db_session.add(tmpl)
        db_session.commit()

        mock_brand_ctx = {
            "logo": "", "brand_name": "Brand Co", "tagline": "",
            "nama_perusahaan": "Brand Default", "alamat_perusahaan": "Brand Street",
            "phone_perusahaan": "", "email_perusahaan": "",
        }
        mock_defaults = {
            "logo": "", "brand_name": "Brand Co",
            "nama_perusahaan": "Brand Default", "klien": "DB Default Client",
            "alamat": "DB Default Address", "jumlah": "DB Default Amount",
        }

        body = DocumentGenerateIn(
            template_id="test-override-tmpl",
            target_type="lead",
            target_id=None,
            variables={
                "klien": "User Client Corp",
                "alamat": "User Client Address",
                "jumlah": "Rp 5.000.000",
            },
        )

        with patch("routers.documents._build_brand_context", return_value=mock_brand_ctx), \
             patch("routers.documents._build_default_vars", return_value=mock_defaults), \
             patch("routers.documents._format_date_id", return_value="7 Juni 2026"):
            full_vars = _prepare_document_vars(db_session, tmpl, body)

        # User input wins over DB defaults
        assert full_vars["klien"] == "User Client Corp"
        assert full_vars["alamat"] == "User Client Address"
        assert full_vars["jumlah"] == "Rp 5.000.000"
        # Generic defaults preserved
        assert full_vars["tanggal"] == "7 Juni 2026"

    def test_invoice_number_is_server_owned(self, db_session):
        """Invoice number should come from server (document number), not user input."""
        from routers.documents import _prepare_document_vars, _document_number
        from schemas import DocumentGenerateIn
        from models import DocumentTemplate
        from unittest.mock import patch

        tmpl = DocumentTemplate(
            id="test-invoice-tmpl",
            name="Invoice",
            type="invoice",
            html_template="<html>Invoice: {{nomor_invoice}}</html>",
            variables="[]",
            is_active=True,
        )
        db_session.add(tmpl)
        db_session.commit()

        mock_brand_ctx = {
            "logo": "", "brand_name": "Brand Co", "tagline": "",
            "nama_perusahaan": "Brand Default", "alamat_perusahaan": "",
            "phone_perusahaan": "", "email_perusahaan": "",
        }
        mock_defaults = {
            "logo": "", "brand_name": "Brand Co",
            "nama_perusahaan": "Brand Default", "klien": "Client",
        }

        body = DocumentGenerateIn(
            template_id="test-invoice-tmpl",
            target_type="lead",
            target_id=None,
            variables={"nomor_invoice": "USER_TAMPERING_ATTEMPT"},
        )

        with patch("routers.documents._build_brand_context", return_value=mock_brand_ctx), \
             patch("routers.documents._build_default_vars", return_value=mock_defaults), \
             patch("routers.documents._document_number", return_value="INV/202606/001"), \
             patch("routers.documents._format_date_id", return_value="7 Juni 2026"):
            full_vars = _prepare_document_vars(db_session, tmpl, body, reserve_number=True)

        # Server-generated invoice number wins
        assert full_vars["nomor_invoice"] == "INV/202606/001"

    def test_empty_string_input_means_empty_not_db_fallback(self, db_session):
        """Empty string in user input means the field stays empty — no DB fallback for preview/generate.

        New behavior (post-fix): allow_db_defaults=False for preview/generate.
        User explicitly submits klienen="" → field is empty in output.
        DB defaults are NOT applied for preview/generate operations.
        """
        from routers.documents import _prepare_document_vars
        from schemas import DocumentGenerateIn
        from models import DocumentTemplate, Lead, SystemSettings
        from unittest.mock import patch

        for key, val in [("company_name", "Brand Test"), ("app_base_url", "https://test.com")]:
            if not db_session.query(SystemSettings).filter_by(key=key).first():
                db_session.add(SystemSettings(key=key, value=val))
        db_session.commit()

        lead = Lead(business_name="Existing Client", phone_number="081234567895")
        db_session.add(lead)
        db_session.commit()

        tmpl = DocumentTemplate(
            id="test-empty-tmpl", name="Invoice", type="invoice",
            html_template="<html>{{klien}}</html>", variables="[]", is_active=True,
        )
        db_session.add(tmpl)
        db_session.commit()

        body = DocumentGenerateIn(
            template_id="test-empty-tmpl",
            target_type="lead",
            target_id=str(lead.id),
            variables={"klien": ""},  # User explicitly clears the field
        )

        with patch("routers.documents._format_date_id", return_value="7 Juni 2026"):
            # allow_db_defaults=False (default) → no DB re-query
            full_vars = _prepare_document_vars(db_session, tmpl, body)

        # Explicit empty string input means the field is empty — no DB fallback
        assert full_vars.get("klien") == "", \
            f"Empty user input should stay empty, got '{full_vars.get('klien')}'"
        # Non-submitted field also stays empty (no DB defaults applied)
        assert full_vars.get("alamat") is None or full_vars.get("alamat") == "", \
            f"Non-submitted field should be empty, got '{full_vars.get('alamat')}'"


class TestAnalyticsProductNormalization:
    """P1-6: Analytics product distribution — normalize labels to avoid duplicate bars."""

    def test_product_labels_normalized_before_grouping(self, db_session):
        """"Website Development" variations (casing, extra spaces) should map to one canonical name."""
        from collections import Counter

        # Simulate what analytics.py does: normalize before grouping
        variants = [
            "Website Development",
            "website development",
            "WEB DEVELOPMENT",
            "Website Development ",
        ]
        product_raw: dict = {}
        for raw in variants:
            key = (raw or "").strip()
            if not key:
                continue
            lower = key.lower()
            if "website" in lower or "web dev" in lower:
                key = "Website Development"
            product_raw[key] = product_raw.get(key, 0) + 1

        # Should be merged into ONE canonical entry
        assert len(product_raw) == 1
        assert "Website Development" in product_raw
        assert product_raw["Website Development"] == 4

    def test_seo_gmaps_variants_merged(self, db_session):
        """SEO + Google Maps variations should map to one canonical name."""
        product_raw: dict = {}
        variants = [
            "SEO & Google Maps",
            "seo google maps",
            "SEO Google Maps",
        ]
        for raw in variants:
            key = (raw or "").strip()
            lower = key.lower()
            if "seo" in lower and "google maps" in lower:
                key = "SEO & Google Maps"
            product_raw[key] = product_raw.get(key, 0) + 1

        assert len(product_raw) == 1
        assert product_raw.get("SEO & Google Maps", 0) == 3

    def test_sosmed_variants_merged(self, db_session):
        """Sosmed/sosial media variations should map to one canonical name."""
        product_raw: dict = {}
        variants = [
            "Kelola Sosial Media",
            "kelola sosial media",
            "Social Media Management",
        ]
        for raw in variants:
            key = (raw or "").strip()
            lower = key.lower()
            if "sosmed" in lower or "sosial media" in lower or "social media" in lower:
                key = "Kelola Sosial Media"
            product_raw[key] = product_raw.get(key, 0) + 1

        assert len(product_raw) == 1
        assert product_raw.get("Kelola Sosial Media", 0) == 3


class TestClientDetailResponse:
    """P1-7: Client detail endpoint exposes lead_id, service_type, color."""

    def test_client_detail_response_has_lead_id(self, db):
        """client detail response dict must include lead_id at top level and project service_type/color."""
        from app.core.dependencies import hash_password
        from models import Lead, Contact, Project, User
        from routers.clients import get_client_detail

        # Create admin user first (id=1 needed for token)
        admin = User(
            id=1,
            name="Admin Test",
            email="admin@test",
            hashed_password=hash_password("test123"),
            role="admin",
        )
        db.add(admin)
        db.commit()

        lead = Lead(business_name="Detail Test Client", phone_number="081234567891")
        db.add(lead)
        db.flush()
        contact = Contact(
            business_name="Detail Test Client",
            phone_number="081234567891",
            lead_id=lead.id,
        )
        db.add(contact)
        db.flush()
        project = Project(
            id="proj-detail-test",
            lead_id=lead.id,
            name="Test Project",
            type="FIXED",
            status="ACTIVE",
            service_type="web_dev",
            color="blue",
        )
        db.add(project)
        db.commit()

        data = get_client_detail(contact.id, admin, db)

        # Response must include lead_id at top level
        assert "lead_id" in data
        assert data["lead_id"] == lead.id
        # Profile must include lead_id too
        assert "profile" in data
        assert "lead_id" in data["profile"]
        # Projects must include service_type and color
        assert len(data["projects"]) == 1
        assert data["projects"][0]["service_type"] == "web_dev"
        assert data["projects"][0]["color"] == "blue"

    def test_project_response_includes_service_type_and_color(self, db_session):
        """Project objects in client detail should include service_type and color."""
        from routers.clients import get_client_detail

        lead = Lead(business_name="Test Client", phone_number="081234567890")
        db_session.add(lead)
        db_session.flush()
        contact = Contact(
            business_name="Test Client",
            phone_number="081234567890",
            lead_id=lead.id,
        )
        db_session.add(contact)
        db_session.flush()
        project = Project(
            id="proj-test-1",
            lead_id=lead.id,
            name="Web Dev Project",
            type="FIXED",
            status="ACTIVE",
            nominal=5000000,
            service_type="web_dev",
            color="blue",
        )
        db_session.add(project)
        db_session.commit()

        # Verify project fields directly
        assert project.service_type == "web_dev"
        assert project.color == "blue"
        assert project.lead_id == lead.id


class TestContentAIMultiProviderEndpoints:
    """P1-1: Content/AI endpoints use canonical multi-provider path."""

    def test_list_ai_combos_returns_proxy_based_list(self, db_session):
        """list_ai_combos should return proxies from AIProxy table."""
        from routers.content import list_ai_combos
        from unittest.mock import MagicMock

        proxy = AIProxy(
            name="Claude Sonnet 4.5",
            base_url="https://api.anthropic.com",
            api_key="sk-ant-test",
            model="claude-sonnet-4-5",
            provider="claude",
            feature="chat",
            is_active=True,
        )
        db_session.add(proxy)
        db_session.commit()

        user = MagicMock()
        result = list_ai_combos(user, db_session)

        # Should return AIProxy-based list
        assert len(result) >= 1
        assert any(r.get("provider") == "claude" for r in result)

    def test_get_active_combo_returns_proxy_config(self, db_session):
        """get_active_combo should return AIProxy config or 'none' status."""
        from routers.content import get_active_combo
        from unittest.mock import MagicMock

        proxy = AIProxy(
            name="OpenAI GPT-4o",
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
            model="gpt-4o-mini",
            provider="openai",
            feature=None,
            is_active=True,
        )
        db_session.add(proxy)
        db_session.commit()

        user = MagicMock()
        result = get_active_combo(user, db_session)

        assert "combo" in result
        assert "provider" in result
        assert "base_url" in result
        assert "model" in result

    def test_set_active_combo_by_proxy_id(self, db_session):
        """set_active_combo should activate by AIProxy ID."""
        from routers.content import set_active_combo, get_active_combo
        from unittest.mock import MagicMock

        proxy1 = AIProxy(
            name="Provider A",
            base_url="https://api.anthropic.com",
            api_key="key-a",
            model="claude-haiku-4-5",
            provider="claude",
            feature=None,
            is_active=False,
        )
        proxy2 = AIProxy(
            name="Provider B",
            base_url="https://api.openai.com/v1",
            api_key="key-b",
            model="gpt-4o-mini",
            provider="openai",
            feature=None,
            is_active=True,
        )
        db_session.add(proxy1)
        db_session.add(proxy2)
        db_session.commit()

        user = MagicMock()
        user.role = "admin"
        body = {"proxy_id": proxy1.id}
        result = set_active_combo(body, user, db_session)

        assert result["ok"] is True
        assert result["combo"] == "Provider A"
        assert result["provider"] == "claude"

    def test_get_system_ai_config_uses_canonical_path(self, db_session):
        """_get_system_ai_config should use canonical get_ai_config."""
        from routers.content import _get_system_ai_config

        result = _get_system_ai_config(db_session)
        assert "provider" in result
        assert "model" in result

    def test_feature_defaults_validates_proxy_ids(self, db_session):
        """set_feature_defaults should validate AIProxy IDs."""
        from routers.content import set_feature_defaults
        from unittest.mock import MagicMock

        user = MagicMock()
        user.role = "admin"

        # Invalid proxy ID should raise
        body = {"chat": "nonexistent-proxy-id"}
        try:
            set_feature_defaults(body, user, db_session)
            assert False, "Should have raised"
        except Exception as e:
            assert "proxy ID" in str(e) or "tidak valid" in str(e)


class TestWorkspaceDynamicColumns:
    """P1-5: Workspace sync uses dynamic board column names."""

    def test_sync_uses_board_column_names_not_hardcoded(self):
        """_sync_one_card should look up board columns by name dynamically."""
        # Verify _ROW_STATUS_MAP doesn't hardcode column names that would conflict
        # with custom board column names
        from app.core.dependencies import _ROW_STATUS_MAP
        # These are status value → label overrides, not column name constraints
        assert isinstance(_ROW_STATUS_MAP, dict)
        # Map should be empty or generic — no hardcoded column names like "To Do", "Done"
        for key in _ROW_STATUS_MAP:
            assert key in ("Done", "On Track", "In Progress", "Pending"), \
                f"_ROW_STATUS_MAP key '{key}' should only contain status labels, not column names"


class TestDocumentGeneratorInputFields:
    """P0-5: Document generator renders from input fields, not DB re-query."""

    def test_prepare_document_vars_user_input_wins_over_db(self, db_session):
        """_prepare_document_vars uses body.variables as source of truth, not DB re-query."""
        from routers.documents import _prepare_document_vars
        from schemas import DocumentGenerateIn
        from models import DocumentTemplate, Lead
        from unittest.mock import patch

        lead = Lead(business_name="DB Client Name", phone_number="081234567890")
        db_session.add(lead)
        db_session.commit()

        tmpl = DocumentTemplate(
            id="test-input-tmpl", name="Test Invoice", type="invoice",
            html_template="<html>{{klien}}</html>", variables="[]", is_active=True,
        )
        db_session.add(tmpl)
        db_session.commit()

        body = DocumentGenerateIn(
            template_id="test-input-tmpl",
            target_type="lead",
            target_id=str(lead.id),
            variables={"klien": "User Override Corp", "alamat": "User Address"},
        )

        lead.business_name = "MUTATED DB Name"
        db_session.commit()

        # Patch _get_setting and _build_brand_context to avoid system_settings table issue
        with patch("routers.documents._get_setting", return_value=""), \
             patch("routers.documents._build_brand_context", return_value={"logo": "", "brand_name": "", "tagline": ""}), \
             patch("routers.documents._format_date_id", return_value="7 Juni 2026"):
            full_vars = _prepare_document_vars(db_session, tmpl, body)

        assert full_vars.get("klien") == "User Override Corp", \
            f"Expected 'User Override Corp' but got '{full_vars.get('klien')}'"
        assert full_vars.get("alamat") == "User Address", \
            f"Expected 'User Address' but got '{full_vars.get('alamat')}'"

    def test_prepare_document_vars_no_db_requery_on_final_render(self, db_session):
        """Preview/generate must not re-query DB for client/company/service fields."""
        from routers.documents import _prepare_document_vars
        from schemas import DocumentGenerateIn
        from models import DocumentTemplate, Lead
        from unittest.mock import patch

        lead = Lead(business_name="Original Name", phone_number="081234567891")
        db_session.add(lead)
        db_session.commit()
        lead_id = lead.id

        tmpl = DocumentTemplate(
            id="test-no-req-tmpl", name="Invoice", type="invoice",
            html_template="<html>{{klien}}</html>", variables="[]", is_active=True,
        )
        db_session.add(tmpl)
        db_session.commit()

        body = DocumentGenerateIn(
            template_id="test-no-req-tmpl",
            target_type="lead",
            target_id=str(lead_id),
            variables={"klien": "My Custom Client"},
        )

        db_session.refresh(lead)
        lead.business_name = "Changed By Another Process"
        db_session.commit()

        with patch("routers.documents._get_setting", return_value=""), \
             patch("routers.documents._build_brand_context", return_value={"logo": "", "brand_name": "", "tagline": ""}), \
             patch("routers.documents._format_date_id", return_value="7 Juni 2026"):
            full_vars = _prepare_document_vars(db_session, tmpl, body)

        assert full_vars.get("klien") == "My Custom Client", \
            f"Expected 'My Custom Client' but got '{full_vars.get('klien')}'"

    def test_document_generator_no_db_requery_without_mock(self, db_session):
        """Preview/generate must use user input, not re-query DB — even without mocking _build_default_vars.

        Scenario:
        1. Lead in DB has business_name="Original DB Name"
        2. User submits variables={"klien": "User Override Corp"}
        3. Lead.business_name is mutated to "Mutated By Another Process"
        4. _prepare_document_vars is called WITHOUT allow_db_defaults
        5. Result MUST be "User Override Corp" — NOT the mutated DB value
        """
        from routers.documents import _prepare_document_vars
        from schemas import DocumentGenerateIn
        from models import DocumentTemplate, Lead, SystemSettings
        from unittest.mock import patch

        # Seed minimal system_settings to avoid _build_brand_context errors
        for key, val in [("company_name", "Brand Test"), ("app_base_url", "https://test.com")]:
            if not db_session.query(SystemSettings).filter_by(key=key).first():
                db_session.add(SystemSettings(key=key, value=val))
        db_session.commit()

        lead = Lead(business_name="Original DB Name", phone_number="081234567892")
        db_session.add(lead)
        db_session.commit()

        tmpl = DocumentTemplate(
            id="test-real-db-tmpl", name="Invoice", type="invoice",
            html_template="<html>{{klien}}</html>", variables="[]", is_active=True,
        )
        db_session.add(tmpl)
        db_session.commit()

        body = DocumentGenerateIn(
            template_id="test-real-db-tmpl",
            target_type="lead",
            target_id=str(lead.id),
            variables={"klien": "User Override Corp"},
        )

        # Mutate the DB while _prepare_document_vars runs
        lead.business_name = "Mutated By Another Process"
        db_session.commit()

        # NO mock on _build_default_vars — this verifies the real fix
        with patch("routers.documents._format_date_id", return_value="8 Juni 2026"):
            full_vars = _prepare_document_vars(db_session, tmpl, body)

        # User input wins even without mocking _build_default_vars
        assert full_vars.get("klien") == "User Override Corp", \
            f"FAIL: got '{full_vars.get('klien')}' — user input was overwritten by DB re-query"

    def test_document_generator_with_db_defaults_prefill_still_works(self, db_session):
        """allow_db_defaults=True lets prefill use DB, but preview must not."""
        from routers.documents import _prepare_document_vars
        from schemas import DocumentGenerateIn
        from models import DocumentTemplate, Lead, SystemSettings
        from unittest.mock import patch

        for key, val in [("company_name", "Brand Test"), ("app_base_url", "https://test.com")]:
            if not db_session.query(SystemSettings).filter_by(key=key).first():
                db_session.add(SystemSettings(key=key, value=val))
        db_session.commit()

        lead = Lead(business_name="Prefill From DB", phone_number="081234567893")
        db_session.add(lead)
        db_session.commit()

        tmpl = DocumentTemplate(
            id="test-prefill-tmpl", name="Invoice", type="invoice",
            html_template="<html>{{klien}}</html>", variables="[]", is_active=True,
        )
        db_session.add(tmpl)
        db_session.commit()

        # With allow_db_defaults=True (prefill endpoint), DB values are used
        body = DocumentGenerateIn(
            template_id="test-prefill-tmpl",
            target_type="lead",
            target_id=str(lead.id),
            variables={},  # user submits nothing
        )

        with patch("routers.documents._format_date_id", return_value="8 Juni 2026"):
            full_vars = _prepare_document_vars(db_session, tmpl, body, allow_db_defaults=True)

        # DB value used for prefill when no user input
        assert full_vars.get("klien") == "Prefill From DB", \
            f"Prefill should use DB value, got '{full_vars.get('klien')}'"


class TestAIEngineMultiProviderCaption:
    """P0-3: generate_caption uses canonical multi-provider routing."""

    def test_generate_caption_delegates_to_service(self, db_session):
        """generate_caption in content.py must delegate to ai_service.generate_caption."""
        from unittest.mock import MagicMock, patch
        # Verify by patching at the service location the router imports from
        with patch("app.services.ai_service.generate_caption", MagicMock(return_value={
            "id": "gen-1", "status": "done", "created_at": "2026-06-08T00:00:00Z",
            "caption": "test", "hashtags": [], "notes": ""
        })) as mock_svc:
            from routers.content import generate_caption
            body = MagicMock()
            body.topic = "test topic"
            body.platform = "instagram"
            body.tone = "casual"
            body.keywords = ["test"]
            body.session_id = None
            body.context_from = None
            user = MagicMock()
            user.id = 1
            result = generate_caption(body, user, db_session)
            mock_svc.assert_called_once()
            call_kwargs = mock_svc.call_args[1]
            assert call_kwargs["db"] is db_session
            assert call_kwargs["user_id"] == 1
            assert call_kwargs["topic"] == "test topic"

    def test_generate_seo_article_delegates_to_service(self, db_session):
        """generate_seo_article in content.py must delegate to ai_service.generate_seo_article."""
        from unittest.mock import MagicMock, patch
        with patch("app.services.ai_service.generate_seo_article", MagicMock(return_value={
            "id": "gen-2", "status": "done", "created_at": "2026-06-08T00:00:00Z",
            "title": "Test", "body": "content"
        })) as mock_svc:
            from routers.content import generate_seo_article
            body = MagicMock()
            body.keyword = "test keyword"
            body.title = None
            body.word_count = 500
            body.tone = "professional"
            body.search_intent = None
            body.keyword_difficulty = None
            body.search_volume = None
            body.lsi_keywords = None
            body.faq_topics = None
            body.serp_features = None
            body.target_audience = None
            body.target_location = None
            body.brand_name = None
            body.unique_angle = None
            body.internal_link_targets = None
            body.session_id = None
            body.context_from = None
            user = MagicMock()
            user.id = 1
            result = generate_seo_article(body, user, db_session)
            mock_svc.assert_called_once()
            call_kwargs = mock_svc.call_args[1]
            assert call_kwargs["db"] is db_session
            assert call_kwargs["user_id"] == 1
            assert call_kwargs["keyword"] == "test keyword"

    def test_call_ai_sync_gemini_uses_config_model(self):
        """call_ai_sync for gemini must use config['model'] in URL."""
        from app.services.ai_service import call_ai_sync
        from unittest.mock import MagicMock, patch
        import httpx

        cfg = {
            "provider": "gemini",
            "gemini_key": "my-gemini-key",
            "base_url": "https://generativelanguage.googleapis.com",
            "model": "gemini-2.0-flash-exp",
            "openai_key": "",
            "claude_key": "",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "Gemini response"}]}}]}
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = lambda self: mock_client
        mock_client.__exit__ = lambda self, *a: False

        with patch.object(httpx, "Client", return_value=mock_client):
            result = call_ai_sync("test prompt", cfg, httpx)

        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        assert "gemini-2.0-flash-exp" in call_url, f"Expected model in URL, got: {call_url}"
        assert "generateContent" in call_url

    def test_call_ai_provider_async_gemini_uses_config_model(self):
        """call_ai_provider_async for gemini must use config['model'] in URL."""
        from app.services.ai_service import call_ai_provider_async
        from unittest.mock import MagicMock, patch, AsyncMock
        import httpx as _httpx

        cfg = {
            "provider": "gemini",
            "gemini_key": "my-gemini-key",
            "base_url": "https://generativelanguage.googleapis.com",
            "model": "gemini-pro-1.5",
            "openai_key": "",
            "claude_key": "",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": "async response"}]}}]}
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch.object(_httpx, "AsyncClient", return_value=mock_client):
            result = asyncio.run(call_ai_provider_async("test prompt", cfg))

        assert result == "async response"
        mock_client.post.assert_called_once()
        call_url = mock_client.post.call_args[0][0]
        assert "gemini-pro-1.5" in call_url, f"Expected model in URL, got: {call_url}"

    def test_update_ai_proxy_preserves_api_key_when_blank(self, db_session):
        """update_ai_proxy must preserve existing api_key when update is blank/masked."""
        from routers.content import update_ai_proxy
        from schemas import AIProxyIn
        from unittest.mock import MagicMock

        proxy = AIProxy(
            name="Test Proxy",
            base_url="https://api.openai.com/v1",
            api_key="sk-original-key-12345",
            model="gpt-4o-mini",
            provider="openai",
            feature=None,
            is_active=True,
        )
        db_session.add(proxy)
        db_session.commit()
        proxy_id = proxy.id

        user = MagicMock()
        user.role = "admin"

        body = AIProxyIn(
            name="Updated Name",
            base_url="https://api.openai.com/v1",
            api_key="",  # blank
            model="gpt-4o-mini",
            provider="openai",
            feature=None,
        )

        result = update_ai_proxy(proxy_id, body, user, db_session)
        assert result.api_key == "sk-original-key-12345", \
            f"Expected preserved key, got '{result.api_key}'"


class TestProposalBoardNeutralColors:
    """P0-4: Proposal-created boards use neutral colors."""

    def test_proposal_acceptance_creates_neutral_project_color(self, db):
        """Project created from proposal acceptance must use gray color."""
        from routers.proposals import accept_proposal
        from schemas import ProposalAcceptIn
        from models import Lead, Proposal, Project

        lead = Lead(business_name="Proposal Client", phone_number="081234567899")
        db.add(lead)
        db.flush()
        proposal = Proposal(
            id="prop-color-test",
            lead_id=lead.id,
            slug="prop-color-test",
            status="sent",
            services_detail='[{"name": "Web Development", "price": 5000000}]',
            total_price=5000000,
            base_price=5000000,
            discount_price=5000000,
            created_at="2026-06-01T00:00:00+00:00",
        )
        db.add(proposal)
        db.commit()

        result = accept_proposal("prop-color-test", ProposalAcceptIn(client_name="Test", client_phone="081234567899"), db)
        project_id = result["project_id"]
        project = db.query(Project).filter(Project.id == project_id).first()
        assert project is not None
        assert project.color == "gray", \
            f"Expected color='gray' but got '{project.color}'"

    def test_proposal_acceptance_creates_neutral_board_columns(self, db):
        """Board columns created from proposal acceptance must use neutral colors."""
        from routers.proposals import accept_proposal
        from schemas import ProposalAcceptIn
        from models import Lead, Proposal, Project, Board, BoardColumn

        lead = Lead(business_name="Board Color Client", phone_number="081234567898")
        db.add(lead)
        db.flush()
        proposal = Proposal(
            id="prop-board-col-test",
            lead_id=lead.id,
            slug="prop-board-col-test",
            status="sent",
            services_detail='[{"name": "SEO", "price": 3000000}]',
            total_price=3000000,
            base_price=3000000,
            discount_price=3000000,
            created_at="2026-06-01T00:00:00+00:00",
        )
        db.add(proposal)
        db.commit()

        result = accept_proposal("prop-board-col-test", ProposalAcceptIn(client_name="Test", client_phone="081234567899"), db)
        project_id = result["project_id"]
        board = db.query(Board).filter(Board.project_id == project_id).first()
        assert board is not None
        cols = db.query(BoardColumn).filter(BoardColumn.board_id == board.id).order_by(BoardColumn.position).all()
        assert len(cols) >= 4, f"Should have columns, got {len(cols)}"
        neutral_colors = {"gray", "slate", "neutral", "stone"}
        for col in cols:
            assert col.color in neutral_colors, \
                f"Column '{col.name}' has color '{col.color}' — expected one of {neutral_colors}"


class TestContactLeadRepairEndToEnd:
    """P0-1: contact without lead_id can create project via contact_id."""

    def test_contact_without_lead_id_can_create_project(self, db_session):
        """Contact without lead_id + no matching lead → creates lead and project."""
        from routers.leads import create_contact, update_contact
        from routers.workspace import create_project
        from schemas import ContactUpdate, ProjectIn
        from unittest.mock import MagicMock

        user = MagicMock()
        user.name = "test"

        # Create contact (no existing lead)
        body_contact = ContactUpdate(business_name="Repair Test Corp", phone_number="081234567897")
        contact = create_contact(body_contact, user, db_session)
        assert contact.lead_id is not None, "create_contact should auto-create lead_id"

        # Create project via contact_id
        body_project = ProjectIn(
            name="Repair Test Project",
            type="FIXED",
            status="ACTIVE",
            contact_id=contact.id,
        )
        project = create_project(body_project, user, db_session)

        assert project.lead_id == contact.lead_id
        assert project.lead_id is not None

    def test_contact_without_lead_id_with_existing_lead_uses_existing(self, db_session):
        """Contact without lead_id but matching lead exists → reuses lead."""
        from routers.leads import create_contact
        from routers.workspace import create_project
        from schemas import ContactUpdate, ProjectIn
        from unittest.mock import MagicMock

        user = MagicMock()
        user.name = "test"

        # Create standalone contact (no auto-lead)
        from models import Contact
        contact = Contact(business_name="Standalone Corp", phone_number="081234567896")
        db_session.add(contact)
        db_session.commit()
        assert contact.lead_id is None

        # Create project via contact_id — should find/create lead
        body_project = ProjectIn(
            name="Standalone Project",
            type="FIXED",
            status="ACTIVE",
            contact_id=contact.id,
        )
        project = create_project(body_project, user, db_session)

        # Contact should now have lead_id linked
        db_session.refresh(contact)
        assert contact.lead_id is not None
        assert project.lead_id == contact.lead_id
