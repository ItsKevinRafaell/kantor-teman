const SERVICE_LABEL_MAP: Record<string, string> = {
  web_dev: "Web Development",
  seo_gmaps: "SEO & Google Maps",
  sosmed: "Social Media",
  maintenance: "Maintenance",
  web_dev_bulanan: "Web Dev Bulanan",
  branding: "Logo & Branding",
  general: "Lainnya",
};

export function getServiceLabel(slug: string | null | undefined): string | null {
  if (!slug) return null;
  return SERVICE_LABEL_MAP[slug] ?? slug;
}
