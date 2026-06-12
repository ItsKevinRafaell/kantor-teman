# Week 3-4 Implementation Plan
**Updated:** 2026-06-08
**Focus:** Caching, Better Matching, Intent Structure, AI Fallback Planning

---

## WEEK 3: CORE IMPROVEMENTS

### Day 1: Caching Layer (2026-06-08)

**Goal:** Reduce DB load via in-memory cache

**Tasks:**
```bash
# 1. Install dependency
cd /opt/leadbot
npm install node-cache --save

# 2. Create cache service
touch src/services/cacheService.js

# 3. Implementation checklist
- [x] Create cacheService.js
- [ ] Keyword cache (TTL 10 min)
- [ ] Stats cache (TTL 10 sec)
- [ ] Invalidation on keyword CRUD
- [ ] Test cache hit/miss
```

**Code Structure:**
```javascript
// src/services/cacheService.js
const NodeCache = require('node-cache');

class CacheService {
  constructor() {
    this.keywordCache = new NodeCache({ stdTTL: 600 }); // 10 min
    this.statsCache = new NodeCache({ stdTTL: 10 });    // 10 sec
    this.conversationCache = new NodeCache({ stdTTL: 10 });
  }

  // Keyword cache
  getKeywords() { ... }
  invalidateKeywords() { ... }

  // Stats cache
  getStats() { ... }
  invalidateStats() { ... }
}
```

**Testing:**
```bash
# Monitor cache performance
curl http://localhost:20035/api/dashboard/keywords
# First call: cache miss (hit DB)
# Second call: cache hit (instant)
```

**Success Criteria:**
- ✅ Keyword lookup <1ms (cached)
- ✅ Stats endpoint response <5ms (cached)
- ✅ Cache invalidates on keyword add/update/delete

**Effort:** 4 hours

---

### Day 2: Better Keyword Matching (2026-06-09)

**Goal:** Score-based matching with word boundaries

**Current Logic:**
```javascript
// ❌ Naive includes()
if (message.toLowerCase().includes(keyword.toLowerCase())) {
  return response; // First match wins
}
```

**New Logic:**
```javascript
// ✅ Regex + Scoring
const matches = [];
for (const kw of keywords) {
  const regex = new RegExp(`\\b${kw.keyword}\\b`, 'i');
  if (regex.test(message)) {
    const score =
      (kw.priority * 10) +           // Priority weight
      (kw.keyword.length * 2) +       // Specificity
      (kw.keyword.split(' ').length * 5); // Multi-word bonus

    matches.push({ keyword: kw, score });
  }
}

// Return highest score
matches.sort((a, b) => b.score - a.score);
return matches[0]?.keyword.response;
```

**Test Cases:**
```javascript
// Test 1: Word boundary
Message: "halo"
Expected: Match "halo", NOT "halodoc"

// Test 2: Scoring
Message: "halo mau tanya harga"
Keywords: "halo" (priority 1), "harga" (priority 2)
Expected: "harga" wins (score: 30 vs 18)

// Test 3: Multi-word
Message: "info harga produk"
Keywords: "info" (5 chars), "harga produk" (13 chars, 2 words)
Expected: "harga produk" wins (specificity + multi-word bonus)
```

**Implementation Steps:**
1. Refactor `findMatchingKeyword()` in `src/services/keywordService.js`
2. Add test file `tests/keywordMatching.test.js`
3. Run tests
4. Deploy
5. Monitor via logs

**Success Criteria:**
- ✅ No false positives (halo ≠ halodoc)
- ✅ Intent detection accurate (harga wins over halo)
- ✅ Multi-word keywords prioritized

**Effort:** 3-4 hours

---

### Day 3: Intent Schema Design (2026-06-10)

**Goal:** Design migration to intent-based structure

**Current Schema:**
```sql
keywords (id, keyword, response, priority, active, created_at)
```

