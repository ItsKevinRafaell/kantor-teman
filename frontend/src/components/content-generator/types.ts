// Shared types + helpers for content-generator module

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ContentProvider {
  id: string; name: string; tool_type: string; base_url: string;
  api_key?: string; model: string; is_active: boolean; created_at: string;
}

export interface ContentSession {
  id: string; name: string; description?: string; created_at: string;
}

export interface ContentGeneration {
  id: string; session_id?: string; tool_type: string;
  input_data: Record<string, unknown>; output_data: unknown;
  model_used?: string; provider_name?: string; status: string;
  error_msg?: string; created_at: string;
}

export type Tool = "seo_article" | "image" | "caption";
export type ToastState = { msg: string; type: "success" | "error" | "info" } | null;

export interface ContentGenResult {
  title: string; meta_description: string; body: string;
  focus_keyword: string; secondary_keywords: string[]; id?: string;
}

export type ContentBlock =
  | { type: "h2"; text: string; id: string }
  | { type: "h3"; text: string; id: string }
  | { type: "p"; text: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] }
  | { type: "blockquote"; text: string };

// ─── Tool metadata ────────────────────────────────────────────────────────────

export const TOOL_LABELS: Record<Tool, string> = {
  seo_article: "SEO Article",
  image: "Image Generator",
  caption: "Caption Sosmed",
};

export const TOOL_COLORS: Record<Tool, string> = {
  seo_article: "bg-neutral-100 dark:bg-neutral-800/30 text-neutral-700 dark:text-neutral-300",
  image: "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300",
  caption: "bg-neutral-100 dark:bg-neutral-800/30 text-neutral-700 dark:text-neutral-300",
};

// ─── Helpers ───────────────────────────────────────────────────────────────────

export function formatDate(d: string) {
  return new Date(d).toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text).catch(() => {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  });
}

export function escapeHtml(str: string): string {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

export function applyInlineMarkdownSafe(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, (_, p1) => `<strong>${escapeHtml(p1)}</strong>`)
    .replace(/\*(.+?)\*/g, (_, p1) => `<em>${escapeHtml(p1)}</em>`);
}

export function markdownToHtml(md: string): string {
  const lines = md.split("\n");
  const parts: string[] = [];
  let inList = false;
  const endList = () => { if (inList) { parts.push("</ul>"); inList = false; } };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith("## ")) {
      endList();
      parts.push(`<h2 class="text-lg font-bold mt-5 mb-2 text-neutral-800 dark:text-neutral-200">${applyInlineMarkdownSafe(line.slice(3))}</h2>`);
    } else if (line.startsWith("### ")) {
      endList();
      parts.push(`<h3 class="text-base font-semibold mt-4 mb-1 text-neutral-700 dark:text-neutral-300">${applyInlineMarkdownSafe(line.slice(4))}</h3>`);
    } else if (line.startsWith("#### ")) {
      endList();
      parts.push(`<h4 class="text-sm font-semibold mt-3 mb-1 text-neutral-600 dark:text-neutral-400">${applyInlineMarkdownSafe(line.slice(5))}</h4>`);
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!inList) { parts.push(`<ul class="list-disc ml-5 my-2 space-y-0.5">`); inList = true; }
      parts.push(`<li class="text-sm text-neutral-700 dark:text-neutral-300">${applyInlineMarkdownSafe(line.slice(2))}</li>`);
    } else if (line.trim() === "") {
      endList();
    } else {
      endList();
      parts.push(`<p class="text-sm text-neutral-700 dark:text-neutral-300 mb-2 leading-relaxed">${applyInlineMarkdownSafe(line)}</p>`);
    }
  }
  endList();
  return parts.join("\n");
}

export function slugify(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9\s-]/g, "").trim().replace(/\s+/g, "-");
}

export function stripInlineMarkdown(text: string): string {
  return text.replace(/\*\*(.+?)\*\*/g, "$1").replace(/\*(.+?)\*/g, "$1");
}

export function markdownToContentBlocks(markdown: string): ContentBlock[] {
  const lines = markdown.split("\n");
  const blocks: ContentBlock[] = [];
  let listType: "ul" | "ol" | null = null;
  let listItems: string[] = [];

  function flushList() {
    if (listType && listItems.length) {
      blocks.push({ type: listType, items: [...listItems] });
    }
    listType = null;
    listItems = [];
  }

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith("## ")) {
      flushList();
      const text = stripInlineMarkdown(line.slice(3).trim());
      blocks.push({ type: "h2", text, id: slugify(text) });
    } else if (line.startsWith("### ")) {
      flushList();
      const text = stripInlineMarkdown(line.slice(4).trim());
      blocks.push({ type: "h3", text, id: slugify(text) });
    } else if (line.startsWith("> ")) {
      flushList();
      blocks.push({ type: "blockquote", text: stripInlineMarkdown(line.slice(2).trim()) });
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      if (listType !== "ul") { flushList(); listType = "ul"; }
      listItems.push(stripInlineMarkdown(line.slice(2).trim()));
    } else if (/^\d+\. /.test(line)) {
      if (listType !== "ol") { flushList(); listType = "ol"; }
      listItems.push(stripInlineMarkdown(line.replace(/^\d+\. /, "").trim()));
    } else if (line.trim() === "") {
      flushList();
    } else {
      flushList();
      blocks.push({ type: "p", text: stripInlineMarkdown(line.trim()) });
    }
  }
  flushList();
  return blocks;
}

export async function exportToDocx(result: ContentGenResult) {
  const { Document, Paragraph, TextRun, HeadingLevel, Packer } = await import("docx");
  const children: InstanceType<typeof Paragraph>[] = [];

  children.push(new Paragraph({ text: result.title, heading: HeadingLevel.HEADING_1 }));
  children.push(new Paragraph({ text: "" }));
  children.push(new Paragraph({
    children: [
      new TextRun({ text: "Meta Description: ", bold: true }),
      new TextRun({ text: result.meta_description }),
    ],
  }));
  if (result.secondary_keywords?.length) {
    children.push(new Paragraph({
      children: [
        new TextRun({ text: "Secondary Keywords: ", bold: true }),
        new TextRun({ text: result.secondary_keywords.join(", ") }),
      ],
    }));
  }
  children.push(new Paragraph({ text: "" }));

  for (const raw of result.body.split("\n")) {
    const line = raw.trimEnd();
    const strip = (s: string) => s.replace(/\*\*(.+?)\*\*/g, "$1").replace(/\*(.+?)\*/g, "$1");
    if (line.startsWith("## ")) {
      children.push(new Paragraph({ text: strip(line.slice(3)), heading: HeadingLevel.HEADING_2 }));
    } else if (line.startsWith("### ")) {
      children.push(new Paragraph({ text: strip(line.slice(4)), heading: HeadingLevel.HEADING_3 }));
    } else if (line.startsWith("#### ")) {
      children.push(new Paragraph({ text: strip(line.slice(5)), heading: HeadingLevel.HEADING_4 }));
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      children.push(new Paragraph({ text: strip(line.slice(2)), bullet: { level: 0 } }));
    } else if (line.trim() === "") {
      children.push(new Paragraph({ text: "" }));
    } else {
      children.push(new Paragraph({ text: strip(line) }));
    }
  }

  const doc = new Document({ sections: [{ children }] });
  const blob = await Packer.toBlob(doc);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${result.title.replace(/[^a-z0-9\s]/gi, "").trim().replace(/\s+/g, "_") || "seo_article"}.docx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
