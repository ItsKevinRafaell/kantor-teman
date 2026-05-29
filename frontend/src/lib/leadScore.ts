export type ScoreTier = "closing" | "pendekatan" | "belum_match";

export function getScoreTier(score: number): ScoreTier {
  if (score >= 80) return "closing";
  if (score >= 50) return "pendekatan";
  return "belum_match";
}

export function getScoreLabel(score: number): string {
  const tier = getScoreTier(score);
  if (tier === "closing") return "Siap Closing";
  if (tier === "pendekatan") return "Perlu Pendekatan";
  return "Belum Match";
}

export function getScoreIcon(score: number): string {
  const tier = getScoreTier(score);
  if (tier === "closing") return "\u{1F3AF}";
  if (tier === "pendekatan") return "\u{1F4DE}";
  return "\u{1F4A4}";
}

export function getScoreColor(score: number): string {
  const tier = getScoreTier(score);
  if (tier === "closing") return "bg-green-500";
  if (tier === "pendekatan") return "bg-orange-500";
  return "bg-gray-400";
}

export function getScoreTextColor(score: number): string {
  const tier = getScoreTier(score);
  if (tier === "closing") return "text-green-600";
  if (tier === "pendekatan") return "text-orange-600";
  return "text-gray-500";
}
