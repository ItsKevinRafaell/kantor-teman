export const meta = {
  name: 'map-report-pipeline',
  description: 'Map KantorTeman report pipeline (backend generate + evidence + PDF) and propose how to support rich comparison tables + screenshot proof',
  phases: [
    { title: 'Map', detail: 'parallel readers on report subsystems' },
    { title: 'Synthesize', detail: 'gap analysis + design proposal' },
  ],
}

const ROOT = '/home/kevin/kantorteman/backend'

const MAP_SCHEMA = {
  type: 'object',
  properties: {
    area: { type: 'string' },
    files: { type: 'array', items: { type: 'string' }, description: 'file:line refs' },
    findings: { type: 'array', items: { type: 'string' } },
    canDoToday: { type: 'array', items: { type: 'string' }, description: 'what current structure already supports' },
    cannotDo: { type: 'array', items: { type: 'string' }, description: 'gaps vs rich tables + image proof' },
  },
  required: ['area', 'files', 'findings', 'canDoToday', 'cannotDo'],
}

phase('Map')

const [pipeline, evidence, render] = await parallel([
  () => agent(
    `Map the BACKEND report generation pipeline in ${ROOT}. Read routers that handle /api/reports and /api/reports/generate (likely routers/workspace.py or a reports router). Find the generate handler: how does it assemble metrics JSON, auto-pull workspace+board+attachment data, build the narrative/executive_summary, and produce the PDF/docx output? Find the PDF/docx generator code (search for docx, reportlab, weasyprint, jinja, template). Report: exact file:line refs, the full data flow from POST /api/reports/generate to final PDF, what fields go into the document, and whether the PDF layout supports arbitrary comparison tables + embedded images or is fixed-layout. Focus: can the generator render a user-supplied comparison TABLE (rows of label/previous/current/delta) and embed uploaded SCREENSHOT images today?`,
    { label: 'map:backend-pipeline', phase: 'Map', schema: MAP_SCHEMA }
  ),
  () => agent(
    `Map EVIDENCE / ATTACHMENT storage in ${ROOT}. The public client report has a "Bukti Pengerjaan" section showing evidence items with url/file_path/link/label. Find: the evidence model/table, how evidence is attached to a report, whether there is IMAGE UPLOAD (file upload endpoint, uploads/ folder, static file serving) or only URL links. Search models for Evidence, Attachment, ClientDocument, ReportSnapshot.evidence. Search routers for upload, multipart, UploadFile. Report file:line refs, the evidence data shape, and specifically: can a user UPLOAD an image screenshot today and have it embedded in the report, or is it URL-link-only?`,
    { label: 'map:evidence', phase: 'Map', schema: MAP_SCHEMA }
  ),
  () => agent(
    `Map the PUBLIC report RENDER side at /home/kevin/kantorteman/frontend/src/app/client-report/[slug]/page.tsx AND the admin form at /home/kevin/kantorteman/frontend/src/app/documents/reports/page.content.tsx. For the PUBLIC page: how does it render the comparisons table (ReportComparisonBlocks), service metrics, before/after retainer, evidence list, narrative sections? For the ADMIN form: what is the full field system (SEO_MONTHLY_FIELDS, SERVICE_FIELDS, reportComparisonFields, retainer before/after, narrative textareas)? Report file:line refs and specifically: (a) does the comparison table already render label/previous/current/delta rows from metrics.comparisons? (b) can the admin input an arbitrary NUMBER of comparison rows, or is it fixed per-service-type? (c) is there any image/preview rendering in evidence, or only external links?`,
    { label: 'map:frontend-render', phase: 'Map', schema: MAP_SCHEMA }
  ),
])

phase('Synthesize')

