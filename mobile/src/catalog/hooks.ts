import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../api/errors";
import {
  type CategoryNode,
  catalogService,
  type ProductCard,
  type ProductDetail,
  type ProductQuery,
} from "./catalogService";

function errorText(error: unknown): string {
  return error instanceof ApiError ? error.message : "Не удалось загрузить данные.";
}

type Resource<T> = { data: T | null; loading: boolean; error: string | null; reload: () => void };

function useResource<T>(load: () => Promise<T>, key: string): Resource<T> {
  const [state, setState] = useState<Omit<Resource<T>, "reload">>({
    data: null,
    loading: true,
    error: null,
  });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    load()
      .then((data) => !cancelled && setState({ data, loading: false, error: null }))
      .catch((error: unknown) => {
        if (!cancelled) setState((prev) => ({ ...prev, loading: false, error: errorText(error) }));
      });
    return () => {
      cancelled = true;
    };
    // Перезапуск определяют key и version; load пересоздаётся на каждый рендер.
  }, [key, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { ...state, reload };
}

export function useCategories() {
  return useResource<CategoryNode[]>(() => catalogService.categories(), "categories");
}

export function useProduct(slug: string) {
  return useResource<ProductDetail>(() => catalogService.product(slug), slug);
}

/** Лента товаров с фильтрами и подгрузкой страниц при прокрутке. */
export function useProductFeed(query: ProductQuery) {
  const [items, setItems] = useState<ProductCard[]>([]);
  const [count, setCount] = useState<number | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const page = useRef(0);
  const generation = useRef(0); // ответы для прежнего фильтра отбрасываются
  // Объект фильтров пересоздаётся на каждый рендер — перезагрузка только при изменении значений.
  const key = JSON.stringify(query);

  const loadPage = useCallback(
    async (reset: boolean) => {
      const current = ++generation.current;
      const nextPage = reset ? 1 : page.current + 1;
      setLoading(true);
      setError(null);
      try {
        const data = await catalogService.products({ ...(JSON.parse(key) as ProductQuery), page: nextPage });
        if (current !== generation.current) return;
        page.current = nextPage;
        setItems((prev) => (reset ? data.results : [...prev, ...data.results]));
        setCount(data.count);
        setHasMore(Boolean(data.next));
      } catch (err) {
        if (current === generation.current) setError(errorText(err));
      } finally {
        if (current === generation.current) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    },
    [key],
  );

  useEffect(() => {
    setItems([]);
    setCount(null);
    setHasMore(true);
    void loadPage(true);
  }, [loadPage]);

  const loadMore = useCallback(() => {
    if (!loading && hasMore && !error) void loadPage(false);
  }, [loading, hasMore, error, loadPage]);

  const refresh = useCallback(() => {
    setRefreshing(true);
    void loadPage(true);
  }, [loadPage]);

  return { items, count, loading, refreshing, error, hasMore, loadMore, refresh };
}
