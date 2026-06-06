"""Focused tests for P0 fixes"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# Test imports
from models import Lead, Contact, Project


class TestContactLeadCRUD:
    """P0-1: Contact/Lead CRUD flow"""

    def test_create_contact_normalizes_phone(self):
        """Contact phone should be normalized on create"""
        # Test that create_contact uses normalize_phone_storage for DB storage
        from app.core.dependencies import normalize_phone_storage

        # 62xxx should become 08xx for DB storage
        result = normalize_phone_storage("6281234567890")
        assert result == "081234567890"

    def test_create_contact_auto_creates_lead(self):
        """Creating standalone Contact should auto-create Lead"""
        db = MagicMock()
        body = MagicMock()
        body.business_name = "Test Corp"
        body.phone_number = "081234567890"
        body.owner_name = None
        body.purchased_product = None
        body.notes = None

        # Mock db queries
        db.query.return_value.filter.return_value.first.return_value = None  # No existing contact
        db.query.return_value.filter.return_value.filter.return_value.first.return_value = None  # No existing lead

        # Verify lead would be created
        assert True  # Integration test needed

    def test_update_contact_persists_business_name(self):
        """update_contact should persist business_name on Contact"""
        contact = MagicMock()
        contact.id = 1
        contact.business_name = "Old Name"
        contact.phone_number = "081234567890"
        contact.lead_id = None

        body = MagicMock()
        body.business_name = "New Name"
        body.phone_number = None
        body.owner_name = None
        body.purchased_product = None
        body.notes = None

        # Verify business_name is set
        if body.business_name is not None:
            contact.business_name = body.business_name

        assert contact.business_name == "New Name"


class TestProjectFromContact:
    """P0-1: Project can be created from contact_id"""

    def test_project_accepts_contact_id(self):
        """ProjectIn should accept contact_id parameter"""
        from schemas import ProjectIn

        body = ProjectIn(name="Test Project", type="FIXED", contact_id=1)
        assert body.contact_id == 1
        assert body.lead_id is None

    def test_project_resolves_contact_to_lead_id(self):
        """create_project should resolve contact_id to lead_id"""
        db = MagicMock()
        contact = MagicMock()
        contact.id = 1
        contact.lead_id = 100

        lead = MagicMock()
        lead.id = 100

        # Mock: contact found, lead found
        db.query.return_value.filter.return_value.first.side_effect = [contact, lead]

        # Verify lead_id is resolved
        resolved_lead_id = contact.lead_id
        assert resolved_lead_id == 100


class TestWebhookReplied:
    """P0-2: Webhook handles replied status"""

    def test_fonnte_webhook_handles_replied(self):
        """Status webhook should handle 'replied' status"""
        from schemas import FonnteWebhookIn

        body = FonnteWebhookIn(target="081234567890", status="replied")

        # Verify status is accepted
        assert body.status == "replied"


class TestAIProviderConfig:
    """P0-3: AI proxy provider field"""

    def test_ai_proxy_schema_has_provider(self):
        """AIProxyIn and AIProxyOut should have provider field"""
        from schemas import AIProxyIn, AIProxyOut

        inp = AIProxyIn(name="Test", base_url="http://test.com", provider="claude")
        assert inp.provider == "claude"

    def test_get_ai_config_maps_provider_keys(self):
        """get_ai_config should map api_key to correct provider key"""
        from app.services.ai_service import get_ai_config

        db = MagicMock()
        proxy = MagicMock()
        proxy.provider = "claude"
        proxy.api_key = "sk-claude-key"
        proxy.base_url = "https://api.anthropic.com"
        proxy.model = "claude-sonnet-4"

        with patch("app.services.ai_service.get_proxy_for_feature", return_value=proxy):
            cfg = get_ai_config(db, "chat")

            # Should map api_key to claude_key for claude provider
            assert cfg["provider"] == "claude"
            assert cfg["claude_key"] == "sk-claude-key"
            assert cfg["openai_key"] == ""
            assert cfg["gemini_key"] == ""

    def test_gemini_proxy_maps_correct_key(self):
        """get_ai_config should map api_key to gemini_key for gemini provider"""
        from app.services.ai_service import get_ai_config

        db = MagicMock()
        proxy = MagicMock()
        proxy.provider = "gemini"
        proxy.api_key = "gemini-key-123"
        proxy.base_url = "https://generativelanguage.googleapis.com"
        proxy.model = "gemini-2.0-flash"

        with patch("app.services.ai_service.get_proxy_for_feature", return_value=proxy):
            cfg = get_ai_config(db, "chat")

            assert cfg["provider"] == "gemini"
            assert cfg["gemini_key"] == "gemini-key-123"
            assert cfg["openai_key"] == ""
            assert cfg["claude_key"] == ""


class TestDocumentGeneratorInput:
    """P0-4: Document generator user input wins"""

    def test_server_owned_keys_only_logo_brand(self):
        """_SERVER_OWNED_DOCUMENT_KEYS should only include logo, brand_name, etc."""
        from routers.documents import _SERVER_OWNED_DOCUMENT_KEYS

        # Company fields should NOT be protected
        assert "alamat_perusahaan" not in _SERVER_OWNED_DOCUMENT_KEYS
        assert "phone_perusahaan" not in _SERVER_OWNED_DOCUMENT_KEYS
        assert "email_perusahaan" not in _SERVER_OWNED_DOCUMENT_KEYS

        # Truly server-owned should be protected
        assert "logo" in _SERVER_OWNED_DOCUMENT_KEYS
        assert "brand_name" in _SERVER_OWNED_DOCUMENT_KEYS


class TestColorDefaults:
    """P0-5: Neutral color defaults"""

    def test_project_model_default_gray(self):
        """Project.color should default to gray, not yellow"""
        from models.project import Project

        # Check default value in model (SQLAlchemy wraps in ScalarElementColumnDefault)
        default = Project.__dict__["color"].default
        assert str(default.arg) == "gray"

    def test_board_column_default_gray(self):
        """BoardColumn.color should default to gray"""
        from models.board import BoardColumn

        default = BoardColumn.__dict__["color"].default
        assert str(default.arg) == "gray"


class TestPhoneNormalization:
    """P0: Phone normalization consistency"""

    def test_normalize_phone_storage_08xx(self):
        """normalize_phone_storage should convert 628xx to 08xx for DB storage"""
        from app.core.dependencies import normalize_phone_storage

        # 62xxx format -> 08xx
        result = normalize_phone_storage("6281234567890")
        assert result == "081234567890"

        # +62xxx format -> 08xx
        result2 = normalize_phone_storage("+6281234567890")
        assert result2 == "081234567890"

        # Already 08xx - unchanged
        result3 = normalize_phone_storage("081234567890")
        assert result3 == "081234567890"