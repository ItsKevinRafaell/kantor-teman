"""initial - Create all tables from models"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "125ed4a3a428"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Create all tables from models.

    For existing databases (tables already exist):
      1. Run: alembic stamp head
      2. All future changes: alembic revision --autogenerate && alembic upgrade head

    For fresh databases (empty):
      1. Just run: alembic upgrade head
    """
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS ads_campaigns (
    "id" VARCHAR(36) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "target_audience" VARCHAR(255) NOT NULL,
    "budget" FLOAT NOT NULL,
    "drive_link" VARCHAR(255) NULL,
    "leads_count" INTEGER NULL,
    "conversions_count" INTEGER NULL,
    "status" VARCHAR(255) NOT NULL,
    "created_at" VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS ai_models (
    "id" VARCHAR(36) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "model_id" VARCHAR(255) NOT NULL,
    "description" TEXT NULL,
    "capabilities" TEXT NOT NULL,
    "is_active" INTEGER NULL,
    "is_default_chat" INTEGER NULL,
    "is_default_image" INTEGER NULL,
    "is_default_article" INTEGER NULL,
    "is_default_analysis" INTEGER NULL,
    "created_at" VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS ai_proxies (
    "id" VARCHAR(36) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "base_url" VARCHAR(500) NOT NULL,
    "api_key" VARCHAR(500) NULL,
    "model" VARCHAR(255) NULL,
    "provider" VARCHAR(50) NOT NULL,
    "feature" VARCHAR(50) NULL,
    "is_active" BOOLEAN NULL,
    "created_at" VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_ai_proxies_feature ON ai_proxies ("feature")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS audit_logs (
    "id" INTEGER NOT NULL,
    "timestamp" VARCHAR(255) NOT NULL,
    "actor" VARCHAR(255) NOT NULL,
    "action" VARCHAR(255) NOT NULL,
    "table_name" VARCHAR(255) NOT NULL,
    "record_id" VARCHAR(255) NOT NULL,
    "details" TEXT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS brand_kits (
    "id" VARCHAR(36) NOT NULL,
    "kit_name" VARCHAR(255) NOT NULL,
    "is_active" BOOLEAN NULL,
    "created_at" VARCHAR(255) NOT NULL,
    "brand_name" VARCHAR(255) NULL,
    "tagline" VARCHAR(255) NULL,
    "phone" VARCHAR(50) NULL,
    "email" VARCHAR(255) NULL,
    "address" TEXT NULL,
    "logo" TEXT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS categories (
    "id" VARCHAR(36) NOT NULL,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "description" TEXT NULL,
    "is_active" BOOLEAN NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE UNIQUE INDEX IF NOT EXISTS uq_categories_name ON categories ("name")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS content_providers (
    "id" VARCHAR(36) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "tool_type" VARCHAR(50) NOT NULL,
    "base_url" VARCHAR(500) NOT NULL,
    "api_key" VARCHAR(500) NULL,
    "model" VARCHAR(255) NOT NULL,
    "extra_params" TEXT NULL,
    "is_active" BOOLEAN NULL,
    "created_at" VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS content_schedules (
    "id" VARCHAR(36) NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "type" VARCHAR(255) NOT NULL,
    "schedule_date" VARCHAR(255) NOT NULL,
    "google_event_id" VARCHAR(255) NULL,
    "status" VARCHAR(255) NOT NULL,
    "created_at" VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS document_sequences (
    "id" INTEGER NOT NULL,
    "target_id" VARCHAR(255) NOT NULL,
    "template_type" VARCHAR(50) NOT NULL,
    "last_seq" INTEGER NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS document_templates (
    "id" VARCHAR(36) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "type" VARCHAR(50) NOT NULL,
    "html_template" TEXT NOT NULL,
    "variables" TEXT NULL,
    "is_active" BOOLEAN NULL,
    "created_at" VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS leads (
    "id" INTEGER NOT NULL,
    "business_name" VARCHAR(255) NOT NULL,
    "phone_number" VARCHAR(255) NOT NULL UNIQUE,
    "address" VARCHAR(255) NULL,
    "original_url" VARCHAR(255) NULL,
    "status" VARCHAR(255) NOT NULL,
    "product_interest" VARCHAR(255) NULL,
    "batch_name" VARCHAR(255) NULL,
    "rating" INTEGER NULL,
    "is_archived" BOOLEAN NULL,
    "deleted_at" VARCHAR(255) NULL,
    "lead_score" INTEGER NULL,
    "website_url" VARCHAR(500) NULL,
    "google_rating" FLOAT NULL,
    "review_count" INTEGER NULL,
    "latitude" FLOAT NULL,
    "longitude" FLOAT NULL,
    "last_followup_at" VARCHAR(255) NULL,
    "sales_owner" VARCHAR(255) NULL,
    "next_action_at" VARCHAR(255) NULL,
    "loss_reason" VARCHAR(500) NULL,
    "do_not_contact" BOOLEAN NOT NULL,
    "score_adjustment" INTEGER NOT NULL,
    "score_adjustment_reason" VARCHAR(500) NULL,
    "score_updated_at" VARCHAR(255) NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE UNIQUE INDEX IF NOT EXISTS uq_leads_phone_number ON leads ("phone_number")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS message_templates (
    "id" INTEGER NOT NULL,
    "product_category" VARCHAR(255) NOT NULL,
    "variant_name" VARCHAR(255) NOT NULL,
    "content" TEXT NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    "id" VARCHAR(36) NOT NULL,
    "user_id" INTEGER NOT NULL,
    "token_hash" VARCHAR(64) NOT NULL UNIQUE,
    "expires_at" VARCHAR(255) NOT NULL,
    "used_at" VARCHAR(255) NULL,
    "created_at" VARCHAR(255) NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE UNIQUE INDEX IF NOT EXISTS ix_password_reset_tokens_token_hash ON password_reset_tokens ("token_hash")'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_password_reset_tokens_user_id ON password_reset_tokens ("user_id")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS payment_methods (
    "id" INTEGER NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "account_number" VARCHAR(255) NULL,
    "account_name" VARCHAR(255) NULL,
    "notes" TEXT NULL,
    "is_active" BOOLEAN NULL,
    "position" INTEGER NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS provider_configs (
    "id" VARCHAR(36) NOT NULL,
    "provider_name" VARCHAR(255) NOT NULL,
    "remaining_quota" FLOAT NULL,
    "monthly_quota" FLOAT NULL,
    "price_per_unit_idr" FLOAT NULL,
    "price_input_token_usd" FLOAT NULL,
    "price_output_token_usd" FLOAT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS rate_limits (
    "id" INTEGER NOT NULL,
    "ip" VARCHAR(45) NULL,
    "key" VARCHAR(255) NOT NULL,
    "ts" DATETIME NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_rate_limits_key ON rate_limits ("key")'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_rate_limits_key_ts ON rate_limits ("key", "ts")'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_rate_limits_ip ON rate_limits ("ip")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS scrape_history (
    "id" INTEGER NOT NULL,
    "category" VARCHAR(255) NOT NULL,
    "location" VARCHAR(255) NOT NULL,
    "product_interest" VARCHAR(255) NULL,
    "results_count" INTEGER NULL,
    "scraped_at" VARCHAR(255) NOT NULL,
    "batch_name" VARCHAR(255) NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS service_items (
    "id" VARCHAR(36) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "default_price" FLOAT NOT NULL,
    "default_features" TEXT NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS system_settings (
    "id" INTEGER NOT NULL,
    "key" VARCHAR(255) NOT NULL UNIQUE,
    "value" TEXT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE UNIQUE INDEX IF NOT EXISTS uq_system_settings_key ON system_settings ("key")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS users (
    "id" INTEGER NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "hashed_password" VARCHAR(255) NOT NULL,
    "role" VARCHAR(50) NOT NULL,
    "token_version" INTEGER NOT NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users ("email")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS wallets (
    "id" INTEGER NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "balance" FLOAT NOT NULL,
    "icon" VARCHAR(255) NULL,
    "color" VARCHAR(255) NULL,
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS brand_assets (
    "id" VARCHAR(36) NOT NULL,
    "kit_id" VARCHAR(36) NOT NULL,
    "asset_type" VARCHAR(50) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "value" TEXT NULL,
    "file_url" VARCHAR(500) NULL,
    "position" INTEGER NULL,
    "asset_metadata" TEXT NULL,
    FOREIGN KEY (kit_id) REFERENCES brand_kits(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS client_credentials (
    "id" VARCHAR(36) NOT NULL,
    "lead_id" INTEGER NULL,
    "category" VARCHAR(255) NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "fields" TEXT NOT NULL,
    "created_at" VARCHAR(255) NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS client_documents (
    "id" VARCHAR(36) NOT NULL,
    "lead_id" INTEGER NULL,
    "title" VARCHAR(255) NOT NULL,
    "cloud_url" VARCHAR(255) NOT NULL,
    "created_at" VARCHAR(255) NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS client_notes (
    "id" VARCHAR(36) NOT NULL,
    "lead_id" INTEGER NOT NULL,
    "timestamp" VARCHAR(255) NOT NULL,
    "actor" VARCHAR(255) NOT NULL,
    "category" VARCHAR(255) NOT NULL,
    "content" TEXT NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS contacts (
    "id" INTEGER NOT NULL,
    "business_name" VARCHAR(255) NOT NULL,
    "owner_name" VARCHAR(255) NULL,
    "phone_number" VARCHAR(255) NOT NULL UNIQUE,
    "purchased_product" VARCHAR(255) NULL,
    "notes" TEXT NULL,
    "lead_id" INTEGER NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE UNIQUE INDEX IF NOT EXISTS uq_contacts_phone_number ON contacts ("phone_number")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS content_sessions (
    "id" VARCHAR(36) NOT NULL,
    "user_id" INTEGER NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT NULL,
    "created_at" VARCHAR(255) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS document_folders (
    "id" VARCHAR(36) NOT NULL,
    "user_id" INTEGER NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "parent_id" VARCHAR(36) NULL,
    "color" VARCHAR(20) NOT NULL,
    "created_at" VARCHAR(255) NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES document_folders(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS dynamic_templates (
    "id" VARCHAR(36) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "type" VARCHAR(255) NOT NULL,
    "content" TEXT NOT NULL,
    "is_active" BOOLEAN NULL,
    "category_id" VARCHAR(36) NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS followup_sequences (
    "id" VARCHAR(36) NOT NULL,
    "lead_id" INTEGER NOT NULL,
    "template_ids" TEXT NOT NULL,
    "delays" TEXT NOT NULL,
    "current_step" INTEGER NULL,
    "status" VARCHAR(255) NULL,
    "started_at" VARCHAR(255) NOT NULL,
    "next_send_at" VARCHAR(255) NULL,
    "stopped_reason" VARCHAR(255) NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS generated_documents (
    "id" VARCHAR(36) NOT NULL,
    "template_id" VARCHAR(36) NULL,
    "template_name" VARCHAR(255) NULL,
    "target_type" VARCHAR(50) NULL,
    "target_id" VARCHAR(255) NULL,
    "variables_used" TEXT NULL,
    "file_url" VARCHAR(500) NULL,
    "display_filename" VARCHAR(500) NULL,
    "status" VARCHAR(50) NOT NULL,
    "payment_status" VARCHAR(50) NULL,
    "review_notes" TEXT NULL,
    "approved_at" VARCHAR(255) NULL,
    "rejected_at" VARCHAR(255) NULL,
    "sent_at" VARCHAR(255) NULL,
    "signed_at" VARCHAR(255) NULL,
    "archived_at" VARCHAR(255) NULL,
    "generated_at" VARCHAR(255) NOT NULL,
    "generated_by" VARCHAR(255) NULL,
    FOREIGN KEY (template_id) REFERENCES document_templates(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS lead_activity_logs (
    "id" VARCHAR(36) NOT NULL,
    "lead_id" INTEGER NOT NULL,
    "activity_type" VARCHAR(255) NOT NULL,
    "created_at" VARCHAR(255) NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS lead_analyses (
    "id" INTEGER NOT NULL,
    "lead_id" INTEGER NOT NULL,
    "analysis" TEXT NOT NULL,
    "pain_points" TEXT NULL,
    "suggested_product" VARCHAR(255) NULL,
    "analyzed_at" VARCHAR(255) NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS notifications (
    "id" VARCHAR(36) NOT NULL,
    "user_id" INTEGER NULL,
    "title" VARCHAR(255) NOT NULL,
    "message" TEXT NOT NULL,
    "type" VARCHAR(50) NOT NULL,
    "target_type" VARCHAR(50) NULL,
    "target_id" VARCHAR(255) NULL,
    "action_url" VARCHAR(1000) NULL,
    "is_read" BOOLEAN NOT NULL,
    "created_at" VARCHAR(255) NOT NULL,
    "read_at" VARCHAR(255) NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS products (
    "id" VARCHAR(36) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT NULL,
    "base_price" FLOAT NOT NULL,
    "features" TEXT NOT NULL,
    "category" VARCHAR(255) NULL,
    "category_id" VARCHAR(36) NULL,
    "is_active" BOOLEAN NULL,
    "is_retainer" BOOLEAN NULL,
    "monthly_ads_cost" FLOAT NULL,
    "roi_months" INTEGER NULL,
    "roi_multiplier" FLOAT NULL,
    "comparison_points" TEXT NULL,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS projects (
    "id" VARCHAR(36) NOT NULL,
    "lead_id" INTEGER NULL,
    "name" VARCHAR(255) NOT NULL,
    "type" VARCHAR(255) NOT NULL,
    "status" VARCHAR(255) NOT NULL,
    "nominal" FLOAT NOT NULL,
    "start_date" VARCHAR(255) NULL,
    "end_date" VARCHAR(255) NULL,
    "color" VARCHAR(50) NULL,
    "is_archived" BOOLEAN NOT NULL,
    "service_type" VARCHAR(50) NULL,
    "contract_months" INTEGER NULL,
    "dp_percent" FLOAT NULL,
    "monthly_invoice_enabled" BOOLEAN NOT NULL,
    "next_invoice_date" VARCHAR(255) NULL,
    "completed_at" VARCHAR(255) NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS proposals (
    "id" VARCHAR(36) NOT NULL,
    "lead_id" INTEGER NOT NULL,
    "services_detail" TEXT NOT NULL,
    "total_price" FLOAT NOT NULL,
    "additional_options" TEXT NULL,
    "status" VARCHAR(255) NOT NULL,
    "created_at" VARCHAR(255) NULL,
    "is_archived" BOOLEAN NULL,
    "deleted_at" VARCHAR(255) NULL,
    "slug" VARCHAR(255) NULL UNIQUE,
    "base_price" FLOAT NULL,
    "discount_price" FLOAT NULL,
    "discount_expires_at" VARCHAR(255) NULL,
    "first_viewed_at" VARCHAR(255) NULL,
    "faqs" TEXT NULL,
    "selected_addons" TEXT NULL,
    "timeline_data" TEXT NULL,
    "roi_data" TEXT NULL,
    "accepted_at" VARCHAR(255) NULL,
    "rejected_at" VARCHAR(255) NULL,
    "report_open_count" INTEGER NOT NULL,
    "last_report_viewed_at" VARCHAR(255) NULL,
    "max_report_duration_seconds" INTEGER NOT NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE UNIQUE INDEX IF NOT EXISTS uq_proposals_slug ON proposals ("slug")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS subscriptions (
    "id" INTEGER NOT NULL,
    "wallet_id" INTEGER NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "amount" FLOAT NOT NULL,
    "billing_cycle" VARCHAR(255) NOT NULL,
    "next_billing_date" VARCHAR(255) NOT NULL,
    "is_active" BOOLEAN NULL,
    FOREIGN KEY (wallet_id) REFERENCES wallets(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS transactions (
    "id" INTEGER NOT NULL,
    "wallet_id" INTEGER NOT NULL,
    "type" VARCHAR(255) NOT NULL,
    "amount" FLOAT NOT NULL,
    "category" VARCHAR(255) NULL,
    "date" VARCHAR(255) NOT NULL,
    "notes" TEXT NULL,
    "lead_id" INTEGER NULL,
    "is_billed" BOOLEAN NULL,
    "is_archived" BOOLEAN NULL,
    "deleted_at" VARCHAR(255) NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    FOREIGN KEY (wallet_id) REFERENCES wallets(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS blast_campaigns (
    "id" VARCHAR(36) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "template_id" VARCHAR(36) NULL,
    "filter_criteria" TEXT NOT NULL,
    "scheduled_for" VARCHAR(255) NOT NULL,
    "status" VARCHAR(255) NOT NULL,
    "sent_count" INTEGER NULL,
    "failed_count" INTEGER NULL,
    "total_operational_cost_idr" FLOAT NULL,
    "converted_clients_count" INTEGER NULL,
    "created_at" VARCHAR(255) NOT NULL,
    FOREIGN KEY (template_id) REFERENCES dynamic_templates(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS boards (
    "id" VARCHAR(36) NOT NULL,
    "project_id" VARCHAR(36) NOT NULL,
    "created_at" VARCHAR(255) NULL,
    "color" VARCHAR(50) NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS content_generations (
    "id" VARCHAR(36) NOT NULL,
    "user_id" INTEGER NOT NULL,
    "session_id" VARCHAR(36) NULL,
    "tool_type" VARCHAR(50) NOT NULL,
    "input_data" TEXT NOT NULL,
    "output_data" TEXT NULL,
    "model_used" VARCHAR(255) NULL,
    "provider_name" VARCHAR(255) NULL,
    "status" VARCHAR(50) NOT NULL,
    "error_msg" TEXT NULL,
    "created_at" VARCHAR(255) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (session_id) REFERENCES content_sessions(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS documents (
    "id" VARCHAR(36) NOT NULL,
    "user_id" INTEGER NOT NULL,
    "folder_id" VARCHAR(36) NULL,
    "name" VARCHAR(255) NOT NULL,
    "type" VARCHAR(50) NOT NULL,
    "content" TEXT NULL,
    "file_size" INTEGER NULL,
    "title" VARCHAR(500) NOT NULL,
    "body" TEXT NULL,
    "url" VARCHAR(2000) NULL,
    "tags" TEXT NOT NULL,
    "status" VARCHAR(50) NOT NULL,
    "review_notes" TEXT NULL,
    "approved_at" VARCHAR(255) NULL,
    "rejected_at" VARCHAR(255) NULL,
    "sent_at" VARCHAR(255) NULL,
    "signed_at" VARCHAR(255) NULL,
    "archived_at" VARCHAR(255) NULL,
    "source_type" VARCHAR(50) NULL,
    "source_id" VARCHAR(255) NULL,
    "created_at" VARCHAR(255) NOT NULL,
    "updated_at" VARCHAR(255) NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (folder_id) REFERENCES document_folders(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS proposal_analytics (
    "id" VARCHAR(36) NOT NULL,
    "proposal_id" VARCHAR(36) NOT NULL,
    "opened_at" VARCHAR(255) NOT NULL,
    "last_ping" VARCHAR(255) NULL,
    "total_time_seconds" INTEGER NULL,
    "sections_viewed" TEXT NULL,
    "event" VARCHAR(50) NULL,
    "duration_seconds" INTEGER NULL,
    "visitor_hash" VARCHAR(64) NULL,
    "source" VARCHAR(50) NULL,
    "metadata_json" TEXT NULL,
    FOREIGN KEY (proposal_id) REFERENCES proposals(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS reengagement_alerts (
    "id" VARCHAR(36) NOT NULL,
    "lead_id" INTEGER NOT NULL,
    "proposal_id" VARCHAR(36) NOT NULL,
    "triggered_at" VARCHAR(255) NOT NULL,
    "is_read" BOOLEAN NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    FOREIGN KEY (proposal_id) REFERENCES proposals(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS report_snapshots (
    "id" VARCHAR(36) NOT NULL,
    "report_type" VARCHAR(50) NOT NULL,
    "target_type" VARCHAR(50) NOT NULL,
    "target_id" VARCHAR(255) NULL,
    "project_id" VARCHAR(36) NULL,
    "lead_id" INTEGER NULL,
    "service_type" VARCHAR(50) NULL,
    "title" VARCHAR(500) NOT NULL,
    "period_start" VARCHAR(50) NULL,
    "period_end" VARCHAR(50) NULL,
    "month_number" INTEGER NULL,
    "metrics_json" TEXT NOT NULL,
    "evidence_json" TEXT NOT NULL,
    "narrative_json" TEXT NOT NULL,
    "public_slug" VARCHAR(255) NULL UNIQUE,
    "public_enabled" BOOLEAN NOT NULL,
    "open_count" INTEGER NOT NULL,
    "first_viewed_at" VARCHAR(255) NULL,
    "last_viewed_at" VARCHAR(255) NULL,
    "max_duration_seconds" INTEGER NOT NULL,
    "generated_document_id" VARCHAR(36) NULL,
    "status" VARCHAR(50) NOT NULL,
    "generated_by" VARCHAR(255) NULL,
    "created_at" VARCHAR(255) NOT NULL,
    "updated_at" VARCHAR(255) NULL,
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    FOREIGN KEY (generated_document_id) REFERENCES generated_documents(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE UNIQUE INDEX IF NOT EXISTS ix_report_snapshots_public_slug ON report_snapshots ("public_slug")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS workspace_sheets (
    "id" VARCHAR(36) NOT NULL,
    "project_id" VARCHAR(36) NOT NULL,
    "sheet_index" INTEGER NOT NULL,
    "sheet_label" VARCHAR(100) NOT NULL,
    "service_type" VARCHAR(50) NULL,
    "month_number" INTEGER NULL,
    "created_at" VARCHAR(255) NOT NULL,
    "updated_at" VARCHAR(255) NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_workspace_sheets_project_id ON workspace_sheets ("project_id")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS blast_messages (
    "id" VARCHAR(36) NOT NULL,
    "campaign_id" VARCHAR(36) NULL,
    "lead_id" INTEGER NOT NULL,
    "template_id" VARCHAR(36) NULL,
    "phone_number" VARCHAR(255) NOT NULL,
    "sent_at" VARCHAR(255) NOT NULL,
    "delivered_at" VARCHAR(255) NULL,
    "read_at" VARCHAR(255) NULL,
    "replied_at" VARCHAR(255) NULL,
    "status" VARCHAR(50) NOT NULL,
    "error_message" TEXT NULL,
    FOREIGN KEY (campaign_id) REFERENCES blast_campaigns(id),
    FOREIGN KEY (template_id) REFERENCES dynamic_templates(id),
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_blast_messages_lead_id ON blast_messages ("lead_id")'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_blast_messages_phone_number ON blast_messages ("phone_number")'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_blast_messages_template_id ON blast_messages ("template_id")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS board_columns (
    "id" VARCHAR(36) NOT NULL,
    "board_id" VARCHAR(36) NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "position" INTEGER NULL,
    "color" VARCHAR(50) NULL,
    FOREIGN KEY (board_id) REFERENCES boards(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS workspace_columns (
    "id" VARCHAR(36) NOT NULL,
    "sheet_id" VARCHAR(36) NOT NULL,
    "column_key" VARCHAR(100) NOT NULL,
    "column_label" VARCHAR(100) NOT NULL,
    "column_type" VARCHAR(30) NOT NULL,
    "column_options" TEXT NULL,
    "column_order" INTEGER NOT NULL,
    "is_system" BOOLEAN NULL,
    "created_at" VARCHAR(255) NOT NULL,
    FOREIGN KEY (sheet_id) REFERENCES workspace_sheets(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_workspace_columns_sheet_id ON workspace_columns ("sheet_id")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS board_cards (
    "id" VARCHAR(36) NOT NULL,
    "column_id" VARCHAR(36) NOT NULL,
    "title" VARCHAR(255) NOT NULL,
    "description" TEXT NULL,
    "assignee" VARCHAR(255) NULL,
    "due_date" VARCHAR(255) NULL,
    "labels" TEXT NULL,
    "position" INTEGER NULL,
    "is_archived" BOOLEAN NULL,
    "created_at" VARCHAR(255) NULL,
    "updated_at" VARCHAR(255) NULL,
    "lead_id" INTEGER NULL,
    "color" VARCHAR(50) NULL,
    FOREIGN KEY (column_id) REFERENCES board_columns(id),
    FOREIGN KEY (lead_id) REFERENCES leads(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS board_card_activities (
    "id" VARCHAR(36) NOT NULL,
    "card_id" VARCHAR(36) NOT NULL,
    "action" VARCHAR(255) NOT NULL,
    "description" VARCHAR(255) NOT NULL,
    "actor" VARCHAR(255) NOT NULL,
    "created_at" VARCHAR(255) NULL,
    FOREIGN KEY (card_id) REFERENCES board_cards(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS board_card_attachments (
    "id" VARCHAR(36) NOT NULL,
    "card_id" VARCHAR(36) NOT NULL,
    "file_path" VARCHAR(500) NOT NULL,
    "file_name" VARCHAR(255) NOT NULL,
    "file_type" VARCHAR(100) NULL,
    "uploaded_by" VARCHAR(255) NULL,
    "uploaded_at" VARCHAR(255) NULL,
    FOREIGN KEY (card_id) REFERENCES board_cards(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS board_card_checklists (
    "id" VARCHAR(36) NOT NULL,
    "card_id" VARCHAR(36) NOT NULL,
    "text" VARCHAR(255) NOT NULL,
    "is_done" BOOLEAN NULL,
    "position" INTEGER NULL,
    FOREIGN KEY (card_id) REFERENCES board_cards(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS board_card_comments (
    "id" VARCHAR(36) NOT NULL,
    "card_id" VARCHAR(36) NOT NULL,
    "author" VARCHAR(255) NOT NULL,
    "content" TEXT NOT NULL,
    "created_at" VARCHAR(255) NULL,
    FOREIGN KEY (card_id) REFERENCES board_cards(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS workspace_rows (
    "id" VARCHAR(36) NOT NULL,
    "sheet_id" VARCHAR(36) NOT NULL,
    "row_order" INTEGER NOT NULL,
    "board_card_id" VARCHAR(36) NULL,
    "is_template" BOOLEAN NULL,
    "created_at" VARCHAR(255) NOT NULL,
    "updated_at" VARCHAR(255) NULL,
    FOREIGN KEY (board_card_id) REFERENCES board_cards(id),
    FOREIGN KEY (sheet_id) REFERENCES workspace_sheets(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_workspace_rows_sheet_id ON workspace_rows ("sheet_id")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS workspace_attachments (
    "id" VARCHAR(36) NOT NULL,
    "row_id" VARCHAR(36) NOT NULL,
    "column_id" VARCHAR(36) NOT NULL,
    "file_path" VARCHAR(500) NOT NULL,
    "file_name" VARCHAR(255) NOT NULL,
    "file_type" VARCHAR(100) NULL,
    "uploaded_at" VARCHAR(255) NOT NULL,
    FOREIGN KEY (row_id) REFERENCES workspace_rows(id),
    FOREIGN KEY (column_id) REFERENCES workspace_columns(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_workspace_attachments_row_id ON workspace_attachments ("row_id")'''))
    op.execute(sa.text('''
CREATE TABLE IF NOT EXISTS workspace_cells (
    "id" VARCHAR(36) NOT NULL,
    "row_id" VARCHAR(36) NOT NULL,
    "column_id" VARCHAR(36) NOT NULL,
    "value_text" TEXT NULL,
    "value_bool" BOOLEAN NULL,
    "value_number" FLOAT NULL,
    "value_date" VARCHAR(50) NULL,
    "value_json" TEXT NULL,
    "updated_at" VARCHAR(255) NULL,
    FOREIGN KEY (column_id) REFERENCES workspace_columns(id),
    FOREIGN KEY (row_id) REFERENCES workspace_rows(id),
    PRIMARY KEY (id)
)'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_workspace_cells_row_id ON workspace_cells ("row_id")'''))
    op.execute(sa.text('''CREATE INDEX IF NOT EXISTS ix_workspace_cells_column_id ON workspace_cells ("column_id")'''))

def downgrade() -> None:
    """Drop all tables."""
    op.execute(sa.text('DROP TABLE IF EXISTS workspace_cells'))
    op.execute(sa.text('DROP TABLE IF EXISTS workspace_attachments'))
    op.execute(sa.text('DROP TABLE IF EXISTS workspace_rows'))
    op.execute(sa.text('DROP TABLE IF EXISTS board_card_comments'))
    op.execute(sa.text('DROP TABLE IF EXISTS board_card_checklists'))
    op.execute(sa.text('DROP TABLE IF EXISTS board_card_attachments'))
    op.execute(sa.text('DROP TABLE IF EXISTS board_card_activities'))
    op.execute(sa.text('DROP TABLE IF EXISTS board_cards'))
    op.execute(sa.text('DROP TABLE IF EXISTS workspace_columns'))
    op.execute(sa.text('DROP TABLE IF EXISTS board_columns'))
    op.execute(sa.text('DROP TABLE IF EXISTS blast_messages'))
    op.execute(sa.text('DROP TABLE IF EXISTS workspace_sheets'))
    op.execute(sa.text('DROP TABLE IF EXISTS report_snapshots'))
    op.execute(sa.text('DROP TABLE IF EXISTS reengagement_alerts'))
    op.execute(sa.text('DROP TABLE IF EXISTS proposal_analytics'))
    op.execute(sa.text('DROP TABLE IF EXISTS documents'))
    op.execute(sa.text('DROP TABLE IF EXISTS content_generations'))
    op.execute(sa.text('DROP TABLE IF EXISTS boards'))
    op.execute(sa.text('DROP TABLE IF EXISTS blast_campaigns'))
    op.execute(sa.text('DROP TABLE IF EXISTS transactions'))
    op.execute(sa.text('DROP TABLE IF EXISTS subscriptions'))
    op.execute(sa.text('DROP TABLE IF EXISTS proposals'))
    op.execute(sa.text('DROP TABLE IF EXISTS projects'))
    op.execute(sa.text('DROP TABLE IF EXISTS products'))
    op.execute(sa.text('DROP TABLE IF EXISTS notifications'))
    op.execute(sa.text('DROP TABLE IF EXISTS lead_analyses'))
    op.execute(sa.text('DROP TABLE IF EXISTS lead_activity_logs'))
    op.execute(sa.text('DROP TABLE IF EXISTS generated_documents'))
    op.execute(sa.text('DROP TABLE IF EXISTS followup_sequences'))
    op.execute(sa.text('DROP TABLE IF EXISTS dynamic_templates'))
    op.execute(sa.text('DROP TABLE IF EXISTS document_folders'))
    op.execute(sa.text('DROP TABLE IF EXISTS content_sessions'))
    op.execute(sa.text('DROP TABLE IF EXISTS contacts'))
    op.execute(sa.text('DROP TABLE IF EXISTS client_notes'))
    op.execute(sa.text('DROP TABLE IF EXISTS client_documents'))
    op.execute(sa.text('DROP TABLE IF EXISTS client_credentials'))
    op.execute(sa.text('DROP TABLE IF EXISTS brand_assets'))
    op.execute(sa.text('DROP TABLE IF EXISTS wallets'))
    op.execute(sa.text('DROP TABLE IF EXISTS users'))
    op.execute(sa.text('DROP TABLE IF EXISTS system_settings'))
    op.execute(sa.text('DROP TABLE IF EXISTS service_items'))
    op.execute(sa.text('DROP TABLE IF EXISTS scrape_history'))
    op.execute(sa.text('DROP TABLE IF EXISTS rate_limits'))
    op.execute(sa.text('DROP TABLE IF EXISTS provider_configs'))
    op.execute(sa.text('DROP TABLE IF EXISTS payment_methods'))
    op.execute(sa.text('DROP TABLE IF EXISTS password_reset_tokens'))
    op.execute(sa.text('DROP TABLE IF EXISTS message_templates'))
    op.execute(sa.text('DROP TABLE IF EXISTS leads'))
    op.execute(sa.text('DROP TABLE IF EXISTS document_templates'))
    op.execute(sa.text('DROP TABLE IF EXISTS document_sequences'))
    op.execute(sa.text('DROP TABLE IF EXISTS content_schedules'))
    op.execute(sa.text('DROP TABLE IF EXISTS content_providers'))
    op.execute(sa.text('DROP TABLE IF EXISTS categories'))
    op.execute(sa.text('DROP TABLE IF EXISTS brand_kits'))
    op.execute(sa.text('DROP TABLE IF EXISTS audit_logs'))
    op.execute(sa.text('DROP TABLE IF EXISTS ai_proxies'))
    op.execute(sa.text('DROP TABLE IF EXISTS ai_models'))
    op.execute(sa.text('DROP TABLE IF EXISTS ads_campaigns'))