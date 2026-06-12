const NodeCache = require('node-cache');

// Stats cache: 30 sec TTL (dashboard)
const statsCache = new NodeCache({ stdTTL: 30, checkperiod: 15 });

// Lead queue cache: 5 min TTL (dedup)
const leadQueueCache = new NodeCache({ stdTTL: 300, checkperiod: 30 });

module.exports = {
  statsCache,
  leadQueueCache,

  // Invalidate stats cache
  invalidateStats() {
    statsCache.flushAll();
  },

  // Check if lead already processed (dedup)
  isLeadDuplicate(phone, message) {
    const key = `${phone}:${message.substring(0, 50)}`;
    return leadQueueCache.has(key);
  },

  // Mark lead as processed
  markLeadProcessed(phone, message) {
    const key = `${phone}:${message.substring(0, 50)}`;
    leadQueueCache.set(key, true);
  }
};
