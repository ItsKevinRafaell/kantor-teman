const db = require('../db');
const { statsCache } = require('./cacheService');
const eventService = require('./eventService');

function safeStage(stage) {
  return String(stage || 'new').toLowerCase().replace(/[^a-z0-9_/-]/g, '').slice(0, 50) || 'new';
}

function safeScore(score) {
  const parsed = parseInt(score, 10);
  if (!Number.isFinite(parsed)) return 0;
  return Math.max(0, Math.min(100, parsed));
}

class ConversationService {
  async getOrCreateConversation(phone, contactName = null) {
    let result = await db.query(
      "SELECT * FROM conversations WHERE phone = $1 AND status IN ('active', 'escalated') ORDER BY created_at DESC LIMIT 1",
      [phone]
    );

    if (result.rows.length === 0) {
      result = await db.query(
        'INSERT INTO conversations (phone, contact_name, channel) VALUES ($1, $2, $3) RETURNING *',
        [phone, contactName, 'waha']
      );
      eventService.emit('conversation', result.rows[0]);
      return result.rows[0];
    }

    if (contactName && !result.rows[0].contact_name) {
      result = await db.query(
        'UPDATE conversations SET contact_name = $2, updated_at = NOW() WHERE id = $1 RETURNING *',
        [result.rows[0].id, contactName]
      );
      eventService.emit('conversation', result.rows[0]);
    }

    return result.rows[0];
  }

  async getConversation(conversationId) {
    const result = await db.query('SELECT * FROM conversations WHERE id = $1', [conversationId]);
    return result.rows[0] || null;
  }

  async addMessage(conversationId, direction, content, options = {}) {
    const result = await db.query(
      `INSERT INTO messages (conversation_id, direction, content, responder, message_type, external_id, metadata)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING *`,
      [
        conversationId,
        direction,
        content,
        options.responder || null,
        options.messageType || 'text',
        options.externalId || null,
        JSON.stringify(options.metadata || {}),
      ]
    );

    await db.query('UPDATE conversations SET updated_at = NOW() WHERE id = $1', [conversationId]);
    statsCache.del('stats');
    eventService.emit('message', result.rows[0]);
    return result.rows[0];
  }

  async getConversationMessages(conversationId) {
    const result = await db.query('SELECT * FROM messages WHERE conversation_id = $1 ORDER BY timestamp ASC', [conversationId]);
    return result.rows;
  }

  async getRecentMessages(conversationId, limit = 10) {
    const result = await db.query(
      'SELECT direction, content AS message, responder, timestamp FROM messages WHERE conversation_id = $1 ORDER BY timestamp DESC LIMIT $2',
      [conversationId, limit]
    );
    return result.rows.reverse();
  }

  async getActiveConversations() {
    const result = await db.query(
      `SELECT c.*,
        (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) AS last_message,
        (SELECT direction FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) AS last_direction,
        (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) AS message_count
       FROM conversations c
       WHERE c.status IN ('active', 'escalated')
       ORDER BY c.updated_at DESC`
    );
    return result.rows;
  }

  async setAutoReplyPaused(conversationId, paused) {
    const result = await db.query(
      'UPDATE conversations SET auto_reply_paused = $2, updated_at = NOW() WHERE id = $1 RETURNING *',
      [conversationId, paused === true]
    );
    if (result.rows[0]) eventService.emit('conversation', result.rows[0]);
    return result.rows[0] || null;
  }

  async markHumanReply(conversationId) {
    const result = await db.query(
      `UPDATE conversations
       SET auto_reply_paused = true, last_human_reply_at = NOW(), updated_at = NOW()
       WHERE id = $1
       RETURNING *`,
      [conversationId]
    );
    if (result.rows[0]) eventService.emit('conversation', result.rows[0]);
    return result.rows[0] || null;
  }

  async updateLeadInsights(conversationId, insights = {}) {
    const result = await db.query(
      `UPDATE conversations
       SET lead_stage = $2, lead_score = $3, last_ai_reason = $4, updated_at = NOW()
       WHERE id = $1
       RETURNING *`,
      [
        conversationId,
        safeStage(insights.leadStage),
        safeScore(insights.leadScore),
        String(insights.reason || '').slice(0, 1000),
      ]
    );
    if (result.rows[0]) eventService.emit('conversation', result.rows[0]);
    return result.rows[0] || null;
  }

  async escalate(conversationId, escalatedBy, reason) {
    await db.query("UPDATE conversations SET status = 'escalated', updated_at = NOW() WHERE id = $1", [conversationId]);
    const result = await db.query(
      'INSERT INTO escalations (conversation_id, escalated_by, reason, status) VALUES ($1, $2, $3, $4) RETURNING *',
      [conversationId, escalatedBy, reason, 'pending']
    );
    eventService.emit('escalation', result.rows[0]);
    return result.rows[0];
  }

  async closeConversation(conversationId) {
    await db.query("UPDATE conversations SET status = 'closed', updated_at = NOW() WHERE id = $1", [conversationId]);
    eventService.emit('conversation', { id: conversationId, status: 'closed' });
  }

  async getDashboardStats() {
    const cached = statsCache.get('stats');
    if (cached) return cached;

    const result = await db.query(`
      SELECT
        (SELECT COUNT(*) FROM conversations) AS total,
        (SELECT COUNT(*) FROM conversations WHERE status = 'active') AS active,
        (SELECT COUNT(*) FROM conversations WHERE status = 'escalated') AS escalated,
        (SELECT COUNT(*) FROM conversations WHERE auto_reply_paused = true AND status IN ('active', 'escalated')) AS paused,
        (SELECT COUNT(*) FROM messages WHERE timestamp >= CURRENT_DATE) AS messages_today,
        (SELECT COUNT(*) FROM messages WHERE direction = 'outbound' AND responder = 'ai_owner_sales' AND timestamp >= CURRENT_DATE) AS ai_replied_today,
        (SELECT COUNT(*) FROM messages WHERE direction = 'outbound' AND timestamp >= CURRENT_DATE) AS outbound_today,
        (SELECT COUNT(*) FROM escalations WHERE created_at >= CURRENT_DATE) AS escalated_today
    `);

    const row = result.rows[0];
    const totalMessages = parseInt(row.messages_today, 10);
    const aiReplies = parseInt(row.ai_replied_today, 10);
    const stats = {
      total: parseInt(row.total, 10),
      active: parseInt(row.active, 10),
      escalated: parseInt(row.escalated, 10),
      paused: parseInt(row.paused, 10),
      messagesToday: totalMessages,
      autoRepliedToday: aiReplies,
      outboundToday: parseInt(row.outbound_today, 10),
      escalatedToday: parseInt(row.escalated_today, 10),
      autoReplyRate: totalMessages > 0 ? Math.round((aiReplies / totalMessages) * 100) : 0,
      updatedAt: new Date().toISOString(),
    };

    statsCache.set('stats', stats);
    return stats;
  }

  async getLeadCandidates() {
    const result = await db.query(
      `SELECT c.*,
        (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY timestamp DESC LIMIT 1) AS last_message,
        (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) AS message_count
       FROM conversations c
       WHERE c.status IN ('active', 'escalated')
       ORDER BY c.lead_score DESC, c.updated_at DESC
       LIMIT 50`
    );
    return result.rows;
  }
}

module.exports = new ConversationService();
