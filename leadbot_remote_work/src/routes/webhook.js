const express = require('express');
const router = express.Router();
const config = require('../config');
const db = require('../db');
const conversationService = require('../services/conversationService');
const wahaService = require('../services/wahaService');
const telegramService = require('../services/telegramService');
const leadService = require('../services/leadService');
const rateLimit = require('../middleware/rateLimit');
const aiService = require('../services/aiService');
const escalationService = require('../services/escalationService');

function verifyWebhookSecret(req, res, next) {
  if (!config.waha.webhookSecret) return next();
  const provided = req.get('x-webhook-secret') || req.get('x-waha-secret') || req.query.secret || req.body.secret;
  if (provided === config.waha.webhookSecret) return next();
  return res.status(401).json({ error: 'Invalid webhook secret' });
}

function verifyKantorTemanBridge(req, res, next) {
  if (!config.kantorteman.bridgeToken) {
    return res.status(503).json({ error: 'KANTORTEMAN_BRIDGE_TOKEN belum dikonfigurasi' });
  }
  const provided = req.get('x-kantorteman-key')
    || req.get('x-leadbot-key')
    || (req.get('authorization') || '').replace(/^Bearer\s+/i, '')
    || req.query.secret
    || '';
  if (provided === config.kantorteman.bridgeToken) return next();
  return res.status(401).json({ error: 'Invalid KantorTeman bridge token' });
}

function pickBridgeTarget(body) {
  return body.target || body.phone || body.phone_number || body.to || body.chatId || '';
}

function pickBridgeText(body) {
  return body.text || body.message || body.body || '';
}

router.get('/health', async (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    rateLimit: rateLimit.getStats(),
    ai: aiService.getStatus(),
    waha: wahaService.getStatus(),
    escalations: await escalationService.getEscalationCount(),
  });
});

router.get('/integrations/kantorteman/health', verifyKantorTemanBridge, async (req, res) => {
  res.json({
    status: 'ok',
    bridge: 'kantorteman',
    demo: config.kantorteman.bridgeDemo,
    bridgeTokenConfigured: Boolean(config.kantorteman.bridgeToken),
    allowedActions: ['health', 'whatsapp.demo_send'],
    waha: wahaService.getStatus(),
    timestamp: new Date().toISOString(),
  });
});

router.post('/webhook', verifyWebhookSecret, async (req, res) => {
  try {
    const payload = wahaService.parseWebhookPayload(req.body);
    if (payload.fromMe) return res.json({ success: true, ignored: 'from_me' });
    if (!payload.sender) return res.status(400).json({ error: 'Payload tidak valid: sender kosong' });

    const inboundText = payload.message || (payload.media ? '[Media diterima]' : '');
    if (!inboundText) return res.json({ success: true, ignored: 'empty_message' });

    if (!rateLimit.checkRateLimit(payload.sender)) {
      console.log('[Webhook] Rate limited:', payload.sender);
      return res.status(429).json({ error: 'Rate limit exceeded' });
    }

    console.log('[Webhook] WAHA inbound from', payload.sender);
    const conversation = await conversationService.getOrCreateConversation(payload.sender, payload.name);
    await conversationService.addMessage(conversation.id, 'inbound', inboundText, {
      responder: 'customer',
      messageType: payload.messageType,
      externalId: payload.externalId,
      metadata: {
        rawEvent: payload.rawEvent,
        media: payload.media,
      },
    });

    telegramService.notifyNewConversation(payload.sender, payload.name, inboundText)
      .catch((err) => console.log('[Telegram] Notification skipped:', err.message));

    if (conversation.auto_reply_paused) {
      return res.json({
        success: true,
        action: 'saved_only',
        responder: 'human_paused',
        autoReply: false,
        paused: true,
      });
    }

    const leadContext = await getLeadContext(conversation.id);
    const aiResult = await aiService.generateSalesResponse(inboundText, leadContext);
    if (!aiResult.success) {
      await escalationService.createEscalation(conversation.id, inboundText, 'AI gagal: ' + aiResult.error, leadContext);
      return res.json({
        success: true,
        action: 'ai_failed_escalated',
        responder: 'ai_owner_sales',
        autoReply: false,
        escalated: true,
        error: aiResult.error,
      });
    }

    const routeResult = await sendAutoReply(conversation, payload.sender, aiResult.response, aiResult);
    await conversationService.updateLeadInsights(conversation.id, aiResult);
    const leadResult = await maybeCreateExternalLead(payload, aiResult);
    if (leadResult?.success) {
      await db.query('UPDATE conversations SET source = $1 WHERE id = $2', ['leadbot_ai', conversation.id]);
    }

    if (aiResult.needsAdmin) {
      await escalationService.createEscalation(conversation.id, inboundText, aiResult.reason || 'AI meminta admin cek', leadContext);
      telegramService.notifyEscalation(payload.sender, payload.name, aiResult.reason || 'AI meminta admin cek')
        .catch((err) => console.log('[Telegram] Escalation notification skipped:', err.message));
    }

    res.json({
      success: true,
      action: routeResult.action,
      responder: routeResult.responder,
      autoReply: routeResult.autoReply,
      escalated: Boolean(aiResult.needsAdmin),
      leadStage: aiResult.leadStage,
      leadScore: aiResult.leadScore,
      leadCreated: Boolean(leadResult?.success),
    });
  } catch (error) {
    console.error('[Webhook] Error:', error);
    res.status(500).json({ error: error.message });
  }
});

