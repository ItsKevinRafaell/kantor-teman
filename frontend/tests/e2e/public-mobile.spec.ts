import fs from "node:fs";
import path from "node:path";
import { expect, type Page, test } from "@playwright/test";

const reportSlug = process.env.PLAYWRIGHT_REPORT_SLUG || "toko-makmur-pusat-oleh-oleh-khas-tegal";
const proposalId = process.env.PLAYWRIGHT_PROPOSAL_ID || "6f291ed3-dae2-41de-b845-1ee085ce0cbb";
const artifactDir = path.join(process.cwd(), "qa-artifacts");

function attachFatalWatch(page: Page) {
  const fatal: string[] = [];
  page.on("pageerror", (error) => fatal.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const text = message.text();
    const ignored = ["favicon", "net::ERR_ABORTED"];
    if (!ignored.some((item) => text.includes(item))) fatal.push(`console: ${text}`);
  });
  return fatal;
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => {
    const root = document.documentElement;
    return root.scrollWidth - root.clientWidth;
  });
  expect(overflow).toBeLessThanOrEqual(2);
}

test.describe("QA mobile public pages", () => {
  test.beforeAll(() => {
    fs.mkdirSync(artifactDir, { recursive: true });
  });

  test("report mobile menarik dan tetap valid tanpa AI analysis scrape", async ({ page }) => {
    const fatal = attachFatalWatch(page);

    await page.goto(`/report/${reportSlug}`);
    await page.waitForLoadState("domcontentloaded");

    await expect(page.locator("body")).toContainText("Laporan Audit Digital");
    await expect(page.locator("body")).toContainText(/Area yang Perlu Dicek|Masalah Kritis yang Ditemukan/);
    await expect(page.locator("body")).toContainText("Belum ada AI analysis scrape detail");
    await expect(page.locator("body")).toContainText("Fakta Pasar Digital");
    await expect(page.getByRole("link", { name: /Konsultasi Gratis via WhatsApp|Daftar Antrean/i })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await page.screenshot({ path: path.join(artifactDir, "report-mobile.png"), fullPage: true });

    expect(fatal, fatal.join("\n")).toEqual([]);
  });

  test("proposal mobile tidak overflow dan CTA jelas", async ({ page }) => {
    const fatal = attachFatalWatch(page);

    await page.goto(`/proposal/${proposalId}`);
    await page.waitForLoadState("domcontentloaded");

    await expect(page.locator("body")).toContainText("Proposal Solusi");
    await expect(page.locator("body")).toContainText("Rincian Nilai Investasi");
    const pricing = page.locator("section", { hasText: "Rincian Nilai Investasi" });
    await expect(pricing).toContainText(/Rp\s*1\.000\.000/);
    await expect(pricing).not.toContainText("Rp 0");
    await expect(page.locator("body")).toContainText(/Setuju & (Mulai Project|Amankan Jadwal Eksekusi)|Proposal Diterima|Penawaran ini telah ditolak/);
    await expectNoHorizontalOverflow(page);
    await page.screenshot({ path: path.join(artifactDir, "proposal-mobile.png"), fullPage: true });

    expect(fatal, fatal.join("\n")).toEqual([]);
  });
});
