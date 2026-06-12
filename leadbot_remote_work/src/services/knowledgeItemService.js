const db = require('../db');

const VALID_TYPES = [
  'business_profile',
  'product',
  'price',
  'promo',
  'order_flow',
  'payment',
  'shipping',
  'location',
  'business_hours',
  'policy',
  'faq',
  'bot_boundary',
];

function normalizeType(type) {
  return String(type || '').trim().toLowerCase();
}

function normalizeKeywords(value) {
  if (!value) return [];
  const raw = Array.isArray(value) ? value : String(value).split(/[,;\n|]+/);
  return [...new Set(raw
    .map((item) => String(item || '').toLowerCase().replace(/\s+/g, ' ').trim())
    .filter(Boolean))];
}

function normalizeMetadata(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return value;
}

function validatePayload(payload, partial = false) {
  const data = payload || {};
  const next = {};

  if (!partial || data.type !== undefined) {
    next.type = normalizeType(data.type);
    if (!VALID_TYPES.includes(next.type)) {
      throw new Error('Tipe data usaha tidak valid');
    }
  }

  if (!partial || data.title !== undefined) {
    next.title = String(data.title || '').trim();
    if (!next.title) throw new Error('Judul wajib diisi');
  }

  if (!partial || data.content !== undefined) {
    next.content = String(data.content || '').trim();
    if (!next.content) throw new Error('Isi data wajib diisi');
  }

  if (data.keywords !== undefined) next.keywords = normalizeKeywords(data.keywords);
  if (data.metadata !== undefined) next.metadata = normalizeMetadata(data.metadata);
  if (data.active !== undefined) next.active = data.active !== false;

  return next;
}

class KnowledgeItemService {
  getValidTypes() {
    return VALID_TYPES;
  }

  async list(filters = {}) {
    const where = [];
    const params = [];

    if (filters.type) {
      params.push(normalizeType(filters.type));
      where.push('type = $' + params.length);
    }

    if (filters.active !== undefined) {
      params.push(filters.active === true || filters.active === 'true');
      where.push('active = $' + params.length);
    }

    if (filters.q) {
      params.push('%' + String(filters.q).toLowerCase().trim() + '%');
      where.push('(LOWER(title) LIKE $' + params.length + ' OR LOWER(content) LIKE $' + params.length + ')');
    }

    const result = await db.query(
      `SELECT *
       FROM knowledge_items
       ${where.length ? 'WHERE ' + where.join(' AND ') : ''}
       ORDER BY active DESC, type ASC, title ASC, created_at DESC`,
      params
    );
    return result.rows;
  }

  async getActiveItems() {
    return this.list({ active: true });
  }

  async create(payload) {
    const data = validatePayload(payload);
    const result = await db.query(
      `INSERT INTO knowledge_items (type, title, content, keywords, metadata, active)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING *`,
      [
        data.type,
        data.title,
        data.content,
        data.keywords || [],
        JSON.stringify(data.metadata || {}),
        data.active !== false,
      ]
    );
    return result.rows[0];
  }

  async replaceSetupItems(items) {
    const rows = Array.isArray(items) ? items : [];
    const normalized = rows.map((item) => {
      const data = validatePayload(item);
      return {
        ...data,
        metadata: {
          ...(data.metadata || {}),
          source: 'dashboard_setup',
        },
      };
    });

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await client.query("DELETE FROM knowledge_items WHERE metadata->>'source' = 'dashboard_setup'");

      const inserted = [];
      for (const item of normalized) {
        const result = await client.query(
          `INSERT INTO knowledge_items (type, title, content, keywords, metadata, active)
           VALUES ($1, $2, $3, $4, $5, $6)
           RETURNING *`,
          [
            item.type,
            item.title,
            item.content,
            item.keywords || [],
            JSON.stringify(item.metadata || {}),
            item.active !== false,
          ]
        );
        inserted.push(result.rows[0]);
      }

      await client.query('COMMIT');
      return inserted;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async update(id, payload) {
    const data = validatePayload(payload, true);
    const sets = [];
    const params = [id];

    for (const field of ['type', 'title', 'content', 'keywords', 'metadata', 'active']) {
      if (data[field] === undefined) continue;
      params.push(field === 'metadata' ? JSON.stringify(data[field]) : data[field]);
      sets.push(field + ' = $' + params.length);
    }

    if (!sets.length) throw new Error('Tidak ada data yang diubah');

    const result = await db.query(
      `UPDATE knowledge_items
       SET ${sets.join(', ')}, updated_at = NOW()
       WHERE id = $1
       RETURNING *`,
      params
    );
    return result.rows[0] || null;
  }

  async delete(id) {
    const result = await db.query('DELETE FROM knowledge_items WHERE id = $1 RETURNING id', [id]);
    return result.rowCount > 0;
  }
}

module.exports = new KnowledgeItemService();