**New Schema:**
```sql
CREATE TABLE intents (
  id SERIAL PRIMARY KEY,
  name VARCHAR(50) UNIQUE NOT NULL,
  description TEXT,
  confidence_threshold DECIMAL(3,2) DEFAULT 0.70,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE intent_keywords (
  id SERIAL PRIMARY KEY,
  intent_id INT REFERENCES intents(id) ON DELETE CASCADE,
  keyword VARCHAR(255) NOT NULL,
  weight INT DEFAULT 1,
  active BOOLEAN DEFAULT true,
  UNIQUE(intent_id, keyword)
);

CREATE TABLE intent_responses (
  id SERIAL PRIMARY KEY,
  intent_id INT REFERENCES intents(id) ON DELETE CASCADE,
  response_text TEXT NOT NULL,
  tone VARCHAR(20) DEFAULT 'casual', -- 'formal', 'casual', 'friendly'
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW()
);
```

**Migration Strategy:**
```sql
-- Step 1: Create new tables (no data yet)
-- Step 2: Seed default intents
INSERT INTO intents (name, description) VALUES
  ('greeting', 'User greets the bot'),
  ('pricing', 'User asks about price/cost'),
  ('product_info', 'User asks about products/services'),
  ('promo', 'User asks about discounts'),
  ('location', 'User asks about address/location'),
  ('shipping', 'User asks about delivery'),
  ('payment', 'User asks about payment methods'),
  ('complaint', 'User has complaint'),
  ('refund', 'User asks about refund/return'),
  ('human_admin', 'User explicitly asks for human'),
  ('unknown', 'Fallback when no match');

-- Step 3: Migrate existing keywords
INSERT INTO intent_keywords (intent_id, keyword, weight)
SELECT
  (SELECT id FROM intents WHERE name = 'greeting'),
  keyword,
  priority
FROM keywords
WHERE keyword IN ('halo', 'hello', 'hi');

-- Step 4: Keep old table for backward compatibility
-- (Don't drop keywords table yet)
```

**Tasks:**
- [ ] Write migration SQL script
- [ ] Create `migrations/001_intent_structure.sql`
- [ ] Test migration on dev/staging
- [ ] Document rollback plan
- [ ] Update keywordService to support both schemas

**Effort:** 4 hours (design + script)

---

## WEEK 4: POLISH & AI PLANNING

### Day 4: Conversation Cache + Pagination (2026-06-11)

**Goal:** Optimize dashboard performance

**Tasks:**
- [ ] Cache conversation list (TTL 10 sec)
- [ ] Add pagination to `/api/dashboard/conversations`
- [ ] Limit: 20 conversations per page
- [ ] Test with 100+ conversations

**Effort:** 3 hours

---

### Day 5: Response Variants (2026-06-12)

**Goal:** Avoid repetitive bot responses

**Implementation:**
```javascript
// Instead of single response
response: "Halo! Terima kasih..."

// Multiple variants
responses: [
  "Halo! Terima kasih telah menghubungi 🙏",
  "Hai! Ada yang bisa kami bantu? 😊",
  "Selamat datang! Tim kami siap membantu 👋"
]

// Pick random variant
function getResponse(intent_id) {
  const variants = getResponseVariants(intent_id);
  return variants[Math.floor(Math.random() * variants.length)];
}
```

**Tasks:**
- [ ] Add response variants to intent_responses table
- [ ] Update auto-reply logic to pick random variant
- [ ] Seed 3 variants per intent
- [ ] Test randomness

**Effort:** 2-3 hours

---

### Day 6-7: AI Fallback Planning (2026-06-13/14)

**Goal:** Design AI integration strategy

**Confidence-Based Flow:**
```javascript
async function handleMessage(message) {
  const match = await findIntent(message);

  // High confidence → auto-reply
  if (match.confidence >= 0.8) {
    return selectResponseVariant(match.intent_id);
  }

  // Medium confidence → AI assist (optional)
  if (match.confidence >= 0.5 && AI_ENABLED) {
    return await aiGenerateResponse(message, match.intent_id, knowledgeBase);
  }

  // Low confidence → escalate
  await notifyAdmin(message);
  return "Mohon tunggu ya kak, admin kami akan segera membantu 🙏";
}
```

