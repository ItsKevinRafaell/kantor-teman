const { leadQueueCache } = require('./cacheService');

class LeadService {
  constructor() {
    this.apiBase = process.env.KANTORTEMAN_API_URL || 'https://api.kantorteman.my.id';
    this.apiKey = process.env.KANTORTEMAN_API_KEY || '';
    this.enabled = !!this.apiKey;

    // Lead extraction patterns
    this.PHONE_PATTERNS = [
      /(\+?62[0-9]{9,12})/g,
      /(08[0-9]{8,11})/g,
      /(628[0-9]{8,11})/g,
    ];

    // Intent keywords for lead qualification
    this.LEAD_KEYWORDS = [
      'order', 'beli', 'pesan', 'tertarik', 'mau', 'ingin', 'butuh', 'req', 'request',
      'tanya harga', 'harga berapa', 'hargany', 'diskon', 'promo', 'murah', 'gratis',
      'booking', 'reservasi', 'jadwal', 'konsultasi', 'demo', 'trial', 'quotation',
      'penawaran', 'proyek', 'project', 'renovasi', 'bangun', 'desain', 'rencana',
    ];
  }

  // Normalize phone number
  normalizePhone(phone) {
    if (!phone) return null;
    let p = phone.replace(/[\s\-\(\)]/g, '');
    if (p.startsWith('+')) p = p.substring(1);
    if (p.startsWith('62')) p = '0' + p.substring(2);
    if (p.startsWith('8') && p.length >= 9) p = '0' + p;
    return p.length >= 9 ? p : null;
  }

  // Extract business name from message
  extractBusinessName(message, contactName) {
    if (contactName && contactName !== 'Unknown') return contactName;
    return 'Lead dari WhatsApp';
  }

  // Check if message qualifies as lead
  shouldGenerateLead(message) {
    if (!message) return false;
    const lower = message.toLowerCase();
    for (const kw of this.LEAD_KEYWORDS) {
      if (lower.includes(kw)) return true;
    }
    return false;
  }

  // Check dedup
  isDuplicate(phone, message) {
    const key = `lead:${phone}:${message.substring(0, 80).trim()}`;
    if (leadQueueCache.has(key)) return true;
    leadQueueCache.set(key, true, 3600); // 1 hour dedup
    return false;
  }

  // Extract phone from sender or message
  extractPhone(sender, message) {
    // Try sender first
    let phone = this.normalizePhone(sender);
    if (phone) return phone;

    // Try to find in message
    for (const pattern of this.PHONE_PATTERNS) {
      const match = message.match(pattern);
      if (match) {
        phone = this.normalizePhone(match[0]);
        if (phone) return phone;
      }
    }
    return null;
  }

  // POST lead to KantorTeman
  async createLead(phone, businessName, message, contactName) {
    if (!this.enabled) {
      console.log('[LeadService] KantorTeman API not configured, skipping');
      return { success: false, reason: 'API not configured' };
    }

    if (this.isDuplicate(phone, message)) {
      console.log('[LeadService] Duplicate lead detected, skipping');
      return { success: false, reason: 'Duplicate' };
    }

    try {
      const payload = {
        business_name: businessName || this.extractBusinessName(message, contactName),
        phone_number: phone,
        source: 'leadbot_wa',
        message: message.substring(0, 500),
        product_interest: this.extractProductInterest(message),
      };

      const response = await fetch(this.apiBase + '/api/leads/external', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': this.apiKey,
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (response.ok) {
        console.log('[LeadService] Lead created:', data.lead_id);
        return { success: true, leadId: data.lead_id, duplicate: data.duplicate };
      } else {
        console.error('[LeadService] API error:', data.detail);
        return { success: false, reason: data.detail };
      }
    } catch (error) {
      console.error('[LeadService] Error:', error.message);
      return { success: false, reason: error.message };
    }
  }

  // Extract product interest from message
  extractProductInterest(message) {
    const lower = message.toLowerCase();
    const categories = {
      'renovasi': ['renovasi', 'renovate', 'perbaikan', 'pembangunan'],
      'desain': ['desain', 'design', 'interior', 'arsitek', 'layout'],
      'furniture': ['furniture', 'meja', 'kursi', 'lemari', 'rak', 'kitchen'],
      'elektronik': ['laptop', 'komputer', 'printer', 'proyektor', 'ac', 'tv'],
      'atk': ['atk', 'alat tulis', 'kertas', 'pulpen', 'binder'],
      'konsultasi': ['konsultasi', 'consulting', 'advisor', 'mentoring'],
    };

    for (const [category, keywords] of Object.entries(categories)) {
      for (const kw of keywords) {
        if (lower.includes(kw)) return category;
      }
    }
    return 'general';
  }

  // Sync leads from KantorTeman to LeadBot (reverse sync)
  async syncFromKantorTeman() {
    if (!this.enabled) return { success: false, reason: 'API not configured' };

    try {
      const response = await fetch(this.apiBase + '/api/leads', {
        headers: { 'X-API-Key': this.apiKey },
      });

      if (!response.ok) return { success: false, reason: 'API error' };

      const leads = await response.json();
      // Would create conversations from KT leads here
      console.log('[LeadService] Synced', leads.length, 'leads from KantorTeman');
      return { success: true, count: leads.length };
    } catch (error) {
      return { success: false, reason: error.message };
    }
  }
}

module.exports = new LeadService();
