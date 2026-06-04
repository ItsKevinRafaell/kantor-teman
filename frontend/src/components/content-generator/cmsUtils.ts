"use client";

import { apiFetch } from "../../lib/api";
import { slugify, markdownToContentBlocks } from "./types";
import type { ContentGenResult } from "./types";

export async function publishArticleToCms(result: ContentGenResult | null) {
  if (!result) return;
  const blocks = markdownToContentBlocks(result.body);
  const slug = slugify(result.title).slice(0, 100);
  const res = await apiFetch("/api/cms/publish-article", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: result.title,
      slug,
      excerpt: result.meta_description,
      content: JSON.stringify(blocks),
      meta_description: result.meta_description,
      focus_keyword: result.focus_keyword,
      status: "draft",
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || await res.text());
  }
}
