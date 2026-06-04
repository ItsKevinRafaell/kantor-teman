export function formatRupiah(num: number): string {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(num);
}

export function formatRupiahInput(value: string | number): string {
  const num = typeof value === "number" ? value : cleanRupiahInput(value);
  if (num === 0 && typeof value === "string" && value === "") return "";
  return "Rp " + num.toLocaleString("id-ID");
}

export function cleanRupiahInput(value: string): number {
  const cleaned = value.replace(/[^0-9]/g, "");
  return parseInt(cleaned, 10) || 0;
}
