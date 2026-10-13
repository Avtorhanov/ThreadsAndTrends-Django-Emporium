/**
 * Деньги приходят из API целыми копейками. Перевод в рубли — только для отображения
 * и ввода; арифметика с копейками ведётся в целых числах.
 */

const rublesFormat = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });

export function formatKopecks(kopecks: number | null | undefined): string {
  if (kopecks === null || kopecks === undefined) return "—";
  const sign = kopecks < 0 ? "-" : "";
  const abs = Math.abs(kopecks);
  const rubles = Math.trunc(abs / 100);
  const rest = abs % 100;
  const fraction = rest ? `,${String(rest).padStart(2, "0")}` : "";
  return `${sign}${rublesFormat.format(rubles)}${fraction} ₽`;
}

/** Копейки → строка для поля ввода: 199050 → «1990,50». */
export function kopecksToInput(kopecks: number | null | undefined): string {
  if (kopecks === null || kopecks === undefined) return "";
  const rubles = Math.trunc(kopecks / 100);
  const rest = kopecks % 100;
  return rest ? `${rubles},${String(rest).padStart(2, "0")}` : String(rubles);
}

/** «1 990,5» / «1990.50» → 199050. Некорректный ввод → null (без float-арифметики). */
export function parseRublesToKopecks(input: string): number | null {
  const normalized = input.replace(/[\s ]/g, "").replace(",", ".");
  const match = /^(\d{1,12})(?:\.(\d{1,2}))?$/.exec(normalized);
  if (!match) return null;
  const rubles = Number(match[1]);
  const kopecks = Number((match[2] ?? "").padEnd(2, "0"));
  return rubles * 100 + kopecks;
}
