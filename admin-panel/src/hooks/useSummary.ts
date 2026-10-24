import { useEffect, useState } from "react";

import { ApiError } from "../api/errors";
import { type AdminSummary, summaryService } from "../api/summary";

type State = { data: AdminSummary | null; loading: boolean; error: string | null };

export function useSummary() {
  const [state, setState] = useState<State>({ data: null, loading: true, error: null });

  useEffect(() => {
    let cancelled = false;
    summaryService
      .get()
      .then((data) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setState({
          data: null,
          loading: false,
          error: error instanceof ApiError ? error.message : "Не удалось загрузить сводку.",
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
