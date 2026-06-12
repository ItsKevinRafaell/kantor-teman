const config = require('../config');
const knowledgeItemService = require('./knowledgeItemService');
const knowledgeService = require('./knowledgeService');

const HUMAN_FALLBACK_MESSAGE = 'Bisa kak. Supaya saya jawab tepat, boleh info detail kebutuhan atau produk yang kakak maksud dulu?';
const HUMAN_FALLBACK_MARKER = '[HUMAN_FALLBACK]';
const VALID_STAGES = new Set(['new', 'interested', 'follow_up', 'hot_lead', 'closing', 'not_fit', 'admin_needed']);

function normalizeMessageText(message) {
  return String(message || '').replace(/\s+/g, ' ').trim();
}

function clampScore(value) {
  const parsed = parseInt(value, 10);
  if (!Number.isFinite(parsed)) return 0;
  return Math.max(0, Math.min(100, parsed));
}

function normalizeStage(value) {
  const stage = String(value || 'new').toLowerCase().replace(/[^a-z0-9_/-]/g, '');
  return VALID_STAGES.has(stage) ? stage : 'new';
}

function compactKnowledgeItems(items = []) {
  return items
    .filter((item) => item && item.active !== false)
    .slice(0, 60)
    .map((item) => {
      const keywords = Array.isArray(item.keywords) && item.keywords.length ? ' | kata kunci: ' + item.keywords.join(', ') : '';
      return '- [' + item.type + '] ' + item.title + ': ' + normalizeMessageText(item.content).slice(0, 1200) + keywords;
    })
    .join('\n');
}

function compactHistory(history = []) {
  return history.slice(-10).map((item) => {
    const who = item.direction === 'inbound' ? 'Customer' : (item.responder === 'admin' ? 'Admin' : 'Bisnis');
    return who + ': ' + normalizeMessageText(item.message || item.content || '');
  }).join('\n');
}

function buildSalesPrompt(userMessage, leadContext = {}) {
  const knowledgeText = leadContext.knowledgeItemsText
    || compactKnowledgeItems(leadContext.knowledgeItems || [])
    || leadContext.knowledgeText
    || knowledgeService.knowledgeToText(leadContext.knowledge);
  const historyText = compactHistory(leadContext.lastMessages || []);

  return [
    'Kamu adalah owner sekaligus sales senior dari bisnis UMKM Indonesia yang sedang membalas WhatsApp customer.',
    'Tujuan utama: bantu customer paham, percaya, dan maju ke langkah berikutnya tanpa terasa seperti bot.',
    'Gaya bicara: natural, hangat, ringkas, pakai Bahasa Indonesia, boleh pakai "kak", tidak kaku, tidak lebay.',
    'Jangan menyebut diri sebagai AI, sistem otomatis, sales, admin, model, atau bot.',
    '',
    'Aturan fakta ketat:',
    '- Jangan mengarang harga, stok, promo, garansi, refund, alamat, SLA, diskon, atau janji layanan.',
    '- Jika data tidak cukup, jawab bagian yang aman lalu tanya 1 pertanyaan lanjutan paling penting.',
    '- Jika customer komplain, minta berhenti dihubungi, refund, ancaman, atau kasus sensitif, tetap sopan dan tandai needs_admin=true.',
    '- Balasan WhatsApp ideal 1-4 kalimat. Boleh poin pendek jika customer tanya banyak hal.',
    '- Dorong next step yang jelas: pilih paket, kirim lokasi, kirim kebutuhan, atau konfirmasi order.',
    '',
    'Pipeline lead_stage wajib salah satu:',
    'new, interested, follow_up, hot_lead, closing, not_fit, admin_needed.',
    'lead_score 0-100: makin tinggi jika customer punya kebutuhan jelas, tanya harga/order, kirim lokasi, atau siap lanjut.',
    '',
    knowledgeText ? 'Data usaha yang boleh dipakai:\n' + knowledgeText : 'Data usaha belum lengkap.',
    historyText ? 'Riwayat chat:\n' + historyText : '',
    'Pesan customer terbaru: ' + normalizeMessageText(userMessage),
    '',
    'Balas hanya JSON valid tanpa markdown dengan bentuk:',
    '{"reply":"...","lead_stage":"interested","lead_score":60,"confidence":0.8,"needs_admin":false,"reason":"..."}',
  ].filter(Boolean).join('\n');
}

