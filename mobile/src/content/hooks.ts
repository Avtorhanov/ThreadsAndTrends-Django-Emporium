import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../api/errors";
import { type Article, type ArticleDetail, type Contact, contentService } from "./contentService";

function errorText(error: unknown): string {
  return error instanceof ApiError ? error.message : "Не удалось загрузить данные.";
}

type State<T> = { data: T | null; loading: boolean; error: string | null };

function useLoad<T>(load: () => Promise<T>, key: string) {
  const [state, setState] = useState<State<T>>({ data: null, loading: true, error: null });
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

/** Вкладка «Контакты»: каналы связи и статьи одним экраном. */
export function useContactsTab() {
  return useLoad<{ contacts: Contact[]; articles: Article[] }>(async () => {
    const [contacts, articles] = await Promise.all([
      contentService.contacts(),
      contentService.articles(),
    ]);
    return { contacts, articles };
  }, "contacts-tab");
}

export function useArticle(slug: string) {
  return useLoad<ArticleDetail>(() => contentService.article(slug), slug);
}
