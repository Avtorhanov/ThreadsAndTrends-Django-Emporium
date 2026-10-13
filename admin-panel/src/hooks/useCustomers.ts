import { useCallback, useEffect, useState } from "react";

import {
  type Customer,
  type CustomerPage,
  type CustomerQuery,
  customersService,
} from "../api/customers";
import { ApiError } from "../api/errors";

type State = { data: CustomerPage | null; loading: boolean; error: string | null };

/** Страница клиентов по фильтрам; устаревшие ответы (быстрый ввод в поиске) отбрасываются. */
export function useCustomers(query: CustomerQuery) {
  const [state, setState] = useState<State>({ data: null, loading: true, error: null });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    customersService
      .list(query)
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const message = error instanceof ApiError ? error.message : "Не удалось загрузить клиентов.";
        setState((prev) => ({ ...prev, loading: false, error: message }));
      });
    return () => {
      cancelled = true;
    };
    // query разложен на примитивы, чтобы новый объект с теми же значениями не вызывал запрос.
  }, [query.search, query.status, query.page, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);

  /** Подменяет строку после действия (блокировка и т.п.) без перезагрузки страницы. */
  const replace = useCallback((customer: Customer) => {
    setState((prev) =>
      prev.data
        ? {
            ...prev,
            data: {
              ...prev.data,
              results: prev.data.results.map((row) => (row.id === customer.id ? customer : row)),
            },
          }
        : prev,
    );
  }, []);

  return { ...state, reload, replace };
}
