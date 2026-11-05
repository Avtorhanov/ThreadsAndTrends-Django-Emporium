/**
 * Демо-режим панели на GitHub Pages (сборка с VITE_PREVIEW=1): сервера нет, admin-API отвечает
 * имитация в браузере — deploy/preview/assets/sim.js (одна «база» в localStorage на панель и
 * магазин превью). Изменения сохраняются и сразу видны в магазине; заказы покупателей из
 * магазина приходят сюда. Начальные данные — снимок API на демо-каталоге (preview-api.json).
 * В боевую сборку модуль не попадает (динамический импорт под флагом).
 *
 * Вход имитируется: логин и пароль администратора превью лежат в снимке (`_login`) и
 * сверяются в браузере — это не защита, на Pages только демо-данные.
 */

type SimResult = { status: number; body: unknown };
type Sim = {
  ready(): Promise<unknown>;
  reset(): Promise<unknown>;
  api(method: string, url: string, body?: unknown): Promise<SimResult>;
};

declare global {
  interface Window {
    DidiSim?: Sim;
  }
}

function loadScript(src: string, base: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.setAttribute("data-base", base);
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Не загрузился ${src}`));
    document.head.append(script);
  });
}

/** Новый товар или заказ открыт по прямой ссылке: Pages отдал 404, а 404 вернул сюда с ?route=. */
function restoreRoute(base: string) {
  const params = new URLSearchParams(window.location.search);
  const route = params.get("route");
  if (!route) return;
  window.history.replaceState(null, "", base + route.replace(/^\/+/, ""));
}

async function readBody(request: Request): Promise<unknown> {
  if (request.method === "GET" || request.method === "HEAD") return undefined;
  const type = request.headers.get("Content-Type") ?? "";
  if (type.includes("multipart/form-data")) return request.formData();
  const text = await request.text();
  if (!text) return {};
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return {};
  }
}

export async function installPreview(): Promise<void> {
  const base = import.meta.env.BASE_URL; // "/<репозиторий>/panel/"
  const site = base.replace(/panel\/?$/, ""); // "/<репозиторий>/"
  restoreRoute(base);
  await loadScript(`${site}static/preview/sim.js`, site.replace(/\/$/, ""));
  const sim = window.DidiSim;
  if (!sim) throw new Error("Имитация сервера не загрузилась");
  await sim.ready();
  const realFetch = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = input instanceof Request ? input : new Request(input, init);
    const url = new URL(request.url, window.location.href);
    if (!url.pathname.startsWith("/api/")) return realFetch(input, init);
    const result = await sim.api(request.method, url.pathname + url.search, await readBody(request));
    const empty = result.status === 204 || result.body === null || result.body === undefined;
    return new Response(empty ? null : JSON.stringify(result.body), {
      status: result.status,
      headers: { "Content-Type": "application/json" },
    });
  };
}
