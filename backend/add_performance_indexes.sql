-- Performance Optimization: Add indexes for frequently queried columns
-- For PostgreSQL: psql $DATABASE_URL < add_performance_indexes.sql
-- For MySQL: mysql -h localhost -u USER -p DATABASE < add_performance_indexes.sql

-- Foreign key indexes
CREATE INDEX IF NOT EXISTS idx_proposals_lead_id ON proposals(lead_id);
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_folder_id ON documents(folder_id);
CREATE INDEX IF NOT EXISTS idx_brand_assets_kit_id ON brand_assets(kit_id);
CREATE INDEX IF NOT EXISTS idx_generated_documents_template_id ON generated_documents(template_id);
CREATE INDEX IF NOT EXISTS idx_transactions_lead_id ON transactions(lead_id);
CREATE INDEX IF NOT EXISTS idx_transactions_wallet_id ON transactions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_wallet_id ON subscriptions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_board_columns_board_id ON board_columns(board_id);
CREATE INDEX IF NOT EXISTS idx_board_cards_column_id ON board_cards(column_id);
CREATE INDEX IF NOT EXISTS idx_board_cards_lead_id ON board_cards(lead_id);
CREATE INDEX IF NOT EXISTS idx_board_card_comments_card_id ON board_card_comments(card_id);
CREATE INDEX IF NOT EXISTS idx_board_card_checklist_card_id ON board_card_checklist(card_id);
CREATE INDEX IF NOT EXISTS idx_board_card_activity_card_id ON board_card_activity(card_id);
CREATE INDEX IF NOT EXISTS idx_workspace_sheets_project_id ON workspace_sheets(project_id);
CREATE INDEX IF NOT EXISTS idx_workspace_columns_sheet_id ON workspace_columns(sheet_id);
CREATE INDEX IF NOT EXISTS idx_workspace_rows_sheet_id ON workspace_rows(sheet_id);
CREATE INDEX IF NOT EXISTS idx_workspace_cells_row_id ON workspace_cells(row_id);
CREATE INDEX IF NOT EXISTS idx_workspace_cells_column_id ON workspace_cells(column_id);
CREATE INDEX IF NOT EXISTS idx_workspace_attachments_row_id ON workspace_attachments(row_id);
CREATE INDEX IF NOT EXISTS idx_content_generations_session_id ON content_generations(session_id);
CREATE INDEX IF NOT EXISTS idx_content_generations_user_id ON content_generations(user_id);
CREATE INDEX IF NOT EXISTS idx_content_sessions_user_id ON content_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_proposal_analytics_proposal_id ON proposal_analytics(proposal_id);
CREATE INDEX IF NOT EXISTS idx_lead_activity_log_lead_id ON lead_activity_log(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_analysis_lead_id ON lead_analysis(lead_id);
CREATE INDEX IF NOT EXISTS idx_projects_lead_id ON projects(lead_id);
CREATE INDEX IF NOT EXISTS idx_client_notes_lead_id ON client_notes(lead_id);
CREATE INDEX IF NOT EXISTS idx_client_credentials_lead_id ON client_credentials(lead_id);
CREATE INDEX IF NOT EXISTS idx_client_documents_lead_id ON client_documents(lead_id);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_proposals_archived_created ON proposals(is_archived, created_at);
CREATE INDEX IF NOT EXISTS idx_proposals_lead_archived ON proposals(lead_id, is_archived);
CREATE INDEX IF NOT EXISTS idx_transactions_deleted_date ON transactions(deleted_at, date);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_batch ON leads(batch_name);
CREATE INDEX IF NOT EXISTS idx_board_cards_column_position ON board_cards(column_id, position);

-- Search/filter indexes
CREATE INDEX IF NOT EXISTS idx_leads_business_name ON leads(business_name(100));
CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone_number);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name(100));
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_ai_proxies_feature_active ON ai_proxies(feature, is_active);
CREATE INDEX IF NOT EXISTS idx_documents_title ON documents(title(100));
CREATE INDEX IF NOT EXISTS idx_document_templates_type_active ON document_templates(type, is_active);

-- Timestamp indexes for sorting/filtering
CREATE INDEX IF NOT EXISTS idx_proposals_created_at ON proposals(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_documents_updated_at ON documents(updated_at);
CREATE INDEX IF NOT EXISTS idx_content_generations_created_at ON content_generations(created_at);
CREATE INDEX IF NOT EXISTS idx_board_card_activity_created_at ON board_card_activity(created_at);

-- Additional composite indexes for common filters
CREATE INDEX IF NOT EXISTS idx_leads_archived_deleted ON leads(is_archived, deleted_at);
CREATE INDEX IF NOT EXISTS idx_board_cards_archived ON board_cards(is_archived);

-- MySQL verification query - check index sizes
-- SELECT
--     table_name,
--     index_name,
--     ROUND(stat_value * @@innodb_page_size / 1024 / 1024, 2) AS size_mb
-- FROM mysql.innodb_index_stats
-- WHERE database_name = DATABASE()
-- AND stat_name = 'size'
-- ORDER BY stat_value DESC
-- LIMIT 30;