**AI Use Cases:**
1. **AI Suggested Reply (Dashboard):**
   - Admin opens conversation
   - AI suggests 3 reply options
   - Admin picks one or writes custom

2. **AI Summarize Conversation:**
   - Admin clicks "Summarize"
   - AI extracts: intent, pain points, status, next action

3. **AI Classify Unknown Messages:**
   - Bot receives unmatched message
   - AI classifies into nearest intent
   - Log for keyword training

**Tasks:**
- [ ] Design AI service interface
- [ ] Choose AI provider (OpenAI, Anthropic, local LLM)
- [ ] Implement knowledge base structure
- [ ] Build prompt templates
- [ ] Add AI toggle in dashboard settings

**Effort:** 2 days (planning + basic implementation)

---

## ARCHITECTURE DECISIONS

### Why In-Memory Cache (Not Redis)?

**Current State:**
- Single Node.js process
- Traffic: <1000 messages/day
- Keywords: ~5-50 (small dataset)
- VPS: 4GB RAM (plenty for in-memory)

**When to Upgrade to Redis:**
- Multi-process (PM2 cluster mode)
- Multiple servers (load balanced)
- Shared cache across services
- Rate limiting globally
- Queue management (background jobs)
- Pub/sub for real-time features

**Verdict:** In-memory sufficient for now. Redis when traffic >5000 msg/day or multi-server.

---

### Why Score-Based Matching (Not NLP)?

**Current Need:**
- 10-100 keywords
- Simple intent detection
- Low latency (<10ms)
- Predictable behavior

**NLP/ML Worth It When:**
- 1000+ keywords
- Complex multi-intent messages
- Sentiment analysis needed
- Context-aware responses
- Budget for AI API calls

**Verdict:** Score-based matching sufficient for MVP. NLP/AI for fallback layer only.

---

### Why Intent-Based Structure?

**Benefits:**
1. **Scalable:** Add new keywords without duplicating responses
2. **Multi-tenant ready:** Each client customizes intent responses
3. **AI-ready:** Intent → AI prompt template
4. **Maintainable:** Update 1 response variant, affects all keywords in intent

**Trade-offs:**
- More complex schema
- Migration effort
- Need backward compatibility

**Verdict:** Worth it for long-term product vision (SaaS CS bot).

---

## TESTING CHECKLIST

### Caching Tests
- [ ] Cache hit on second keyword lookup
- [ ] Cache miss after TTL expires
- [ ] Cache invalidates on keyword CRUD
- [ ] Memory usage stays <50MB

### Matching Tests
- [ ] "halo" matches, "halodoc" doesn't
- [ ] "harga" beats "halo" in "halo mau tanya harga"
- [ ] Multi-word keywords score higher
- [ ] Case insensitive matching

### Intent Schema Tests
- [ ] Migration runs without errors
- [ ] Old keywords still work (backward compat)
- [ ] New intent_keywords work
- [ ] Response variants return different text

---

## MONITORING

**Metrics to Track:**
```javascript
// Cache performance
- cache_hit_rate: hits / (hits + misses)
- cache_memory_usage: MB

// Matching accuracy
- auto_reply_rate: matched / total
- escalation_rate: escalated / total
- avg_confidence_score: sum(scores) / count

// Performance
- keyword_lookup_latency: ms
- message_processing_time: ms
- db_query_count: per minute
```

**Logging:**
```javascript
// On every message
console.log({
  message_id,
  phone,
  message_text: message.substring(0, 50),
  matched_intent: intent?.name,
  confidence: score,
  response_time_ms,
  cache_hit: true/false
});
```

---

*Plan by Friday (IT PM)*