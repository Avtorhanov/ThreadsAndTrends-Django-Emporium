import { useEffect, useState } from "react";

import { api } from "../api/client";

/**
 * Слово рядом с плашкой «DiDi» (по умолчанию «shop») — настройка магазина (панель → «Внешний вид»
 * → «Тема магазина», `show_wordmark` + `wordmark`). Читается из публичной темы: её видит любой
 * сотрудник, даже без доступа к разделу «Главная и тема». Одно значение на всю панель; «Тема
 * магазина» после сохранения обновляет его сразу. null — слово выключено или пустое.
 */
let current: string | null = "shop";
let loaded: Promise<void> | null = null;
const listeners = new Set<() => void>();

function publish(value: string | null) {
  current = value;
  listeners.forEach((listener) => listener());
}

function load(): Promise<void> {
  loaded ??= api
    .GET("/api/v1/content/theme/")
    .then(({ data }) => {
      if (data) publish(data.show_wordmark && data.wordmark ? data.wordmark : null);
    })
    .catch(() => {
      // Нет сети — логотип как по умолчанию; при следующем открытии панели запросим снова.
      loaded = null;
    });
  return loaded;
}

export function setWordmark(show: boolean, word: string) {
  publish(show && word ? word : null);
}

export function useWordmark(): string | null {
  const [value, setValue] = useState(current);
  useEffect(() => {
    const listener = () => setValue(current);
    listeners.add(listener);
    void load();
    setValue(current);
    return () => {
      listeners.delete(listener);
    };
  }, []);
  return value;
}
