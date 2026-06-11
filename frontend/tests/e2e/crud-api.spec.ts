import fs from "node:fs";
import path from "node:path";
import { expect, test, type APIRequestContext, type APIResponse } from "@playwright/test";

const apiBase = process.env.PLAYWRIGHT_API_BASE_URL || "http://localhost:8000";
const adminEmail = process.env.PLAYWRIGHT_ADMIN_EMAIL || "admin@kantorteman.com";
const adminPassword = process.env.PLAYWRIGHT_ADMIN_PASSWORD || "admin123";

type Headers = Record<string, string>;
const uploadsRoot = path.resolve(process.cwd(), "..", "backend", "app", "uploads");

async function expectOk(response: APIResponse, label: string) {
  if (response.ok()) return;
  throw new Error(`${label} failed: HTTP ${response.status()} ${await response.text()}`);
}

async function expectStatus(response: APIResponse, statuses: number[], label: string) {
  if (statuses.includes(response.status())) return;
  throw new Error(`${label} expected ${statuses.join("/")} but got HTTP ${response.status()} ${await response.text()}`);
}

async function json<T>(response: APIResponse, label: string): Promise<T> {
  await expectOk(response, label);
  return response.json() as Promise<T>;
}

async function login(request: APIRequestContext): Promise<Headers> {
  const response = await request.post(`${apiBase}/api/auth/login`, {
    data: { email: adminEmail, password: adminPassword },
  });
  const body = await json<{ access_token: string }>(response, "login admin");
  return { Authorization: `Bearer ${body.access_token}` };
}

async function cleanupDelete(request: APIRequestContext, url: string, headers: Headers) {
  try {
    const response = await request.delete(`${apiBase}${url}`, { headers });
    await expectStatus(response, [200, 204, 404], `cleanup ${url}`);
  } catch (error) {
    console.warn(error);
  }
}

async function cleanupGeneratedDocumentsForLead(request: APIRequestContext, leadId: number, headers: Headers) {
  try {
    const response = await request.get(`${apiBase}/api/generated-documents?lead_id=${leadId}`, { headers });
    if (!response.ok()) return;
    const docs = await response.json() as Array<{ id: string }>;
    for (const doc of docs) {
      await cleanupArchiveForGeneratedDoc(request, doc.id, headers);
      await cleanupDelete(request, `/api/documents/generated/${doc.id}`, headers);
    }
  } catch (error) {
    console.warn(error);
  }
}

async function cleanupArchiveForGeneratedDoc(request: APIRequestContext, documentId: string, headers: Headers) {
  try {
    const response = await request.get(`${apiBase}/api/archive?limit=200`, { headers });
    if (!response.ok()) return;
    const archiveDocs = await response.json() as Array<{ id: string; source_id?: string | null }>;
    for (const doc of archiveDocs.filter((item) => item.source_id === documentId)) {
      await cleanupDelete(request, `/api/archive/${doc.id}`, headers);
    }
  } catch (error) {
    console.warn(error);
  }
}

function cleanupLocalUpload(fileUrl: string | undefined) {
  if (!fileUrl?.startsWith("/uploads/")) return;
  const localPath = path.resolve(process.cwd(), "..", "backend", "app", fileUrl.replace(/^\/+/, ""));
  if (!localPath.startsWith(`${uploadsRoot}${path.sep}`)) return;
  try {
    if (fs.existsSync(localPath)) fs.unlinkSync(localPath);
    let dir = path.dirname(localPath);
    while (dir.startsWith(`${uploadsRoot}${path.sep}`)) {
      if (fs.readdirSync(dir).length > 0) break;
      fs.rmdirSync(dir);
      dir = path.dirname(dir);
    }
  } catch (error) {
    console.warn(error);
  }
}

