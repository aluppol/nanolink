const secondMs = 1000;
const minuteMs = 60 * secondMs;
const hourMs = 60 * minuteMs;
const dayMs = 24 * hourMs;

export function describeElapsed(fromIso: string, now: Date): string {
  const from = Date.parse(fromIso);
  if (Number.isNaN(from)) {
    return "";
  }
  const elapsed = now.getTime() - from;
  if (elapsed < 45 * secondMs) {
    return "just now";
  }
  if (elapsed < 45 * minuteMs) {
    return `${Math.max(1, Math.round(elapsed / minuteMs))} min ago`;
  }
  if (elapsed < 22 * hourMs) {
    return `${countOf(Math.max(1, Math.round(elapsed / hourMs)), "hour")} ago`;
  }
  if (elapsed < 36 * hourMs) {
    return "yesterday";
  }
  if (elapsed < 26 * dayMs) {
    return `${countOf(Math.round(elapsed / dayMs), "day")} ago`;
  }
  return new Date(from).toISOString().slice(0, 10);
}

function countOf(amount: number, unit: string): string {
  return amount === 1 ? `1 ${unit}` : `${amount} ${unit}s`;
}
