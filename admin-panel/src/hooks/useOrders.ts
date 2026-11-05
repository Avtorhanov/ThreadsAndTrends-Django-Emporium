import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../api/errors";
import {
  type AdminOrderDetail,
  type AdminOrderPage,
  type OrderQuery,
  ordersService,
} from "../api/orders";

function errorText(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

type ListState = { data: AdminOrderPage | null; loading: boolean; error: string | null };

/** Страница заказов по фильтрам; устаревшие ответы (быстрый ввод в поиске) отбрасываются. */
export function useOrders(query: OrderQuery) {
  const [state, setState] = useState<ListState>({ data: null, loading: true, error: null });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    ordersService
      .list(query)
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setState((prev) => ({
          ...prev,
          loading: false,
          error: errorText(error, "Не удалось загрузить заказы."),
        }));
      });
    return () => {
      cancelled = true;
    };
    // query разложен на примитивы: новый объект с теми же значениями не вызывает запрос.
  }, [
    query.search,
    query.status,
    query.unfinished,
    query.payment,
    query.delivery,
    query.createdFrom,
    query.createdTo,
    query.customer,
    query.page,
    version,
  ]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { ...state, reload };
}

type DetailState = { data: AdminOrderDetail | null; loading: boolean; error: string | null };

export function useOrder(id: number | null) {
  const [state, setState] = useState<DetailState>({ data: null, loading: true, error: null });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (id === null) {
      setState({ data: null, loading: false, error: "Заказ не найден." });
      return;
    }
    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    ordersService
      .get(id)
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState((prev) => ({
            ...prev,
            loading: false,
            error: errorText(error, "Не удалось загрузить заказ."),
          }));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  const set = useCallback(
    (data: AdminOrderDetail) => setState({ data, loading: false, error: null }),
    [],
  );
  return { ...state, reload, set };
}
