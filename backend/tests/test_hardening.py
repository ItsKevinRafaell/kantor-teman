import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime

from cryptography.fernet import Fernet
from fastapi import HTTPException


TEST_DIR = tempfile.mkdtemp(prefix="kantorteman-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DIR}/test.db"
os.environ["SECRET_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["JWT_SECRET"] = "test-secret-at-least-16-chars"
os.environ["ENABLE_BACKGROUND_SCHEDULER"] = "false"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import main  # noqa: E402


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

    def test_folder_delete_keeps_docs_and_moves_children_to_root(self):
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

        main.delete_archive_folder(parent.id, current_user=self.admin, db=self.db)

        self.assertIsNone(self.db.query(main.Document).filter(main.Document.id == doc.id).one().folder_id)
        self.assertIsNone(self.db.query(main.DocumentFolder).filter(main.DocumentFolder.id == child.id).one().parent_id)

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


if __name__ == "__main__":
    unittest.main()
