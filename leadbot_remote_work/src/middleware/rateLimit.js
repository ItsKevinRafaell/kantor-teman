const db = require('../db');

const rateLimitState = new Map();

const LIMITS = {
  perPhone: { count: 10, windowMs: 60000 },
  global: { count: 100, windowMs: 60000 },
};

function cleanupExpired() {
  const now = Date.now();
  for (const [key, data] of rateLimitState.entries()) {
    if (now - data.windowStart > LIMITS.global.windowMs) {
      rateLimitState.delete(key);
    }
  }
}

setInterval(cleanupExpired, 60000);

module.exports = {
  checkRateLimit(phone) {
    const now = Date.now();

    const phoneKey = 'phone:' + phone;
    let phoneData = rateLimitState.get(phoneKey);

    if (!phoneData || now - phoneData.windowStart > LIMITS.perPhone.windowMs) {
      phoneData = { count: 0, windowStart: now };
    }

    phoneData.count++;
    rateLimitState.set(phoneKey, phoneData);

    if (phoneData.count > LIMITS.perPhone.count) {
      console.log('[RateLimit] Phone limit exceeded:', phone);
      return false;
    }

    const globalKey = 'global';
    let globalData = rateLimitState.get(globalKey);

    if (!globalData || now - globalData.windowStart > LIMITS.global.windowMs) {
      globalData = { count: 0, windowStart: now };
    }

    globalData.count++;
    rateLimitState.set(globalKey, globalData);

    if (globalData.count > LIMITS.global.count) {
      console.log('[RateLimit] Global limit exceeded');
      return false;
    }

    return true;
  },

  getStats() {
    let total = 0;
    let phoneCount = 0;
    const now = Date.now();

    for (const [key, data] of rateLimitState.entries()) {
      if (key === 'global') continue;
      if (now - data.windowStart < LIMITS.perPhone.windowMs) {
        phoneCount++;
        total += data.count;
      }
    }

    return {
      activePhones: phoneCount,
      totalRequests: total,
      globalCount: rateLimitState.get('global')?.count || 0,
    };
  }
};
