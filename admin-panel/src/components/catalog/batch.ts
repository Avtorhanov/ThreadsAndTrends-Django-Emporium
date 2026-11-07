import type { Category, ProductRow } from "../../api/catalog";
import { isLeaf, sortCategoryTree } from "../../hooks/useCatalog";

export const MAX_BATCH_PHOTOS = 60;

/** Цветовая метка категории в пачке: по порядку категорий, по кругу (8 тонов в styles.css). */
const TONES = 8;

export type BatchCategory = Category & { depth: number; tone: number };

/** Конечные категории (в них можно класть товары) с тоном метки. */
export function batchCategories(categories: Category[]): BatchCategory[] {
  return sortCategoryTree(categories)
    .filter(isLeaf)
    .map((category, index) => ({ ...category, tone: index % TONES }));
}

/** Подпись категории: подкатегория — с родителем, чтобы не путать одинаковые имена. */
export function categoryLabel(category: BatchCategory, all: Category[]): string {
  if (!category.depth) return category.name;
  const parent = all.find((item) => item.id === category.parent);
  return parent ? `${parent.name} · ${category.name}` : category.name;
}

/** Черновик готов к публикации, когда у него есть цена. */
export function isReady(product: ProductRow): boolean {
  return product.price_kopecks !== null;
}

export function plural(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  const word =
    mod10 === 1 && mod100 !== 11
      ? one
      : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)
        ? few
        : many;
  return `${n} ${word}`;
}

export const products = (n: number) => plural(n, "товар", "товара", "товаров");
export const drafts = (n: number) => plural(n, "черновик", "черновика", "черновиков");
