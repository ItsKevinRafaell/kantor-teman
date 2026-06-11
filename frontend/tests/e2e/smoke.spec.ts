import { expect, type Page, test } from "@playwright/test";

const adminEmail = process.env.PLAYWRIGHT_ADMIN_EMAIL || "admin@kantorteman.com";
const adminPassword = process.env.PLAYWRIGHT_ADMIN_PASSWORD || "admin123";

const moduleRoutes = [
  { path: "/dashboard", heading: "Dashboard" },
  { path: "/leads", heading: /Prospek|Leads|Pipeline/i },
  { path: "/clients", heading: /Klien|Buku Klien/i },
  { path: "/board", heading: /Board|Project Board/i },
  { path: "/workspace", heading: /Workspace Klien/i },
  { path: "/proposals", heading: /Riwayat Proposal/i },
  { path: "/documents", heading: /Arsip Tim|Dokumen/i },
  { path: "/documents/generator", heading: /Document Generator|Generator Dokumen|Dokumen Resmi/i },
  { path: "/content-generator", heading: /Generator Konten|Artikel SEO/i },
  { path: "/settings?tab=team", heading: /Pengaturan|Tim & Role/i },
  { path: "/master/products", heading: /Produk|Katalog/i },
  { path: "/master/categories", heading: /Kategori/i },
  { path: "/master/templates", heading: /Template/i },
  { path: "/docs", heading: /Dokumentasi/i },
];

function attachFatalWatch(page: Page) {
  const fatal: string[] = [];

  page.on("pageerror", (error) => {
    fatal.push(`pageerror: ${error.message}`);
  });

  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const text = message.text();
    const ignored = [
      "favicon",
      "Failed to load resource: the server responded with a status of 404",
      "net::ERR_ABORTED",
      "Failed to fetch RSC payload",
    ];
    if (!ignored.some((item) => text.includes(item))) {
      fatal.push(`console: ${text}`);
    }
  });

  return fatal;
}

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Masuk" }).click();
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
}

test.describe("QA smoke modul utama", () => {
  test("login dan halaman operasional utama stabil", async ({ page }) => {
    const fatal = attachFatalWatch(page);
    await login(page);

    for (const route of moduleRoutes) {
      await test.step(`buka ${route.path}`, async () => {
        await page.goto(route.path);
        await page.waitForLoadState("domcontentloaded");
        await expect(page.locator("body")).not.toContainText("404");
        await expect(page.locator("body")).not.toContainText("Token tidak ditemukan");
        await expect(page.locator("body")).not.toContainText("Gagal memuat");
        await expect(page.locator("body")).toContainText(route.heading);
      });
    }

    expect(fatal, fatal.join("\n")).toEqual([]);
  });
});
