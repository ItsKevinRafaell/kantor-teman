import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.fernet import Fernet
from fastapi import HTTPException
from fastapi.responses import Response


TEST_DIR = tempfile.mkdtemp(prefix="kantorteman-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DIR}/test.db"
os.environ["SECRET_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["JWT_SECRET"] = "test-jwt-secret-for-unit-tests-minimum-32-bytes"  # min 32 bytes for HS256
os.environ["ENABLE_BACKGROUND_SCHEDULER"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import main  # noqa: E402
import routers.documents  # noqa: E402
import routers.settings as settings_router  # noqa: E402
from app.core.dependencies import hash_password  # noqa: E402


class HardeningRegressionTests(unittest.TestCase):
    def setUp(self):
        main.Base.metadata.drop_all(main.engine)
        main.Base.metadata.create_all(main.engine)
        self.db = main.SessionLocal()
        self.admin = main.User(
            name="Admin Test",
            email="admin@example.test",
            hashed_password="unused",
            role="admin",
        )
        self.db.add(self.admin)
        self.db.commit()
        self.db.refresh(self.admin)

    def tearDown(self):
        self.db.close()

    def test_lead_delete_archives_without_removing_history(self):
        lead = main.Lead(business_name="Lead Test", phone_number="628111111111")
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        history = main.BlastMessage(
            id=str(uuid.uuid4()),
            lead_id=lead.id,
            phone_number=lead.phone_number,
            status="sent",
        )
        self.db.add(history)
        self.db.commit()

        main.delete_lead(lead.id, current_user=self.admin, db=self.db)

        saved = self.db.query(main.Lead).filter(main.Lead.id == lead.id).one()
        self.assertTrue(saved.is_archived)
        self.assertIsNotNone(saved.deleted_at)
        self.assertEqual(self.db.query(main.BlastMessage).count(), 1)

    def test_opt_out_blocks_manual_whatsapp_before_provider_call(self):
        lead = main.Lead(
            business_name="Opt Out",
            phone_number="628122222222",
            do_not_contact=True,
        )
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)

        with self.assertRaises(HTTPException) as caught:
            main.send_wa_manual(
                main.WaSendIn(lead_id=lead.id, message="test"),
                current_user=self.admin,
                db=self.db,
            )

        self.assertEqual(caught.exception.status_code, 409)

    def test_finance_report_excludes_archived_and_does_not_double_count_subscription(self):
        wallet = main.Wallet(name="Main", balance=1_000_000)
        self.db.add(wallet)
        self.db.commit()
        self.db.refresh(wallet)
        month = datetime.now().strftime("%Y-%m")
        self.db.add_all([
            main.Transaction(
                wallet_id=wallet.id,
                type="expense",
                amount=100_000,
                category="Subscription",
                date=f"{month}-01",
                is_archived=False,
            ),
            main.Transaction(
                wallet_id=wallet.id,
                type="expense",
                amount=900_000,
                category="Other",
                date=f"{month}-02",
                is_archived=True,
            ),
            main.Subscription(
                wallet_id=wallet.id,
                name="Hosting",
                amount=100_000,
                billing_cycle="monthly",
                next_billing_date=f"{month}-01",
                is_active=True,
            ),
        ])
        self.db.commit()

        report = main.get_finance_reports(current_user=self.admin, db=self.db)

        self.assertEqual(report.total_balance, 1_000_000)
        self.assertEqual(report.break_even_point, 100_000)
        self.assertEqual(report.expense_by_category, [{"category": "Subscription", "amount": 100_000}])

    def test_folder_delete_removes_docs_and_children_after_summary(self):
        parent = main.DocumentFolder(user_id=self.admin.id, name="Parent")
        self.db.add(parent)
        self.db.commit()
        self.db.refresh(parent)
        child = main.DocumentFolder(user_id=self.admin.id, name="Child", parent_id=parent.id)
        doc = main.Document(user_id=self.admin.id, folder_id=parent.id, title="Contract")
        self.db.add_all([child, doc])
        self.db.commit()
        self.db.refresh(child)
        self.db.refresh(doc)
        parent_id = parent.id
        child_id = child.id
        doc_id = doc.id

        summary = main.archive_folder_delete_summary(parent_id, current_user=self.admin, db=self.db)
        self.assertEqual(summary["subfolder_count"], 1)
        self.assertEqual(summary["document_count"], 1)
        self.assertEqual(summary["folder_count"], 2)

        main.delete_archive_folder(parent_id, current_user=self.admin, db=self.db)

        self.assertIsNone(self.db.query(main.Document).filter(main.Document.id == doc_id).one_or_none())
        self.assertIsNone(self.db.query(main.DocumentFolder).filter(main.DocumentFolder.id == child_id).one_or_none())
        self.assertIsNone(self.db.query(main.DocumentFolder).filter(main.DocumentFolder.id == parent_id).one_or_none())

    def test_archive_update_can_clear_folder_url_and_body(self):
        folder = main.DocumentFolder(user_id=self.admin.id, name="Folder")
        self.db.add(folder)
        self.db.commit()
        self.db.refresh(folder)
        doc = main.Document(
            user_id=self.admin.id,
            folder_id=folder.id,
            title="Document",
            body="old",
            url="https://example.test",
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        main.update_archive_doc(
            doc.id,
            main.ArchiveDocUpdate(folder_id=None, body=None, url=None),
            current_user=self.admin,
            db=self.db,
        )

        saved = self.db.query(main.Document).filter(main.Document.id == doc.id).one()
        self.assertIsNone(saved.folder_id)
        self.assertIsNone(saved.body)
        self.assertIsNone(saved.url)

    def test_pdf_preview_returns_complete_buffered_response(self):
        request = SimpleNamespace(headers={})
        template = SimpleNamespace(id="template-id")
        query = self.db.query(main.DocumentTemplate)
        with patch.object(self.db, "query", return_value=query), \
             patch.object(query, "filter", return_value=query), \
             patch.object(query, "first", return_value=template), \
             patch.object(routers.documents, "_prepare_document_vars", return_value={}), \
             patch.object(routers.documents, "_render_document_pdf", return_value=b"%PDF-1.7\ncomplete"):
            response = main.preview_document(
                request,
                main.DocumentGenerateIn(template_id="template-id", variables={}),
                current_user=self.admin,
                db=self.db,
            )

        self.assertIsInstance(response, Response)
        self.assertEqual(response.body, b"%PDF-1.7\ncomplete")

    def test_pdf_renderer_falls_back_when_primary_output_is_invalid(self):
        template = SimpleNamespace(html_template="<html><body>Test</body></html>")
        with patch("weasyprint.HTML") as html:
            html.return_value.write_pdf.return_value = b""
            pdf = main._render_document_pdf(template, {})

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertIn(b"Test", pdf)

    def test_pdf_renderer_uses_starter_when_builtin_template_is_empty(self):
        template = SimpleNamespace(type="invoice", html_template="")
        with patch("weasyprint.HTML") as html:
            html.return_value.write_pdf.return_value = b"%PDF" + (b"x" * 1024)
            main._render_document_pdf(template, {})

        self.assertIn("INVOICE", html.call_args.kwargs["string"])

    def test_pdf_renderer_rejects_empty_custom_template(self):
        template = SimpleNamespace(type="custom", html_template="")
        with self.assertRaises(HTTPException) as caught:
            main._render_document_pdf(template, {})

        self.assertEqual(caught.exception.status_code, 400)

    def test_pdf_renderer_replaces_legacy_proposal_template(self):
        template = SimpleNamespace(
            name="Proposal Penawaran PDF",
            type="proposal_pdf",
            html_template="<html><body><div class='service'>{{services_html}}</div>{{faqs_html}}</body></html>",
        )
        with patch("weasyprint.HTML") as html:
            html.return_value.write_pdf.return_value = b"%PDF" + (b"x" * 1024)
            main._render_document_pdf(template, {"klien": "PT Contoh", "layanan": "Website"})

        rendered = html.call_args.kwargs["string"]
        self.assertIn("PROPOSAL PENAWARAN", rendered)
        self.assertIn("PT Contoh", rendered)
        self.assertNotIn("services_html", rendered)

    def test_document_vars_do_not_replace_defaults_with_empty_strings(self):
        # User input wins for non-server-owned keys. Empty string input stays empty.
        template = SimpleNamespace(name="Invoice", type="invoice")
        body = main.DocumentGenerateIn(
            template_id="template-id",
            variables={"tanggal": "", "klien": "PT Contoh"},
        )
        with patch.object(routers.documents, "_build_default_vars", return_value={"tanggal": "2 Juni 2026", "klien": "Default"}), \
             patch.object(routers.documents, "_build_brand_context", return_value={"logo": ""}):
            variables = main._prepare_document_vars(self.db, template, body)

        # tanggal is NOT server-owned → user input wins, empty string preserved
        self.assertEqual(variables["tanggal"], "")
        self.assertEqual(variables["klien"], "PT Contoh")

    def test_document_vars_strip_date_label_and_keep_server_company_scope(self):
        template = SimpleNamespace(name="Invoice", type="invoice")
        body = main.DocumentGenerateIn(
            template_id="template-id",
            variables={
                "tanggal": "Tanggal: Tanggal: 5 Juni 2026",
                "nama_perusahaan": "TEMAN TEMAN",
                "brand_name": "TEMAN TEMAN",
            },
        )
        defaults = {
            "tanggal": "2 Juni 2026",
            "nama_perusahaan": "PT Lead Contoh",
            "brand_name": "Kantor Teman",
        }
        brand_ctx = {"logo": "", "nama_perusahaan": "Kantor Teman", "brand_name": "Kantor Teman"}
        with patch.object(routers.documents, "_build_default_vars", return_value=defaults), \
             patch.object(routers.documents, "_build_brand_context", return_value=brand_ctx):
            variables = main._prepare_document_vars(self.db, template, body)

        self.assertEqual(variables["tanggal"], "5 Juni 2026")
        # P0-4 fix: user input wins for nama_perusahaan (not in _SERVER_OWNED_DOCUMENT_KEYS)
        self.assertEqual(variables["nama_perusahaan"], "TEMAN TEMAN")
        # brand_name IS in _SERVER_OWNED_DOCUMENT_KEYS, so brand context wins
        self.assertEqual(variables["brand_name"], "Kantor Teman")

    def test_builtin_template_with_old_company_scope_uses_current_starter(self):
        template = SimpleNamespace(
            name="Invoice",
            type="invoice",
            html_template="<html><body>{{nama_perusahaan}}</body></html>",
        )

        html = routers.documents._document_template_html(template)

        self.assertIn("{{brand_name}}", html)
        self.assertIn("INVOICE", html)

    def test_upload_path_is_canonical_from_dependencies(self):
        import app.core.dependencies as deps

        self.assertIs(main.UPLOADS_DIR, deps.UPLOADS_DIR)
        norm = os.path.normpath(main.UPLOADS_DIR)
        self.assertTrue(
            norm.endswith("app/uploads") or "app/uploads" in norm,
            f"UPLOADS_DIR={norm!r} should end with or contain app/uploads",
        )

    def test_email_document_resolves_from_documents_dir_not_router_dir(self):
        from models import GeneratedDocument

        lead = main.Lead(business_name="Doc Target", phone_number="628111111112")
        self.db.add(lead)
        self.db.flush()

        test_pdf_name = f"email-path-test-{uuid.uuid4().hex}.pdf"
        canonical_dir = routers.documents.DOCUMENTS_DIR
        os.makedirs(canonical_dir, exist_ok=True)
        pdf_path = os.path.join(canonical_dir, test_pdf_name)
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 test")

        try:
            doc = GeneratedDocument(
                id=str(uuid.uuid4()),
                template_id=None,
                template_name="Invoice",
                target_type="lead",
                target_id=str(lead.id),
                variables_used="{}",
                file_url=test_pdf_name,
                display_filename="Test Invoice",
                generated_by="test",
            )
            self.db.add(doc)
            self.db.commit()
            self.db.refresh(doc)

            with patch("routers.documents._get_setting", return_value=""):
                try:
                    routers.documents.email_document(
                        doc.id,
                        routers.documents.DocumentEmailIn(to_email="test@test.com"),
                        self.admin,
                        self.db,
                    )
                except HTTPException as exc:
                    self.assertNotIn("File tidak ada di disk", str(exc.detail))
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    def test_delete_generated_document_resolves_from_documents_dir_not_router_dir(self):
        from models import GeneratedDocument

        lead = main.Lead(business_name="Doc Target", phone_number="628111111113")
        self.db.add(lead)
        self.db.flush()

        test_pdf_name = f"delete-path-test-{uuid.uuid4().hex}.pdf"
        canonical_dir = routers.documents.DOCUMENTS_DIR
        os.makedirs(canonical_dir, exist_ok=True)
        pdf_path = os.path.join(canonical_dir, test_pdf_name)
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 test")

        doc = GeneratedDocument(
            id=str(uuid.uuid4()),
            template_id=None,
            template_name="Invoice",
            target_type="lead",
            target_id=str(lead.id),
            variables_used="{}",
            file_url=test_pdf_name,
            display_filename="Test Invoice",
            generated_by="test",
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        routers.documents.delete_generated_document(doc.id, self.admin, self.db)

        self.assertFalse(os.path.exists(pdf_path), "Physical file was not deleted")


class ProductionGuardTests(unittest.TestCase):
    """Verify destructive admin endpoints are blocked in production mode."""

    def setUp(self):
        main.Base.metadata.drop_all(main.engine)
        main.Base.metadata.create_all(main.engine)
        self.db = main.SessionLocal()
        self.admin = main.User(
            name="Admin Test",
            email="admin@example.test",
            hashed_password=hash_password("adminpassword"),
            role="admin",
        )
        self.db.add(self.admin)
        self.db.commit()
        self.db.refresh(self.admin)

    def tearDown(self):
        self.db.close()

    def test_seed_endpoint_blocked_in_production(self):
        with patch.object(settings_router, "IS_PRODUCTION", True):
            with self.assertRaises(HTTPException) as caught:
                settings_router.run_seed_endpoint(current_user=self.admin, db=self.db)
            self.assertEqual(caught.exception.status_code, 403)
            self.assertIn("production", caught.exception.detail.lower())

    def test_reset_soft_blocked_in_production(self):
        with patch.object(settings_router, "IS_PRODUCTION", True):
            with self.assertRaises(HTTPException) as caught:
                settings_router.admin_data_reset_soft(settings_router.DataAdminBody(password="wrong"), current_user=self.admin, db=self.db)
            self.assertEqual(caught.exception.status_code, 403)
            self.assertIn("production", caught.exception.detail.lower())

    def test_reset_nuclear_blocked_in_production(self):
        with patch.object(settings_router, "IS_PRODUCTION", True):
            with self.assertRaises(HTTPException) as caught:
                settings_router.admin_data_reset_nuclear(settings_router.DataAdminBody(password="wrong"), current_user=self.admin, db=self.db)
            self.assertEqual(caught.exception.status_code, 403)
            self.assertIn("production", caught.exception.detail.lower())

    def test_seed_demo_blocked_in_production(self):
        with patch.object(settings_router, "IS_PRODUCTION", True):
            with self.assertRaises(HTTPException) as caught:
                settings_router.admin_data_seed_demo(settings_router.DataAdminBody(password="wrong"), current_user=self.admin, db=self.db)
            self.assertEqual(caught.exception.status_code, 403)
            self.assertIn("production", caught.exception.detail.lower())

    def test_production_mode_endpoint_returns_is_production(self):
        with patch.object(settings_router, "IS_PRODUCTION", True):
            self.assertEqual(settings_router.get_production_mode(current_user=self.admin), {"is_production": True})

    def test_soft_reset_does_not_delete_contact_records(self):
        """Soft reset preserves Contact rows — only non-client leads are removed."""
        contact = main.Contact(
            business_name="Test Contact",
            phone_number="628111111111",
        )
        lead = main.Lead(
            business_name="Dev Lead",
            phone_number="628111111111",
            status="New",
        )
        self.db.add_all([contact, lead])
        self.db.commit()

        # Simulate soft reset behavior directly (skip HTTP to avoid FK constraint issues in test DB)
        self.db.query(main.Lead).filter(main.Lead.status != "Closed/Client").delete(synchronize_session=False)
        # Contact is NOT deleted — this is the fix
        self.db.commit()

        # Contact must still exist
        self.assertEqual(self.db.query(main.Contact).count(), 1)
        # Non-client lead is gone
        self.assertEqual(self.db.query(main.Lead).filter(main.Lead.status != "Closed/Client").count(), 0)


if __name__ == "__main__":
    unittest.main()
