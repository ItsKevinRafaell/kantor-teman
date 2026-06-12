const db = require('../db');
const config = require('../config');
const eventService = require('./eventService');

const ESCALATE_KEYWORDS = [
  'komplain', 'keluhan', 'refund', 'retur', 'tidak puas', 'kecewa',
  'cancel order', 'batalkan pesanan', 'pesanan batal', 'complaint',
  'tidak sesuai', 'barang salah', 'pesanan salah', 'salah kirim',
  'stop', 'unsubscribe', 'berhenti menerima chat', 'jangan chat', 'hapus nomor'
];

function isUuid(value) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(value || ''));
}

function mapRow(row) {
  if (!row) return null;
  return {
    id: row.id,
    conversationId: row.conversation_id,
    phone: row.phone,
    contactName: row.contact_name,
    message: row.message || row.reason || '',
    reason: row.reason || '',
    leadContext: row.lead_context || {},
    status: row.status,
    createdAt: row.created_at,
    resolvedAt: row.resolved_at,
    respondedAt: row.responded_at,
    response: row.response,
    responder: row.responder,
  };
}

function shouldEscalate(message, confidence = 1) {
  const lowerMsg = String(message || '').toLowerCase();
  const hasKeyword = ESCALATE_KEYWORDS.some((keyword) => lowerMsg.includes(keyword));
  const lowConfidence = confidence < config.ai.confidenceThreshold;
  return hasKeyword || lowConfidence;
}

async function createEscalation(conversationId, message, reason, leadContext = {}) {
  const existing = await db.query(
    `SELECT e.*, c.phone, c.contact_name
     FROM escalations e
     LEFT JOIN conversations c ON c.id = e.conversation_id
     WHERE e.conversation_id = $1 AND e.status = 'pending'
     ORDER BY e.created_at DESC
     LIMIT 1`,
    [conversationId]
  );

  if (existing.rows.length > 0) {
    const updated = await db.query(
      `UPDATE escalations
       SET message = $2, reason = $3, lead_context = $4::jsonb, created_at = NOW()
       WHERE id = $1
       RETURNING *`,
      [existing.rows[0].id, message, reason, JSON.stringify(leadContext || {})]
    );
    await db.query("UPDATE conversations SET status = 'escalated', updated_at = NOW() WHERE id = $1", [conversationId]);
    const mapped = mapRow({ ...updated.rows[0], phone: existing.rows[0].phone, contact_name: existing.rows[0].contact_name });
    eventService.emit('escalation', mapped);
    return mapped;
  }

  await db.query("UPDATE conversations SET status = 'escalated', updated_at = NOW() WHERE id = $1", [conversationId]);

  const result = await db.query(
    `INSERT INTO escalations (conversation_id, escalated_by, reason, message, lead_context, status)
     VALUES ($1, $2, $3, $4, $5::jsonb, 'pending')
     RETURNING *`,
    [conversationId, 'system', reason, message, JSON.stringify(leadContext || {})]
  );

  const joined = await getEscalation(conversationId);
  console.log('[EscalationService] New escalation:', result.rows[0].id, reason);
  eventService.emit('escalation', joined);
  return joined;
}

async function getPendingEscalations() {
  const result = await db.query(
    `SELECT e.*, c.phone, c.contact_name
     FROM escalations e
     LEFT JOIN conversations c ON c.id = e.conversation_id
     WHERE e.status = 'pending'
     ORDER BY e.created_at DESC`
  );
  return result.rows.map(mapRow);
}

async function getEscalation(idOrConversationId) {
  const query = isUuid(idOrConversationId)
    ? `SELECT e.*, c.phone, c.contact_name
       FROM escalations e LEFT JOIN conversations c ON c.id = e.conversation_id
       WHERE e.conversation_id = $1 AND e.status = 'pending'
       ORDER BY e.created_at DESC LIMIT 1`
    : `SELECT e.*, c.phone, c.contact_name
       FROM escalations e LEFT JOIN conversations c ON c.id = e.conversation_id
       WHERE e.id = $1 LIMIT 1`;

  const result = await db.query(query, [idOrConversationId]);
  return mapRow(result.rows[0]);
}

async function getEscalationCount() {
  const result = await db.query("SELECT COUNT(*) FROM escalations WHERE status = 'pending'");
  return parseInt(result.rows[0].count, 10);
}

async function respondEscalation(conversationId, response, responder = 'admin') {
  const result = await db.query(
    `UPDATE escalations
     SET status = 'responded', response = $2, responder = $3, responded_at = NOW(), resolved_at = NOW()
     WHERE conversation_id = $1 AND status = 'pending'
     RETURNING *`,
    [conversationId, response, responder]
  );

  await db.query("UPDATE conversations SET status = 'active', updated_at = NOW() WHERE id = $1", [conversationId]);
  eventService.emit('escalation', { conversationId, status: 'responded' });
  return result.rows.length > 0;
}

async function closeEscalations(conversationId) {
  await db.query(
    `UPDATE escalations
     SET status = 'closed', resolved_at = NOW()
     WHERE conversation_id = $1 AND status = 'pending'`,
    [conversationId]
  );
  eventService.emit('escalation', { conversationId, status: 'closed' });
}

module.exports = {
  shouldEscalate,
  createEscalation,
  getPendingEscalations,
  getEscalation,
  getEscalationCount,
  respondEscalation,
  closeEscalations,
  getEscalationKeywords: () => [...ESCALATE_KEYWORDS],
  CONFIDENCE_THRESHOLD: config.ai.confidenceThreshold,
};