const PROPOSAL_SCHEMA = {
  type: 'object',
  properties: {
    gaps: { type: 'array', items: { type: 'string' }, description: 'concrete gaps between current system and user real report sample' },
    whatAlreadyWorks: { type: 'array', items: { type: 'string' }, description: 'parts of the real sample the current system already handles' },
    approaches: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          summary: { type: 'string' },
          fileChanges: { type: 'array', items: { type: 'string' } },
          pros: { type: 'array', items: { type: 'string' } },
          cons: { type: 'array', items: { type: 'string' } },
          effort: { type: 'string', enum: ['S', 'M', 'L'] },
        },
        required: ['name', 'summary', 'fileChanges', 'pros', 'cons', 'effort'],
      },
    },
    recommendation: { type: 'string' },
    openQuestions: { type: 'array', items: { type: 'string' } },
  },
  required: ['gaps', 'whatAlreadyWorks', 'approaches', 'recommendation', 'openQuestions'],
}

const USER_REAL_SAMPLE = `
User's REAL monthly SEO report (MLS / PT Mitra Lindung Sarana, periode 1-30 Juni 2026) contains:
- HASIL PEKERJAAN section
- "Metriks Keseluruhan" COMPARISON TABLE: Bulan Mei 2026 vs Bulan Juni 2026 with columns (Metric, previous, current, Perubahan %). Rows: Total Impresi ~38.000 -> ~39.300 +3,42%; Total Klik 529 -> 620 +17,20%; Average CTR 1.4% -> 1.6%; Average Position 6.7 -> 6.4.
- A SECOND comparison table "Kemajuan Proyek Total": Benchmark Awal (Januari 2026) vs Bulan Juni 2026. Total Impresi ~20.900 -> ~39.300 +88,04%; Total Klik 248 -> 620 +150%.
- "GRAFIK DARI GOOGLE SEARCH CONSOLE" — a chart image (screenshot from GSC).
- "AKTIVITAS YANG TELAH DILAKUKAN BULAN INI": BACKUP BULANAN (ada ss), PEMBUATAN 10 ARTIKEL STUDI KASUS (ada ss), PERUBAHAN KONTAK HALAMAN CABANG BANDUNG, HASIL ARTIKEL — each activity WITH a screenshot proof.
- "RENCANA & FOKUS BULAN BERIKUTNYA": target table Benchmark vs Target Bulan depan (Total Impresi target 40.000, Total Klik target 530) + TOPIK ARTIKEL JULI 2026.
- Footer: TERIMAKASIH, PT MITRA LINDUNG SARANA, PERIODE 1-30 JUNI 2026.
User quote: "metric yang pasti gw masukin... kalau cuman data bisa jadi bentuknya tabel, tapi rata-rata gw masukin proven ss juga" (if just data -> table form, but mostly I also input proven screenshots).
`

const proposal = await agent(
  `You are designing how to evolve the KantorTeman client-report system so it matches the user's REAL report workflow.\n\n` +
  `Here are 3 subsystem maps (JSON):\n\n` +
  `BACKEND PIPELINE:\n${JSON.stringify(pipeline, null, 2)}\n\n` +
  `EVIDENCE/ATTACHMENT:\n${JSON.stringify(evidence, null, 2)}\n\n` +
  `FRONTEND RENDER+FORM:\n${JSON.stringify(render, null, 2)}\n\n` +
  `USER'S REAL REPORT SAMPLE:\n${USER_REAL_SAMPLE}\n\n` +
  `Task: Identify concrete GAPS between current system and the real sample. Note what ALREADY WORKS (e.g. if comparison table rendering exists, if evidence list exists). Propose 2-3 distinct APPROACHES to support (a) flexible/arbitrary comparison tables (multiple tables: month-vs-month AND benchmark-vs-now AND target), and (b) embedded screenshot image proof per activity. For each approach give file-level changes, pros, cons, effort S/M/L. Give a clear RECOMMENDATION and open questions that need user input. Be concrete and reference the actual files found.`,
  { label: 'synthesize:proposal', phase: 'Synthesize', schema: PROPOSAL_SCHEMA, effort: 'high' }
)

return { pipeline, evidence, render, proposal }