test.describe.serial("QA API CRUD create-cleanup", () => {
  let authHeaders: Headers;

  test.beforeAll(async ({ playwright }) => {
    const api = await playwright.request.newContext();
    try {
      authHeaders = await login(api);
    } finally {
      await api.dispose();
    }
  });

  test("master data produk, kategori, dan template bisa CRUD", async ({ request }) => {
    const headers = authHeaders;
    const runId = Date.now().toString();
    let categoryId: string | undefined;
    let productId: string | undefined;
    let templateId: string | undefined;

    try {
      const category = await json<{ id: string; name: string }>(
        await request.post(`${apiBase}/api/categories`, {
          headers,
          data: {
            name: `QA Kategori ${runId}`,
            description: "Kategori sementara untuk QA otomatis",
            is_active: true,
          },
        }),
        "create category",
      );
      categoryId = category.id;

      const product = await json<{ id: string; name: string; category_id: string; features: string[] }>(
        await request.post(`${apiBase}/api/products`, {
          headers,
          data: {
            name: `QA Produk ${runId}`,
            description: "Produk sementara untuk QA otomatis",
            base_price: 123456,
            features: ["Audit awal", "Laporan ringkas"],
            category_id: categoryId,
            is_active: true,
            is_retainer: false,
          },
        }),
        "create product",
      );
      productId = product.id;
      expect(product.category_id).toBe(categoryId);
      expect(product.features).toContain("Audit awal");

      const updatedProduct = await json<{ name: string; base_price: number }>(
        await request.put(`${apiBase}/api/products/${productId}`, {
          headers,
          data: {
            name: `QA Produk Updated ${runId}`,
            description: "Produk sementara untuk QA update",
            base_price: 654321,
            features: ["Audit awal", "Follow up"],
            category_id: categoryId,
            is_active: true,
            is_retainer: true,
          },
        }),
        "update product",
      );
      expect(updatedProduct.name).toContain("Updated");
      expect(updatedProduct.base_price).toBe(654321);

      const template = await json<{ id: string; category_id: string | null }>(
        await request.post(`${apiBase}/api/dynamic-templates`, {
          headers,
          data: {
            name: `QA Template ${runId}`,
            type: "WA_BLAST",
            content: "Halo {{business_name}}, ini pesan QA otomatis.",
            is_active: true,
            category_id: categoryId,
          },
        }),
        "create dynamic template",
      );
      templateId = template.id;
      expect(template.category_id).toBe(categoryId);

      const templates = await json<Array<{ id: string }>>(
        await request.get(`${apiBase}/api/dynamic-templates?category_id=${categoryId}&type=WA_BLAST`, { headers }),
        "list dynamic templates by category",
      );
      expect(templates.some((item) => item.id === templateId)).toBeTruthy();
    } finally {
      if (templateId) await cleanupDelete(request, `/api/dynamic-templates/${templateId}`, headers);
      if (productId) await cleanupDelete(request, `/api/products/${productId}`, headers);
      if (categoryId) await cleanupDelete(request, `/api/categories/${categoryId}`, headers);
    }
  });

  test("dokumen invoice bisa generate PDF dan update workflow pembayaran", async ({ request }) => {
    const headers = authHeaders;
    const runId = Date.now().toString();
    let leadId: number | undefined;
    let templateId: string | undefined;
    let generatedDocumentId: string | undefined;

    try {
      const lead = await json<{ id: number }>(
        await request.post(`${apiBase}/api/leads`, {
          headers,
          data: {
            business_name: `QA Invoice Lead ${runId}`,
            phone_number: `08991${runId.slice(-8)}`,
            address: "Jl. QA Otomatis, Jakarta",
            product_interest: "SEO & Google Maps",
            batch_name: `QA-${runId}`,
          },
        }),
        "create invoice lead",
      );
      leadId = lead.id;

      const template = await json<{ id: string }>(
        await request.post(`${apiBase}/api/document-templates`, {
          headers,
          data: {
            name: `QA Invoice Template ${runId}`,
            type: "invoice",
            html_template: [
              "<html><body>",
              "<h1>Invoice {{nomor_invoice}}</h1>",
              "<p>Klien: {{klien}}</p>",
              "<p>Layanan: {{layanan}}</p>",
              "<table>{{items_rows}}</table>",
              "<p>Total: {{total}}</p>",
              "</body></html>",
            ].join(""),
            variables: ["nomor_invoice", "klien", "layanan", "items_rows", "total"],
            is_active: true,
          },
        }),
        "create document template",
      );
      templateId = template.id;

      const generated = await json<{ document_id: string; file_url: string; display_filename: string }>(
        await request.post(`${apiBase}/api/documents/generate`, {
          headers,
          data: {
            template_id: templateId,
            target_type: "lead",
            target_id: String(leadId),
            variables: {
              klien: `QA Invoice Lead ${runId}`,
              layanan: "SEO & Google Maps",
              items_rows: "<tr><td>SEO & Google Maps</td><td>1</td><td>Rp 123.456</td><td>Rp 123.456</td></tr>",
              total: "Rp 123.456",
            },
          },
        }),
        "generate invoice pdf",
      );
      generatedDocumentId = generated.document_id;
      expect(generated.file_url).toContain(".pdf");
      expect(generated.display_filename).toContain("INV");

      const workflow = await json<{ status: string; payment_status: string | null }>(
        await request.patch(`${apiBase}/api/documents/generated/${generatedDocumentId}/workflow`, {
          headers,
          data: {
            status: "Dikirim",
            payment_status: "Lunas",
            review_notes: "QA invoice paid",
          },
        }),
        "update generated document workflow",
      );
      expect(workflow.status).toBe("Dikirim");
      expect(workflow.payment_status).toBe("Lunas");

      await cleanupArchiveForGeneratedDoc(request, generatedDocumentId, headers);
    } finally {
      if (generatedDocumentId) await cleanupDelete(request, `/api/documents/generated/${generatedDocumentId}`, headers);
      if (templateId) await cleanupDelete(request, `/api/document-templates/${templateId}`, headers);
      if (leadId) await cleanupDelete(request, `/api/leads/${leadId}`, headers);
    }
  });

  test("proposal reject dan accept membuat status, project, board, workspace", async ({ request }) => {
    const headers = authHeaders;
    const runId = Date.now().toString();
    const leadIds: number[] = [];
    const proposalIds: string[] = [];
    let acceptedProjectId: string | undefined;
    const acceptedPhone = `08992${runId.slice(-8)}`;

    try {
      const rejectLead = await json<{ id: number }>(
        await request.post(`${apiBase}/api/leads`, {
          headers,
          data: {
            business_name: `QA Reject Lead ${runId}`,
            phone_number: `08993${runId.slice(-8)}`,
            address: "Jl. QA Reject, Bandung",
            product_interest: "Website",
            batch_name: `QA-${runId}`,
          },
        }),
        "create reject lead",
      );
      leadIds.push(rejectLead.id);

      const rejectProposal = await json<{ id: string; slug: string }>(
        await request.post(`${apiBase}/api/proposals`, {
          headers,
          data: {
            lead_id: rejectLead.id,
            services: [{ name: "Website Company Profile", price: 1000000, features: ["Design", "Deploy"] }],
            additional_options: "QA reject flow",
          },
        }),
        "create reject proposal",
      );
      proposalIds.push(rejectProposal.id);

      const rejected = await json<{ success: boolean; already_rejected: boolean }>(
        await request.post(`${apiBase}/api/proposals/public/${rejectProposal.slug}/reject`, {
          data: { reason: "QA otomatis" },
        }),
        "reject public proposal",
      );
      expect(rejected.success).toBeTruthy();
      expect(rejected.already_rejected).toBeFalsy();

      const publicRejected = await json<{ status: string }>(
        await request.get(`${apiBase}/api/proposals/public/${rejectProposal.id}`),
        "get rejected public proposal",
      );
      expect(publicRejected.status).toBe("rejected");

      const acceptLead = await json<{ id: number }>(
        await request.post(`${apiBase}/api/leads`, {
          headers,
          data: {
            business_name: `QA Accept Lead ${runId}`,
            phone_number: acceptedPhone,
            address: "Jl. QA Accept, Surabaya",
            product_interest: "SEO & Google Maps",
            batch_name: `QA-${runId}`,
          },
        }),
        "create accept lead",
      );
      leadIds.push(acceptLead.id);

      const acceptProposal = await json<{ id: string; slug: string }>(
        await request.post(`${apiBase}/api/proposals`, {
          headers,
          data: {
            lead_id: acceptLead.id,
            services: [{ name: "SEO Retainer QA", price: 1500000, features: ["Keyword", "Report"] }],
            additional_options: "QA accept flow",
          },
        }),
        "create accept proposal",
      );
      proposalIds.push(acceptProposal.id);

      const accepted = await json<{ success: boolean; project_id: string; already_accepted: boolean; generated_documents?: string[] }>(
        await request.post(`${apiBase}/api/proposals/public/${acceptProposal.slug}/accept`, {
          data: {
            client_name: "QA Client",
            client_phone: acceptedPhone,
            accept_notes: "QA accept otomatis",
          },
        }),
        "accept public proposal",
      );
      expect(accepted.success).toBeTruthy();
      expect(accepted.already_accepted).toBeFalsy();
      acceptedProjectId = accepted.project_id;

      const project = await json<{ id: string; lead_id: number; status: string; monthly_invoice_enabled: boolean }>(
        await request.get(`${apiBase}/api/projects/${acceptedProjectId}`, { headers }),
        "get accepted project",
      );
      expect(project.lead_id).toBe(acceptLead.id);
      expect(project.status).toBe("ACTIVE");

      const workspace = await json<{ sheets: Array<{ rows: unknown[] }> }>(
        await request.get(`${apiBase}/api/workspace/${acceptedProjectId}`, { headers }),
        "get accepted workspace",
      );
      expect(workspace.sheets.length).toBeGreaterThan(0);
      expect(workspace.sheets.some((sheet) => sheet.rows.length > 0)).toBeTruthy();

      const board = await json<{ columns: Array<{ name: string; cards: unknown[] }> }>(
        await request.get(`${apiBase}/api/projects/${acceptedProjectId}/board`, { headers }),
        "get accepted board",
      );
      expect(board.columns.map((column) => column.name)).toEqual(expect.arrayContaining(["To Do", "In Progress", "Review", "Done"]));
      expect(board.columns.some((column) => column.cards.length > 0)).toBeTruthy();

      await cleanupGeneratedDocumentsForLead(request, acceptLead.id, headers);
    } finally {
      if (acceptedProjectId) await cleanupDelete(request, `/api/projects/${acceptedProjectId}`, headers);

      try {
        const contactsResponse = await request.get(`${apiBase}/api/contacts`, { headers });
        if (contactsResponse.ok()) {
          const contacts = await contactsResponse.json() as Array<{ id: number; phone_number: string }>;
          for (const contact of contacts.filter((item) => item.phone_number === acceptedPhone)) {
            await cleanupDelete(request, `/api/contacts/${contact.id}`, headers);
          }
        }
      } catch (error) {
        console.warn(error);
      }

      for (const proposalId of proposalIds) await cleanupDelete(request, `/api/proposals/${proposalId}`, headers);
      for (const leadId of leadIds) {
        await cleanupGeneratedDocumentsForLead(request, leadId, headers);
        await cleanupDelete(request, `/api/leads/${leadId}`, headers);
      }
    }
  });

  test("board card dan workspace row menerima attachment", async ({ request }) => {
    const headers = authHeaders;
    const runId = Date.now().toString();
    let leadId: number | undefined;
    let projectId: string | undefined;
    let cardId: string | undefined;
    const uploadUrls: string[] = [];

    try {
      const lead = await json<{ id: number }>(
        await request.post(`${apiBase}/api/leads`, {
          headers,
          data: {
            business_name: `QA Attachment Lead ${runId}`,
            phone_number: `08994${runId.slice(-8)}`,
            address: "Jl. QA Attachment, Semarang",
            product_interest: "Website",
            batch_name: `QA-${runId}`,
          },
        }),
        "create attachment lead",
      );
      leadId = lead.id;

      const project = await json<{ id: string }>(
        await request.post(`${apiBase}/api/projects`, {
          headers,
          data: {
            lead_id: leadId,
            name: `QA Attachment Project ${runId}`,
            type: "FIXED",
            status: "ACTIVE",
            nominal: 500000,
            start_date: "2026-06-10",
            end_date: "2026-07-10",
            service_type: "web_dev",
            contract_months: 1,
            color: "gray",
          },
        }),
        "create attachment project",
      );
      projectId = project.id;

      const board = await json<{ columns: Array<{ id: string; name: string }> }>(
        await request.get(`${apiBase}/api/projects/${projectId}/board`, { headers }),
        "get project board for attachment",
      );
      const todoColumn = board.columns.find((column) => column.name === "To Do") || board.columns[0];
      expect(todoColumn).toBeTruthy();

      const card = await json<{ id: string }>(
        await request.post(`${apiBase}/api/board-columns/${todoColumn.id}/cards`, {
          headers,
          data: {
            title: `QA Attachment Card ${runId}`,
            description: "Card sementara untuk upload attachment",
            labels: ["qa"],
            color: "gray",
          },
        }),
        "create board card",
      );
      cardId = card.id;

      const boardUpload = await json<{ id: string; file_name: string; file_path: string }>(
        await request.post(`${apiBase}/api/board-cards/${cardId}/attachments`, {
          headers,
          multipart: {
            file: {
              name: `qa-board-${runId}.txt`,
              mimeType: "text/plain",
              buffer: Buffer.from("QA board attachment"),
            },
          },
        }),
        "upload board card attachment",
      );
      expect(boardUpload.file_name).toContain("qa-board");
      expect(boardUpload.file_path).toContain(`/uploads/board/${cardId}/`);
      uploadUrls.push(boardUpload.file_path);

      const cardDetail = await json<{ attachments: Array<{ id: string }> }>(
        await request.get(`${apiBase}/api/board-cards/${cardId}`, { headers }),
        "get board card with attachment",
      );
      expect(cardDetail.attachments.some((item) => item.id === boardUpload.id)).toBeTruthy();

      const workspace = await json<{ sheets: Array<{ columns: Array<{ id: string; column_key: string }>; rows: Array<{ id: string }> }> }>(
        await request.get(`${apiBase}/api/workspace/${projectId}`, { headers }),
        "get workspace for attachment",
      );
      const sheet = workspace.sheets.find((item) => item.rows.length > 0) || workspace.sheets[0];
      expect(sheet).toBeTruthy();
      const row = sheet.rows[0];
      const column = sheet.columns.find((item) => ["output_link", "bukti", "link_bukti", "catatan"].includes(item.column_key)) || sheet.columns[0];
      expect(row).toBeTruthy();
      expect(column).toBeTruthy();

      const workspaceUpload = await json<{ id: string; file_name: string; file_url: string }>(
        await request.post(`${apiBase}/api/workspace/row/${row.id}/attachment`, {
          headers,
          multipart: {
            column_id: column.id,
            file: {
              name: `qa-workspace-${runId}.pdf`,
              mimeType: "application/pdf",
              buffer: Buffer.from("%PDF-1.4\n% QA workspace attachment\n"),
            },
          },
        }),
        "upload workspace attachment",
      );
      expect(workspaceUpload.file_name).toContain("qa-workspace");
      expect(workspaceUpload.file_url).toContain(`/uploads/workspace/${projectId}/${row.id}/`);
      uploadUrls.push(workspaceUpload.file_url);
    } finally {
      for (const uploadUrl of uploadUrls) cleanupLocalUpload(uploadUrl);
      if (cardId) await cleanupDelete(request, `/api/board-cards/${cardId}`, headers);
      if (projectId) await cleanupDelete(request, `/api/projects/${projectId}`, headers);
      if (leadId) await cleanupDelete(request, `/api/leads/${leadId}`, headers);
    }
  });

  test("workspace custom field, row duplicate, dan laporan bulanan bisa create-cleanup", async ({ request }) => {
    const headers = authHeaders;
    const runId = Date.now().toString();
    let leadId: number | undefined;
    let projectId: string | undefined;
    let customColumnId: string | undefined;
    let reportUrl: string | undefined;

    try {
      const lead = await json<{ id: number }>(
        await request.post(`${apiBase}/api/leads`, {
          headers,
          data: {
            business_name: `QA Workspace Lead ${runId}`,
            phone_number: `08995${runId.slice(-8)}`,
            address: "Jl. QA Workspace, Bandung",
            product_interest: "Website",
            batch_name: `QA-${runId}`,
          },
        }),
        "create workspace lead",
      );
      leadId = lead.id;

      const project = await json<{ id: string }>(
        await request.post(`${apiBase}/api/projects`, {
          headers,
          data: {
            lead_id: leadId,
            name: `QA Workspace Project ${runId}`,
            type: "FIXED",
            status: "ACTIVE",
            nominal: 900000,
            start_date: "2026-06-10",
            end_date: "2026-07-10",
            service_type: "web_dev",
            contract_months: 1,
            color: "gray",
          },
        }),
        "create workspace project",
      );
      projectId = project.id;

      const workspace = await json<{ sheets: Array<{ id: string; month_number: number | null; columns: Array<{ id: string; column_key: string }>; rows: Array<{ id: string }> }> }>(
        await request.get(`${apiBase}/api/workspace/${projectId}`, { headers }),
        "get workspace for custom field",
      );
      const sheet = workspace.sheets.find((item) => item.month_number === 1) || workspace.sheets[0];
      expect(sheet).toBeTruthy();

      const columnKey = `qa_field_${runId}`;
      const customColumn = await json<{ id: string; column_label: string; column_options: string[] }>(
        await request.post(`${apiBase}/api/workspace/sheet/${sheet.id}/column`, {
          headers,
          data: {
            column_key: columnKey,
            column_label: "QA Field",
            column_type: "select",
            column_options: ["Brief", "Review"],
          },
        }),
        "create workspace custom column",
      );
      customColumnId = customColumn.id;
      expect(customColumn.column_options).toContain("Review");

      const updatedColumn = await json<{ column_label: string; column_options: string[] }>(
        await request.patch(`${apiBase}/api/workspace/column/${customColumnId}`, {
          headers,
          data: {
            column_label: "QA Field Updated",
            column_type: "select",
            column_options: ["Brief", "Produksi", "Review"],
          },
        }),
        "update workspace custom column",
      );
      expect(updatedColumn.column_label).toBe("QA Field Updated");
      expect(updatedColumn.column_options).toContain("Produksi");

      const row = await json<{ id: string; cells: Record<string, unknown> }>(
        await request.post(`${apiBase}/api/workspace/sheet/${sheet.id}/row`, {
          headers,
          data: { cells: { task_name: `QA Custom Task ${runId}`, [columnKey]: "Review" } },
        }),
        "create workspace custom row",
      );
      expect(row.id).toBeTruthy();

      const duplicate = await json<{ id: string }>(
        await request.post(`${apiBase}/api/workspace/row/${row.id}/duplicate`, { headers }),
        "duplicate workspace row",
      );
      expect(duplicate.id).not.toBe(row.id);

      await expectOk(
        await request.patch(`${apiBase}/api/workspace/sheet/${sheet.id}/reorder-columns`, {
          headers,
          data: { column_ids: [...sheet.columns.map((column) => column.id), customColumnId] },
        }),
        "reorder workspace columns",
      );

      const report = await json<{ file_url: string; summary: { total_tasks: number } }>(
        await request.post(`${apiBase}/api/workspace/${projectId}/generate-monthly-report?month=1`, { headers }),
        "generate monthly workspace report",
      );
      reportUrl = report.file_url;
      expect(report.file_url).toContain(".pdf");
      expect(report.summary.total_tasks).toBeGreaterThan(0);
    } finally {
      if (reportUrl) cleanupLocalUpload(reportUrl);
      if (customColumnId) await cleanupDelete(request, `/api/workspace/column/${customColumnId}`, headers);
      if (projectId) await cleanupDelete(request, `/api/projects/${projectId}`, headers);
      if (leadId) await cleanupDelete(request, `/api/leads/${leadId}`, headers);
    }
  });

  test("archive nested folder delete menghapus isi setelah summary", async ({ request }) => {
    const headers = authHeaders;
    const runId = Date.now().toString();
    let parentFolderId: string | undefined;
    let childFolderId: string | undefined;
    let docId: string | undefined;

    try {
      const parent = await json<{ id: string }>(
        await request.post(`${apiBase}/api/archive/folders`, {
          headers,
          data: { name: `QA Arsip Parent ${runId}`, color: "#EAB308", parent_id: null },
        }),
        "create archive parent folder",
      );
      parentFolderId = parent.id;

      const child = await json<{ id: string; parent_id: string }>(
        await request.post(`${apiBase}/api/archive/folders`, {
          headers,
          data: { name: `QA Arsip Child ${runId}`, color: "#3B82F6", parent_id: parentFolderId },
        }),
        "create archive child folder",
      );
      childFolderId = child.id;
      expect(child.parent_id).toBe(parentFolderId);

      const doc = await json<{ id: string; folder_id: string }>(
        await request.post(`${apiBase}/api/archive`, {
          headers,
          data: {
            title: `QA Arsip Doc ${runId}`,
            body: "Dokumen sementara untuk QA recursive delete",
            url: null,
            tags: ["qa"],
            folder_id: childFolderId,
          },
        }),
        "create archive doc in child folder",
      );
      docId = doc.id;
      expect(doc.folder_id).toBe(childFolderId);

      const summary = await json<{ subfolder_count: number; document_count: number; folder_count: number }>(
        await request.get(`${apiBase}/api/archive/folders/${parentFolderId}/delete-summary`, { headers }),
        "archive folder delete summary",
      );
      expect(summary.subfolder_count).toBe(1);
      expect(summary.document_count).toBe(1);
      expect(summary.folder_count).toBe(2);

      await expectStatus(
        await request.delete(`${apiBase}/api/archive/folders/${parentFolderId}`, { headers }),
        [204],
        "delete archive parent recursively",
      );

      parentFolderId = undefined;
      childFolderId = undefined;
      docId = undefined;

      const deletedDoc = await request.get(`${apiBase}/api/archive/${doc.id}`, { headers });
      expect(deletedDoc.status()).toBe(404);
    } finally {
      if (docId) await cleanupDelete(request, `/api/archive/${docId}`, headers);
      if (childFolderId) await cleanupDelete(request, `/api/archive/folders/${childFolderId}`, headers);
      if (parentFolderId) await cleanupDelete(request, `/api/archive/folders/${parentFolderId}`, headers);
    }
  });

  test("backup dan reset endpoint tetap terlindungi", async ({ request }) => {
    const headers = authHeaders;

    const unauthBackup = await request.get(`${apiBase}/api/admin/data/backup`);
    expect(unauthBackup.status()).toBe(401);

    const softReset = await request.post(`${apiBase}/api/admin/data/reset-soft`, {
      headers,
      data: { password: "wrong-password-from-qa" },
    });
    expect(softReset.status()).toBe(403);

    const nuclearReset = await request.post(`${apiBase}/api/admin/data/reset-nuclear`, {
      headers,
      data: { password: "wrong-password-from-qa" },
    });
    expect(nuclearReset.status()).toBe(403);
  });
});
