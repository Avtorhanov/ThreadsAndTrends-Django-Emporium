import { useEffect, useState } from "react";

import { api } from "../api/client";

/**
 * Слово «shop» рядом с плашкой «DiDi» — настройка магазина (панель → «Внешний вид» → «Тема
 * магазина», `show_wordmark`). Читается из публичной темы: её видит любой сотрудник, даже без
 * доступа к разделу «Главная и тема». Одно значение на всю панель; «Тема магазина» после
 * сохранения обновляет его сразу.
 */
let current = true;
let loaded: Promise<void> | null = null;
const listeners = new Set<() => void>();

function publish(value: boolean) {
  current = value;
  listeners.forEach((listener) => listener());
}

function load(): Promise<void> {
  loaded ??= api
    .GET("/api/v1/content/theme/")
    .then(({ data }) => {
      if (data) publish(data.show_wordmark);
    })
    .catch(() => {
      // Нет сети — логотип как по умолчанию; при следующем открытии панели запросим снова.
      loaded = null;
    });
  return loaded;
}

export function setWordmark(value: boolean) {
  publish(value);
}

export function useWordmark(): boolean {
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
