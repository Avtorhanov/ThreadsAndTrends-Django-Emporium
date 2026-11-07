/** Типы размеров и таблица обуви — для пачки, нового товара и вариантов.
 *
 * Размер товара — строка; тип нигде не хранится (выбирается вручную). Обувь записывается
 * «RU · US», например «38 · 8 US». Таблица — та же, что на сайте: store/sizes.py
 * (менять синхронно). US — по длине стопы, как у Nike; RU — общепринятая сетка. */

export type ShoeRow = { ru: number; cm: string; women: string | null; men: string | null };

export const SHOE_CHART: ShoeRow[] = [
  { ru: 35, cm: "22,5", women: "5,5", men: null },
  { ru: 36, cm: "23", women: "6", men: null },
  { ru: 37, cm: "24", women: "7,5", men: null },
  { ru: 38, cm: "24,5", women: "8", men: "6,5" },
  { ru: 39, cm: "25", women: "8,5", men: "7" },
  { ru: 40, cm: "26", women: "10", men: "8" },
  { ru: 41, cm: "26,5", women: "10,5", men: "9" },
  { ru: 42, cm: "27", women: "11", men: "9,5" },
  { ru: 43, cm: "28", women: null, men: "10,5" },
  { ru: 44, cm: "28,5", women: null, men: "11" },
  { ru: 45, cm: "29", women: null, men: "12" },
  { ru: 46, cm: "30", women: null, men: "13" },
];

export type SizeType = {
  id: "clothes" | "women-shoes" | "men-shoes" | "kids";
  label: string;
  sizes: string[];
  /** Отмечены сразу при выборе типа. */
  defaults: string[];
  shoes: boolean;
};

function shoes(scale: "women" | "men"): string[] {
  return SHOE_CHART.flatMap((row) => (row[scale] ? [`${row.ru} · ${row[scale]} US`] : []));
}

const WOMEN = shoes("women");
const MEN = shoes("men");
// Рост ребёнка, см — шаг 6 (92 … 164).
const KIDS = Array.from({ length: 13 }, (_, i) => String(92 + i * 6));

export const SIZE_TYPES: SizeType[] = [
  { id: "clothes", label: "Одежда", sizes: ["XS", "S", "M", "L", "XL", "XXL"], defaults: ["S", "M", "L", "XL"], shoes: false },
  { id: "women-shoes", label: "Обувь жен.", sizes: WOMEN, defaults: WOMEN.filter((s) => /^(36|37|38|39|40) /.test(s)), shoes: true },
  { id: "men-shoes", label: "Обувь муж.", sizes: MEN, defaults: MEN.filter((s) => /^(40|41|42|43|44) /.test(s)), shoes: true },
  { id: "kids", label: "Детское", sizes: KIDS, defaults: ["110", "116", "122", "128", "134"], shoes: false },
];

/** Размеры обуви в формате «38 · 8 US» — для кнопки «Таблица размеров». */
export function hasShoeSizes(sizes: string[]): boolean {
  return sizes.some((size) => / US$/.test(size));
}
