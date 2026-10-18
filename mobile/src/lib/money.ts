/** Деньги приходят из API целыми копейками; рубли — только для отображения. */
export function formatKopecks(kopecks: number): string {
  const sign = kopecks < 0 ? "-" : "";
  const abs = Math.abs(kopecks);
  const rubles = String(Math.trunc(abs / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  const rest = abs % 100;
  const fraction = rest ? `,${String(rest).padStart(2, "0")}` : "";
  return `${sign}${rubles}${fraction} ₽`;
}

/**
 * Сумма в рублях из поля ввода («1 500», «1500,5») → целые копейки без float.
 * Пусто → null; не число → undefined.
 */
export function parseRubles(text: string): number | null | undefined {
  const value = text.replace(/[\s ₽]/g, "");
  if (!value) return null;
  const match = /^(\d{1,9})(?:[.,](\d{1,2}))?$/.exec(value);
  if (!match) return undefined;
  return Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
}
