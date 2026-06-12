const config = require('../config');
const db = require('../db');

const SETTING_KEY = 'product_knowledge';

const DEFAULT_KNOWLEDGE = {
  source: 'default',
  updatedAt: null,
  title: 'Template awal UMKM',
  summary: 'Data usaha spesifik belum diisi. Bot tetap bisa menyapa pelanggan, menggali kebutuhan, menjawab secara umum, dan meminta detail yang dibutuhkan untuk follow up. Jangan mengarang nama usaha, alamat, harga, promo, atau janji layanan yang belum tersedia.',
  services: [],
  workflow: 'Jika pelanggan tertarik, tanyakan kebutuhan utama, nama atau jenis usaha, dan arahkan percakapan agar admin bisa memberi rekomendasi paling sesuai.',
  faq: [],
  raw: {
    businessInfo: {
      businessName: '',
      businessAddress: '',
      productsText: '',
      pricesText: '',
      orderFlow: '',
      notes: '',
    },
  },
};

function asArray(value) {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function normalizeKnowledge(payload, source) {
  const data = payload?.data || payload?.result || payload || {};
  const services = asArray(data.services || data.products || data.items || data.catalog).map((item) => ({
    name: item.name || item.title || item.service_name || item.product_name || 'Layanan',
    description: item.description || item.summary || item.detail || item.content || '',
    price: item.price || item.pricing || item.starting_price || item.price_text || '',
  }));

  const faq = asArray(data.faq || data.faqs || data.questions).map((item) => ({
    question: item.question || item.q || item.title || '',
    answer: item.answer || item.a || item.content || item.description || '',
  })).filter((item) => item.question || item.answer);

  return {
    source,
    updatedAt: new Date().toISOString(),
    title: data.title || data.name || 'Referensi KantorTeman',
    summary: data.summary || data.description || data.about || '',
    services,
    workflow: data.workflow || data.process || data.how_it_works || data.cara_kerja || '',
    faq,
    raw: data,
  };
}

function knowledgeToText(knowledge) {
  const item = knowledge || DEFAULT_KNOWLEDGE;
  const lines = [];
  if (item.title) lines.push('Judul: ' + item.title);
  if (item.summary) lines.push('Ringkasan: ' + item.summary);
  if (item.workflow) lines.push('Cara kerja: ' + item.workflow);
  if (item.services?.length) {
    lines.push('Layanan/produk:');
    for (const service of item.services.slice(0, 20)) {
      const price = service.price ? ' Harga: ' + service.price + '.' : '';
      lines.push('- ' + service.name + ': ' + (service.description || '-') + price);
    }
  }
  if (item.faq?.length) {
    lines.push('FAQ:');
    for (const faq of item.faq.slice(0, 20)) lines.push('- Q: ' + faq.question + ' A: ' + faq.answer);
  }
  return lines.join('\n').slice(0, 6000);
}

async function getKnowledge() {
  const result = await db.query('SELECT value, updated_at FROM settings WHERE key = $1 LIMIT 1', [SETTING_KEY]);
  if (!result.rows.length) return DEFAULT_KNOWLEDGE;
  try {
    return JSON.parse(result.rows[0].value);
  } catch (error) {
    return DEFAULT_KNOWLEDGE;
  }
}

async function saveKnowledge(knowledge, source = 'manual') {
  const normalized = normalizeKnowledge(knowledge, source);
  await db.query(
    `INSERT INTO settings (key, value, updated_at)
     VALUES ($1, $2, NOW())
     ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()`,
    [SETTING_KEY, JSON.stringify(normalized)]
  );
  return normalized;
}

async function fetchJson(url) {
  const headers = { 'Content-Type': 'application/json' };
  if (config.kantorteman.apiKey) {
    headers['X-API-Key'] = config.kantorteman.apiKey;
    headers.Authorization = 'Bearer ' + config.kantorteman.apiKey;
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  const response = await fetch(url, { headers, signal: controller.signal });
  clearTimeout(timeout);
  const text = await response.text();
  let data;
  try { data = JSON.parse(text); } catch (error) { data = { raw: text }; }
  if (!response.ok) throw new Error('HTTP ' + response.status + ': ' + text.slice(0, 250));
  return data;
}

async function syncFromKantorTeman(path) {
  if (!config.kantorteman.apiUrl) throw new Error('KANTORTEMAN_API_URL belum dikonfigurasi');
  const base = config.kantorteman.apiUrl.replace(/\/$/, '');
  const candidates = path ? [path] : [
    '/api/leadbot/knowledge',
    '/api/public/knowledge',
    '/api/services',
    '/api/products',
    '/api/settings/product-knowledge',
  ];

  const errors = [];
  for (const candidate of candidates) {
    const url = candidate.startsWith('http') ? candidate : base + candidate;
    try {
      const data = await fetchJson(url);
      return saveKnowledge(data, 'kantorteman:' + url);
    } catch (error) {
      errors.push(url + ' => ' + error.message);
    }
  }
  throw new Error('Tidak ada endpoint KantorTeman yang berhasil. ' + errors.join(' | '));
}

module.exports = {
  getKnowledge,
  saveKnowledge,
  syncFromKantorTeman,
  knowledgeToText,
  DEFAULT_KNOWLEDGE,
};
