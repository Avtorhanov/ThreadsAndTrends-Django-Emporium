import { type ComponentType, lazy } from "react";

/** Экран панели отдельным куском сборки: первый экран (вход, сводка) грузится без остальных.
 * Остальные куски подгружаются в простое после первой отрисовки (`prefetchPages`) — переход
 * между разделами не ждёт сети. */
const loaders: (() => Promise<unknown>)[] = [];

export function lazyPage<K extends string, M extends Record<K, ComponentType>>(load: () => Promise<M>, name: K) {
  loaders.push(load);
  return lazy(async () => ({ default: (await load())[name] }));
}

export function prefetchPages(): void {
  const run = () => {
    for (const load of loaders) void load().catch(() => undefined);
  };
  if ("requestIdleCallback" in window) window.requestIdleCallback(run, { timeout: 4000 });
  else setTimeout(run, 1500);
}
