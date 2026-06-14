const db = require('./db');
const config = require('./config');

async function runMigrations() {
  await db.query('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"');

  await db.query(`
    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TIMESTAMP DEFAULT NOW()
    )
  `);

  await db.query("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS source VARCHAR(50) DEFAULT NULL");
  await db.query("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS channel VARCHAR(50) DEFAULT 'fonnte'");
  await db.query("ALTER TABLE conversations ALTER COLUMN channel SET DEFAULT 'fonnte'");
  await db.query("UPDATE conversations SET channel = 'fonnte' WHERE channel = 'waha'");
  await db.query("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS auto_reply_paused BOOLEAN DEFAULT false");
  await db.query("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS lead_stage VARCHAR(50) DEFAULT 'new'");
  await db.query("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS lead_score INTEGER DEFAULT 0");
  await db.query("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_ai_reason TEXT");
  await db.query("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_human_reply_at TIMESTAMP");

  await db.query("ALTER TABLE messages ADD COLUMN IF NOT EXISTS responder VARCHAR(100)");
  await db.query("ALTER TABLE messages ADD COLUMN IF NOT EXISTS message_type VARCHAR(50) DEFAULT 'text'");
  await db.query("ALTER TABLE messages ADD COLUMN IF NOT EXISTS external_id TEXT");
  await db.query("ALTER TABLE messages ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb");

  await db.query("ALTER TABLE escalations ADD COLUMN IF NOT EXISTS message TEXT");
  await db.query("ALTER TABLE escalations ADD COLUMN IF NOT EXISTS lead_context JSONB DEFAULT '{}'::jsonb");
  await db.query("ALTER TABLE escalations ADD COLUMN IF NOT EXISTS response TEXT");
  await db.query("ALTER TABLE escalations ADD COLUMN IF NOT EXISTS responder VARCHAR(100)");
  await db.query("ALTER TABLE escalations ADD COLUMN IF NOT EXISTS responded_at TIMESTAMP");
  await db.query('CREATE INDEX IF NOT EXISTS idx_escalations_status_created ON escalations(status, created_at DESC)');
  await db.query('CREATE INDEX IF NOT EXISTS idx_escalations_conversation_status ON escalations(conversation_id, status)');
  await db.query('CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC)');
  await db.query('CREATE INDEX IF NOT EXISTS idx_conversations_lead_stage ON conversations(lead_stage, lead_score DESC)');
  await db.query('CREATE INDEX IF NOT EXISTS idx_messages_external_id ON messages(external_id)');

  await db.query(`
    CREATE TABLE IF NOT EXISTS knowledge_items (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      type VARCHAR(50) NOT NULL,
      title TEXT NOT NULL,
      content TEXT NOT NULL,
      keywords TEXT[] DEFAULT '{}',
      metadata JSONB DEFAULT '{}'::jsonb,
      active BOOLEAN DEFAULT true,
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW()
    )
  `);

  await db.query('CREATE INDEX IF NOT EXISTS idx_knowledge_items_type ON knowledge_items(type)');
  await db.query('CREATE INDEX IF NOT EXISTS idx_knowledge_items_active ON knowledge_items(active)');
  await db.query('CREATE INDEX IF NOT EXISTS idx_knowledge_items_keywords ON knowledge_items USING GIN(keywords)');

  await db.query(`
    CREATE TABLE IF NOT EXISTS document_uploads (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      filename TEXT NOT NULL,
      mime_type TEXT,
      size_bytes INTEGER DEFAULT 0,
      extracted_text TEXT NOT NULL,
      status VARCHAR(50) DEFAULT 'processed',
      created_at TIMESTAMP DEFAULT NOW()
    )
  `);

  await db.query('CREATE INDEX IF NOT EXISTS idx_document_uploads_created ON document_uploads(created_at DESC)');

  await db.query(`
    CREATE TABLE IF NOT EXISTS dashboard_users (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      email TEXT UNIQUE NOT NULL,
      name TEXT NOT NULL,
      password_hash TEXT NOT NULL,
      role VARCHAR(50) DEFAULT 'admin',
      active BOOLEAN DEFAULT true,
      created_at TIMESTAMP DEFAULT NOW(),
      updated_at TIMESTAMP DEFAULT NOW()
    )
  `);

  await db.query('CREATE UNIQUE INDEX IF NOT EXISTS uq_dashboard_users_email_lower ON dashboard_users (LOWER(email))');
  await db.query('CREATE INDEX IF NOT EXISTS idx_dashboard_users_active ON dashboard_users(active)');

  await db.query(`
    CREATE TABLE IF NOT EXISTS dashboard_password_reset_tokens (
      id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
      user_id UUID NOT NULL REFERENCES dashboard_users(id) ON DELETE CASCADE,
      token_hash TEXT UNIQUE NOT NULL,
      expires_at TIMESTAMP NOT NULL,
      used_at TIMESTAMP,
      created_at TIMESTAMP DEFAULT NOW()
    )
  `);

  await db.query('CREATE INDEX IF NOT EXISTS idx_dashboard_reset_user_id ON dashboard_password_reset_tokens(user_id)');
  await db.query('CREATE INDEX IF NOT EXISTS idx_dashboard_reset_expires_at ON dashboard_password_reset_tokens(expires_at)');

  await db.query(
    `INSERT INTO settings (key, value)
     VALUES ('reply_engine', 'ai_owner_sales')
     ON CONFLICT (key) DO NOTHING`
  );
}

module.exports = runMigrations;

if (require.main === module) {
  runMigrations()
    .then(() => {
      console.log('[Migrate] Done');
      process.exit(0);
    })
    .catch((error) => {
      console.error('[Migrate] Failed:', error);
      process.exit(1);
    });
}
