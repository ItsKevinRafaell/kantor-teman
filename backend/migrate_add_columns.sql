-- Migration: add missing columns to provider_configs
-- Safe to run multiple times — ignore "Duplicate column" errors (1060)

ALTER TABLE provider_configs ADD COLUMN monthly_quota FLOAT DEFAULT 0;
ALTER TABLE provider_configs ADD COLUMN price_input_token_usd FLOAT DEFAULT 0;
ALTER TABLE provider_configs ADD COLUMN price_output_token_usd FLOAT DEFAULT 0;
