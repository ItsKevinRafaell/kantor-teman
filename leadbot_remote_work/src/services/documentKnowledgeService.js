const path = require('path');
const pdfParse = require('pdf-parse');
const mammoth = require('mammoth');
const db = require('../db');
const knowledgeItemService = require('./knowledgeItemService');

const MAX_TEXT_CHARS = 30000;

function cleanText(text) {
  return String(text || '')
    .replace(/\r/g, '\n')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
    .slice(0, MAX_TEXT_CHARS);
}

function titleFromFilename(filename) {
  return path.basename(filename || 'Dokumen usaha')
    .replace(/\.[^.]+$/, '')
    .replace(/[-_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim() || 'Dokumen usaha';
}

async function extractText(file) {
  const mimetype = file.mimetype || '';
  const name = file.originalname || '';

  if (mimetype.includes('pdf') || /\.pdf$/i.test(name)) {
    const parsed = await pdfParse(file.buffer);
    return cleanText(parsed.text);
  }

  if (
    mimetype.includes('wordprocessingml')
    || mimetype.includes('msword')
    || /\.(docx|doc)$/i.test(name)
  ) {
    const parsed = await mammoth.extractRawText({ buffer: file.buffer });
    return cleanText(parsed.value);
  }

  return cleanText(file.buffer.toString('utf8'));
}

class DocumentKnowledgeService {
  async processUpload(file) {
    if (!file) throw new Error('File wajib diunggah');
    const extractedText = await extractText(file);
    if (!extractedText) throw new Error('Teks dokumen kosong atau tidak bisa dibaca');

    const upload = await db.query(
      `INSERT INTO document_uploads (filename, mime_type, size_bytes, extracted_text)
       VALUES ($1, $2, $3, $4)
       RETURNING *`,
      [file.originalname || 'upload', file.mimetype || null, file.size || 0, extractedText]
    );

    const item = await knowledgeItemService.create({
      type: 'faq',
      title: 'Dokumen: ' + titleFromFilename(file.originalname),
      content: extractedText,
      keywords: titleFromFilename(file.originalname),
      metadata: {
        source: 'document_upload',
        uploadId: upload.rows[0].id,
        filename: file.originalname || 'upload',
      },
      active: true,
    });

    return {
      upload: upload.rows[0],
      item,
      preview: extractedText.slice(0, 1200),
    };
  }

  async listUploads() {
    const result = await db.query(
      `SELECT id, filename, mime_type, size_bytes, status, created_at
       FROM document_uploads
       ORDER BY created_at DESC
       LIMIT 50`
    );
    return result.rows;
  }
}

module.exports = new DocumentKnowledgeService();
