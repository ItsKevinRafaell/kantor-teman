const express = require('express');
const multer = require('multer');
const router = express.Router();
const conversationService = require('../services/conversationService');
const fonnteService = require('../services/fonnteService');
const aiService = require('../services/aiService');
const escalationService = require('../services/escalationService');
const eventService = require('../services/eventService');
const knowledgeService = require('../services/knowledgeService');
const knowledgeItemService = require('../services/knowledgeItemService');
const documentKnowledgeService = require('../services/documentKnowledgeService');

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 12 * 1024 * 1024 },
});

router.get('/events', eventService.stream);

router.get('/conversations', async (req, res) => {
  try {
    res.json(await conversationService.getActiveConversations());
  } catch (error) {
    console.error('[Dashboard] Error getting conversations:', error);
    res.status(500).json({ error: error.message });
  }
});

router.get('/leads', async (req, res) => {
  try {
    res.json(await conversationService.getLeadCandidates());
  } catch (error) {
    console.error('[Dashboard] Error getting leads:', error);
    res.status(500).json({ error: error.message });
  }
});

router.get('/conversations/:id', async (req, res) => {
  try {
    res.json(await conversationService.getConversationMessages(req.params.id));
  } catch (error) {
    console.error('[Dashboard] Error getting messages:', error);
    res.status(500).json({ error: error.message });
  }
});

router.post('/conversations/:id/reply', async (req, res) => {
  try {
    const message = String(req.body.message || '').trim();
    if (!message) return res.status(400).json({ error: 'Pesan wajib diisi' });

    const conversation = await conversationService.getConversation(req.params.id);
    if (!conversation) return res.status(404).json({ error: 'Percakapan tidak ditemukan' });

    await conversationService.addMessage(req.params.id, 'outbound', message, { responder: 'admin' });
    const sent = await fonnteService.sendMessage(conversation.phone, message);
    await conversationService.markHumanReply(req.params.id);
    await escalationService.respondEscalation(req.params.id, message, 'admin');
    res.json({ success: true, sent, autoReplyPaused: true });
  } catch (error) {
    console.error('[Dashboard] Error sending reply:', error);
    res.status(500).json({ error: error.message });
  }
});

router.post('/conversations/:id/auto-reply', async (req, res) => {
  try {
    const paused = req.body.paused === true || req.body.paused === 'true';
    const conversation = await conversationService.setAutoReplyPaused(req.params.id, paused);
    if (!conversation) return res.status(404).json({ error: 'Percakapan tidak ditemukan' });
    res.json({ success: true, conversation });
  } catch (error) {
    console.error('[Dashboard] Error updating auto-reply:', error);
    res.status(500).json({ error: error.message });
  }
});

router.post('/conversations/:id/escalate', async (req, res) => {
  try {
    const escalation = await escalationService.createEscalation(
      req.params.id,
      req.body.reason || 'Eskalasi manual',
      'Eskalasi manual oleh admin',
      {}
    );
    await conversationService.setAutoReplyPaused(req.params.id, true);
    res.json({ success: true, escalation });
  } catch (error) {
    console.error('[Dashboard] Error escalating:', error);
    res.status(500).json({ error: error.message });
  }
});

router.post('/conversations/:id/close', async (req, res) => {
  try {
    await escalationService.closeEscalations(req.params.id);
    await conversationService.closeConversation(req.params.id);
    res.json({ success: true });
  } catch (error) {
    console.error('[Dashboard] Error closing:', error);
    res.status(500).json({ error: error.message });
  }
});

router.get('/stats', async (req, res) => {
  try {
    res.json({
      ...(await conversationService.getDashboardStats()),
      ai: aiService.getStatus(),
      whatsapp: fonnteService.getStatus(),
      fonnte: fonnteService.getStatus(),
      pendingEscalations: await escalationService.getEscalationCount(),
      realtimeClients: eventService.getClientCount(),
    });
  } catch (error) {
    console.error('[Dashboard] Error getting stats:', error);
    res.status(500).json({ error: error.message });
  }
});

