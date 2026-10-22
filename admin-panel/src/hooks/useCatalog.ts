import { useCallback, useEffect, useState } from "react";

import {
  type Category,
  categoriesService,
  type Product,
  type ProductPage,
  type ProductQuery,
  productsService,
} from "../api/catalog";
import { ApiError } from "../api/errors";

type State<T> = { data: T | null; loading: boolean; error: string | null };

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

/** Загрузка по ключу; ответ на устаревший ключ (быстрый ввод в фильтрах) отбрасывается. */
export function useLoader<T>(load: () => Promise<T>, key: string, fallbackError: string) {
  const [state, setState] = useState<State<T>>({ data: null, loading: true, error: null });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    load()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState((prev) => ({ ...prev, loading: false, error: errorMessage(error, fallbackError) }));
        }
      });
    return () => {
      cancelled = true;
    };
    // load пересоздаётся на каждый рендер; перезапуск определяют key и version.
  }, [key, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  const set = useCallback((data: T) => setState({ data, loading: false, error: null }), []);
  return { ...state, reload, set };
}

export function useCategories() {
  return useLoader(() => categoriesService.list(), "categories", "Не удалось загрузить категории.");
}

export function useProducts(query: ProductQuery) {
  const key = JSON.stringify(query);
  return useLoader<ProductPage>(
    () => productsService.list(query),
    key,
    "Не удалось загрузить товары.",
  );
}

export function useProduct(id: number | null) {
  return useLoader<Product | null>(
    () => (id === null ? Promise.resolve(null) : productsService.get(id)),
    String(id),
    "Не удалось загрузить товар.",
  );
}

/** Дерево для выпадающих списков: корни и их подкатегории по порядку. */
export function sortCategoryTree(categories: Category[]): Array<Category & { depth: number }> {
  const children = new Map<number, Category[]>();
  const roots: Category[] = [];
  for (const category of categories) {
    const parent = category.parent ?? null;
    if (parent === null) roots.push(category);
    else children.set(parent, [...(children.get(parent) ?? []), category]);
  }
  return roots.flatMap((root) => [
    { ...root, depth: 0 },
    ...(children.get(root.id) ?? []).map((child) => ({ ...child, depth: 1 })),
  ]);
}

/** Товары можно класть только в категории без подкатегорий. */
export function isLeaf(category: Category): boolean {
  return category.children_count === 0;
}
