/** Format numeric values as CNY currency. */
export function formatCurrency(value: number, digits = 2): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value ?? 0);
}

/** Format decimal ratio to percent text. */
export function formatPercent(value: number, digits = 2): string {
  return `${((value ?? 0) * 100).toFixed(digits)}%`;
}

/** Format generic number with fixed digits. */
export function formatNumber(value: number, digits = 2): string {
  return Number(value ?? 0).toFixed(digits);
}

/** Convert ISO date string into compact zh-CN date text. */
export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}