router.post('/integrations/kantorteman/whatsapp/send', verifyKantorTemanBridge, async (req, res) => {
  try {
    const target = pickBridgeTarget(req.body || {});
    const text = String(pickBridgeText(req.body || '') || '').trim();
    if (!target) return res.status(400).json({ success: false, error: 'target/phone wajib diisi' });
    if (!text) return res.status(400).json({ success: false, error: 'message/text wajib diisi' });

    const phone = wahaService.normalizePhone(target);
    if (!phone) return res.status(400).json({ success: false, error: 'Nomor WhatsApp tidak valid' });
    if (!rateLimit.checkRateLimit('kt:' + phone)) {
      return res.status(429).json({ success: false, error: 'Rate limit exceeded' });
    }

    const dryRun = config.kantorteman.bridgeDemo || req.body?.dry_run === true || req.body?.demo === true;
    const conversation = await conversationService.getOrCreateConversation(
      phone,
      req.body?.contact_name || req.body?.business_name || req.body?.name || null
    );

    await conversationService.addMessage(conversation.id, 'outbound', text, {
      responder: 'kantorteman_bridge',
      messageType: 'text',
      externalId: req.body?.request_id || null,
      metadata: {
        source: 'kantorteman',
        dryRun,
        campaignId: req.body?.campaign_id || null,
        leadId: req.body?.lead_id || null,
        templateId: req.body?.template_id || null,
        batchName: req.body?.batch_name || null,
      },
    });

    await db.query('UPDATE conversations SET source = $1, updated_at = NOW() WHERE id = $2', ['kantorteman', conversation.id]);

    if (dryRun) {
      return res.json({
        success: true,
        action: 'demo_recorded',
        provider: 'autolead_bridge',
        dryRun: true,
        conversationId: conversation.id,
        phone,
      });
    }

    const sent = await wahaService.sendMessage(phone, text);
    if (!sent.success) {
      return res.status(502).json({
        success: false,
        action: 'send_failed',
        provider: 'autolead_bridge',
        dryRun: false,
        conversationId: conversation.id,
        phone,
        error: sent.error,
      });
    }

    return res.json({
      success: true,
      action: 'sent',
      provider: 'autolead_bridge',
      dryRun: false,
      conversationId: conversation.id,
      phone,
      waha: sent.data || null,
    });
  } catch (error) {
    console.error('[KantorTeman Bridge] Error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

async function sendAutoReply(conversation, phone, response, aiResult) {
  await conversationService.addMessage(conversation.id, 'outbound', response, {
    responder: 'ai_owner_sales',
    metadata: {
      leadStage: aiResult.leadStage,
      leadScore: aiResult.leadScore,
      confidence: aiResult.confidence,
      reason: aiResult.reason,
      provider: aiResult.provider,
      model: aiResult.model,
    },
  });
  const sent = await wahaService.sendMessage(phone, response);
  if (!sent.success) {
    await escalationService.createEscalation(conversation.id, response, 'Auto-reply WAHA gagal dikirim: ' + sent.error, {});
    return { action: 'send_failed_escalated', responder: 'ai_owner_sales', autoReply: false, escalated: true, error: sent.error };
  }
  return { action: 'auto_replied', responder: 'ai_owner_sales', autoReply: true, escalated: false };
}

async function maybeCreateExternalLead(payload, aiResult) {
  const highIntent = aiResult.leadScore >= 60 || ['hot_lead', 'closing', 'follow_up'].includes(aiResult.leadStage);
  if (!highIntent) return null;
  return leadService.createLead(payload.sender, payload.name || 'Lead dari WhatsApp', payload.message, payload.name);
}

async function getLeadContext(conversationId) {
  const conversation = await conversationService.getConversation(conversationId);
  return {
    name: conversation?.contact_name || 'Pelanggan',
    product: 'layanan usaha',
    lastMessages: await conversationService.getRecentMessages(conversationId, 10),
  };
}

module.exports = router;
