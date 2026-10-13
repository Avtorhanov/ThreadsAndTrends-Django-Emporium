import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../api/errors";
import { type OrderDetail, type OrderSummary, orderService } from "./orderService";

function errorText(error: unknown): string {
  return error instanceof ApiError ? error.message : "Не удалось загрузить данные.";
}

/** «Мои заказы» с подгрузкой страниц. */
export function useOrderFeed() {
  const [items, setItems] = useState<OrderSummary[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const page = useRef(0);
  const generation = useRef(0); // ответ устаревшей загрузки отбрасывается

  const loadPage = useCallback(async (reset: boolean) => {
    const current = ++generation.current;
    const nextPage = reset ? 1 : page.current + 1;
    setLoading(true);
    setError(null);
    try {
      const data = await orderService.list(nextPage);
      if (current !== generation.current) return;
      page.current = nextPage;
      setItems((prev) => (reset ? data.results : [...prev, ...data.results]));
      setHasMore(Boolean(data.next));
    } catch (err) {
      if (current === generation.current) setError(errorText(err));
    } finally {
      if (current === generation.current) setLoading(false);
    }
  }, []);

  const refresh = useCallback(() => loadPage(true), [loadPage]);
  const loadMore = useCallback(() => {
    if (!loading && hasMore && !error) void loadPage(false);
  }, [loading, hasMore, error, loadPage]);

  return { items, loading, error, hasMore, refresh, loadMore };
}

/** Один заказ; setOrder — обновить после отмены без повторного запроса. */
export function useOrder(number: string) {
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setOrder(await orderService.get(number));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  }, [number]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { order, setOrder, loading, error, reload };
}
