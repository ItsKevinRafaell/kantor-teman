export function formatRupiahInput(value: string | number): string {
  const num = typeof value === "number" ? value : cleanRupiahInput(value);
  if (num === 0 && typeof value === "string" && value === "") return "";
  return "Rp " + num.toLocaleString("id-ID");
}

export function cleanRupiahInput(value: string): number {
  const cleaned = value.replace(/[^0-9]/g, "");
  return parseInt(cleaned, 10) || 0;
}