function extractModelText(data) {
  if (!data) return '';
  if (typeof data === 'string') return data;
  return data?.choices?.[0]?.message?.content
    || data?.choices?.[0]?.text
    || data?.data?.response
    || data?.response
    || data?.message
    || data?.text
    || '';
}

function parseJsonObject(text) {
  const raw = String(text || '').trim().replace(/^```json\s*/i, '').replace(/^```\s*/i, '').replace(/```$/i, '').trim();
  try { return JSON.parse(raw); } catch (error) {}
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) return null;
  try { return JSON.parse(match[0]); } catch (error) { return null; }
}

async function callOpenAiCompatible(prompt) {
  const base = String(config.ai.baseUrl || '').replace(/\/+$/, '');
  const url = /\/chat\/completions$/i.test(base) ? base : base + '/chat/completions';
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.ai.timeoutMs);
  const headers = { 'Content-Type': 'application/json' };
  if (config.ai.apiKey) headers.Authorization = 'Bearer ' + config.ai.apiKey;
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        model: config.ai.model,
        messages: [
          { role: 'system', content: 'Kamu membalas sebagai owner-sales UMKM. Ikuti format JSON yang diminta.' },
          { role: 'user', content: prompt },
        ],
        max_tokens: config.ai.maxTokens,
        temperature: config.ai.temperature,
      }),
      signal: controller.signal,
    });
    const raw = await response.text();
    let data;
    try { data = JSON.parse(raw); } catch (error) { data = raw; }
    if (!response.ok) return { success: false, error: 'HTTP ' + response.status + ': ' + raw.slice(0, 300) };
    return { success: true, text: extractModelText(data), raw: data };
  } catch (error) {
    return { success: false, error: error.name === 'AbortError' ? 'AI request timeout' : error.message };
  } finally {
    clearTimeout(timeout);
  }
}

function normalizeAiResult(text, fallbackReason = '') {
  const parsed = parseJsonObject(text);
  const obj = parsed || { reply: text };
  let reply = normalizeMessageText(obj.reply || obj.response || obj.message || text);
  const needsHumanMarker = reply.startsWith(HUMAN_FALLBACK_MARKER);
  if (needsHumanMarker) reply = reply.replace(HUMAN_FALLBACK_MARKER, '').trim();
  if (!reply) reply = HUMAN_FALLBACK_MESSAGE;
  const needsAdmin = Boolean(obj.needs_admin || obj.needsHuman || needsHumanMarker);
  return {
    success: true,
    response: reply,
    reply,
    needsHuman: needsAdmin,
    needsAdmin,
    leadStage: needsAdmin ? 'admin_needed' : normalizeStage(obj.lead_stage || obj.leadStage),
    leadScore: clampScore(obj.lead_score || obj.leadScore),
    confidence: Number.isFinite(parseFloat(obj.confidence)) ? parseFloat(obj.confidence) : 0.65,
    reason: normalizeMessageText(obj.reason || fallbackReason).slice(0, 1000),
    provider: config.ai.provider,
    model: config.ai.model,
  };
}

async function generateSalesResponse(userMessage, leadContext = {}) {
  const context = { ...leadContext };
  if (!context.knowledgeItems) {
    context.knowledgeItems = await knowledgeItemService.getActiveItems();
  }
  if (!context.knowledge) {
    context.knowledge = await knowledgeService.getKnowledge();
  }

  const prompt = buildSalesPrompt(userMessage, context);
  const result = await callOpenAiCompatible(prompt);

  if (!result.success) return result;
  return normalizeAiResult(result.text, 'AI owner-sales response');
}

async function generateResponse(userMessage, leadContext = {}) {
  return generateSalesResponse(userMessage, leadContext);
}

function getStatus() {
  return {
    configured: Boolean(config.ai.baseUrl && config.ai.model),
    provider: config.ai.provider,
    endpointStyle: config.ai.endpointStyle,
    baseUrl: config.ai.baseUrl,
    model: config.ai.model,
    maxTokens: config.ai.maxTokens,
    timeoutMs: config.ai.timeoutMs,
    temperature: config.ai.temperature,
  };
}

module.exports = {
  generateResponse,
  generateSalesResponse,
  getStatus,
  buildPrompt: buildSalesPrompt,
  buildSalesPrompt,
  HUMAN_FALLBACK_MESSAGE,
  HUMAN_FALLBACK_MARKER,
};