router.get('/whatsapp/status', async (req, res) => {
  res.json(fonnteService.getStatus());
});

router.get('/knowledge', async (req, res) => {
  try {
    const knowledge = await knowledgeService.getKnowledge();
    res.json({ knowledge, text: knowledgeService.knowledgeToText(knowledge) });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.put('/knowledge', async (req, res) => {
  try {
    const knowledge = await knowledgeService.saveKnowledge(req.body || {}, 'manual');
    res.json({ success: true, knowledge, text: knowledgeService.knowledgeToText(knowledge) });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.post('/knowledge/wizard', async (req, res) => {
  try {
    const items = Array.isArray(req.body.items) ? req.body.items : [];
    const saved = await knowledgeItemService.replaceSetupItems(items);
    res.json({ success: true, items: saved, count: saved.length });
  } catch (error) {
    console.error('[Dashboard] Error saving wizard:', error);
    res.status(400).json({ success: false, error: error.message });
  }
});

router.get('/knowledge-items', async (req, res) => {
  try {
    const filters = { type: req.query.type, q: req.query.q };
    if (req.query.active !== undefined) filters.active = req.query.active;
    res.json({
      types: knowledgeItemService.getValidTypes(),
      items: await knowledgeItemService.list(filters),
    });
  } catch (error) {
    console.error('[Dashboard] Error getting knowledge items:', error);
    res.status(500).json({ error: error.message });
  }
});

router.post('/knowledge-items', async (req, res) => {
  try {
    const item = await knowledgeItemService.create(req.body || {});
    res.status(201).json({ success: true, item });
  } catch (error) {
    console.error('[Dashboard] Error creating knowledge item:', error);
    res.status(400).json({ success: false, error: error.message });
  }
});

router.put('/knowledge-items/setup', async (req, res) => {
  try {
    const items = await knowledgeItemService.replaceSetupItems(req.body?.items || []);
    res.json({ success: true, items, count: items.length, types: knowledgeItemService.getValidTypes() });
  } catch (error) {
    console.error('[Dashboard] Error saving setup knowledge items:', error);
    res.status(400).json({ success: false, error: error.message });
  }
});

router.put('/knowledge-items/:id', async (req, res) => {
  try {
    const item = await knowledgeItemService.update(req.params.id, req.body || {});
    if (!item) return res.status(404).json({ error: 'Data usaha tidak ditemukan' });
    res.json({ success: true, item });
  } catch (error) {
    console.error('[Dashboard] Error updating knowledge item:', error);
    res.status(400).json({ success: false, error: error.message });
  }
});

router.delete('/knowledge-items/:id', async (req, res) => {
  try {
    const deleted = await knowledgeItemService.delete(req.params.id);
    if (!deleted) return res.status(404).json({ error: 'Data usaha tidak ditemukan' });
    res.json({ success: true });
  } catch (error) {
    console.error('[Dashboard] Error deleting knowledge item:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

router.get('/knowledge/uploads', async (req, res) => {
  try {
    res.json({ uploads: await documentKnowledgeService.listUploads() });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.post('/knowledge/upload', upload.single('file'), async (req, res) => {
  try {
    const result = await documentKnowledgeService.processUpload(req.file);
    res.json({ success: true, ...result });
  } catch (error) {
    console.error('[Dashboard] Error uploading knowledge document:', error);
    res.status(400).json({ success: false, error: error.message });
  }
});

router.post('/ai/test', async (req, res) => {
  try {
    const message = String(req.body.message || '').trim();
    if (!message) return res.status(400).json({ error: 'Pesan wajib diisi' });
    const result = await aiService.generateSalesResponse(message, {
      lastMessages: req.body.history || [],
    });
    res.json(result);
  } catch (error) {
    console.error('[Dashboard] Error testing AI:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

module.exports = router;
