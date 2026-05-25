-- Migration: create ai_proxies table for MySQL

CREATE TABLE IF NOT EXISTS ai_proxies (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    base_url VARCHAR(500) NOT NULL,
    api_key_encrypted VARCHAR(500) DEFAULT '',
    model VARCHAR(255) DEFAULT '',
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_ai_proxies_active ON ai_proxies(is_active, id) WHERE is_active = TRUE;